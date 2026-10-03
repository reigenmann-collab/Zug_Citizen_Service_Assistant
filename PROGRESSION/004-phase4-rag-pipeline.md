# 004 – Phase 4 RAG-Pipeline (2026-10-03)

Pipeline: Sprache → Hard-Routing → Retrieval → (Rerank) → Coverage → Generierung → Grounding → Audit-Log.
Code in `rag/`, Evaluation in `eval/`.

## Modell
`gemini-3.1-flash-lite` – Verfügbarkeit geprüft, 61 Modelle gelistet, Generierung getestet. Daneben wäre
`gemini-3.5-flash-lite` verfügbar; nicht gewechselt, weil René 3.1 bestätigt hat. API-Key in `.env`
(gitignored), `.env.example` als Vorlage.

## Reranker: gemessen und begründet verworfen für den Pilotbetrieb

CLAUDE.md verlangt einen Reranker-Entscheid mit Begründung. Drei lokale Kandidaten aus fastembed (ONNX),
gemessen auf dem Retrieval-Smoke-Test (27 Fragen, Kandidaten aus dem dichten Index):

| Reranker | Grösse | @1 | @3 | @5 | ms/Frage |
|---|---|---|---|---|---|
| ohne (nur dense) | – | 16/27 | 23/27 | **26/27** | 0 |
| Xenova/ms-marco-MiniLM-L-12-v2 | 0.12 GB | 9/27 | 20/27 | 21/27 | 5515 |
| BAAI/bge-reranker-base, volle Passagen, 20 Kand. | 1.04 GB | 19/27 | 24/27 | 25/27 | 13959 |
| BAAI/bge-reranker-base, 700 Zeichen, 20 Kand. | 1.04 GB | **20/27** | 24/27 | 25/27 | 6831 |
| BAAI/bge-reranker-base, 400 Zeichen, 20 Kand. | 1.04 GB | 18/27 | 24/27 | 26/27 | 3354 |
| BAAI/bge-reranker-base, 400 Zeichen, 10 Kand. | 1.04 GB | 18/27 | **24/27** | **26/27** | 2099 |

Befunde:
- **ms-marco-MiniLM ist einsprachig englisch** und verschlechtert deutsches Retrieval deutlich
  (@1 16→9). Trotz kleinster Grösse unbrauchbar.
- **bge-reranker-base ist mehrsprachig und wirkt genau dort, wo es nötig ist**: «Parkieren im Parkhaus
  für 3 Stunden» 5→1, «Dauerparkplatz Parkhaus Arena» 2→1, «Gebühr Nachtparkieren» 4→1. Keine NaN-Werte
  (anders als Jina bei den Embeddings; die Prüfung ist als Assertion im Code).
- **Kosten:** 14 s pro Frage mit vollen Passagen. Durch Kürzen auf 400 Zeichen und 10 Kandidaten auf
  2.1 s zu senken, ohne Qualitätsverlust bei @3/@5. Der Prozess belegt dabei **~3.1 GB RAM**.
- `jinaai/jina-reranker-v2-base-multilingual` (1.11 GB) nicht gemessen: gleiche Grössenklasse, damit
  dasselbe RAM-Problem, und Jina hat in diesem Projekt bereits NaN-Vektoren geliefert.

**Entscheid:** Im Pilotbetrieb auf Streamlit Community Cloud **kein Cross-Encoder**. Grund ist nicht die
Qualität, sondern das Gedächtnis: ~1 GB RAM im Free Tier gegen ~3.1 GB Bedarf. Stattdessen `k=10` statt
`k=5` Kontextblöcke, damit der richtige Chunk auch bei Rang 10 im Prompt landet (dense @10 = 26/27).
Der Reranker-Code bleibt und ist über `antworte(..., reranker="bge")` zuschaltbar. **Empfehlung für einen
Host mit ≥4 GB RAM: `bge`, 400 Zeichen, 10 Kandidaten** (+2 bei @1, +1 bei @3, 2.1 s Zusatzlatenz).

## Retrieval: BM25 nicht als Ranking, sondern als Recall-Netz

