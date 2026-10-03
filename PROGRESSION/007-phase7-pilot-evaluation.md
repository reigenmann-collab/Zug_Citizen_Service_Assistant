# 007 – Phase 7 Pilot und Evaluation (2026-10-03)

## Feedback-Schleife nachgerüstet
In der Pilot-Ansicht steht jetzt die Karte **Beurteilung**: richtig / teilweise / falsch / unklar,
dazu Kürzel der beurteilenden Person und eine Bemerkung. Das Urteil geht über
`rag.auditlog.urteil_eintragen()` als eigene Zeile ins Audit-Log; das Protokoll bleibt append-only.

Dafür hat jede Antwort eine eigene Kennung `antwort_id` bekommen. Das Pseudonym allein genügte nicht:
es ist der Hash der Frage und bei wiederholter Frage identisch – ein Urteil liesse sich dann nicht
genau einer Antwort zuordnen.

`eval/urteile.py` führt Antworten und Urteile zusammen und sagt, wie weit der Pilot ist. Es setzt
**keine Schwelle**, solange weniger als 30 von Menschen als falsch markierte Antworten vorliegen, und
begründet das mit dem Intervall aus Phase 5. Es zeigt ausserdem, welche der falschen Antworten **von
keinem strukturellen Signal** erfasst wurden – das sind die wichtigsten Fälle, weil sie heute unbemerkt
durchgehen.

Im Browser geprüft: Urteil abgegeben, im Log geschrieben, über `antwort_id` der Antwortzeile zugeordnet.

## Auswertung des test-Splits – einmalig

Der test-Split war seit Phase 3 reserviert und wurde in Phase 4 bis 6 weder gemessen noch gelesen.
Jetzt einmal ausgewertet, mit der Konfiguration vom Ende der Phase 6:

| Split | automatisch bewertbar | Ermessen | Median |
|---|---|---|---|
| dev (zum Abstimmen benutzt) | 18/19 (95 %) | 5 | 3.1 s |
| **test (unberührt)** | **16/17 (94 %)** | 3 | 4.3 s |

**Kein nennenswerter Abstand zwischen dev und test.** Das spricht dagegen, dass die drei
Prompt-Iterationen aus Phase 4 den Dev-Split überangepasst haben. Es sagt **nichts** darüber, wie das
System auf echten Bürgerfragen abschneidet: beide Sätze stammen von mir und sind aus dem indexierten
Korpus abgeleitet (eval/README.md).

Hard-Routing: 4/4 (T12, T13, T16, T20), davon T16 und T20 Fälle, die zugleich nicht gedeckt wären.
Englische Fragen: 2/2.

## Was der unberührte Split zutage gefördert hat

Vier Antworten wurden als `nicht_gedeckt` markiert – im Dev-Split war es eine. Nachgeprüft:

| Fall | Urteil | Befund |
|---|---|---|
| T04 | **zu Recht** | Antwort zitiert «§ 6» für die Arbeitgeberbestätigung; richtig ist § 11 Abs. 3 Bst. d |
| T14 | **zu Recht** | Zitiert «§ 12» für die Kurzzeittarife; § 12 regelt die Anwohnerparkkarte |
| T07 | **Fehlalarm** | B behauptet eine Vertauschung von Blau und Rot und gibt in der eigenen Begründung genau dieselbe Zuordnung wieder wie die Antwort |
| T17 | **Fehlalarm** | B zieht die Behauptung aus der **Frage** («kostet CHF 50») und übersieht, dass die Antwort sie verneint |

Zwei echte Fundstellenfehler und zwei Schwächen des Prüfers. Beides wäre im Dev-Split nicht aufgefallen.

**Dass Schicht B falsche Fundstellen findet, war nicht geplant.** Für eine Verwaltungsauskunft ist ein
falscher Paragraphenverweis ein ernster Fehler – die Nachvollziehbarkeit ist der Zweck der Zitate –, und
Schicht A kann ihn prinzipiell nicht sehen.

### T17 war ein Fehler in Prüfer **und** Label
Die Antwort korrigierte die Falschannahme korrekt. Schicht A wertete die CHF 50 als erfundene Zahl,
weil sie nicht im Kontext steht – sie stand in der Frage. Und mein Label verbot die Zeichenfolge «50»
in der Antwort, obwohl eine Korrektur die falsche Zahl benennen muss. Der einzige Fehlschlag des
test-Splits geht damit auf zwei Fehler von mir zurück, nicht auf die Antwort.

## Behoben, verifiziert am getrennten Instrument

Der Adversarial-Satz wurde um vier Fälle für genau diese Muster erweitert (G13 bis G16), **nicht** am
test-Split abgestimmt:

- **G13** Korrektur einer Falschannahme → muss `gedeckt` sein
- **G14** korrekte Wiedergabe einer Zuordnung → darf nicht als Vertauschung gelten
- **G15** richtiger Inhalt, falsche Fundstelle → muss `nicht_gedeckt` bleiben
- **G16** Bestätigung der falschen Annahme → muss `nicht_gedeckt` sein (Gegenprobe zu G13)

