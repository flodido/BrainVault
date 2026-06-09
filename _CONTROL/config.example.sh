#!/bin/bash
# BrainVault – lokale Konfiguration (Vorlage)
# Kopieren nach config.sh und anpassen:
#   cp _CONTROL/config.example.sh _CONTROL/config.sh
#
# config.sh ist gitigniert und enthält persönliche IDs und Pfade.

# ── Pfade ────────────────────────────────────────────────────────────────────
VAULT="$HOME/BrainVault"          # Vault-Wurzel — einziger Wert der beim Umzug geändert werden muss
CONTROL_DIR="$VAULT/_CONTROL"

# ── Slack ────────────────────────────────────────────────────────────────────
DISPATCHER_CHANNEL="C_DISPATCHER_ID"   # Channel-ID von #dispatcher
BLOG_CHANNEL="C_BLOG_ID"               # Channel-ID von #blog
FLORIAN_USER="U_YOUR_USER_ID"          # Deine Slack User-ID
BOT_USER="U_BOT_USER_ID"               # User-ID des BrainVault-Bots

# ── Tools ────────────────────────────────────────────────────────────────────
CLAUDE_BIN="$HOME/.local/bin/claude"
MCP_CONFIG="$HOME/.claude/mcp.json"
