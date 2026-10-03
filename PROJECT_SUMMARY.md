# Project Summary: RAG-Assistent Mobilität, Stadt Zug

Stand: 2026-10-03. Ausgangsbasis für weitere Gemeinden. Detailbefunde je Phase stehen in
[PROGRESSION/](PROGRESSION/INDEX.md), Einstieg für den Betrieb in [README.md](README.md).

---

## 1. Was das System tut

Bürgerinnen und Bürger stellen eine Frage zu Mobilitätsthemen einer Gemeinde in eigenen Worten
(Deutsch oder Englisch). Der Assistent antwortet **ausschliesslich aus den offiziellen Quellen**
(Webseiten, Reglemente, Verordnungen, PDFs), zitiert sie und leitet alles, was er nicht sicher
beantworten kann, an eine menschliche Stelle weiter.

Er gibt Auskunft, er entscheidet nicht. Rechtsmittel, Bussen und Haftungsfragen gehen ohne
Modellaufruf direkt an die zuständige Stelle.

## 2. Ergebnisse (Stadt Zug, Pilot-Stand)

| Messgrösse | Ergebnis | Aussagekraft |
|---|---|---|
| Dev-Split, automatisch bewertbar | 18/19 korrekt | Zum Abstimmen benutzt, daher optimistisch |
| Test-Split, einmal gemessen | 16/17 korrekt | Unberührt bis Phase 7, danach nicht mehr unabhängig |
| Grounding-Checker, Adversarial-Satz | 16/16 | Konstruierte Fälle, kein Bürgerdatensatz |
| Hard-Routing (Rechtsmittel, Busse, Haftung) | 7/7 dev, 4/4 test, 0 Fehlalarme | Stichprobe klein |
| Retrieval Hit@5 (27 Fragen) | 26/27 | Smoke-Test, vom Autor der Fragen geschrieben |
| Confidence C trennt richtig/falsch | **nicht nachweisbar** (AUC 0.630, Intervall 0.452–0.791) | Entscheidend: keine Schwelle gesetzt |
| Antwortzeit | Median 3–14 s, Spitzen bis 35 s | Schwankt mit dem Free-Tier-Sprachdienst |

**Wichtigste Einschränkung:** Alle Fragen und Gold-Antworten stammen vom Entwickler-Assistenten
(Claude), abgeleitet aus dem indexierten Korpus. Die Zahlen beschreiben den abgedeckten Fragetyp,
nicht die Leistung bei echten Bürgerfragen. Eine belastbare Aussage braucht Fragen aus dem
Pilotbetrieb und zeilenweise geprüfte Labels.

## 3. Architektur

```
Frage ──► Sprache (de/en) ──► Hard-Routing ──► [Eskalation ohne LLM]
                                  │
                                  ▼
                 Retrieval: dense (FAISS) + BM25-Recall-Netz
                                  │
                                  ▼
                 Coverage: Gebühren nur mit Webseite UND Erlass
                                  │
                                  ▼
                 Generierung (Gemini 3.1 flash-lite, strukturiert)
                                  │
                                  ▼
           Grounding: Schicht A (Zahlen, deterministisch)
                      Schicht B (Aussagen, LLM)
           Vollständigkeit: Beträge der Quelle in der Antwort?
                                  │
                                  ▼
     Entscheid: beantwortet | mit Hinweis | eskaliert  (strukturell, nicht C)
                                  │
                                  ▼
     Deterministisch angehängt: Kontakt, EN-Rechtshinweis
                                  │
                                  ▼
            Audit-Log (gesalzenes Pseudonym, keine Rohfrage)
```

Kernprinzip: **Das Modell erzeugt nur belegbaren Text. Alles, was verweist oder verpflichtet
(Kontaktstellen, Telefonnummern, Webadressen, Rechtshinweise), hängt die Pipeline deterministisch an.**
Das ist die wichtigste Lehre des Projekts, siehe Abschnitt 5.

