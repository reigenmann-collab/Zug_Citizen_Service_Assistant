# 005 – Phase 5 Confidence und Kalibrierung (2026-10-03)

**Dev-Split, Endstand Phase 5: 18/19 automatisch bewertbare Fragen korrekt**, 5 Ermessensfälle
(Urteil in 004: alle erfüllt). Verbleibend D23, siehe offene Punkte.

## Das Ergebnis in einem Satz
**C lässt sich auf der vorhandenen Datenbasis nicht kalibrieren, und jede Schwelle wäre an Rauschen
angepasst.** Eskaliert wird deshalb nach strukturellen Gründen, nicht nach C. C bleibt als Anzeigewert
erhalten und ist im Code als `kalibriert=False` gekennzeichnet.

Das ist die Antwort auf die Vorgabe aus CLAUDE.md: «Schwelle wird kalibriert, nicht gesetzt.» Eine
plausibel aussehende Zahl zu setzen wäre genau der Schwyz-Fehler gewesen.

## Datenbasis
Kalibriert wurde auf **allen generierten Zeilen** aller Läufe, nicht nur auf den automatisch
beantworteten (ausdrückliche Lehre aus Schwyz). `eval/kalibrierung.py`:

- **96 protokollierte Zeilen aus 4 Läufen**, davon **84 generiert** und 12 vor der Generierung eskaliert
- 84 Zeilen mit Urteil: **75 richtig, 9 falsch** (64 automatisch bewertet, 20 nach dem in 004
  dokumentierten Ermessensurteil)
- Zeilen aus älteren Konfigurationen sind absichtlich enthalten. Die Frage ist nicht, welche
  Konfiguration besser ist, sondern ob die Zahl C überhaupt Information über Korrektheit trägt. Dafür
  sind auch frühere Zeilen gültige Beobachtungen – sie liefern überhaupt erst die Negativbeispiele.

## Warum C nicht trennt: die Komponenten sind gesättigt

| Komponente | min | Median | max | häufigster Einzelwert |
|---|---|---|---|---|
| S1 Retrieval | 0.487 | 0.708 | 0.882 | 5 % |
| S2 Quellentreue | 0.500 | 1.000 | 1.000 | **99 %** |
| S3 Selbstbewertung | 0.000 | 1.000 | 1.000 | **87 %** |
| C | 0.549 | 0.912 | 0.965 | 5 % |

S2 ist in 99 % der Zeilen genau 1.0, S3 in 87 % genau 1.0. C ist damit praktisch eine Konstante um 0.91
mit Rauschen aus S1. Und S1 bedeutet für richtige und falsche Antworten fast dasselbe
(Mittel 0.688 gegen 0.695) – die rohe Kosinus-Ähnlichkeit von MiniLM liegt für alles im Bereich 0.6–0.8.

### Trennschärfe (AUC: Wahrscheinlichkeit, dass eine richtige Antwort ein höheres C hat als eine falsche)

| Grösse | AUC | Mittel richtig | Mittel falsch |
|---|---|---|---|
| S1 | 0.556 | 0.687 | 0.690 |
| S2 | 0.556 | 1.000 | 0.944 |
| S3 | 0.554 | 0.948 | 0.889 |
| **C** | **0.630** | 0.890 | 0.851 |

**C: AUC 0.630, 95%-Intervall 0.452 bis 0.791** (2000 Bootstrap-Ziehungen). Das Intervall schliesst 0.5
ein. 0.5 bedeutet: kein Informationsgehalt. Es ist damit statistisch nicht nachweisbar, dass C besser
trennt als ein Münzwurf.

### Was eine Schwelle kosten würde

| Schwelle auf C | blockierte Antworten | davon richtig (unnötig weitergeleitet) | falsche gefangen | falsche durchgelassen |
|---|---|---|---|---|
| 0.80 | 6 | 4 | 2 | 7 |
| 0.85 | 14 | 12 | 2 | 7 |
| 0.90 | 30 | **25** | 5 | 4 |
| 0.95 | 80 | **71** | 9 | 0 |

