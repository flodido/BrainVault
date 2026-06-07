# BrainVault Email Assistant

Der Email Assistant verarbeitet weitergeleitete Gmail-Nachrichten, erstellt Antwortentwürfe mit Claude und holt die Freigabe in Slack im privaten Kanal `#email-assistant` ein.

## Ablauf

1. Florian leitet eine Mail an die Gmail-Adresse des Assistenten weiter.
2. Ganz oben steht ein privater Anweisungsblock:

```text
### ANWEISUNG AN ASSISTENZ
Ziel: Freundlich absagen, aber Kontakt offenhalten.
Stil: Florian Standard, kurz und warm.
Modus: Freigabe in Slack.
### ENDE ANWEISUNG
```

Alternativ kann Florian eine kurze implizite Anweisung oberhalb der Weiterleitung schreiben. Der explizite Block bleibt aber die robusteste Form.

```text
Bitte freundlich zusagen, aber sagen, dass ich die genaue Uhrzeit nochmal bestätige.

---------- Forwarded message ---------
...
```

3. Der Assistant trennt diese Anweisung vom Mailinhalt.
4. Der Assistant prüft, ob die Weiterleitung von einer erlaubten Florian-Adresse kommt.
5. Claude erstellt eine Antwort ohne den privaten Anweisungsblock zu zitieren.
6. Der Entwurf erscheint in einem Slack-Thread.
7. Florian klickt per Reaktion auf den Slack-Vorschlag:

```text
✅ senden
📝 Gmail-Entwurf erstellen
❌ ablehnen
```

Oder Florian antwortet im Thread mit:

```text
senden
```

oder mit einer Verfeinerung, zum Beispiel:

```text
Kürzer. Kein "leider". Schlag Ende Juni vor.
```

Weitere Befehle:

```text
entwurf
ablehnen
```

## Erlaubte Absender

Der Assistant verarbeitet nur weitergeleitete Mails von den Adressen in `allowed_forwarders`:

```json
[
  "florian.million@gmail.com",
  "f.million@it-beratung-million.de",
  "monacobuy@gmail.com"
]
```

Andere Absender werden als `skipped_unauthorized` protokolliert und standardmäßig als gelesen markiert.

## Installation

```bash
cd ~/BrainVault/_CONTROL/email-assistant
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
```

Dann `config.json` anpassen.

## Gmail OAuth

1. In Google Cloud ein OAuth Desktop-App Credential für die Assistenten-Gmail erstellen.
2. Die Datei als `credentials.json` in diesen Ordner legen.
3. Beim ersten Lauf öffnet Google den OAuth-Flow:

```bash
python email_assistant.py --once
```

Der lokale Token wird als `token.json` gespeichert und ist per `.gitignore` ausgeschlossen.

## LaunchAgent

Nach erfolgreichem Test:

```bash
./install-launchagent.sh
```

Der Agent läuft danach alle 2 Minuten.
