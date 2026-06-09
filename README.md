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
├── Gmail → weitergeleitete E-Mails an MailPilot
├── Claude App → Sessions steuern via Remote Control
└── Obsidian → Ergebnisse lesen
        ↓
Tailscale VPN (sicherer Tunnel)
        ↓
Mac mini
├── Dispatcher Session → koordiniert alle Aufgaben
├── Auditor Agent → prüft Quellen, Fußnoten und Nachvollziehbarkeit
├── MailPilot → eigenständiges Tool (separates Repo & LaunchAgent),
│   Gmail lesen, Entwurf bauen, Slack-Freigabe einholen
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
│   ├── AUDITOR-PROMPT.md
│   ├── AUDIT-QUEUE.md
│   ├── SESSION-PROMPTS.md
│   ├── dispatcher.sh                              ← Dispatcher (alle 30 Min Fallback)
│   ├── slack-webhook-listener.py                  ← Webhook-Listener (permanent, KeepAlive)
│   ├── start-slack-listener.sh                    ← Wrapper: lädt config.sh + startet Listener
│   ├── com.brainvault.slack-listener.plist.template  ← LaunchAgent-Vorlage
│   ├── config.sh                                  ← Lokale IDs/Pfade (gitignoriert)
│   └── config.example.sh                          ← Vorlage für config.sh
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
| `#dispatcher` | Aufträge einwerfen, Rückfragen, Ergebnisse, Steuerung der Sessions/Tools |
| `#blog` | Themenfindung & mehrstufige Freigabe für die Content-Pipeline |

---

## MailPilot (ausgelagertes Tool)

