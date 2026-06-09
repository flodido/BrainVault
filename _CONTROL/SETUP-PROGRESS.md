## Erledigt
- [x] BrainVault Ordnerstruktur angelegt
- [x] Kontrolldateien erstellt (TASKS, STATUS, LOG, Prompts)
- [x] Git initialisiert
- [x] gh CLI installiert
- [x] GitHub Repo erstellt und gepusht

## Offen
- [x] Syncthing als System-Daemon einrichten (via Tailscale: http://100.81.198.77:8384)
- [x] Syncthing auf iPhone installieren und BrainVault Vault einrichten
- [ ] Syncthing auf iPad und MacBook Air installieren
- [x] Slack Bot erstellen und MCP konfigurieren
- [x] Dispatcher Session starten und testen
- [x] Dispatcher LaunchAgent einrichten (alle 5 Min, Kill Switch via !stop/!start)
- [x] Dispatcher auf LaunchDaemon (System, Boot-persistent) umgestellt — LaunchAgents deaktiviert (.DISABLED), LaunchDaemon in /Library/LaunchDaemons/; Claude läuft via `sudo -n -u vpn-flodido` um bypassPermissions-Block als root zu umgehen
- [x] Slack Webhook Listener als LaunchDaemon einrichten (Port 9877, Tailscale Funnel, Signatur-Validierung)
- [x] #blog Kanal in Webhook-Listener geroutet: BLOG_CHANNEL → dispatcher.sh --blog; 👀-Reaktion auf Blog-Nachrichten; DISPATCHER-PROMPT.md enthält vollständigen Content-Pipeline-Workflow
- [x] Email Assistant Grundgerüst erstellen (Gmail -> Claude -> Slack-Freigabe -> Gmail Send/Draft)
- [x] Email Assistant Gmail OAuth Credentials erstellen und `credentials.json` hinterlegen
- [x] Email Assistant `config.json` aus `config.example.json` erstellen
- [x] Email Assistant einmal manuell testen: `python email_assistant.py --once`
- [x] Email Assistant LaunchAgent installieren: `_CONTROL/email-assistant/install-launchagent.sh`
- [ ] Komplettes Setup-Script bauen:
      - Tailscale als System-Daemon
      - Syncthing als System-Daemon
      - Docker als System-Daemon + --restart=always
      - Slack MCP Token in ~/.zshrc und ~/.claude/settings.json