Um etwa die Hälfte der falschen Antworten zu fangen, müsste man 30 Antworten weiterleiten, davon 25
richtige. Um alle zu fangen, 80 von 84. Das ist kein Qualitätsfilter, sondern die Abschaffung des Dienstes.

## Der tiefere Grund: zu wenige Fehler
Von den 9 falschen Antworten entfallen
- **4 auf dieselbe Frage D23** in vier Läufen – und dort ist die Antwort inhaltlich richtig, nur das
  Label verlangt zusätzlich die Erlassquelle (offene Rückfrage, siehe unten),
- **4 auf Konfigurationen, die es nicht mehr gibt** (D04, D05, D10, D12 – behoben durch Chunking-Fix,
  BM25-Netz und Prompt-Regeln),
- **2 auf D24**, behoben durch die Vollständigkeitsprüfung (siehe unten).

In der **aktuellen** Konfiguration bleibt auf den 24 Dev-Fragen genau **eine** als falsch gezählte Zeile,
und die ist strittig. Eine Schwelle auf einer Verteilung mit einem einzigen, bestrittenen Negativbeispiel
zu bestimmen, ist nicht möglich – nicht wegen schlechter Methode, sondern wegen fehlender Daten.

**Das ist keine gute Nachricht, sondern eine Messgrenze.** Dass das System auf meinen eigenen 24 Fragen
kaum Fehler macht, sagt wenig: Die Fragen sind aus dem indexierten Korpus abgeleitet (siehe
eval/README.md). Echte Bürgerfragen werden Fehler produzieren, die hier nicht vorkommen.

## Was stattdessen eskaliert: strukturelle Gründe
`rag/confidence.py`. Gemessen auf denselben 63 Zeilen:

| Signal | Zeilen | davon falsch | Fehlerquote |
|---|---|---|---|
| `grounding == nicht_gedeckt` | 1 | 1 | **100 %** |
| `unvollstaendig == true` | 19 | 3 | 16 % |
| `rueckfrage == true` | 4 | 0 | 0 % |
| `betrag_unvollstaendig` (neu, siehe unten) | 2 | 2 | **100 %** |
| Hard-Routing (Phase 4) | 9 | – | 7/7 korrekt erkannt |

Die Gründe sind in zwei Klassen geteilt, weil sie unterschiedlich schwer wiegen:

- **Antwort wird unterdrückt** (`eskaliert`): Hard-Routing, Coverage-Lücke, Dienstfehler. Hier fehlt die
  Grundlage für eine Auskunft ganz.
- **Antwort wird ausgegeben, mit Hinweis und Kontaktangabe** (`beantwortet_mit_hinweis`):
  Grounding `nicht_gedeckt`, `unvollstaendig`, `betrag_unvollstaendig`. Diese Antworten sind oft brauchbar; sie zu verschweigen
  wäre der schlechtere Dienst. Bei `nicht_gedeckt` wird zusätzlich im Antworttext darauf hingewiesen,
  dass die Antwort nicht vollständig gegen die Quellen abgesichert ist.

Vorteil gegenüber einer Punktzahl: Jede Eskalation hat einen benennbaren Grund, der im Audit-Log steht
und einer Bürgerin erklärbar ist. Das entspricht der Governance-Anforderung nach Nachvollziehbarkeit
besser als eine Zahl, die niemand prüfen kann.

## Ein Signal, das messbar trägt: Retrieval-Gesundheit
`eval/kalibrierung_retrieval.py`. Statt auf Antwort-Korrektheit (zu wenige Negativbeispiele) wurde auf ein
Ziel kalibriert, für das genügend Positiv- und Negativbeispiele vorliegen und das **ohne Modellaufruf**
bestimmbar ist: Ist die benötigte Quelle überhaupt im Kontext? Datenbasis 44 Fragen (24 Dev + 27
Smoke-Test, test-Split unberührt), davon 40 gefunden und 4 verfehlt.