Erster Versuch, Reciprocal Rank Fusion aus dichtem Index und BM25. Ergebnis: **schlechter als dense
allein, bei jedem Gewicht.**

| Verfahren | @1 | @3 | @5 |
|---|---|---|---|
| nur dense | **16/27** | **23/27** | **26/27** |
| nur BM25 | 7/27 | 15/27 | 15/27 |
| RRF, BM25-Gewicht 0.15 | 12/27 | 21/27 | 26/27 |
| RRF, BM25-Gewicht 0.3 | 10/27 | 20/27 | 23/27 |
| RRF, BM25-Gewicht 1.0 | 10/27 | 19/27 | 20/27 |

Erklärung: deutsche Komposita ohne Stemming, englische Fragen ohne lexikalische Überlappung zu
deutschen Quellen, und 456 Chunks sind zu wenig für tragfähige IDF-Statistik.

**Dieser Schluss war zu pauschal.** Die Pipeline-Evaluation zeigte einen Fall, in dem der dichte Index
völlig versagt: Bei «Die Gewerbeparkkarte gilt nur in der Stadt Zug, richtig?» lag der richtige Chunk
(§ 14 Gewerbeparkkarte der Zuger Gemeinden) im dichten Index auf **Rang 134**, bei BM25 auf **Rang 4**.
Die aggregierten Smoke-Test-Zahlen verdeckten das, weil dort die Webseiten-Chunks, die dense gut findet,
die Treffer-Bedingung meist schon erfüllten.

**Entscheid:** BM25 bleibt aus dem Ranking heraus, kommt aber als **Recall-Netz** hinzu. Die Reihenfolge
bestimmt weiter der dichte Index; zusätzlich werden bis zu zwei Chunks beigegeben, die BM25 deutlich
bewertet (min_score 4.0) und die dense gar nicht gefunden hat. Sie werden dem Kontext **angehängt**, nicht
in die Rangliste gemischt – das war zuerst falsch gebaut: eingemischt schnitt `k` sie wieder ab, das Netz
hatte keine Wirkung.

Wirkung, gemessen: § 14 erreicht bei beiden Gewerbeparkkarte-Fragen den Kontext. Grenze, ebenfalls
gemessen: Bei der englischen Frage nach der Besucherparkkarte hilft das Netz **nicht** – BM25 kann
englische Fragen nicht auf deutsche Quellen abbilden, und `min_score` verhindert richtigerweise, dass
stattdessen Zufallstreffer beigegeben werden. Englische Fragen bleiben damit allein auf das
mehrsprachige Embedding angewiesen.

## Hard-Routing (vor der Generierung, ohne LLM-Aufruf)
Drei Themen nach CLAUDE.md: Rechtsmittel, Bussen, Haftung. Auf den 44 Testfragen: **7 von 7 richtig
erkannt, 0 Fehlalarme**. Eskalation in 0.0 s, weil kein Modellaufruf stattfindet.
Alle Muster laufen über `rag/norm.py`, das Homoglyphen auf Latin abbildet – die Schwyz-Lehre mit dem
kyrillischen «е» in «busse» ist als Test hinterlegt und greift.

## Grounding-Checker (S2): zwei Schichten, weil keine allein genügt
`eval/grounding_adversarial.json`, 12 Behauptungen:

| | Schicht A (Zahlen, deterministisch) | A + B (LLM, aussagenweise) |
|---|---|---|
| korrekt | 9/12 | **12/12** |

- **Schicht A** prüft jede Zahl mit Einheit gegen den Kontext; Paragraphen- und Erlassnummern werden
  ausgenommen, ausgeschriebene Zahlwörter aufgelöst. Sie fängt alle vier erfundenen Werte, darunter die
  von CLAUDE.md geforderten Fälle: **CHF 200 statt 30/60** und **zehn statt fünf Jahre** → `nicht_gedeckt`.
  Sie lässt alle vier korrekten Aussagen durch, auch die paraphrasierte.
