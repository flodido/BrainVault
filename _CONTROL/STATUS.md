# STATUS

> Echtzeit-Übersicht aller laufenden Sessions. Wird von jeder Session beim Start/Ende aktualisiert.

---

## Sessions

| Session | Rolle | Zustand | Aktueller Task | Letzte Aktivität |
|---------|-------|---------|----------------|------------------|
| DISPATCHER | Koordination | 🟢 Aktiv | Eingang überwachen | — |
| AUDITOR | Quellen-/Nachvollziehbarkeitsprüfung | ⚪ Bereit | Audit-Queue prüfen | — |
| EMAIL-ASSISTANT | Gmail / Slack Freigabe | 🟢 Aktiv | Gmail pollen + Slack-Freigaben prüfen | 2026-06-07 |
| SESSION-A | Recherche / Web | ⚪ Bereit | — | — |
| SESSION-B | Recherche / Web | ⚪ Bereit | — | — |
| SESSION-C | Daten verarbeiten | ⚪ Bereit | — | — |
| SESSION-D | Daten verarbeiten | ⚪ Bereit | — | — |
| SESSION-E | Zusammenfassen | ⚪ Bereit | — | — |

**Zustände:** 🟢 Aktiv | ⚪ Bereit | 🟡 Wartet auf Input | 🔴 Fehler | ⛔ Gestoppt

---

## Audit-Gate

Neue oder wesentlich geänderte Wissensdateien sind erst abgeschlossen, wenn
`brainvault-auditor` sie im passenden Audit-Modus freigegeben hat:
`quick >= 85`, `standard >= 92`, `strict >= 97`. Offene Prüfungen stehen in
`_CONTROL/AUDIT-QUEUE.md`.

---

## Heute erledigt

<!-- Wird automatisch befüllt -->

---

## Notizen

<!-- Dispatcher oder Sessions können hier Hinweise hinterlassen -->