| Merkmal | AUC |
|---|---|
| **top1 (Spitzen-Kosinus)** | **0.706** |
| top3_mittel | 0.688 |
| marge_1_10 | 0.600 |
| streuung_top10 | 0.594 |
| marge_1_4 | 0.481 |

top1: AUC 0.706, 95%-Intervall **0.562 bis 0.850** – schliesst 0.5 **nicht** ein. Das ist ein echtes,
wenn auch schwaches Signal. Bei der Schwelle 0.69 werden alle 4 Verfehlungen erkannt, dafür schlägt die
Warnung bei 18 von 44 Fragen an (Präzision 22 %).

**Einsatz:** als `retrieval_warnung` im Pilot-Bereich der UI, **nicht** als Weiterleitungsregel. 22 %
Präzision taugt für einen Hinweis an Mitarbeitende, nicht für eine Entscheidung. Beruht auf 4
Negativbeispielen und ist mit Pilotdaten zu revidieren. Nebenbefund: Deutsch 36/39 gefunden (92 %),
Englisch 4/5 (80 %) – zu wenige englische Fälle für eine Aussage, passt aber zur in 004 dokumentierten
Schwäche des englischen Pfads.

## Gewichte nicht angepasst, und warum
Der Brief verlangt C = gewichtet(S1, S2, S3). Die Gewichte bleiben bei 0.3 / 0.4 / 0.3. Gewichte lassen
sich nur an Daten anpassen, die zwischen richtig und falsch trennen; solche Daten liegen nicht vor. Eine
Umgewichtung hätte die Zahl verändert, ohne dass irgendetwas dafür spricht – das wäre Anpassung an
Rauschen mit dem Anschein von Sorgfalt.

## Eine Anforderung wurde dem Prompt-Zufall entzogen

Beim Prüflauf dieser Phase fiel D24 (Anwohnerparkkarte, englisch) zurück: **identischer Code, Temperatur
0, einmal vollständig (CHF 30 und CHF 60), einmal verkürzt (nur CHF 30).** Der Prompt war nachweislich
unverändert – es ist Modellvarianz. Eine Gebührenauskunft darf davon nicht abhängen.

Deshalb gibt es jetzt eine **Vollständigkeitsprüfung** als Gegenstück zum Grounding-Checker:

| | Richtung | Was wird gefunden |
|---|---|---|
| Grounding Schicht A | Antwort → Kontext | Beträge in der Antwort, die **nicht** in den Quellen stehen |
| Vollständigkeitsprüfung | Kontext → Antwort | Beträge in den Quellen, die in der Antwort **fehlen** |

Der Zuschnitt war der schwierige Teil. Ein erster Versuch, der alle Beträge zur gefragten Zeiteinheit
verlangte, erzeugte massive Fehlalarme: Bei «Was kostet eine Stunde parkieren?» forderte er sämtliche
Stundenstufen aus § 18 (CHF 3.00 bis 29.00), bei der Anwohnerparkkarte zusätzlich die Parkhaus-Mieten.

Die Prüfung greift jetzt nur beim Muster **paralleler Alternativen**: dieselbe Zeiteinheit kommt in
*mehreren Absätzen desselben Paragraphen* mit unterschiedlichem Betrag vor. Das trifft § 12 Abs. 1
(CHF 30) gegen Abs. 2 (CHF 60) genau. Mehrere Beträge innerhalb **eines** Absatzes sind verschiedene
Sachen – die Stundenstufen und Mietarten in § 18 Abs. 2 – und werden nicht verlangt.

Gemessen auf **84 protokollierten Antworten aus vier Läufen: 2 Auslösungen, beide der echte Fehler,
0 Fehlalarme.** Live verifiziert: Das Modell lieferte wieder nur CHF 30, die Prüfung ergänzte CHF 60 im
Antworttext und setzte den Entscheid auf `beantwortet_mit_hinweis`. D01 und D05 lösten nicht aus.