Änderungen:
1. **Schicht A** nimmt Zahlen aus der Frage aus. Eine Falschannahme lässt sich nur korrigieren, indem
   man sie benennt.
2. **Schicht B** bekommt die Frage zur Einordnung, eine ausdrückliche Regel zu Verneinungen («bewerte
   die Aussage, die die Antwort tatsächlich macht, nie die, die sie verneint»), die Weisung, bei
   `nicht_gedeckt` die Fundstelle zu benennen, auf die sie sich stützt, und den Hinweis, dass eine
   falsche Fundstelle bei richtigem Inhalt ebenfalls `nicht_gedeckt` ist.

| | vorher | nachher |
|---|---|---|
| Adversarial-Satz | 15/16 | **16/16** |
| Schicht A allein | 12/16 | 12/16 |

G16 bestätigt, dass die Ausnahme in Schicht A keine Lücke öffnet: Bestätigt das Modell die falsche Zahl,
fängt Schicht B es weiterhin.

**Der test-Split wurde nach der Korrektur bewusst nicht erneut gemessen.** Ich kenne die Items jetzt;
eine zweite Messung wäre kein unabhängiger Wert mehr. 16/17 bleibt als Schätzung stehen, mit dem
Vermerk, dass der eine Fehlschlag und zwei der vier Hinweise auf behobene Fehler zurückgehen. Für eine
neue unabhängige Zahl braucht es neue Fragen – am besten echte aus dem Pilotbetrieb.

## Plan für den Pilotbetrieb

**Was zu beobachten ist**, in dieser Reihenfolge:
1. Antworten, die von **keinem** strukturellen Signal erfasst sind und trotzdem falsch waren. Das sind
   die Fälle, für die es heute keine Erkennung gibt. `eval/urteile.py` weist sie getrennt aus.
2. Fehlalarmquote der Hinweise. Bei vier Flaggen im test-Split waren zwei Fehlalarme. Schlägt der
   Hinweis zu oft grundlos an, verliert er seine Wirkung.
3. Fragen, die gar nicht gedeckt sind. Sie zeigen, wo der Korpus zu erweitern ist.
4. Antwortzeit. Gemessen 3 bis 35 Sekunden, abhängig von der Auslastung des Sprachdiensts.

**Wann eine Schwelle gesetzt werden darf:** erst wenn mindestens 30 von Menschen als falsch markierte
Antworten vorliegen **und** das Bootstrap-Intervall der AUC die 0.5 nicht mehr einschliesst. Beides
prüft `eval/urteile.py` automatisch. Bis dahin bleibt die Eskalation strukturell.

**Voraussetzungen, die vor dem Pilotstart erfüllt sein müssen:**
- `AUDIT_SALT` in den Streamlit-Secrets. Sonst erzeugt jeder Neustart ein neues Salz.
- **Externe Ablage für das Audit-Log.** `data/audit/` liegt im flüchtigen Container von Streamlit Cloud
  und ist nach einem Neustart weg. Ohne Ablage entstehen keine Kalibrierungsdaten – dann läuft der
  Pilot, ohne das zu liefern, wofür er da ist. Das ist der wichtigste offene Punkt.
- Bezahltes API-Kontingent. Im Free Tier scheiterten bei einem ungebremsten Durchlauf drei von
  24 Fragen am Minutenlimit.
- Geklärt, dass Frage und Kontext an Google gehen dürfen.

## Offene Punkte, die in den Schlussbericht gehören
- **Die Testfragen stammen von mir** und sind nicht unabhängig vom geprüften System. Die 94 % sind eine
  Aussage über den abgedeckten Fragetyp, nicht über die Leistung bei echten Bürgerfragen.
- **Die Labels sind pauschal bestätigt**, nicht zeilenweise geprüft (`label_quelle:
  rene_bestaetigt_pauschal`). Das Prüfblatt `eval/label_sheet.xlsx` ist unverändert. Die Rückfrage zu
  D23 (genügt bei Gebührenfragen die Webseite, oder muss die Erlassquelle dabei sein?) ist offen.
- **Die Confidence ist nicht kalibriert** und wird nicht zur Eskalation benutzt (PROGRESSION/005).
- **Der englische Pfad ist schwächer**: Erlassquellen erreichen den Kontext seltener, weil das
  BM25-Recall-Netz bei englischen Fragen nicht greift.
- **S2 ist nicht unabhängig** – Schicht B benutzt dasselbe Modell wie die Generierung.
- **Barrierefreiheit der Oberfläche ungeprüft.**
- **Befund für die Stadt Zug:** Der Abschnitt «Tarife / Kurzzeittarife» auf der Parkieren-Seite enthält
  ausschliesslich Parkhaus-Tarife, ist aber nicht so bezeichnet; die oberirdischen Tarife nach § 6 und
  § 7 fehlen auf der Webseite ganz. Wer dort den Stundentarif sucht, erhält den falschen Wert.
