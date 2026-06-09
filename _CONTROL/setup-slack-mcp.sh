#!/bin/bash
# BrainVault – Slack MCP + Dispatcher Setup
# Läuft auf einem frischen Mac und richtet alles ein.

set -e

CONFIG_SH="$(dirname "${BASH_SOURCE[0]}")/config.sh"
if [ -f "$CONFIG_SH" ]; then
    source "$CONFIG_SH"
else
    VAULT="$HOME/BrainVault"
fi
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}→ $1${NC}"; }
ok()    { echo -e "${GREEN}✓ $1${NC}"; }
fail()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   BrainVault Slack MCP Setup         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Voraussetzungen prüfen ────────────────────────────────────────────────

info "Prüfe Voraussetzungen..."

command -v brew &>/dev/null || fail "Homebrew nicht gefunden. Installiere zuerst: https://brew.sh"
ok "Homebrew gefunden"

if ! command -v node &>/dev/null; then
    info "Node.js nicht gefunden – installiere via Homebrew..."
    brew install node
fi
ok "Node.js $(node --version) gefunden"

if ! command -v npm &>/dev/null; then
    fail "npm nicht gefunden"
fi
ok "npm $(npm --version) gefunden"

[ -d "$VAULT" ] || fail "BrainVault nicht gefunden unter $VAULT – erst Syncthing einrichten"
ok "BrainVault Verzeichnis gefunden"

# ── 2. Token abfragen ────────────────────────────────────────────────────────

echo ""
info "Slack Bot Token eingeben (xoxb-...):"
read -r -s SLACK_TOKEN
echo ""

[[ "$SLACK_TOKEN" == xoxb-* ]] || fail "Ungültiger Token – muss mit xoxb- beginnen"

# Token testen
SLACK_TEST=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" https://slack.com/api/auth.test)
if echo "$SLACK_TEST" | grep -q '"ok":true'; then
    TEAM_ID=$(echo "$SLACK_TEST" | python3 -c "import sys,json; print(json.load(sys.stdin)['team_id'])")
    ok "Token gültig (Team: $TEAM_ID)"
else
    fail "Token ungültig: $SLACK_TEST"
fi

# ── 3. npm-Paket installieren ────────────────────────────────────────────────

echo ""
info "Installiere @modelcontextprotocol/server-slack..."
npm install -g @modelcontextprotocol/server-slack &>/dev/null
NODE_PATH=$(which node)
MCP_PATH="$(npm root -g)/@modelcontextprotocol/server-slack/dist/index.js"
[ -f "$MCP_PATH" ] || fail "MCP-Paket nicht gefunden unter $MCP_PATH"
ok "Paket installiert: $MCP_PATH"

# ── 4. ~/.claude/mcp.json (global) ──────────────────────────────────────────

echo ""
info "Erstelle ~/.claude/mcp.json..."
mkdir -p "$HOME/.claude"
cat > "$HOME/.claude/mcp.json" <<EOF
{
  "mcpServers": {
    "slack": {
      "command": "$NODE_PATH",
      "args": ["$MCP_PATH"],
      "env": {
        "SLACK_BOT_TOKEN": "$SLACK_TOKEN",
        "SLACK_TEAM_ID": "$TEAM_ID"
      }
    }
  }
}
EOF
ok "~/.claude/mcp.json erstellt"

# ── 5. ~/BrainVault/.mcp.json (Projekt) ─────────────────────────────────────

info "Erstelle $VAULT/.mcp.json..."
cat > "$VAULT/.mcp.json" <<EOF
{
  "mcpServers": {
    "slack": {
      "command": "$NODE_PATH",
      "args": ["$MCP_PATH"],
      "env": {
        "SLACK_BOT_TOKEN": "$SLACK_TOKEN",
        "SLACK_TEAM_ID": "$TEAM_ID"
      }
    }
  }
}
EOF
ok ".mcp.json erstellt"

# ── 6. Token in ~/.zshrc ─────────────────────────────────────────────────────

info "Trage Token in ~/.zshrc ein..."
if grep -q "SLACK_BOT_TOKEN" "$HOME/.zshrc" 2>/dev/null; then
    info "Token bereits in ~/.zshrc – überspringe"
else
    cat >> "$HOME/.zshrc" <<EOF

# BrainVault Slack MCP
export SLACK_BOT_TOKEN="$SLACK_TOKEN"
export SLACK_TEAM_ID="$TEAM_ID"
EOF
    ok "Token in ~/.zshrc eingetragen"
fi

# ── 7. PATH in ~/.zshrc ──────────────────────────────────────────────────────

if ! grep -q "\.local/bin" "$HOME/.zshrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"' >> "$HOME/.zshrc"
    ok "PATH in ~/.zshrc gesetzt"
fi

# ── 8. Dispatcher-Script ausführbar machen ───────────────────────────────────

DISPATCHER="$VAULT/_CONTROL/dispatcher.sh"
if [ -f "$DISPATCHER" ]; then
    chmod +x "$DISPATCHER"
    ok "dispatcher.sh ausführbar gesetzt"
fi

# ── 9. LaunchAgent einrichten ────────────────────────────────────────────────

PLIST="$HOME/Library/LaunchAgents/com.brainvault.dispatcher.plist"
if [ ! -f "$PLIST" ]; then
    info "Erstelle Dispatcher LaunchAgent..."
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.brainvault.dispatcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$DISPATCHER</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$VAULT/_CONTROL/DISPATCHER-RUN.log</string>
    <key>StandardErrorPath</key>
    <string>$VAULT/_CONTROL/DISPATCHER-RUN.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
</dict>
</plist>
EOF
    launchctl load "$PLIST"
    ok "LaunchAgent eingerichtet und gestartet"
else
    ok "LaunchAgent bereits vorhanden"
fi

# ── Fertig ───────────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Setup abgeschlossen!               ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Nächste Schritte:"
echo "  1. Claude Code (VSCode) neu starten"
echo "  2. MCP-Server-Trust bestätigen wenn Claude Code fragt"
echo "  3. Test: Schreib eine Nachricht in #dispatcher"
echo ""
