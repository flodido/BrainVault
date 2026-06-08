#!/bin/bash
# Startet eine interaktive Dispatcher-Session direkt im Terminal,
# ohne über Slack zu laufen. Lädt DISPATCHER-PROMPT.md als ersten Prompt.

cd "$HOME/BrainVault" || exit 1
claude "$(cat _CONTROL/DISPATCHER-PROMPT.md)"
