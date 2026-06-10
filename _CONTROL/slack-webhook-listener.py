#!/usr/bin/env python3
"""
BrainVault Slack Webhook Listener
Läuft permanent als LaunchAgent (KeepAlive).
Empfängt Slack Event Subscriptions, validiert die Signatur
und triggert dispatcher.sh im Hintergrund.
"""
import hashlib
import hmac
import http.server
import json
import logging
import os
import signal
import subprocess
import time

PORT = 9877
HOME               = os.environ.get("HOME", "")
DISPATCHER_CHANNEL = os.environ.get("DISPATCHER_CHANNEL", "")
BLOG_CHANNEL       = os.environ.get("BLOG_CHANNEL", "")
MAILPILOT_CHANNEL  = os.environ.get("MAILPILOT_CHANNEL", "")
MAILPILOT_DIR      = os.environ.get("MAILPILOT_DIR", "")
LOCK_FILE_DISPATCHER = os.path.join(HOME, "BrainVault/_CONTROL/DISPATCHER-RUNNING.lock")
LOCK_FILE_BLOG       = os.path.join(HOME, "BrainVault/_CONTROL/DISPATCHER-BLOG-RUNNING.lock")
LOG_FILE           = os.path.join(HOME, "BrainVault/_CONTROL/slack-listener.log")

_DISPATCHER_SH = ["/bin/bash", os.path.join(HOME, "BrainVault/_CONTROL/dispatcher.sh")]


def build_channel_routes() -> dict:
    routes = {}
    if DISPATCHER_CHANNEL:
        routes[DISPATCHER_CHANNEL] = ("dispatcher", _DISPATCHER_SH)
    if BLOG_CHANNEL:
        routes[BLOG_CHANNEL] = ("dispatcher-blog", _DISPATCHER_SH + ["--blog"])
    if MAILPILOT_CHANNEL and MAILPILOT_DIR:
        venv_python = os.path.join(MAILPILOT_DIR, ".venv/bin/python")
        script      = os.path.join(MAILPILOT_DIR, "email_assistant.py")
        routes[MAILPILOT_CHANNEL] = ("mailpilot", [venv_python, script, "--once"])
    return routes

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def verify_slack_signature(body: bytes, headers) -> bool:
    secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not secret:
        logging.warning("SLACK_SIGNING_SECRET nicht gesetzt — Signaturprüfung übersprungen")
        return True
    ts  = headers.get("X-Slack-Request-Timestamp", "")
    sig = headers.get("X-Slack-Signature", "")
    if not ts or not sig:
        return False
    try:
        if abs(time.time() - float(ts)) > 300:
            logging.warning("Replay-Angriff: Timestamp zu alt")
            return False
    except ValueError:
        return False
    base     = f"v0:{ts}:{body.decode('utf-8')}"
    expected = "v0=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def is_lock_active(lock_file: str) -> bool:
    if not os.path.exists(lock_file):
        return False
    try:
        age = time.time() - os.path.getmtime(lock_file)
        if age > 600:
            os.remove(lock_file)
            return False
        return True
    except OSError:
        return False


def trigger(name: str, cmd: list[str]):
    if name == "dispatcher" and is_lock_active(LOCK_FILE_DISPATCHER):
        logging.info("Dispatcher läuft bereits — Skip")
        return
    if name == "dispatcher-blog" and is_lock_active(LOCK_FILE_BLOG):
        logging.info("Dispatcher-Blog läuft bereits — Skip")
        return
    logging.info(f"Starte {name} im Hintergrund")
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class SlackHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path not in ("/slack/events", "/"):
            self._respond(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        if not verify_slack_signature(body, self.headers):
            logging.warning("Ungültige Slack-Signatur — abgelehnt")
            self._respond(401)
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400)
            return

        # Slack URL-Verifikation beim App-Setup
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge", "")
            self._respond(200, json.dumps({"challenge": challenge}).encode(), "application/json")
            logging.info("URL-Verifikation beantwortet")
            return

        # Sofort 200 antworten (Slack erwartet < 3 s)
        self._respond(200)

        event = payload.get("event", {})
        if event.get("type") == "message" and not event.get("bot_id"):
            channel = event.get("channel", "")
            routes  = build_channel_routes()
            route   = routes.get(channel)
            if route:
                trigger(*route)
            else:
                logging.info(f"Unbekannter Kanal {channel} — ignoriert")

    def _respond(self, status: int, body: bytes = b"", content_type: str = "text/plain"):
        self.send_response(status)
        if body:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        logging.info(fmt % args)


class BrainVaultHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    def _shutdown(signum, frame):
        logging.info(f"Signal {signum} empfangen — Listener beendet sich.")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logging.info(f"Slack Webhook Listener gestartet auf Port {PORT}")
    try:
        server = BrainVaultHTTPServer(("127.0.0.1", PORT), SlackHandler)
        server.serve_forever()
    except Exception as e:
        logging.error(f"Listener abgestürzt: {e}", exc_info=True)
        raise
