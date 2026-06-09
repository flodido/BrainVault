#!/bin/bash
# Wrapper: lädt Umgebungsvariablen und startet den Slack Webhook Listener.
# Wird vom LaunchAgent aufgerufen.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null

export DISPATCHER_CHANNEL
export MAILPILOT_CHANNEL
export MAILPILOT_DIR

exec python3 "$CONTROL_DIR/slack-webhook-listener.py"