> MailPilot ist **kein Teil von BrainVault** mehr, sondern ein eigenständiges,
> öffentliches Projekt mit eigenem Repo. Es läuft auf demselben Mac mini und ist
> per Slack lose mit dem BrainVault-Dispatcher verzahnt, wird aber unabhängig
> entwickelt und gepflegt. Die folgende Kurzbeschreibung dient nur dem
> Verständnis der Slack-Integration aus BrainVault-Sicht — Setup, Steuerung und
> die vollständige Doku liegen im [MailPilot-Repo](https://github.com/flodido/mailpilot)
> selbst.

Weitergeleitete E-Mails werden nicht automatisch beantwortet. MailPilot verarbeitet nur Mails von erlaubten Florian-Absenderadressen, trennt private Instruktionen von der Originalmail, erstellt mit Claude einen Antwortvorschlag und fragt in Slack nach Freigabe.

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

MailPilot postet jeden Entwurf als Thread in einem dedizierten Slack-Kanal.
Darauf lässt sich per Emoji-Reaktion oder Textantwort reagieren — senden, als
Gmail-Entwurf ablegen, ablehnen oder verfeinern (z. B. `Kürzer und etwas
wärmer`). Welcher Kanal das genau ist, wie die Reaktionen im Detail aussehen
und wie das Tool gestartet/gestoppt wird, ist Teil des eigenständigen
[MailPilot-Repos](https://github.com/flodido/mailpilot) und dort dokumentiert.

---

## Voraussetzungen

| Tool | Zweck |
|------|-------|
| Claude Code | KI-Sessions im Terminal |
| tmux | Sessions persistent halten |
| Tailscale | Sicherer Remote-Zugriff |
| Syncthing | Vault-Sync auf alle Geräte |
| Slack | Kommunikation zwischen dir und Sessions |
| Gmail API | Eingang, Entwürfe und Versand für MailPilot (separates Tool, nicht Teil von BrainVault) |
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

### 8. Slack Webhook einrichten (Event-basierter Dispatcher)

Statt alle 5 Minuten zu pollen reagiert der Dispatcher jetzt in Sekunden auf neue Slack-Nachrichten.
Der Listener läuft permanent als macOS LaunchAgent (`KeepAlive: true`) und routet eingehende
Webhook-Events je nach Kanal an den richtigen Prozess.

**Architektur:**
```
Slack-Nachricht
  → HTTPS-Webhook (Tailscale Funnel, öffentliche URL)
  → slack-webhook-listener.py (Port 9877, KeepAlive LaunchAgent)
  → je nach Kanal:
      #dispatcher  →  dispatcher.sh
      #mailpilot   →  email_assistant.py --once
```

**Voraussetzungen:**
- [Tailscale](https://tailscale.com) installiert und eingeloggt
- Slack App mit Bot Token (siehe Schritt 3)
- `SLACK_SIGNING_SECRET` in `~/.zshrc` gesetzt (aus *api.slack.com → Basic Information*)

**Einrichtung:**

1. **config.sh befüllen** (Kanal-IDs aus deinem Slack Workspace):
   ```bash
   cp _CONTROL/config.example.sh _CONTROL/config.sh
   # Kanal-IDs und Pfade in config.sh eintragen
   ```

2. **Signing Secret setzen:**
   ```bash
   echo 'export SLACK_SIGNING_SECRET="dein-secret"' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **LaunchAgent installieren:**
   ```bash
   # Template kopieren und USERNAME ersetzen
   sed 's/USERNAME/dein-macos-username/g' \
     _CONTROL/com.brainvault.slack-listener.plist.template \
     > ~/Library/LaunchAgents/com.brainvault.slack-listener.plist

   launchctl load ~/Library/LaunchAgents/com.brainvault.slack-listener.plist
   ```

4. **Tailscale Funnel aktivieren:**
   ```bash
   tailscale funnel --bg 9877
   # → Öffentliche URL: https://<hostname>.<tailnet>.ts.net
   ```
   Falls Funnel noch nicht freigeschaltet ist, zeigt der Befehl einen Aktivierungslink.

5. **Slack App konfigurieren** unter *api.slack.com → Event Subscriptions*:
   - Request URL: `https://<hostname>.<tailnet>.ts.net/slack/events`
   - Bot Events abonnieren: `message.groups` (für private Kanäle)
   - Änderungen speichern

**Fallback:** Der Dispatcher-LaunchAgent (`com.brainvault.dispatcher`) läuft weiterhin alle 30 Minuten
als Sicherheitsnetz, falls der Webhook kurzzeitig nicht erreichbar ist.

---

## Workflow

1. Idee in Slack `#dispatcher` einwerfen – per iPhone, Apple Watch oder Diktat
2. Dispatcher analysiert und weist der passenden Session zu
3. Session arbeitet selbstständig
4. Ergebnis landet als auditierbare `.md` Note im Vault
5. Auditor prüft Quellen, Fußnoten und Nachvollziehbarkeit im passenden Modus
6. Bei Score unter der Modus-Schwelle geht die Note mit konkreten Nachbesserungen zurück
7. Erst bei Auditor-Freigabe wird der Task als erledigt markiert
8. Syncthing verteilt auf alle Geräte
9. Du bekommst die Rückmeldung im `#dispatcher`-Thread

### Audit-Gate

BrainVault-Notizen mit Recherche-, Analyse-, Konzept- oder
Zusammenfassungscharakter dürfen keine unbelegten Sachbehauptungen enthalten.
Jede nicht-triviale Aussage braucht eine Fußnote (`[^id]`) auf eine konkrete
Quelle. Eine reine Quellenliste am Ende genügt nicht.

Audit-Modi:

- `quick`: ab 85/100 für Skizzen und frühe Entwürfe
- `standard`: ab 92/100 als Default für normale BrainVault-Notizen
- `strict`: ab 97/100 für Veröffentlichung, Website, Kundenbezug, Recht/DSGVO,
  Finanzen, Medizin, harte Zahlen, Zitate oder High-Stakes-Themen

Der Modus kann im Prompt angegeben werden, z. B. `Audit-Modus: standard`.
Ohne Angabe nutzt der Dispatcher `standard` und stuft automatisch auf `strict`
hoch, wenn der Auftrag nach Veröffentlichung oder High-Stakes klingt.

---

## Use Cases im Überblick

Drei wiederkehrende Abläufe zeigen, wie Aufträge durch BrainVault laufen —
von der Idee bis zum geprüften Ergebnis.

### 1. Recherche-Auftrag

Eine Idee in `#dispatcher` wird vom Dispatcher an eine Spezial-Session
weitergegeben, landet als Notiz im Vault und muss den Auditor passieren,
bevor der Task als erledigt gilt.

```mermaid
flowchart LR
    A["💡 Idee in #dispatcher"] --> B["🧭 Dispatcher routet"]
    B --> C["🔬 Session recherchiert"]
    C --> D[("🗂️ Notiz im Vault")]
    D --> E["🔍 Auditor prüft<br/>quick / standard / strict"]
    E -- "Score zu niedrig: REWORK" --> C
    E -- "Score erreicht: approved" --> F["🔔 Rückmeldung im Thread"]
    F --> G["📱 Syncthing → alle Geräte"]
```

### 2. MailPilot (ausgelagertes Tool)

Weitergeleitete Mails mit Anweisungsblock werden nie automatisch beantwortet —
MailPilot baut einen Entwurf und holt sich die Freigabe per Slack-Reaktion
oder Thread-Antwort ein. Läuft als eigenständiges Projekt neben BrainVault,
ist aber über Slack mit dem Dispatcher verzahnt (siehe Abschnitt "MailPilot
(ausgelagertes Tool)" oben).

```mermaid
flowchart LR
    A["📧 Weitergeleitete Mail<br/>+ Anweisungsblock"] --> B["📨 MailPilot<br/>trennt Anweisung von Originalmail"]
    B --> C["✍️ Claude-Entwurf"]
    C --> D{"💬 Slack-Thread<br/>(Freigabe)"}
    D -- "✅ senden" --> E["📤 Gmail: Senden"]
    D -- "📝 Entwurf" --> F["📋 Gmail: Draft erstellen"]
    D -- "Verfeinerung z. B. 'kürzer & wärmer'" --> C
    D -- "❌ ablehnen" --> G["🗑️ verworfen"]
```

### 3. Content-Pipeline mit mehrstufiger Freigabe

Manche Outputs sollen nicht nur im Vault landen, sondern öffentlich
veröffentlicht werden (z. B. auf einer eigenen Website oder einem Blog).
Dafür eignet sich ein dedizierter Kanal, in dem auf Zuruf Themenideen
entstehen, ein doppeltes Audit-Gate (niedrigere Schwelle für die erste
Rückmeldung, strenge Schwelle als Pflicht vor Veröffentlichung) und mehrere
**getrennte, ausdrückliche Bestätigungen**, bevor irgendetwas live geht.

```mermaid
flowchart TD
    A["✍️ Themen-Anfrage in dediziertem Kanal"] --> B["🧭 Dispatcher: Themenvorschläge<br/>1️⃣ 2️⃣ 3️⃣"]
    B --> C["👍 Auswahl durch Florian"]
    C --> D["🔬 Recherche + Entwurf<br/>+ Begleittexte (z. B. Social Media)"]
    D --> E["🔍 Audit: erste Stufe<br/>niedrigere Schwelle"]
    E --> F{"💬 Präsentation im Thread<br/>+ Ablage im Vault"}
    F -- "① ✅ inhaltlich ok" --> G["🔍 Audit: strenge Stufe<br/>Veröffentlichungs-Schwelle"]
    G -- "Score zu niedrig: REWORK" --> D
    G -- "Schwelle erreicht" --> H{"② Bestätigung<br/>'jetzt veröffentlichen?'"}
    H -- "③ ✅ + Commit-Bestätigung" --> I[("🌐 Live-Beitrag<br/>auf eigener Plattform")]
    I --> J["📣 Begleittexte<br/>+ Link zum Teilen"]
```

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