Das ist der zweite Fall in diesem Projekt, in dem eine deterministische Prüfung eine Anforderung
übernimmt, die der Prompt nicht zuverlässig trägt – nach den Kontaktangaben in Phase 4.

## Latenz: nicht stabil messbar
Drei Läufe mit identischem Code ergaben Median **3.1 s**, **9.1 s** und **14.5 s** (max 35.5 s). Im langsamen
Lauf hatte **keine** Generierung einen Wiederholungsversuch (`versuche: 1` in allen 21 Zeilen) – die
Verzögerung kam vom API-Endpunkt selbst, nicht vom Retry und nicht vom Code. Eine belastbare
Latenzangabe ist damit aus dieser Umgebung nicht zu gewinnen; die Anforderung «unter 5 Sekunden» ist mit
einem Free-Tier-Kontingent nicht prüfbar. Für den Pilotbericht: Antwort anzeigen, sobald sie vorliegt,
und die Quellenprüfung nachliefern.

Logging-Lücke, die dabei auffiel: Für den Grounding-Aufruf werden die Versuchszahlen nicht protokolliert,
nur für die Generierung. Vor dem Pilotbetrieb nachziehen.

## Voraussetzung für eine echte Kalibrierung
`rag/auditlog.py` hat jetzt `urteil_eintragen(pseudonym, urteil, …)` mit den Werten
`richtig | falsch | teilweise | unklar`. Das Protokoll bleibt append-only; das Urteil kommt als eigene
Zeile mit Bezug auf das Pseudonym hinzu. Damit erzeugt der Pilotbetrieb genau die Negativbeispiele, die
heute fehlen.

**Empfehlung für den Pilotbericht:** Die Confidence-Schwelle erst festlegen, wenn aus dem Pilotbetrieb
mindestens einige Dutzend von Menschen als falsch markierte Antworten vorliegen. Vorher ist jede Zahl
eine Behauptung. Bis dahin tragen die strukturellen Gründe die Eskalation.

## Offene Punkte
- **D23 ist ungeklärt.** Meine Rückfrage, ob bei Gebührenfragen immer die Erlassquelle im Kontext sein
  muss oder die Webseite genügt, wurde mit der pauschalen Label-Bestätigung nicht beantwortet. Das Label
  ist unverändert übernommen und in `testset.json` als `offene_frage` vermerkt. Es betrifft 4 der 9
  Negativbeispiele und verschiebt damit die Kalibrierungszahlen sichtbar.
- **Labels sind pauschal bestätigt, nicht zeilenweise geprüft.** In `testset.json` steht
  `label_quelle: rene_bestaetigt_pauschal` und `pruefart`. Das Prüfblatt ist unverändert. Für Phase 7
  sollten mindestens die 6 Prio-1-Zeilen zeilenweise durchgesehen werden.
- S2 ist nicht unabhängig: Schicht B des Grounding-Checkers benutzt dasselbe Modell wie die Generierung.
  Für den Pilotbetrieb erwägen, dafür ein anderes Modell zu nehmen.
- S3 als einzelne Zahl ist wertlos (84 % konstant 1.0). Falls S3 beibehalten wird, besser strukturiert
  erfragen (welche Teile der Frage sind gedeckt) statt als Punktzahl.
- Coverage thematisch prüfen statt nach Quellenart (offen aus Phase 4, hier nicht angefasst).

## Reproduzierbarkeit
Die Zahlen oben entstehen mit `python eval/kalibrierung.py` auf den vier Läufen in
`eval/pipeline_dev_*.jsonl` (96 Zeilen). Ein fünfter Lauf wurde beim Aufräumen versehentlich gelöscht;
die damit gerechneten Zwischenwerte (123 Zeilen, AUC 0.616, Intervall 0.468–0.769) sind nicht mehr
reproduzierbar und deshalb nicht übernommen. Am Ergebnis ändert das nichts: Das Intervall schliesst in
beiden Rechnungen 0.5 ein.
