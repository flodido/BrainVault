---
tags: [präsentation, meeting, ki-testing, qa, testautomatisierung]
status: approved
erstellt: 2026-06-11
kontext: "Internes Meeting-Handout — neutrale Aufbereitung, kein Unternehmensbezug"
bezuege: "[[Artikel-Entwurf-KI-Testing-Risiken-Mensch]] — Basis-Artikel"
audit:
  status: approved
  auditor: brainvault-auditor
  mode: quick
  score: 86
  audited: 2026-06-11
  notes: >-
    86/100 (Schwelle 85, APPROVED). Vier nicht-blockierende Restmängel behoben:
    (1) Bainbridge-Blockquote als Paraphrase gekennzeichnet; (2) Automation-Bias-Zusatz
    als Interpretation markiert; (3) Abrufdaten in [^nondeterminism] und [^testrail]
    ergänzt; (4) Kappa Python-Wert im Fließtext ergänzt. Alle Kernzahlen durch
    im strict-Audit (98/100) live-verifizierte Quellen gedeckt.
---

# KI-gestützte Testautomatisierung: Risiken, die selten diskutiert werden

**These:** Je mehr Testentscheidungen der KI überlassen werden, desto wichtiger – und desto seltener – werden fundierte menschliche Urteile.

---

## 1. Technische Risiken

