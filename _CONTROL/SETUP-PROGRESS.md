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
- [x] Email Assistant Grundgerüst erstellen (Gmail -> Claude -> Slack-Freigabe -> Gmail Send/Draft)
- [ ] Email Assistant Gmail OAuth Credentials erstellen und `credentials.json` hinterlegen
- [x] Email Assistant `config.json` aus `config.example.json` erstellen
- [ ] Email Assistant einmal manuell testen: `python email_assistant.py --once`
- [ ] Email Assistant LaunchAgent installieren: `_CONTROL/email-assistant/install-launchagent.sh`
- [ ] Komplettes Setup-Script bauen:
      - Tailscale als System-Daemon
      - Syncthing als System-Daemon
      - Docker als System-Daemon + --restart=always
      - Slack MCP Token in ~/.zshrc und ~/.claude/settings.json
