#!/bin/bash
# BrainVault Emergency Restart
# Startet alle LaunchDaemons neu und zeigt Status.
# Verwendung: sudo bash ~/BrainVault/_CONTROL/brainvault-restart.sh

if [ "$(id -u)" != "0" ]; then
    echo "Fehler: Bitte mit sudo ausführen."
    echo "  sudo bash ~/BrainVault/_CONTROL/brainvault-restart.sh"
    exit 1
fi

DAEMONS=(
    "com.brainvault.slack-listener"
    "com.brainvault.dispatcher"
    "com.brainvault.tailscale-autostart"
)

echo "=== BrainVault Restart ==="
echo ""

for LABEL in "${DAEMONS[@]}"; do
    printf "%-45s" "$LABEL"
    if launchctl list "$LABEL" &>/dev/null; then
        launchctl kickstart -k "system/$LABEL" &>/dev/null
        echo "✓ neu gestartet"
    else
        launchctl bootstrap system "/Library/LaunchDaemons/$LABEL.plist" &>/dev/null
        echo "✓ gestartet (war nicht geladen)"
    fi
done

echo ""
echo "=== Status ==="
echo ""

sleep 2

for LABEL in "${DAEMONS[@]}"; do
    PID=$(launchctl list "$LABEL" 2>/dev/null | awk '/PID/{print $3}' | tr -d ',')
    STATUS=$(launchctl list "$LABEL" 2>/dev/null | awk '/LastExitStatus/{print $3}' | tr -d ',')
    printf "%-45s" "$LABEL"
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        echo "🟢 läuft (PID $PID)"
    else
        echo "⚪ nicht aktiv (LastExitStatus: ${STATUS:-?})"
    fi
done

echo ""
echo "=== Logs ==="
echo ""
echo "Listener: tail -f ~/BrainVault/_CONTROL/slack-listener.log"
echo "Dispatcher: tail -f ~/BrainVault/_CONTROL/DISPATCHER-RUN.log"
