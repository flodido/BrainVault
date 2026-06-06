#!/bin/bash
# BrainVault Dispatcher
# Läuft alle 5 Minuten via LaunchAgent.
# Kill switch: "!stop" in #dispatcher → pausiert. "!start" → fortsetzen.

VAULT="$HOME/BrainVault"
CONTROL="$VAULT/_CONTROL"
STOP_FILE="$CONTROL/DISPATCHER-STOP"
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

# Dispatcher ausführen
log "Starte Dispatcher-Runde..."
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
