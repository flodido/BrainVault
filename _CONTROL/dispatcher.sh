#!/bin/bash
# BrainVault Dispatcher
# Läuft alle 5 Minuten via LaunchAgent.
# Kill switch: "!stop" in #dispatcher → pausiert. "!start" → fortsetzen.

VAULT="$HOME/BrainVault"
CONTROL="$VAULT/_CONTROL"
STOP_FILE="$CONTROL/DISPATCHER-STOP"
LAST_SEEN_FILE="$CONTROL/DISPATCHER-LAST-SEEN-MAIN-TS"
CLAUDE="$HOME/.local/bin/claude"
CHANNEL="C0B9L30KVR6"
USER_ID="U0B8VCCEB9A"
LOG="$CONTROL/DISPATCHER-RUN.log"

# Token aus ~/.zshrc laden (nicht im Repo gespeichert)
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null
TOKEN="${SLACK_BOT_TOKEN:?Fehler: SLACK_BOT_TOKEN nicht gesetzt. Bitte in ~/.zshrc eintragen.}"

cd "$VAULT" || exit 1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

slack_post() {
    curl -s -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"channel\":\"$CHANNEL\",\"text\":\"$1\"}" \
        "https://slack.com/api/chat.postMessage" > /dev/null
}

# Letzte Nachrichten holen (nur Text-Nachrichten vom User)
RECENT=$(curl -s \
    -H "Authorization: Bearer $TOKEN" \
    "https://slack.com/api/conversations.history?channel=$CHANNEL&limit=10")

# Kill-Switch: !stop prüfen
if echo "$RECENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msgs = [m for m in d.get('messages', []) if m.get('user') == '$USER_ID' and '!stop' in m.get('text', '')]
sys.exit(0 if msgs else 1)
" 2>/dev/null; then
    touch "$STOP_FILE"
    slack_post "⏸ Dispatcher pausiert. Sende \`!start\` um ihn fortzusetzen."
    log "STOP-Befehl empfangen. Dispatcher pausiert."
    exit 0
fi

# Kill-Switch: !start prüfen
if echo "$RECENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msgs = [m for m in d.get('messages', []) if m.get('user') == '$USER_ID' and '!start' in m.get('text', '')]
sys.exit(0 if msgs else 1)
" 2>/dev/null; then
    rm -f "$STOP_FILE"
    slack_post "▶️ Dispatcher läuft wieder."
    log "START-Befehl empfangen. Dispatcher fortgesetzt."
fi

# Stop-Datei prüfen
if [ -f "$STOP_FILE" ]; then
    log "Dispatcher pausiert (STOP-Datei vorhanden). Überspringe Runde."
    exit 0
fi

# Nur Claude starten, wenn in der bereits geholten History eine neue offene
# Hauptkanal-Nachricht von Florian vorhanden ist. Die lokale Last-Seen-Datei
# verhindert Wiederholungen, falls Slack keine Reaktionen liefert oder Claude
# die erledigt-Reaktion nicht setzen konnte.
LAST_SEEN=""
[ -f "$LAST_SEEN_FILE" ] && LAST_SEEN=$(cat "$LAST_SEEN_FILE" 2>/dev/null)

TRIGGER_DECISION=$(printf '%s' "$RECENT" | LAST_SEEN="$LAST_SEEN" USER_ID="$USER_ID" python3 -c '
import json, os, sys
from decimal import Decimal, InvalidOperation

user_id = os.environ["USER_ID"]
last_seen = os.environ.get("LAST_SEEN", "").strip()

def to_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return Decimal("0")

try:
    d = json.load(sys.stdin)
except Exception:
    print("ERROR")
    raise SystemExit

if not d.get("ok", False):
    print("ERROR")
    raise SystemExit

baseline_messages = []
candidates = []
for m in d.get("messages", []):
    text = m.get("text", "").strip()
    reactions = m.get("reactions", [])
    reaction_names = {r.get("name") for r in reactions}

    is_from_user = m.get("user") == user_id
    is_bot = "bot_id" in m
    is_command = text.startswith("!")
    is_done = "white_check_mark" in reaction_names or "heavy_check_mark" in reaction_names
    ts = m.get("ts", "")

    if is_from_user and not is_bot and not is_command and ts:
        baseline_messages.append(ts)

    if is_from_user and not is_bot and not is_command and not is_done and ts:
        candidates.append(ts)

if not last_seen:
    latest_seen = max(baseline_messages, key=to_decimal) if baseline_messages else "0"
    print(f"INIT {latest_seen}")
    raise SystemExit

if not candidates:
    print("NONE")
    raise SystemExit

latest = max(candidates, key=to_decimal)
if to_decimal(latest) > to_decimal(last_seen):
    print(f"RUN {latest}")
else:
    print("NONE")
')

if [ "$TRIGGER_DECISION" = "ERROR" ]; then
    log "Slack-History konnte nicht lokal geprüft werden. Überspringe Claude."
    exit 0
fi

if [[ "$TRIGGER_DECISION" == INIT\ * ]]; then
    echo "${TRIGGER_DECISION#INIT }" > "$LAST_SEEN_FILE"
    log "Last-Seen initialisiert (${TRIGGER_DECISION#INIT }). Überspringe Claude."
    exit 0
fi

if [ "$TRIGGER_DECISION" = "NONE" ]; then
    log "Keine neue unverarbeitete Hauptkanal-Nachricht. Überspringe Claude."
    exit 0
fi

TRIGGER_TS="${TRIGGER_DECISION#RUN }"
echo "$TRIGGER_TS" > "$LAST_SEEN_FILE"

# Dispatcher ausführen
log "Starte Dispatcher-Runde für Hauptkanal-Nachricht $TRIGGER_TS..."
"$CLAUDE" --print \
    "Du bist der BrainVault Dispatcher. Führe genau eine Runde aus:
1. Lies #dispatcher (Kanal-ID: C0B9L30KVR6) - die letzten 20 Nachrichten.
2. Verarbeite NUR Nachrichten von User-ID $USER_ID ohne ✅-Reaktion und ohne bot_id.
3. Ignoriere Nachrichten die mit ! beginnen (Steuerbefehle).
4. Für jede neue Nachricht: analysiere, führe aus, antworte im Thread, setze ✅-Reaktion.
5. Wenn keine neuen Nachrichten: tue nichts, gib keine Ausgabe.
Vault-Pfad: $VAULT" \
    --add-dir "$VAULT" \
    2>> "$LOG"

log "Dispatcher-Runde abgeschlossen."