- **Schicht A verfehlt strukturell drei Fälle:** richtige Zahl falsch zugeordnet (CHF 30 für schwere statt
  leichte Motorwagen), unzulässige Verallgemeinerung («in allen Zonen, unabhängig von»), falsche Behörde
  ohne jede Zahl. Alle drei fängt Schicht B.
- Ein Verstoss in Schicht A ist hart und setzt das Urteil, unabhängig von B.
- **Einschränkung:** Schicht B benutzt dasselbe Modell wie die Generierung, ist also keine unabhängige
  Prüfung. In Phase 5 bei der Kalibrierung berücksichtigen.

## Coverage-Check (unabhängig von C)
Der Brief verlangt, bei Gebührenfragen `doc_type: gebuehrentarif` mitzuliefern. Der Phase-2-Befund
präzisiert das: Gebühren stehen **auch** im Erlass, und gefährlich ist der umgekehrte Fall – die Webseite
nennt bei der Anwohnerparkkarte nur CHF 30/Monat, § 12 unterscheidet CHF 30 und CHF 60. Umsetzung:
1. Fragetyp erkennen (Gebühr, Dauer, Zeit, Zuständigkeit, Verfahren).
2. Bei Gebührenfragen **Webseite und Erlass mit Betrag** im Kontext erzwingen; fehlt eine Art, wird sie
   aus den Retrieval-Kandidaten nachgeladen (`ergaenze_gegenstueck`).
3. Fehlt die gefragte Art von Information ganz, wird eskaliert – unabhängig von der Confidence.

**Bekannte Schwäche, gemessen:** Die Regel prüft die Quellen*art*, nicht die thematische Passung. Bei
«Was kostet ein Dauerparkplatz im Parkhaus?» war ein Erlass-Chunk mit Betrag im Kontext (§ 6
Langzeitparkplätze), aber nicht der richtige (§ 18, Rang 10). Die Antwort nannte nur CHF 210 und nicht
CHF 230 für ein reserviertes Parkfeld. Deshalb `k=10`. Eine thematische Prüfung wäre die bessere Lösung
und ist in Phase 5 nachzuziehen.

## Confidence: berechnet, nicht geschwellt
S1 (Retrieval: Spitzen-Kosinus, Mittel Top-3, Abstand), S2 (Grounding), S3 (Selbstbewertung des Modells)
werden berechnet und protokolliert. C = 0.3·S1 + 0.4·S2 + 0.3·S3 ist **vorläufig und ausdrücklich nicht
kalibriert**; CLAUDE.md verlangt Kalibrierung statt gesetzter Schwelle. In Phase 4 wird deshalb **nur** aus
zwei harten Gründen eskaliert: Hard-Routing und Coverage-Lücke. Eine Confidence-Schwelle gibt es noch nicht.

## Prompt-Korrektur durch den Checker
Erster Lauf: Die Antwort zur Anwohnerparkkarte nannte korrekt CHF 30 und CHF 60, behauptete aber,
Webseite und Erlass würden sich «widersprechen». Schicht B beanstandete das zu Recht – die Webseite nennt
nur einen der beiden im Erlass geregelten Tarife, das ist eine Verkürzung, kein Widerspruch. Die
Prompt-Regel vermischte beides. Jetzt getrennt: Verkürzung → alle Varianten nennen, kein Widerspruch
behaupten; echter Widerspruch → beide nennen, nicht auflösen, an die Fachstelle verweisen. Danach S2 = 1.0.
Das ist der erste Fall, in dem der Checker einen Generierungsfehler gefunden hat, nicht umgekehrt.

## Audit-Log
`rag/auditlog.py`: gesalzenes SHA-256-Pseudonym der Frage, **Rohfrage wird nie gespeichert**. Salz aus
`AUDIT_SALT`, lokal einmalig erzeugt in `data/audit/.salt`. Protokolliert werden Zeit, Pseudonym, Sprache,
Entscheid, Eskalationsgrund, Kontext- und benutzte Quellen, S1/S2/S3, C, Grounding-Urteil, Coverage,
Tokens, Dauer.
**Restrisiko für das Governance-Kapitel:** Der Antworttext wird gespeichert, weil der Audit Trail zeigen
muss, was gesagt wurde. Enthält eine Frage Personendaten und greift die Antwort sie auf, stehen sie im Log.