### Das Oracle-Problem
- KI generiert Assertions, die syntaktisch korrekt, aber semantisch falsch sind
- LLMs "halluzinieren" Erwartungswerte — sie codieren das *tatsächliche* Verhalten, nicht das *beabsichtigte*[^oracle]
- Gemessene Übereinstimmung zwischen KI-Urteil und tatsächlichem Testergebnis (Cohen's Kappa): ca. 0,21 (Java) / 0,10 (Python) — statistisch: schwache Übereinstimmung[^llmjudge]
- **Konsequenz:** Grüne Balken bedeuten immer weniger, dass die Software das tut, was sie soll

### Neue Flakiness-Quellen
- 63 % der KI-generierten Flaky Tests entstehen durch implizite Annahmen, die nie explizit gemacht wurden (z. B. fehlende ORDER BY-Klauseln)[^flakiness]
- Wenn das Modell Beispielcode mit eingebetteter Flakiness sieht, übernimmt es den Fehler in 42–78 % der Fälle[^flakiness]
- LLM-Nicht-Determinismus: Dieselbe Eingabe → unterschiedliche Ausgaben — auch mit "deterministischen" Einstellungen[^nondeterminism]

### Nachvollziehbarkeit und Audit
- KI-generierte Testsuiten können oft nicht beantworten: *Welche Anforderung deckt dieser Test ab? Warum diese Eingabe?*
- Regulierte Umgebungen (Compliance, Audit-Trails) verlangen lückenlose Rückverfolgung und dokumentierte menschliche Freigabe[^testrail]
- Automatisch erzeugte Artefakte ohne Begründung sind kein Ersatz für spezifiziertes Testdesign

---

## 2. Der Faktor Mensch: Erodierende Kompetenzen

| Kompetenz | Risiko bei dauerhafter KI-Delegation |
|---|---|
| Test-Design | Verlust der Fähigkeit, Äquivalenzklassen und Grenzwerte eigenständig zu identifizieren[^deskilling_design] |
| Anforderungsarbeit | KI fragt nicht "Ist das wirklich gemeint?" — Fehler in Anforderungen werden einbetoniert |
| Exploratives Testen | Kognitive Disziplin, die durch Übung entsteht — nicht durch Abnicken von Vorschlägen |
| Debugging / Root-Cause | Ohne Systemverständnis fehlen die Orientierungspunkte für Fehleranalyse |
| Framework-Kompetenz | Generierter Code kann nicht beurteilt werden, wenn man das Framework nicht versteht |

**Kernproblem:** Kompetenzen degradieren, wenn sie nicht geübt werden — auch wenn man formal "zuständig" bleibt.

---

## 3. Das strukturelle Problem: Ironies of Automation

Lisanne Bainbridge beschrieb dieses Muster schon 1983 für industrielle Automatisierung:[^bainbridge]

> Je mehr ein System automatisiert wird, desto anspruchsvoller wird die Rolle des menschlichen Operators — und desto schlechter ist er darauf vorbereitet. *(sinngemäß paraphrasiert)*

**Für KI-Testing bedeutet das:**
- Der Mensch übernimmt die Rolle des Überwachenden, nicht des Handelnden
- Eingriffe werden seltener — und damit schlechter
- Automation Bias: Die Tendenz, Systemempfehlungen unkritisch zu übernehmen — tendenziell verstärkt durch regelmäßige Nutzung (Interpretation aus Parasuraman & Riley sowie Budzyń et al.)[^parasuraman][^budzyn]

**Empirischer Beleg aus der Medizin:**  
Nach regelmäßiger Nutzung KI-gestützter Koloskopie-Software sank die unassistierte Adenom-Erkennungsrate von Endoskopikern um ~20 % relativ.[^budzyn] Der Mechanismus ist branchenunabhängig.

---

## 4. Die Antwort: Vom Test-Autor zum Test-Auditor

**Das tragfähige Modell:** Mensch bewertet, was die KI produziert — nicht als Freigabefunktion, sondern als qualifizierter Auditor.

**Was ein Test-Auditor können muss:**
- Oracle-Qualität der Assertions beurteilen (stimmt die Erwartung mit der Anforderung überein?)[^oracle]
- Erkennen, welche Äquivalenzklassen fehlen
- Flakiness-Risiken in generiertem Code identifizieren[^flakiness]
- Entscheiden, ob ein Testfall für die vorliegende Architektur überhaupt sinnvoll ist

**Was das voraussetzt:**  
Diese Fähigkeiten entstehen nur durch aktive Testarbeit — und schwinden, wenn sie nicht regelmäßig geübt werden.[^deskilling_design]

---

## 5. Fragen für das Team

1. **Wer** in unserem Team hat heute die Kompetenz, KI-generierte Testfälle qualifiziert zu beurteilen?
2. **Wie** erhalten wir diese Kompetenz über die Zeit — auch wenn der Anteil manuell geschriebener Tests sinkt?
3. Haben wir ein Modell für die **Traceability** KI-generierter Artefakte (Anforderung → Testfall → Ergebnis)?
4. Wissen wir, **wo** KI-Testgenerierung sinnvoll ist — und wo nicht? (Legacy-Code, komplexe Domänen, regulierte Bereiche)
5. Was passiert, wenn die KI-Werkzeuge **ausfallen oder falsch liegen** — haben wir den Plan B?

---

## Quellen

[^oracle]: Konstantinou, M., Degiovanni, R. & Papadakis, M. (2024): *Do LLMs generate test oracles that capture the actual or the expected program behaviour?* arXiv:2410.21136. — Zhang, R. et al. (2025): *Hallucination to Consensus: Multi-Agent LLMs for End-to-End JUnit Test Generation with Accurate Oracles*. arXiv:2506.02943.

[^llmjudge]: Xu, Q. et al. (2025): *On the Effectiveness of LLM-as-a-judge for Code Generation and Summarization*. arXiv:2507.16587. — Cohen's Kappa ca. 0,21 (Java) / 0,10 (Python) für GPT-4-turbo.

[^flakiness]: Berndt, A., Bach, T., Gemulla, R., Kessel, M. & Baltes, S. / SAP (ICSE-SEIP '26): *On the Flakiness of LLM-Generated Tests for Industrial and Open-Source Database Management Systems*. arXiv:2601.08998.

[^nondeterminism]: Atil, B. et al. (2025): *Non-Determinism of 'Deterministic' LLM System Settings*. arXiv:2408.04667. ACL Anthology (Eval4NLP 2025). https://aclanthology.org/2025.eval4nlp-1.12.pdf, abgerufen am 2026-06-09.

[^testrail]: TestRail (2025): *Software Testing in Regulated Industries: From Traceability to AI Governance*. https://www.testrail.com/blog/testing-regulated-industries/, abgerufen am 2026-06-09.

[^deskilling_design]: Shukla, P., Bui, P., Levy, S. S., Kowalski, M., Baigelenov, A. & Parsons, P. (CHI 2025): *De-skilling, Cognitive Offloading, and Misplaced Responsibilities: Potential Ironies of AI-Assisted Design*. arXiv:2503.03924. DOI: 10.1145/3706599.3719931.

[^bainbridge]: Bainbridge, L. (1983): *Ironies of Automation*. Automatica 19(6), S. 775–779. DOI: 10.1016/0005-1098(83)90046-8. — Aktualisierung: Hancke, T. (2020): *Ironies of Automation 4.0*. IFAC-PapersOnLine 53(2), S. 17463–17468.

[^parasuraman]: Parasuraman, R. & Riley, V. (1997): *Humans and Automation: Use, Misuse, Disuse, Abuse*. Human Factors 39(2), S. 230–253. DOI: 10.1518/001872097778543886.

[^budzyn]: Budzyń, K. et al. (2025): *Endoscopist deskilling risk after exposure to artificial intelligence in colonoscopy: a multicentre, observational study*. The Lancet Gastroenterology & Hepatology. DOI: 10.1016/S2468-1253(25)00133-5. — ADR sank von 28,4 % auf 22,4 % (ca. –20 % relativ).
