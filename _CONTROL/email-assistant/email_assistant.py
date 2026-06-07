#!/usr/bin/env python3
"""Gmail-to-Slack approval assistant for BrainVault."""

from __future__ import annotations

import argparse
import base64
import fcntl
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from contextlib import contextmanager
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"
LOG_PATH = ROOT / "email-assistant.log"
LOCK_PATH = ROOT / "email-assistant.lock"

INSTRUCTION_RE = re.compile(
    r"###\s*ANWEISUNG\s+AN\s+ASSISTENZ\s*(.*?)\s*###\s*ENDE\s+ANWEISUNG",
    re.IGNORECASE | re.DOTALL,
)
FORWARD_MARKER_RE = re.compile(
    r"(?im)^[-\s]*(?:forwarded message|weitergeleitete nachricht|urspruengliche nachricht|original message)[-\s]*$"
)
HEADER_PATTERNS = {
    "from": re.compile(r"(?im)^\s*(?:from|von):\s*(.+?)\s*$"),
    "subject": re.compile(r"(?im)^\s*(?:subject|betreff):\s*(.+?)\s*$"),
    "date": re.compile(r"(?im)^\s*(?:date|datum|sent|gesendet):\s*(.+?)\s*$"),
    "to": re.compile(r"(?im)^\s*(?:to|an):\s*(.+?)\s*$"),
}


@dataclass
class ForwardedMail:
    gmail_id: str
    gmail_thread_id: str | None
    forward_from: str
    forward_subject: str
    instructions: str
    has_instruction_block: bool
    original_from: str
    original_to: str
    original_subject: str
    original_date: str
    original_body: str
    instruction_source: str = "explicit"


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {message}\n")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


@contextmanager
def single_instance() -> Any:
    lock_file = LOCK_PATH.open("w", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("Another Email Assistant run is already active. Skipping this cycle.")
            yield False
            return
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        yield True
    finally:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        finally:
            lock_file.close()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Missing config: {CONFIG_PATH}. Copy config.example.json first.")
    config = load_json(CONFIG_PATH, {})
    required = ["slack_channel_id", "slack_allowed_user_id", "slack_bot_token_env", "claude_command"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise SystemExit(f"Missing config keys: {', '.join(missing)}")
    return config


def load_env_from_zshrc(key: str) -> str | None:
    zshrc = Path.home() / ".zshrc"
    if not zshrc.exists():
        return None
    pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}=(.+?)\s*$")
    for line in zshrc.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        return value
    return None


def get_slack_token(config: dict[str, Any]) -> str:
    key = config["slack_bot_token_env"]
    token = os.environ.get(key) or load_env_from_zshrc(key)
    if not token:
        raise SystemExit(f"Missing Slack token. Set {key} in the environment or ~/.zshrc.")
    return token


def slack_api(token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://slack.com/api/{method}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload else "GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Slack API request failed: {method}: {exc}") from exc
    if not result.get("ok"):
        raise RuntimeError(f"Slack API error in {method}: {result}")
    return result


def slack_replies(token: str, channel: str, thread_ts: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"channel": channel, "ts": thread_ts, "limit": 100})
    url = f"https://slack.com/api/conversations.replies?{query}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Slack API error in conversations.replies: {result}")
    return result.get("messages", [])


def slack_reaction_command(message: dict[str, Any], allowed_user: str) -> str | None:
    reaction_commands = {
        "white_check_mark": "senden",
        "heavy_check_mark": "senden",
        "outbox_tray": "senden",
        "memo": "entwurf",
        "pencil": "entwurf",
        "x": "ablehnen",
        "no_entry_sign": "ablehnen",
    }
    for reaction in message.get("reactions", []):
        name = reaction.get("name")
        users = reaction.get("users", [])
        if name in reaction_commands and allowed_user in users:
            return reaction_commands[name]
    return None


def slack_post(token: str, channel: str, text: str, thread_ts: str | None = None) -> str:
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    result = slack_api(token, "chat.postMessage", payload)
    return result["ts"]


def ensure_gmail_credentials(open_browser: bool = True, auth_port: int = 0) -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    scopes = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
    ]
    creds = None
    token_path = ROOT / "token.json"
    credentials_path = ROOT / "credentials.json"

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not credentials_path.exists():
            raise SystemExit(f"Missing Gmail OAuth credentials: {credentials_path}")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
        creds = flow.run_local_server(port=auth_port, open_browser=open_browser)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def gmail_service() -> Any:
    from googleapiclient.discovery import build

    creds = ensure_gmail_credentials()
    return build("gmail", "v1", credentials=creds)