## Fehlerbehandlung
`rag/llm.py`: Retry mit exponentiellem Backoff und Jitter bei 503, 429, 500 und Timeouts, vier Versuche.
Danach deutsche beziehungsweise englische Fehlermeldung und Eskalation an einen Menschen – kein Traceback.

## Ergebnis auf dem Dev-Split (24 Fragen, k=10, ohne Reranker)

| Konfiguration | automatisch bewertbar | Median | > 5 s |
|---|---|---|---|
| Baseline: altes Chunking, nur dense | 14/19 | 3.2 s | 1/24 |
| + Chunking korrigiert, + BM25-Recall-Netz | 17/19 | 2.9 s | 1/24 |
| + Prompt-Regel 6a und EN-Regel 0 | **18/19** | 3.1 s | 3/24 |

Fünf Fragen sind nicht automatisch bewertbar (Ermessen) und werden getrennt ausgewiesen; sie zählen
nicht in die Quote. Der test-Split blieb unangetastet.

**Verbleibender Fehlschlag D23** (englische Frage nach der Besucherparkkarte): Die Antwort ist inhaltlich
richtig (CHF 5.00, aus der Webseite), aber § 13 war nicht im Kontext. Das ist teils ein zu strenges Label
– die Webseite genügt für die Antwort – und teils ein echter Befund: Auf dem englischen Pfad erreicht die
Erlassquelle den Kontext nicht, weil das BM25-Netz bei englischen Fragen nicht greift. **Das Label wurde
nicht gelockert**; René entscheidet beim Prüfen des Label-Sheets.

**Prompt-Iterationen:** drei, alle aus Dev-Beobachtungen und alle als allgemeine Regeln formuliert, nicht
als Einzelfall-Korrekturen (Trennung Verkürzung/Widerspruch; Beträge beziffern statt umschreiben;
keine Verweisziele nennen). Bei 24 Dev-Fragen ist die Gefahr der Überanpassung real und im Pilotbericht
zu nennen.

## Der Grounding-Checker hat drei Generierungsfehler gefunden

Nicht umgekehrt. Das ist das stärkste Argument für die zweite Schicht:

1. **Falsch behaupteter Widerspruch.** Antwort nannte CHF 30 und CHF 60 korrekt, behauptete aber, Webseite
   und Erlass widersprächen sich. Tatsächlich nennt die Webseite nur einen der beiden geregelten Tarife.
2. **Unbelegtes Verweisziel.** «Ob Parkkarten verfügbar sind, können Sie über den Online-Schalter in
   Erfahrung bringen.» Die Quelle sagt, dort könne man Parkkarten *bestellen* – nicht, man könne die
   Verfügbarkeit abfragen.
3. **Erfundene Webadresse.** Bei der Frage nach der Hundeanmeldung nannte das Modell stadtzug.ch, was in
   den Quellen nicht steht.

**Folge für die Architektur:** Verweise, Kontaktangaben und der englische Rechtshinweis werden jetzt
**deterministisch von der Pipeline angehängt**, nach der Grounding-Prüfung. Das Modell erzeugt
ausschliesslich Text, der aus den Quellen belegbar ist, und darf keine Kontaktstelle, Telefonnummer,
Webadresse oder ein weiterführendes System nennen. Eine halluzinierte Telefonnummer wäre ein schwerer
Fehler; Nummern aus dem Prompt hätten ausserdem Schicht A ausgelöst, weil sie nicht im Kontext stehen.

## Ermessensfälle: mein vorläufiges Urteil (von René zu bestätigen)

| ID | Frage | Urteil | Mangel |
|---|---|---|---|
| D02 | Was kostet eine Stunde parkieren? | erfüllt | Unterscheidet § 6, § 7 und Webseiten-Tarif korrekt, ordnet den Webseiten-Tarif aber nicht dem Parkhaus zu – das kann das Modell nicht wissen, die Webseite sagt es selbst nicht (siehe Korpusmangel unten) |
| D16 | Anzahl Parkplätze Parkhaus Arena | erfüllt | – |
| D17 | Verfügbare Anwohnerkarten Zone 2 | erfüllt | – |
| D18 | Hundeanmeldung | erfüllt | Wird korrekt als ausserhalb des Themengebiets erkannt |
| D19 | «Ich brauche eine Parkkarte.» | erfüllt | Gibt Übersicht statt Rückfrage; das Gold-Label lässt beides zu |