## 4. Repository-Aufbau

| Pfad | Inhalt | Wiederverwendbar? |
|---|---|---|
| `crawler/crawl.py` | Crawl einer Gemeindewebseite, Sitemap, robots.txt, Link-Tiefe | **ja**, Domain und Startseiten anpassen |
| `crawler/crawl_extra.py` | Anhänge von Erlassen, Mobilitäts-News | Zug-spezifisch (tlex-Anhänge) |
| `ingest/extract_html.py` | Site-Chrome entfernen, Überschriftenpfad, Tabellen | **ja** |
| `ingest/extract_law.py` | Erlass-JSON → Paragraphen, Fussnoten aufgelöst | **nur** für tlex-JSON; andere Gemeinden anders |
| `ingest/ingest.py` | Relevanz-Tagging, PDF-Textlayer-Prüfung, Duplikate | Relevanz-Regeln Zug-spezifisch |
| `ingest/chunk.py` | Chunking: Erlass je §, Web je Abschnitt, PDF je Seite | **ja**, Regeln generisch |
| `ingest/index.py` | fastembed + FAISS, NaN-Prüfung | **ja** |
| `rag/retrieve.py` | dense, BM25-Netz | **ja** |
| `rag/rerank.py` | Cross-Encoder (gemessen, im Pilot abgeschaltet) | ja, optional |
| `rag/norm.py` | Homoglyphen, Umlaute, Normalisierung | **ja** |
| `rag/lang.py` | DE/EN-Erkennung | **ja** |
| `rag/routing.py` | Hard-Routing-Muster (Rechtsmittel, Busse, Haftung) | Muster generisch, **Kontaktstelle anpassen** |
| `rag/coverage.py` | Gebührenregel, Vollständigkeit paralleler Beträge | **ja** (Gebührenregel ggf. anpassen) |
| `rag/generate.py` | Systemprompt DE/EN, Quellenblöcke | **Prompt ist Zug-spezifisch**, Struktur übernehmen |
| `rag/grounding.py` | Schicht A und B | **ja** |
| `rag/confidence.py` | strukturelle Eskalation, Warnschwelle Retrieval | **ja** |
| `rag/auditlog.py` | Pseudonyme, Urteile | **ja** |
| `rag/pipeline.py` | Ablauf | **ja**, Konstanten prüfen |
| `rag/llm.py` | Gemini, Backoff, 429-Behandlung | **ja** |
| `app.py`, `ui/` | Streamlit-Oberfläche nach Entwurf | Texte und Farben anpassen |
| `eval/` | Testset, Adversarial-Satz, Evaluation, Kalibrierung | **Methodik ja**, Inhalt neu schreiben |
| `PROGRESSION/` | Befunde je Phase | Vorlage für das Protokoll |
| `CLAUDE.md` | Projektvorgaben | Vorlage, Gemeinde-Details ersetzen |

## 5. Lehren, die auf andere Gemeinden übertragbar sind

**Quellen und Korpus**
1. **Webseiten verkürzen Rechtstexte.** Die Webseite nannte CHF 30 pro Monat; der Erlass unterscheidet
   CHF 30 und CHF 60 je nach Bedingung. Erlass und Webseite müssen zusammen geprüft werden.
2. **Gebühren stehen oft im Erlass, nicht nur auf Webseiten.** Die Vorannahme aus dem Brief war nur
   teilweise richtig. Vor dem Coverage-Check den Korpus prüfen.
3. **Die Webseite kann eine Tabelle zeigen, die nur einen Teil der Regeln abdeckt.** Hier: Parkhaus-
   Tarife ohne Hinweis, dass die oberirdischen Tarife fehlen. Das ist ein Befund für die Gemeinde selbst.
4. **Sitemap und Navigation erfassen nicht alle Unterseiten.** Der Crawler muss den Inhalt des Hauptbereichs
   auslesen, bevor die Navigation entfernt wird – sonst fehlen die Kacheln mit den Links.
