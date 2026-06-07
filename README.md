# 🧠 BrainVault

> Ein persönlicher KI-Cluster der rund um die Uhr arbeitet und alles Wissen an einem Ort sammelt.

---

## Die Idee

Auf einem Mac mini laufen mehrere Claude Code Sessions parallel – jede spezialisiert auf eine Aufgabe. Alle Ergebnisse landen automatisch in diesem Obsidian Vault. Du steuerst alles vom iPhone oder der Apple Watch aus, während der Mac mini im Hintergrund arbeitet.

Morgens beim Kaffee sind alle Aufgaben erledigt und die Ergebnisse warten in Obsidian.

---

## Architektur

```
Du (iPhone / Apple Watch)
├── Slack → Ideen einwerfen, Benachrichtigungen
├── Gmail → weitergeleitete E-Mails an den Assistant
├── Claude App → Sessions steuern via Remote Control
└── Obsidian → Ergebnisse lesen
        ↓
Tailscale VPN (sicherer Tunnel)
        ↓
Mac mini
├── Dispatcher Session → koordiniert alle Aufgaben
├── Email Assistant → Gmail lesen, Entwurf bauen, Slack-Freigabe einholen
├── Session A & B → Recherche / Web-Suche
├── Session C & D → Daten verarbeiten
└── Session E → Texte zusammenfassen
        ↓
Syncthing (System-Daemon)
        ↓
Alle Geräte (iPhone, iPad, MacBook)
```

---

## Vault Struktur

```
BrainVault/
├── _CONTROL/               ← Steuerung des Systems
│   ├── TASKS.md            ← Aufgaben-Queue
│   ├── STATUS.md           ← Session-Übersicht
│   ├── LOG.md              ← Aktivitätslog
│   ├── DISPATCHER-PROMPT.md
│   └── SESSION-PROMPTS.md
├── _INBOX/                 ← Rohdaten, noch nicht verarbeitet
├── _ARCHIVE/               ← Erledigte Aufgaben
├── Research/
│   ├── Tech/
│   ├── Finance/
│   └── Science/
└── Data/
    ├── Raw/
    └── Processed/
```

---

## Slack Channels

| Channel | Zweck |
|---------|-------|
| `#brain-ideen` | Du wirfst Ideen rein → Dispatcher verteilt |
| `#brain-fragen` | Sessions fragen dich bei Unklarheiten |
| `#brain-status` | Dispatcher → Sessions: Aufgaben-Zuweisung |
| `#brain-fertig` | Sessions → Du: Ergebnisse fertig |
| `#dispatcher` | Dispatcher und Email Assistant: direkte Freigaben/Threads |

---

## Email Assistant

Weitergeleitete E-Mails werden nicht automatisch beantwortet. Der Assistant verarbeitet nur Mails von erlaubten Florian-Absenderadressen, trennt private Instruktionen von der Originalmail, erstellt mit Claude einen Antwortvorschlag und fragt in Slack nach Freigabe.

### Weiterleitungsformat

```text
### ANWEISUNG AN ASSISTENZ
Ziel: Freundlich absagen, aber Kontakt offenhalten.
Stil: Florian Standard, kurz und warm.
Modus: Freigabe in Slack.
### ENDE ANWEISUNG

[weitergeleitete Originalmail]
```

Alles im Anweisungsblock ist privater Steuerkontext und darf niemals in der Antwort auftauchen.
Kurze implizite Anweisungen oberhalb der weitergeleiteten Nachricht werden ebenfalls als privater Steuerkontext erkannt; der explizite Block ist aber robuster.

### Slack-Freigabe

Der Assistant postet den Entwurf als Thread in `#dispatcher`. Florian antwortet dort mit:

```text
senden
```

oder:

```text
entwurf
ablehnen
```

Jede andere Thread-Antwort wird als Verfeinerung verstanden, z.B. `Kürzer und etwas wärmer`.

Setup und Code liegen unter `_CONTROL/email-assistant/`.

---

## Voraussetzungen

| Tool | Zweck |
|------|-------|
| Claude Code | KI-Sessions im Terminal |
| tmux | Sessions persistent halten |
| Tailscale | Sicherer Remote-Zugriff |
| Syncthing | Vault-Sync auf alle Geräte |
| Slack | Kommunikation zwischen dir und Sessions |
| Gmail API | Eingang, Entwürfe und Versand für den Email Assistant |
| Obsidian | Vault lesen auf allen Geräten |

---

## Setup

### 1. Repository klonen

```bash
git clone https://github.com/dein-user/BrainVault.git ~/BrainVault
```

### 2. Abhängigkeiten installieren

```bash
brew install tmux syncthing
npm install -g @anthropic-ai/claude-code
```

### 3. Slack Bot einrichten

1. Slack App erstellen unter [api.slack.com](https://api.slack.com)
2. Bot Token Scopes aktivieren: `channels:read`, `chat:write`, `channels:history`
3. Token als Umgebungsvariable setzen:

```bash
echo 'export SLACK_BOT_TOKEN=xoxb-dein-token' >> ~/.zshrc
source ~/.zshrc
```

### 4. Claude Code MCP konfigurieren

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
      }
    }
  }
}
```

### 5. Syncthing einrichten

```bash
brew services start syncthing
# Browser öffnen: http://localhost:8384
# BrainVault Ordner als Sync-Ordner eintragen
# Geräte via Tailscale verbinden
```

### 6. Sessions starten

```bash
# Dispatcher
tmux new -s dispatcher
claude
# → Prompt aus _CONTROL/DISPATCHER-PROMPT.md einfügen

# Specialist Sessions
tmux new -s session-a
claude
# → Prompt aus _CONTROL/SESSION-PROMPTS.md einfügen
```

### 7. Remote Control aktivieren

```bash
# In jeder Claude Code Session:
/rc
# QR Code mit Claude iPhone App scannen
```

---

## Workflow

1. Idee in Slack `#brain-ideen` einwerfen – per iPhone, Apple Watch oder Diktat
2. Dispatcher analysiert und weist der passenden Session zu
3. Session arbeitet selbstständig
4. Ergebnis landet als `.md` Note im Vault
5. Syncthing verteilt auf alle Geräte
6. Du bekommst Notification in `#brain-fertig`

---

## Sicherheit

- SSH nur per Key, kein Passwort
- SSH nur über Tailscale erreichbar – Port 22 im Internet unsichtbar
- Separater Claude-User: Admin-Rechte, kein iCloud-Login
- Hauptuser nicht SSH-fähig
- FileVault aktiv
- Kein Auto-Login (Mac mini steht in WG)

---

## Nach einem Stromausfall

Alle kritischen Services laufen als System-Daemons und starten automatisch:

| Service | Methode |
|---------|---------|
| Tailscale | System-Daemon |
| Syncthing | System-Daemon |
| Docker | System-Daemon + `--restart=always` |

Boot Volume = externe Platte → immer als erstes verfügbar.

---

## Dieses Repo

Dieses Repository enthält den **Grundaufbau** des BrainVault – Ordnerstruktur, Kontrolldateien und Session-Prompts. Es ist als Vorlage gedacht.

Der Live-Sync zwischen Geräten läuft über **Syncthing**, nicht über Git. Git dient nur als Backup und zur Weitergabe des Grundaufbaus.

---

*Built with Claude Code · Obsidian · Tailscale · Syncthing · Slack*