## Befund für die Stadt Zug (Korpusmangel, nicht Systemmangel)
Der Abschnitt «Tarife / Kurzzeittarife» auf der Seite Parkieren enthält ausschliesslich **Parkhaus**-Tarife
(identisch mit § 18 Abs. 2 Bst. b), ist aber nicht als solcher bezeichnet und steht auf gleicher
Gliederungsebene wie «Parkhäuser». Die oberirdischen Tarife nach § 6 und § 7 (CHF 1.00–2.00/h) stehen
**gar nicht** auf der Webseite. Wer dort nach dem Stundentarif sucht, erhält den falschen Wert. Das ist
ein Hinweis, der im Pilotbericht an die Stadt gehen sollte: Der Assistent kann die Lücke aus dem Erlass
schliessen, die Webseite allein führt in die Irre.

## Latenz
Median 3.1 s. Ausreisser bei langen Antworten: 9 s und 14 s, weil die Grounding-Prüfung auf dem ganzen
Antworttext läuft und mit dessen Länge wächst. Für die Pilot-UI (Phase 6) folgt daraus: Antwort zuerst
anzeigen, Konfidenz und Quellenprüfung nachliefern. Das passt zum freigegebenen Prototyp, der die
Pilot-Ansicht ohnehin rechts und ausblendbar hat.

## Kontingent
Der API-Key läuft im Free Tier. Beim ersten Dev-Lauf ohne Pause scheiterten drei Fragen an
`429 RESOURCE_EXHAUSTED`; die Fehlerbehandlung hat korrekt eskaliert statt abzustürzen. Der Backoff wartet
bei 429 jetzt in Minutenschritten statt Sekunden und respektiert ein von der API genanntes `retryDelay`.
Jede Frage kostet zwei Modellaufrufe (Generierung und Grounding); bei einem Verstoss in Schicht A wird
der zweite gespart, weil das Urteil schon feststeht. Für den Pilotbetrieb mit mehreren Nutzenden ist ein
bezahltes Kontingent nötig.

## Offen für Phase 5
- Coverage thematisch prüfen, nicht nur nach Quellenart.
- Gewichtung von S1/S2/S3 und Schwelle kalibrieren, auf **allen** generierten Zeilen.
- Unabhängigkeit von Schicht B: ein anderes Modell oder eine deterministische Zweitprüfung erwägen.
- Kategorie `gedeckt_aber_veraltet` (Fall G10): Der Checker trennt nicht zwischen «steht wörtlich im
  Erlass» und «durch Fussnote überholt». Derzeit über den Generierungs-Prompt gelöst, nicht im Checker.
- Latenz: Grounding asynchron oder Antwortlänge begrenzen; Median ist in Ordnung, die Ausreisser nicht.
- **Asymmetrie Deutsch/Englisch.** Der englische Pfad ist schwächer: Erlassquellen erreichen den Kontext
  seltener (BM25-Netz greift nicht), und das Modell neigte dazu, deutsche Beträge zu umschreiben statt zu
  beziffern. Letzteres ist per Prompt behoben, das Retrieval nicht. Zu prüfen wäre, intern auf Deutsch zu
  retrieven und zu generieren und erst die fertige Antwort zu übersetzen – die Quellenangaben bleiben
  ohnehin deutsch.
- Confidence ist kein Mass für Nützlichkeit: D16 und D17 erreichen C = 0.92 bzw. 0.91, obwohl sie gar
  keine Sachauskunft geben. Richtig, denn «die Quellen enthalten dazu nichts» ist gut belegt. Bei der
  Kalibrierung muss die Deckungslücke über `unvollstaendig` und Coverage laufen, nicht über C.
