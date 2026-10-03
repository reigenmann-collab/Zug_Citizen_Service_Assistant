# Evaluation – Stadt Zug RAG

## Warum dieses Verzeichnis vor Phase 4 entsteht
In Schwyz ist die Evaluation nie vollständig durchgelaufen (siehe CLAUDE.md). Testset, Label-Sheet und
Kalibrierungsplan werden deshalb **vor** dem Bau der Pipeline festgelegt, damit nicht am Ende das
Messinstrument an das Ergebnis angepasst wird.

## Die drei Dateien

| Datei | Zweck | Wann benutzt |
|---|---|---|
| `retrieval_testset.json` (27 Fragen) | **Smoke-Test** nur für Retrieval: Findet die Suche den richtigen Chunk? Prüft Hit@k, nicht die Antwort. | Phase 3 fortlaufend, Phase 4 bei Reranker-Vergleich |
| `testset.json` (44 Fragen, dev/test) | **Evaluationsset** für die ganze Pipeline: Antwortinhalt, Quellen, Eskalation, Sprache | dev in Phase 4–6, test einmalig in Phase 7 |
| `grounding_adversarial.json` (12 Behauptungen) | **Unit-Test für den Grounding-Checker** (S2): erkennt er erfundene Zahlen? | Phase 4–5 |

## Dev/Test-Disziplin
- **dev (24 Fragen):** Hier wird getunt – Prompts, Reranker, Schwellen, Coverage-Regeln. Beliebig oft messbar.
- **test (20 Fragen):** Wird in Phase 4–6 **nicht** gemessen und nicht gelesen, um Prompts daran anzupassen.
  Erst in Phase 7 einmal ausgewertet. Jede weitere Auswertung wird im Bericht vermerkt.
- Die Kalibrierung der Confidence-Schwelle erfolgt auf **allen generierten Zeilen**, nicht nur auf den
  automatisch beantworteten (Lehre aus Schwyz, CLAUDE.md).

## Kategorien in `testset.json`

| Kategorie | Erwartung |
|---|---|
| `A_gedeckt` | Antwort vollständig aus einer Quelle; Quellenangabe Pflicht |
| `B_zwei_quellen` | Webseite **und** Erlass nötig; eine Quelle allein ist eine falsche Antwort → Coverage-Check |
| `C_hard_routing` | Busse, Rechtsmittel, Haftung → Eskalation **vor** der Generierung, unabhängig von der Confidence |
| `D_nicht_gedeckt` | Plausible Frage ohne Antwort im Korpus → als nicht gedeckt melden, nichts erfinden |
| `E_falschannahme` | Die Frage enthält eine falsche Zahl oder Annahme → korrigieren, nicht bestätigen |
| `F_mehrdeutig` | Mehrere korrekte Antworten je Kontext → differenzieren oder Rückfrage |
| Suffix `_en` | Englische Antwort **plus** festem Hinweis, dass sie nicht rechtsverbindlich ist |

## Die drei wichtigsten Fälle
1. **D01 / T01 – Webseite verkürzt den Erlass.** Anwohnerparkkarte: Webseite nennt nur CHF 30/Mt.,
   SRS 7.7.5-2 § 12 unterscheidet CHF 30 (Nachtparkgebühr bezahlt) und CHF 60 (inklusive). Eine Antwort
   mit nur CHF 30 ist unvollständig.
2. **D02 / T11 – Tarife sind mehrdeutig.** Die Webseite zeigt unter «Tarife / Kurzzeittarife» ausschliesslich
   **Parkhaus**-Tarife (= § 18 Abs. 2 Bst. b). Die oberirdischen Tarife nach § 6 und § 7 (CHF 1.00–2.00/h)
   stehen **nur** im Erlass. «Was kostet eine Stunde parkieren?» hat damit drei richtige Antworten.
3. **D04 – Webseite und Erlass scheinen zu widersprechen.** § 11 Abs. 2 listet Zone 4 Gimenen als
   Anwohnerbevorzugungszone; die Webseite sagt, für Zone 4 würden keine Karten ausgegeben
   (zulässig nach § 11 Abs. 4). Der Assistent darf den Widerspruch nicht selbst auflösen.

## Grenzen, die im Pilotbericht stehen müssen
- **Die Fragen und die Gold-Antworten stammen von Claude**, abgeleitet aus dem indexierten Korpus. Sie sind
  damit **nicht unabhängig** von dem System, das sie prüfen: blinde Flecken des Korpus bleiben unentdeckt,
  weil ich Fragen formuliere, deren Antwort ich im Korpus gesehen habe. Alle Zeilen tragen
  `label_quelle: claude_vorschlag` und ein leeres Feld `geprueft_von`.
- **Vor Phase 7 müssen die Labels von René geprüft werden.** `python eval/label_sheet.py` erzeugt
  `eval/label_sheet.csv` zum Ausfüllen. Ungeprüfte Zeilen werden im Bericht getrennt ausgewiesen.
- **44 Fragen sind zu wenig für belastbare Prozentwerte.** Bei 24 Dev-Fragen entspricht eine einzelne
  Frage gut 4 Prozentpunkten; das Konfidenzintervall ist breiter als die meisten Unterschiede, die man
  messen möchte. Die Zahlen zeigen Richtung und Fehlermuster, keine Genauigkeit.
- Echte Bürgerfragen fehlen. Falls Logdaten der Stadt Zug verfügbar wären, sollten sie das Set ersetzen.