5. **Fussnoten in Erlassen** (z. B. «heute: Abteilung Sicherheit und Verkehr») müssen aufgelöst
   werden, sonst gibt der Assistent veraltete Bezeichnungen aus.

**Retrieval**
6. **Hybrid-Suche (RRF) hat aggregiert verschlechtert** und war gleichzeitig falsch bewertet: Im Einzelfall
   lag der richtige Erlass-Chunk im dichten Index auf Rang 134, bei BM25 auf Rang 4. Lösung: BM25 als
   **Recall-Netz** mit zusätzlichen Chunks, nicht als Ranking-Faktor. Englische Fragen profitieren nicht.
7. **Chunking darf Themengrenzen nicht überschreiten.** Ein kurzer Unterabschnitt hat einen Nachbarabschnitt
   verschluckt; der Chunk trug dann einen falschen Pfad. Regel: Nur eigene Unterabschnitte zusammenfassen.
8. **Reranker**: Der mehrsprachige Cross-Encoder wirkt, braucht aber ~3,1 GB RAM. Der englischsprachige
   MS-MARCO-Reranker verschlechtert Deutsch deutlich. Hosting-Limit vorab klären.
9. **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2` ist gleich gut wie mpnet, halb so gross. Jina v2
   de lieferte NaN-Vektoren (wie in Schwyz). Immer NaN-Prüfung einbauen.

**Generierung und Prüfung**
10. **Das Modell verschweigt Varianten.** Dieselbe Frage, identischer Code, Temperatur 0: einmal alle
    Beträge, einmal nur einer. Eine Gebührenauskunft darf nicht vom Prompt-Zufall abhängen → deterministische
    Vollständigkeitsprüfung auf **parallele Absätze** desselben Paragraphen. Enger zugeschnitten fällt
    sie nicht bei jeder Stufenliste an.
11. **Der Grounding-Prüfer verwechselt Verneinungen.** «Die Aussage, X koste 50, ist nicht korrekt» wird als
    Behauptung von 50 gelesen. Zahlen aus der Frage müssen für Schicht A ausgenommen werden, und der
    Prüfer braucht die Regel «bewerte die Aussage, die die Antwort tatsächlich macht».
12. **Der Prüfer findet echte Fehler, die man nicht erwartet.** Falsche Paragraphenverweise (Inhalt richtig,
    Fundstelle falsch) wurden nur über Schicht B gefunden. Schicht A kann sie prinzipiell nicht sehen.
13. **Schicht B benutzt dasselbe Modell wie die Generierung.** Keine unabhängige Prüfung. Für einen
    produktiven Einsatz ein zweites Modell erwägen.
14. **Verweise, Telefonnummern, Webadressen nie vom Modell erzeugen lassen.** Es hat «stadtzug.ch» und
    einen Online-Schalter mit Funktionen genannt, die die Quelle nicht hergibt. Pipeline hängt sie an.
15. **Die Confidence trennt nicht.** Die Komponenten sind gesättigt (S2 = 1.0 in 99 % der Fälle, S3 = 1.0
    in 87 %). C ist praktisch konstant. **Keine Schwelle setzen, bevor Pilotdaten vorliegen.** Eskalation
    über strukturelle Gründe: Hard-Routing, Coverage-Lücke, Dienstfehler (unterdrückt), Grounding,
    Unvollständigkeit, Betragsvollständigkeit (mit Hinweis).

**Evaluation**
16. **Der test-Split ist einmal messbar.** Wer ihn nach jeder Änderung misst, hat keinen Testsatz mehr.
17. **Die Testfragen dürfen nicht vom Entwickler-Assistenten stammen, wenn eine Zahl belastbar sein soll.**
    Nur Ihr System, Ihre Stadt, Ihre Bürgerfragen. Für eine neue Gemeinde: zuerst Fragen aus Anfragen an
    die Verwaltung sammeln, dann erst bauen.
18. **Kalibrierung braucht Fehlerbeispiele.** Ohne mindestens 30 als falsch markierte Antworten ist jede
    Schwelle Rauschen. Die Feedback-Schleife (Beurteilung in der Pilot-Ansicht) ist deshalb Pflicht.
19. **Kalibrierung auf allen generierten Zeilen**, nicht nur auf den automatisch beantworteten (Schwyz-Lehre).

**Betrieb und Technik**
20. **Streamlit: ein HTML-Block pro Konversation.** Offene `<div>` über mehrere `st.markdown`-Aufrufe
    funktionieren nicht; der Chatrahmen bleibt leer.
21. **Streamlit: Leerzeilen im `<style>`-Block** beenden den Raw-HTML-Block (Schwyz-Lehre). `css()` entfernt sie.
22. **Frage sofort anzeigen**, bevor die Antwort fertig ist. Sonst wirkt die App bei 3–35 s Antwortzeit
    hängengeblieben.
23. **Free Tier ist für den Pilot zu knapp.** 429 RESOURCE_EXHAUSTED tritt nach wenigen Anfragen auf. Backoff
    muss in Minuten rechnen, nicht in Sekunden. Bezahltes Kontingent einplanen.
24. **Audit-Log auf Streamlit Cloud ist flüchtig.** Ohne externe Ablage keine Kalibrierungsdaten.
25. **`AUDIT_SALT` in den Secrets.** Ohne festen Wert ist das Pseudonym nach jedem Neustart neu.
26. **Eigene `antwort_id` je Antwort.** Das Frage-Pseudonym ist bei wiederholter Frage identisch; ein Urteil
    liesse sich sonst nicht zuordnen.
27. **Patches mit Heredoc und Python-Strings:** Backslash-Escapes (`\n`, `\u`) werden beim Schreiben verfälscht.
    Mehrfach passiert (Syntaxfehler, verschluckte Ersetzungen). Bei komplexen Änderungen den Editor nehmen,
    danach `ast.parse` und Import prüfen.

## 6. Playbook: neue Gemeinde

Geschätzter Aufwand bei gleicher Technik: **einige Tage für den Korpus, eine Woche für Evaluation und Pilot.**
Die Pipeline selbst muss nicht neu gebaut werden.

1. **Scope klären.** Welche Themen (nicht nur Parken), welche Sprachen, welche Rechtstexte. Entscheid
   schriftlich festhalten (Vorlage: `ZG_scope_and_corpus.md`).
2. **Robots und Nutzungsbedingungen prüfen**, Sitemap lesen, Hauptbereich identifizieren.
3. **Crawl** (`crawler/crawl.py` mit neuen Startseiten). Rohdaten vollständig speichern.
4. **Erlasse holen.** Prüfen, ob die Gemeinde eine JSON-API hat (wie tlex). Falls nicht: HTML-Parser für
   Paragraphen schreiben (`extract_law.py` als Vorlage).
5. **Korpus-Inventar** mit Relevanz-Tagging. Gebühren-Befunde: Webseite gegen Erlass prüfen.
6. **Ingestion und Chunking** (`ingest/`). Index bauen, NaN-Prüfung.
7. **Testfragen sammeln**, bevor gebaut wird: 20 bis 30 echte Fragen aus der Verwaltung, dazu
   Falschannahmen, Mehrdeutiges, Nicht-Gedecktes, Hard-Routing-Fälle. **Zwei Splits, dev und test,
   test wird nicht angefasst.**
8. **Prompt und Routing-Muster** an die Gemeinde anpassen: Kontaktstellen, Rechtsmittel-Begriffe, Sprache.
9. **Grounding-Adversarial-Satz** aus dem eigenen Korpus bauen (erfundene Zahl, verneinte Zahl, falsche
   Fundstelle, falsche Behörde).
10. **Evaluation auf dev**, Prompt-Iterationen als allgemeine Regeln, nicht als Einzelfall-Korrekturen.
11. **test einmal messen**, danach nicht mehr anfassen.
12. **Oberfläche** nach Gemeinde-Design (`ui/stil.py`, `ui/texte.py`), im Browser testen.
13. **Pilot** mit Feedback-Knopf, externer Log-Ablage, `AUDIT_SALT`, bezahltem Kontingent.
14. **Schwelle erst nach ≥30 falschen Urteilen** und stabilem Bootstrap-Intervall (`eval/urteile.py`).
15. **Befunde für die Gemeinde** sammeln (fehlende Tarife, widersprüchliche Seiten). Das ist oft
    der sichtbarste Nutzen für die Verwaltung.

## 7. Offene Punkte

- **Externe Ablage des Audit-Logs** für den Pilot (Blocker für Kalibrierung).
- **Datenschutz:** Frage und Kontext gehen an Google (Gemini). Für Schweizer Gemeinden vorab klären; der
  Brief verlangt «Swiss deployment preferred». Ein Schweizer oder lokaler Modellbetrieb wäre die Alternative.
- **Unabhängiges Testset** aus echten Bürgerfragen.
- **Zeilenweise Prüfung der Gold-Labels** (aktuell pauschal bestätigt, `eval/label_sheet.xlsx` unverändert).
  Die Rückfrage zu D23 ist offen.
- **Englischer Pfad schwächer**: Erlassquellen erreichen den Kontext seltener. Vorschlag: intern deutsch
  arbeiten, Antwort übersetzen.
- **Unabhängige Grounding-Prüfung** (zweites Modell).
- **Coverage thematisch statt nach Quellenart** prüfen.
- **Barrierefreiheit** der Oberfläche (Kontraste, Tastatur, Screenreader) ungeprüft.
- **Antwort sofort zeigen**, Prüfung nachliefern (würde `antworte()` in zwei Schritte teilen).
- **Feedback-Knopf** ist vorhanden, aber nur in der Pilot-Ansicht.
- **Latenz** im Free Tier nicht stabil messbar; Zielwert 5 s nicht belegt.

## 8. Entscheide, die Sie erneut prüfen sollten

| Entscheid | Begründung | Revision wann |
|---|---|---|
| Kein Cross-Encoder-Reranker im Pilot | 3,1 GB RAM, Community Cloud 2,7 GB pro App | bei ≥4 GB Hosting |
| Keine Confidence-Schwelle | AUC-Intervall schliesst 0.5 ein | nach ≥30 falschen Urteilen |
| Strukturelle Eskalation | nachvollziehbar, prüfbar, nicht an C gebunden | nach Pilotauswertung |
| Gemini flash-lite | verfügbar, günstig, Fehler wie oben | bei Hosting-Entscheid (Schweiz?) |
| MiniLM statt mpnet | gleiche Qualität, halb so gross | bei grösserem Korpus |
| BM25 nur als Recall-Netz | RRF hat gemessen geschadet | bei englischem Pfad |
| Testset vom Entwickler-Assistenten | schnell, aber nicht unabhängig | vor Pilotauswertung ersetzen |

## 9. Dateien für die Übergabe

- Quellcode: `app.py`, `rag/`, `ui/`, `ingest/`, `crawler/`, `eval/`
- Index und Korpus: `data/index/` (klein, im Repo), `data/clean/`, `data/raw/` (gross, nicht einchecken)
- Dokumentation: `README.md`, `PROJECT_SUMMARY.md` (diese Datei), `PROGRESSION/` (Phasen 1–7),
  `CLAUDE.md`, `ZG_scope_and_corpus.md`
- Konfiguration: `requirements.txt`, `.streamlit/config.toml`, `.streamlit/secrets.toml.example`, `.env.example`

Geheimnisse (`.env`, `.streamlit/secrets.toml`) sind gitignored. **Der während dieser Session im Chat
geteilte API-Schlüssel sollte rotiert werden.**
