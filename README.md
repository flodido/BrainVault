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
| `#dispatcher` | Dispatcher-Steuerung |
| `#email-assistant` | Private Freigaben und Verfeinerungen für MailPilot-Entwürfe |

---

## MailPilot (ausgelagertes Tool)

> MailPilot ist **kein Teil von BrainVault** mehr, sondern ein eigenständiges,
> öffentliches Projekt mit eigenem Repo und LaunchAgent (siehe unten). Es läuft
> zwar auf demselben Mac mini und ist über Slack mit dem BrainVault-Dispatcher
> verzahnt, wird aber unabhängig entwickelt und gepflegt. Die folgende
> Kurzbeschreibung dient nur dem Verständnis der Slack-Integration aus
> BrainVault-Sicht — die vollständige Doku liegt im MailPilot-Repo selbst.

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

MailPilot postet den Entwurf als Thread in `#email-assistant`. Florian reagiert dort mit Emoji-Aktionen:

```text
✅ senden
📝 Gmail-Entwurf erstellen
❌ ablehnen
```

Alternativ antwortet Florian im Thread mit:

```text
senden
```

oder:

```text
entwurf
ablehnen
```

Jede andere Thread-Antwort wird als Verfeinerung verstanden, z.B. `Kürzer und etwas wärmer`.

Setup und Code wurden in das eigenständige (öffentliche) Repo
[MailPilot](https://github.com/flodido/mailpilot) ausgelagert
(`/Users/Shared/GIT/mailpilot/`), LaunchAgent: `com.mailpilot.email-assistant`.

**Steuerung über den Dispatcher:** Florian kann den MailPilot-LaunchAgent direkt
per Klartext-Nachricht in `#dispatcher` starten/stoppen — z. B. `stop mailpilot`
oder `mailpilot starten` (bewusst ohne führenden Slash, da Slack `/...`-Nachrichten
sonst als eigene Slash-Commands abfängt, statt sie an den Bot weiterzuleiten). Der
Dispatcher führt `launchctl unload`/`load` aus, verifiziert den Status und meldet
das Ergebnis im Thread.

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

---

## Workflow

1. Idee in Slack `#brain-ideen` einwerfen – per iPhone, Apple Watch oder Diktat
2. Dispatcher analysiert und weist der passenden Session zu
3. Session arbeitet selbstständig
4. Ergebnis landet als auditierbare `.md` Note im Vault
5. Auditor prüft Quellen, Fußnoten und Nachvollziehbarkeit im passenden Modus
6. Bei Score unter der Modus-Schwelle geht die Note mit konkreten Nachbesserungen zurück
7. Erst bei Auditor-Freigabe wird der Task als erledigt markiert
8. Syncthing verteilt auf alle Geräte
9. Du bekommst Notification in `#brain-fertig`

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

Eine Idee in `#brain-ideen` wird vom Dispatcher an eine Spezial-Session
weitergegeben, landet als Notiz im Vault und muss den Auditor passieren,
bevor der Task als erledigt gilt.

```mermaid
flowchart LR
    A["💡 Idee in #brain-ideen"] --> B["🧭 Dispatcher routet"]
    B --> C["🔬 Session recherchiert"]
    C --> D[("🗂️ Notiz im Vault")]
    D --> E["🔍 Auditor prüft<br/>quick / standard / strict"]
    E -- "Score zu niedrig: REWORK" --> C
    E -- "Score erreicht: approved" --> F["🔔 #brain-fertig"]
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
    C --> D{"💬 Slack-Thread<br/>#email-assistant"}
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
