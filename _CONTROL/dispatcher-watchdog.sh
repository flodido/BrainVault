#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# BrainVault Dispatcher Watchdog
#
# Pollt Slack-Kanäle günstig per curl (kein Claude) und startet den Dispatcher
# nur wenn tatsächlich Aufträge vorliegen. Wird via LaunchAgent alle 5 Min.
# ausgeführt und läuft auch bei geschlossenem Terminal.
#
# Setup:  siehe _CONTROL/WATCHDOG-SETUP.md
# Log:    _CONTROL/watchdog.log  (nur bei Aktivität)
# State:  _CONTROL/watchdog-state.json
# Lock:   /tmp/brainvault-dispatcher-watchdog.lock
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

# ── Konfiguration ─────────────────────────────────────────────────────────────
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
VAULT_DIR="$VAULT"
STATE_FILE="$CONTROL_DIR/watchdog-state.json"
LOG_FILE="$CONTROL_DIR/watchdog.log"
LOCK_FILE="/tmp/brainvault-dispatcher-watchdog.lock"

# ── Token aus MCP-Konfiguration lesen (Single Source of Truth) ────────────────
SLACK_TOKEN=$(jq -r '.mcpServers.slack.env.SLACK_BOT_TOKEN' "$MCP_CONFIG" 2>/dev/null)
if [[ -z "$SLACK_TOKEN" || "$SLACK_TOKEN" == "null" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FEHLER: Slack-Token nicht in $MCP_CONFIG" >> "$LOG_FILE"
    exit 1
fi

# ── Lock: Mehrfachausführung verhindern ───────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
    pid=$(cat "$LOCK_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        exit 0  # Vorheriger Dispatcher-Lauf noch aktiv — überspringen
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

slack_get() {
    curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/$1"
}

# ── Zustand lesen ─────────────────────────────────────────────────────────────
last_blog_check=$(jq -r '.last_blog_check // "0"' "$STATE_FILE" 2>/dev/null || echo "0")
last_blog_check=${last_blog_check:-0}

# ── 1. #dispatcher Hauptkanal: Florian-Nachrichten ohne ✅ ───────────────────
dispatcher_response=$(slack_get "conversations.history?channel=${DISPATCHER_CHANNEL}&limit=20")

dispatcher_main=$(echo "$dispatcher_response" | jq "
  [.messages[] | select(
    .user == \"$FLORIAN_USER\" and
    (.bot_id == null) and
    (.reactions // [] | map(.name) | contains([\"white_check_mark\"]) | not)
  )] | length" 2>/dev/null || echo "0")

# ── 2. #dispatcher Threads: Florian-Replies ohne ✅ (wo Bot schon antwortete) ─
dispatcher_threads=0
thread_ts_list=$(echo "$dispatcher_response" | jq -r "
  .messages[] |
  select(
    .reply_count > 0 and
    (.reply_users // [] | contains([\"$BOT_USER\"])) and
    (.reply_users // [] | contains([\"$FLORIAN_USER\"]))
  ) | .thread_ts" 2>/dev/null || true)

for ts in $thread_ts_list; do
    count=$(slack_get "conversations.replies?channel=${DISPATCHER_CHANNEL}&ts=${ts}" | jq "
      [.messages[] | select(
        .user == \"$FLORIAN_USER\" and
        .ts != .thread_ts and
        (.reactions // [] | map(.name) | contains([\"white_check_mark\"]) | not)
      )] | length" 2>/dev/null || echo "0")
    dispatcher_threads=$(( dispatcher_threads + count ))
done

# ── 3. #blog Hauptkanal: Florian-Nachrichten ohne ✅ ─────────────────────────
blog_response=$(slack_get "conversations.history?channel=${BLOG_CHANNEL}&limit=20")

blog_main=$(echo "$blog_response" | jq "
  [.messages[] | select(
    .user == \"$FLORIAN_USER\" and
    (.bot_id == null) and
    (.reactions // [] | map(.name) | contains([\"white_check_mark\"]) | not)
  )] | length" 2>/dev/null || echo "0")

# ── 4. #blog: Emoji-Auswahl (1️⃣/2️⃣/3️⃣) von Florian auf Bot-Nachrichten ──────
# Erkennt wenn Florian ein Thema ausgewählt hat (Reaktion auf Vorschlagsnachricht)
blog_selections=$(echo "$blog_response" | jq "
  [.messages[] | select(
    .bot_id != null and
    ((.ts | tonumber) > ($last_blog_check | tonumber)) and
    (
      .reactions // [] |
      map(select(.name == \"one\" or .name == \"two\" or .name == \"three\")) |
      map(.users[]) |
      contains([\"$FLORIAN_USER\"])
    )
  )] | length" 2>/dev/null || echo "0")

# ── 5. Entscheidung ───────────────────────────────────────────────────────────
total=$(( dispatcher_main + dispatcher_threads + blog_main + blog_selections ))

if [ "$total" -gt 0 ]; then
    log "Aufträge gefunden — dispatcher: ${dispatcher_main} Haupt + ${dispatcher_threads} Threads | blog: ${blog_main} Nachrichten + ${blog_selections} Emoji-Auswahlen — Dispatcher startet"

    cd "$VAULT_DIR"
    claude -p "$(cat _CONTROL/DISPATCHER-PROMPT.md)" \
        --allowedTools "mcp__slack__slack_get_channel_history,mcp__slack__slack_get_thread_replies,mcp__slack__slack_post_message,mcp__slack__slack_reply_to_thread,mcp__slack__slack_add_reaction,Bash,Read,Write,Edit,WebSearch,WebFetch,Agent" \
        >> "$LOG_FILE" 2>&1

    # Timestamp nach erfolgreichem Lauf speichern
    echo "{\"last_blog_check\": $(date +%s), \"last_run\": \"$(date '+%Y-%m-%dT%H:%M:%S')\"}" \
        > "$STATE_FILE"

    log "Dispatcher-Run abgeschlossen"
else
    : # Kein Logging bei Idle — verhindert Log-Spam
fi
