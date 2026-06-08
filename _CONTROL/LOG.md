# LOG

> Chronologisches Protokoll aller Aktivitäten. Nur anhängen, nie löschen.
> Format: `[YYYY-MM-DD HH:MM] [SESSION] Nachricht`

---

## Einträge

<!-- Sessions schreiben hier mit: echo "[$(date '+%Y-%m-%d %H:%M')] [SESSION-X] Nachricht" >> LOG.md -->

[2026-06-07 13:25] [CODEX] Email Assistant Grundgerüst erstellt: Gmail-Polling, privater Anweisungsblock, Claude-Entwurf, Slack-Freigabethread, Gmail Send/Draft.
[2026-06-07 14:18] [CODEX] Email Assistant auf Mac mini eingerichtet: OAuth Token erstellt, Gmail API getestet, LaunchAgent installiert.
[2026-06-08 10:25] [DISPATCHER] Runde geprüft: alle Hauptkanal-Nachrichten und Bot-Threads von Florian bereits mit ✅ markiert. Keine neuen Aufträge zu verarbeiten.
[2026-06-08 11:15] [CODEX] BrainVault Auditor eingerichtet: Subagent brainvault-auditor, AUDITOR-PROMPT, AUDIT-QUEUE und Dispatcher-/Session-Workflows mit 97/100 Quellen-Gate ergänzt.
[2026-06-08 11:55] [CODEX] Artikel-Entwurf KI-Agenten QA Konzernpraxis mit Fussnoten nachbearbeitet und durch brainvault-auditor freigegeben: Score 98/100.
[2026-06-08 12:10] [CODEX] BrainVault Auditor auf Audit-Modi umgestellt: quick >=85, standard >=92, strict >=97; Dispatcher setzt standard als Default und stuft High-Stakes-/Publikationsinhalte automatisch auf strict.
[2026-06-08 14:48] [CLAUDE] Blog-Sektion in itbm-Repo umgesetzt (Astro Content Collection /blog + /en/blog) und #blog-Slack-Kanal für Themenfindungs-Workflow eingerichtet: Vorschläge → Emoji-Auswahl → Entwurf+Social-Posts → Freigabe → Veröffentlichung.
[2026-06-08 15:10] [CLAUDE] #blog-Content-Pipeline-Workflow in DISPATCHER-PROMPT.md persistiert (Themenvorschläge → Auswahl → Entwurf+Social → quick/strict-Audit → 3 getrennte Bestätigungen → Veröffentlichung). Vorher nur in Claude-Memory dokumentiert, jetzt im Repo versioniert und für die laufende Dispatcher-Session wirksam.
[2026-06-08 15:50] [CLAUDE] Email-Assistant-Umzug zu MailPilot abgeschlossen (von Codex begonnen): venv/config/credentials/state ins MailPilot-Repo übernommen, neuen LaunchAgent installiert und getestet (LastExitStatus 0), alten LaunchAgent entladen+entfernt, altes _CONTROL/email-assistant/ (131MB inkl. venv) gelöscht, README-Pfadverweis aktualisiert.