def gmail_list_messages(service: Any, query: str, max_results: int = 10) -> list[dict[str, Any]]:
    result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return result.get("messages", [])


def gmail_raw_message(service: Any, message_id: str) -> tuple[Message, dict[str, Any]]:
    meta = service.users().messages().get(userId="me", id=message_id, format="raw").execute()
    raw = base64.urlsafe_b64decode(meta["raw"].encode("utf-8"))
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    return msg, meta


def gmail_mark_read(service: Any, message_id: str) -> None:
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


def gmail_send(service: Any, to_addr: str, subject: str, body: str) -> dict[str, Any]:
    message = EmailMessage()
    message["To"] = to_addr
    message["Subject"] = ensure_reply_subject(subject)
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def gmail_create_draft(service: Any, to_addr: str, subject: str, body: str) -> dict[str, Any]:
    message = EmailMessage()
    message["To"] = to_addr
    message["Subject"] = ensure_reply_subject(subject)
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()


def extract_text(msg: Message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = (part.get_content_disposition() or "").lower()
            if disposition == "attachment":
                continue
            content_type = part.get_content_type()
            try:
                content = part.get_content()
            except Exception:
                continue
            if content_type == "text/plain":
                plain_parts.append(str(content))
            elif content_type == "text/html":
                html_parts.append(str(content))
    else:
        try:
            content = str(msg.get_content())
        except Exception:
            content = ""
        if msg.get_content_type() == "text/html":
            html_parts.append(content)
        else:
            plain_parts.append(content)

    if plain_parts:
        return "\n".join(plain_parts).strip()
    return html_to_text("\n".join(html_parts)).strip()


def first_rfc822_attachment(msg: Message) -> Message | None:
    if not msg.is_multipart():
        return None
    for part in msg.walk():
        if part.get_content_type() != "message/rfc822":
            continue
        payload = part.get_payload()
        if isinstance(payload, list) and payload:
            return payload[0]
    return None


def html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(br|/p|/div|/li)\b[^>]*>", "\n", value)
    value = re.sub(r"(?is)<style\b.*?</style>|<script\b.*?</script>", "", value)
    value = re.sub(r"(?is)<[^>]+>", "", value)
    return html.unescape(value)


def parse_forwarded_mail(message_id: str, msg: Message, meta: dict[str, Any], config: dict[str, Any]) -> ForwardedMail:
    rfc822 = first_rfc822_attachment(msg)
    text = extract_text(msg)
    instruction_match = INSTRUCTION_RE.search(text)
    has_instruction_block = instruction_match is not None
    public_text = INSTRUCTION_RE.sub("", text).strip()
    if instruction_match:
        instructions = instruction_match.group(1).strip()
        instruction_source = "explicit"
    else:
        implicit = implicit_instruction_text(public_text)
        if implicit:
            instructions = implicit
            instruction_source = "implicit"
        else:
            instructions = default_missing_instruction(config)
            instruction_source = "missing"

    forward_from = str(msg.get("From", ""))
    forward_subject = str(msg.get("Subject", ""))

    if rfc822:
        original_body = extract_text(rfc822)
        original_from = str(rfc822.get("From", ""))
        original_to = str(rfc822.get("To", ""))
        original_subject = str(rfc822.get("Subject", forward_subject))
        original_date = str(rfc822.get("Date", ""))
    else:
        forwarded_chunk = forwarded_body_chunk(public_text)
        original_from = header_value("from", forwarded_chunk)
        original_to = header_value("to", forwarded_chunk)
        original_subject = header_value("subject", forwarded_chunk) or strip_forward_prefix(forward_subject)
        original_date = header_value("date", forwarded_chunk)
        original_body = body_after_forwarded_headers(forwarded_chunk) or forwarded_chunk

    return ForwardedMail(
        gmail_id=message_id,
        gmail_thread_id=meta.get("threadId"),
        forward_from=forward_from,
        forward_subject=forward_subject,
        instructions=instructions,
        has_instruction_block=has_instruction_block,
        original_from=original_from.strip(),
        original_to=original_to.strip(),
        original_subject=original_subject.strip(),
        original_date=original_date.strip(),
        original_body=original_body.strip(),
        instruction_source=instruction_source,
    )


def default_missing_instruction(config: dict[str, Any]) -> str:
    return (
        f"Kein expliziter Anweisungsblock gefunden. Erstelle nur einen vorsichtigen Entwurf. "
        f"Standardstil: {config.get('style_profile', '')}. Modus: {config.get('default_mode', 'Freigabe in Slack')}."
    )


def implicit_instruction_text(text: str) -> str:
    if not text.strip():
        return ""
    match = FORWARD_MARKER_RE.search(text)
    if match:
        return text[: match.start()].strip()
    # RFC822-forward clients often put the original mail in an attachment and
    # leave only Florian's instruction text in the wrapper body.
    if not any(pattern.search(text) for pattern in HEADER_PATTERNS.values()):
        return text.strip()
    return ""


def forwarded_body_chunk(text: str) -> str:
    match = FORWARD_MARKER_RE.search(text)
    if match:
        return text[match.end() :].strip()
    return text.strip()


def header_value(name: str, text: str) -> str:
    pattern = HEADER_PATTERNS[name]
    matches = pattern.findall(text)
    return matches[0].strip() if matches else ""


def body_after_forwarded_headers(text: str) -> str:
    lines = text.splitlines()
    last_header_idx = -1
    for idx, line in enumerate(lines[:80]):
        if any(pattern.match(line) for pattern in HEADER_PATTERNS.values()):
            last_header_idx = idx
    if last_header_idx >= 0:
        return "\n".join(lines[last_header_idx + 1 :]).strip()
    return text.strip()


def extract_email_address(value: str) -> str:
    addresses = getaddresses([value])
    for _name, addr in addresses:
        if addr and "@" in addr:
            return addr
    _name, addr = parseaddr(value)
    return addr if "@" in addr else ""


def is_allowed_forwarder(config: dict[str, Any], forward_from: str) -> bool:
    allowed = [addr.lower() for addr in config.get("allowed_forwarders", []) if addr]
    if not allowed:
        return True
    sender = extract_email_address(forward_from).lower()
    return sender in allowed


def strip_forward_prefix(subject: str) -> str:
    subject = subject.strip()
    while True:
        new = re.sub(r"(?i)^\s*(fwd?|wg|weitergeleitet|aw|re)\s*:\s*", "", subject).strip()
        if new == subject:
            return subject
        subject = new


def ensure_reply_subject(subject: str) -> str:
    subject = strip_forward_prefix(subject or "Antwort")
    if re.match(r"(?i)^\s*(re|aw)\s*:", subject):
        return subject
    return f"Re: {subject}"


def claude_draft(config: dict[str, Any], mail: ForwardedMail, previous_draft: str | None = None, refinement: str | None = None) -> str:
    command = config["claude_command"]
    signature = config.get("assistant_signature", "KI-Assistenz von Florian Million")
    style_profile = config.get("style_profile", "")
    recipient = extract_email_address(mail.original_from) or mail.original_from or "UNBEKANNT"

    prompt = f"""
Du bist die KI-Assistenz von Florian Million und erstellst E-Mail-Antworten.

Harte Regeln:
- Gib nur den E-Mail-Body aus, keinen Betreff und keine Erklärung.
- Zitiere oder erwähne die privaten Anweisungen niemals.
- Übernimm keine internen Steuerwörter wie "Modus", "Ziel" oder "Stil" in die Antwort.
- Erfinde keine Zusagen, Termine, Preise, Fakten oder Entscheidungen.
- Antworte in der Sprache der Originalmail, außer Florian verlangt explizit etwas anderes.
- Beende jede Antwort exakt mit dieser Signatur:

{signature}

Standardstil:
{style_profile}

Private Anweisungen von Florian:
{mail.instructions}

Originalmail:
Von: {mail.original_from}
An: {mail.original_to}
Datum: {mail.original_date}
Betreff: {mail.original_subject}
Empfaenger der Antwort: {recipient}

{mail.original_body}
""".strip()

    if previous_draft and refinement:
        prompt += f"""

Bisheriger Entwurf:
{previous_draft}

Neue Verfeinerung von Florian:
{refinement}

Erstelle eine neue Version. Gib wieder nur den E-Mail-Body aus.
""".rstrip()

    result = subprocess.run(
        [command, "--print", prompt],
        cwd=config.get("vault_path") or str(ROOT.parent.parent),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude failed: {result.stderr.strip() or result.stdout.strip()}")
    cleaned = sanitize_draft(result.stdout.strip(), mail.instructions)
    return ensure_signature(cleaned, signature)


def sanitize_draft(draft: str, instructions: str) -> str:
    draft = INSTRUCTION_RE.sub("", draft).strip()
    leaked_lines = {line.strip() for line in instructions.splitlines() if line.strip()}
    safe_lines = []
    for line in draft.splitlines():
        stripped = line.strip()
        if stripped in leaked_lines:
            continue
        if re.match(r"(?i)^(ziel|stil|modus|aufgabe|wichtig)\s*:", stripped):
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines).strip()


def ensure_signature(draft: str, signature: str) -> str:
    if signature.strip() in draft:
        return draft.strip()
    return f"{draft.rstrip()}\n\n{signature.strip()}".strip()


def post_new_mail_to_slack(token: str, config: dict[str, Any], mail: ForwardedMail, draft: str) -> str:
    recipient = extract_email_address(mail.original_from)
    status = "Freigabe benötigt"
    if mail.instruction_source == "implicit":
        status = "Implizite Anweisung erkannt"
    elif mail.instruction_source == "missing":
        status = "Anweisungsblock fehlt, vorsichtiger Entwurf"
    if not recipient:
        status = "Empfänger unklar, bitte im Thread klären"

    text = (
        f":email: Neue Antwort vorbereitet\n"
        f"*Status:* {status}\n"
        f"*Empfänger:* {recipient or mail.original_from or 'unklar'}\n"
        f"*Betreff:* {ensure_reply_subject(mail.original_subject)}\n\n"
        f"*Vorschlag:*\n```{draft}```\n\n"
        f"Reagiere mit :white_check_mark: zum Senden, :memo: für Gmail-Entwurf, :x: zum Ablehnen. "
        f"Für Verfeinerungen antworte im Thread."
    )
    return slack_post(token, config["slack_channel_id"], text)


def is_blocked_send(config: dict[str, Any], mail: ForwardedMail, draft: str) -> str | None:
    haystack = f"{mail.instructions}\n{mail.original_subject}\n{mail.original_body}\n{draft}".lower()
    for keyword in config.get("blocked_send_keywords", []):
        if keyword.lower() in haystack:
            return keyword
    return None


def process_new_gmail(service: Any, token: str, config: dict[str, Any], state: dict[str, Any]) -> None:
    processed = state.setdefault("messages", {})
    query = config.get("gmail_query", "in:inbox is:unread -from:me")
    for item in gmail_list_messages(service, query):
        message_id = item["id"]
        if message_id in processed:
            continue
        try:
            msg, meta = gmail_raw_message(service, message_id)
            mail = parse_forwarded_mail(message_id, msg, meta, config)
            if not is_allowed_forwarder(config, mail.forward_from):
                sender = extract_email_address(mail.forward_from) or mail.forward_from or "unknown"
                processed[message_id] = {
                    "status": "skipped_unauthorized",
                    "sender": sender,
                    "subject": mail.forward_subject,
                    "created_at": time.time(),
                }
                if config.get("mark_unauthorized_read", True):
                    gmail_mark_read(service, message_id)
                log(f"Skipped unauthorized Gmail message {message_id} from {sender}.")
                continue
            draft = claude_draft(config, mail)
            slack_ts = post_new_mail_to_slack(token, config, mail, draft)
            processed[message_id] = {
                "status": "pending",
                "slack_ts": slack_ts,
                "last_reply_ts": slack_ts,
                "draft": draft,
                "recipient": extract_email_address(mail.original_from),
                "subject": mail.original_subject,
                "mail": mail.__dict__,
            }
            gmail_mark_read(service, message_id)
            log(f"Posted Gmail message {message_id} to Slack thread {slack_ts}.")
        except Exception as exc:
            processed[message_id] = {"status": "error", "error": str(exc), "created_at": time.time()}
            log(f"Error processing Gmail message {message_id}: {exc}")


def process_slack_approvals(service: Any, token: str, config: dict[str, Any], state: dict[str, Any]) -> None:
    allowed_user = config["slack_allowed_user_id"]
    channel = config["slack_channel_id"]
    for message_id, record in list(state.get("messages", {}).items()):
        if record.get("status") != "pending":
            continue
        thread_ts = record.get("slack_ts")
        if not thread_ts:
            continue
        messages = slack_replies(token, channel, thread_ts)
        if messages:
            command = slack_reaction_command(messages[0], allowed_user)
            if command:
                record["last_reply_ts"] = max(record.get("last_reply_ts") or thread_ts, thread_ts)
                handle_slack_reply(service, token, config, message_id, record, command, thread_ts)
                continue
        last_seen = float(record.get("last_reply_ts") or thread_ts)
        user_replies = [
            msg
            for msg in messages
            if msg.get("user") == allowed_user
            and not msg.get("bot_id")
            and float(msg.get("ts", "0")) > last_seen
        ]
        for reply in sorted(user_replies, key=lambda msg: float(msg["ts"])):
            text = normalize_slack_text(reply.get("text", ""))
            record["last_reply_ts"] = reply["ts"]
            handle_slack_reply(service, token, config, message_id, record, text, thread_ts)


def normalize_slack_text(text: str) -> str:
    text = re.sub(r"<mailto:([^|>]+)(?:\|[^>]+)?>", r"\1", text)
    return html.unescape(text).strip()


def handle_slack_reply(
    service: Any,
    token: str,
    config: dict[str, Any],
    message_id: str,
    record: dict[str, Any],
    text: str,
    thread_ts: str,
) -> None:
    command = text.lower().strip()
    mail = ForwardedMail(**record["mail"])
    recipient = record.get("recipient") or extract_email_address(mail.original_from)
    subject = record.get("subject") or mail.original_subject
    draft = record.get("draft", "")

    if command in {"senden", "send"}:
        if not recipient:
            slack_post(token, config["slack_channel_id"], "Ich kann noch nicht senden: Der Original-Empfänger ist unklar.", thread_ts)
            return
        blocked = is_blocked_send(config, mail, draft)
        if blocked:
            slack_post(
                token,
                config["slack_channel_id"],
                f"Senden blockiert wegen sensiblem Stichwort `{blocked}`. Antworte mit einer Verfeinerung oder nutze `entwurf`.",
                thread_ts,
            )
            return
        gmail_send(service, recipient, subject, draft)
        record["status"] = "sent"
        record["sent_at"] = time.time()
        slack_post(token, config["slack_channel_id"], f"Gesendet an `{recipient}`.", thread_ts)
        log(f"Sent reply for Gmail message {message_id} to {recipient}.")
        return

    if command in {"entwurf", "draft"}:
        if not recipient:
            slack_post(token, config["slack_channel_id"], "Ich kann keinen Gmail-Entwurf erstellen: Der Original-Empfänger ist unklar.", thread_ts)
            return
        result = gmail_create_draft(service, recipient, subject, draft)
        record["status"] = "drafted"
        record["gmail_draft_id"] = result.get("id")
        record["drafted_at"] = time.time()
        slack_post(token, config["slack_channel_id"], f"Gmail-Entwurf erstellt für `{recipient}`.", thread_ts)
        log(f"Created Gmail draft for message {message_id}.")
        return

    if command in {"ablehnen", "reject", "verwerfen"}:
        record["status"] = "rejected"
        record["rejected_at"] = time.time()
        slack_post(token, config["slack_channel_id"], "Verworfen. Ich sende nichts.", thread_ts)
        log(f"Rejected Gmail message {message_id}.")
        return

    if text:
        new_draft = claude_draft(config, mail, previous_draft=draft, refinement=text)
        record["draft"] = new_draft
        slack_post(
            token,
            config["slack_channel_id"],
            f"Neue Version:\n```{new_draft}```\n\nReagiere mit :white_check_mark: zum Senden, :memo: für Gmail-Entwurf, :x: zum Ablehnen. Für weitere Änderungen antworte im Thread.",
            thread_ts,
        )
        log(f"Refined draft for Gmail message {message_id}.")


def run_once() -> None:
    with single_instance() as acquired:
        if not acquired:
            return
        config = load_config()
        state = load_json(STATE_PATH, {"messages": {}})
        token = get_slack_token(config)
        service = gmail_service()

        process_new_gmail(service, token, config, state)
        process_slack_approvals(service, token, config, state)
        save_json(STATE_PATH, state)


def main() -> None:
    parser = argparse.ArgumentParser(description="BrainVault Gmail-to-Slack email assistant")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle")
    parser.add_argument("--auth-only", action="store_true", help="Only authorize Gmail and write token.json")
    parser.add_argument("--no-browser", action="store_true", help="Print the OAuth URL instead of opening a browser")
    parser.add_argument("--auth-port", type=int, default=0, help="Local OAuth callback port, useful with SSH tunnels")
    args = parser.parse_args()

    if args.auth_only:
        ensure_gmail_credentials(open_browser=not args.no_browser, auth_port=args.auth_port)
        print(f"Gmail OAuth token written to {ROOT / 'token.json'}")
        return

    if args.once:
        run_once()
        return

    while True:
        try:
            run_once()
        except Exception as exc:
            log(f"Run failed: {exc}")
            print(f"Run failed: {exc}", file=sys.stderr)
        time.sleep(120)


if __name__ == "__main__":
    main()
