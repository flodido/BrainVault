#!/bin/bash
# Startet eine interaktive Dispatcher-Session direkt im Terminal,
# ohne über Slack zu laufen. Lädt DISPATCHER-PROMPT.md als ersten Prompt.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"
cd "$VAULT" || exit 1
claude "$(cat _CONTROL/DISPATCHER-PROMPT.md)"
