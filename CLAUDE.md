# CLAUDE.md – RAG Citizen Service Assistant Stadt Zug

## Zuerst lesen (in dieser Reihenfolge)
1. `ZG_scope_and_corpus.md` – Entscheide, Korpus-Inventar, technische Befunde
2. `Vorlagen/1. PROJECT_BRIEF_KANTON_ZUG_RAG_OneNoteCoPilot.md` – Anforderungen (Achtung: Brief sagt "Canton Zug" und "Parking Services", gemeint ist **Stadt Zug, alle Mobilitätsthemen**)
3. `Claude outputs for Code/2.detailed_KANTON_ZUG_RAG_STARTER_PACK/` (01-06, kurze Eckpunkte: Brief, Architektur, Crawling, Governance, Pitch, Implementierungsplan)
4. `Vorlagen/RAGChatBotSZ/INDEX.md`, `001-prototype-build-and-deploy.md`, `SESSION_RECAP_fromCode_PM4 prototype status.md` – Erfahrungen aus dem Schwyz-Prototyp
5. `zg_rag_prototype.html` – genehmigter UI-Entwurf (Mock-Daten)
6. Projektberichte in `Vorlagen/REI_Community-RAG-Chatbot_…` bei Bedarf

## Rangfolge bei Widersprüchen
`ZG_scope_and_corpus.md` (Entscheide von René) > Starter-Pack > Brief in `Vorlagen/`. Brief und Starter-Pack sagen "Kanton Zug", "zg.ch" und "Parkieren"; gemeint sind **Stadt Zug**, stadtzug.ch + zug.tlex.ch und **alle Mobilitätsthemen**. Der Starter-Pack ist knapp (je Datei wenige Zeilen) und ergänzt den Brief.

## Übernahmen aus dem Starter-Pack
- Pipeline: Sprache erkennen → Retrieval → **Reranking** → LLM → Confidence → Antwort oder Eskalation.
- Komponenten: Crawler, Ingestion, Chunking, Embeddings, Vector DB, API, UI.
- Metadaten pro Dokument: URL, Titel, Dokumenttyp, Sprache, Änderungsdatum (zusätzlich: SRS-Nummer, `doc_type`, Abrufdatum).
- Governance: Quellenpflicht, Human-in-the-Loop, Eskalation bei Unsicherheit, Audit Trail, Datenschutz Schweiz, keine automatisierten Entscheide.
- Phasen: 1 Crawl, 2 Ingestion, 3 Vector DB, 4 RAG, 5 Confidence Scoring, 6 UI, 7 Pilot und Evaluation. Nach jeder Phase kurz berichten und Freigabe abwarten.
- `05_PITCH_FOR_HARALD_ROTTER.md` ist nur Hintergrund (Positionierung: Servicequalität statt Chatbot-Technologie), nichts daraus bauen.

## Scope
- Gemeinde: Stadt Zug (stadtzug.ch). Alle Themen unter https://stadtzug.ch/de/mobilitaet (Parkieren, Baustellen, Strassenverkehr, Winterdienst, Zufahrtsbewilligung, Elektromobilität, Gemeindestrassen/Wanderwege).
- Rechtstexte: SRS 7.7.5-1 (nächtliches Dauerparkieren) und SRS 7.7.5-2 von zug.tlex.ch. Volltext über `https://zug.tlex.ch/api/de/texts_of_law/<SRS>/show_as_json` (die Seite ist eine JS-App). Vorher robots.txt und Nutzungsbedingungen prüfen.
- Nur Information, keine Entscheide, Einsprachen oder Transaktionen. Mensch entscheidet.
- Online-Parkkartenschalter (pk.omcomputer.ch) nur verlinken.

## Sprache
- Quellen sind Deutsch. Frage auf Deutsch → Antwort auf Deutsch.
- Frage auf Englisch → Antwort auf Englisch **plus festen Hinweis**: Die englische Antwort ist nicht rechtsverbindlich, Amtssprache ist Deutsch, massgebend sind die deutschen Quellen. Quellenangaben bleiben unverändert.

## Technik-Entscheide
- Python-Pipeline wie Schwyz, plus Reranking: ingest → chunk_index → retrieve → rerank → generate → coverage + confidence → routing → auditlog. Reranker (lokal, mehrsprachig) in Phase 4 evaluieren und begründen.
- LLM: Gemini flash-lite. Vor Start Modellverfügbarkeit prüfen. Qualitätstest: Der Grounding-Checker muss einen erfundenen Preis (Fr. 200 statt 150) und eine erfundene Gültigkeitsdauer als `nicht_gedeckt` markieren.
- Embeddings lokal. Nicht Jina v2 de (liefert NaN-Vektoren unter onnxruntime 1.29 / Python 3.14); `paraphrase-multilingual-MiniLM-L12-v2` als Ausgangspunkt, Alternativen testen.
- Confidence C = gewichtet(S1 Retrieval, S2 Quellentreue, S3 Selbstbewertung). Schwelle wird kalibriert, nicht gesetzt.
- Coverage-Check unabhängig von C. Gebühren stehen oft nur auf Webseiten (z. B. Nachtparkieren CHF 30/Mt, Reglement nennt keinen Betrag) → `doc_type: gebuehrentarif` muss bei Gebührenfragen mitgeliefert werden.
- Hard-Routing (Rechtsmittel, Busse, Haftung) vor der Generierung, getrennt von Confidence-Eskalation.
- Audit-Log mit salted SHA-256-Pseudonymen, Rohfrage nie speichern.
- Hinweis: In Erlassen heisst "Polizeiposten/Stadtpolizei" heute "Abteilung Sicherheit und Verkehr".

## Stolpersteine aus Schwyz
- Leerzeile in einem `<style>`-Block beendet Streamlits Raw-HTML-Block → Leerzeilen vor Injection entfernen.
- Site-Chrome (Navigation, Login) im Content-Container beim Crawlen entfernen, sonst verschmutzt es jeden Chunk.
- Gescannte PDFs brauchen OCR. Vor dem Indexieren prüfen, ob ein Textlayer existiert.
- Kalibrierung auf **allen generierten** Zeilen, nicht nur auf automatisch beantworteten.
- Regex-Muster auf Kyrillisch-Lookalikes prüfen (ein Cyrillic "е" hat "busse" gebrochen).
- Fehlerbehandlung für API-Überlast (503): Retry mit Backoff, deutsche Fehlermeldung statt Traceback.
- API-Key nie ins Repo (`.env` gitignored, Secrets im Hosting).
- Streamlit Cloud deployt bei jedem Push automatisch; bei scheinbar fehlender Änderung Browser hart neu laden.

## UI
- Design angelehnt an zg.ch: Inter; primary-650 #435075, primary-600 #353f72, primary-800 #252342, secondary-500 #0070b8, support-100 #f5f9ff, Akzent #e07031; H1 34px/700 #150023.
- Layout wie Prototyp: Bürger-Ansicht links, ausblendbare Pilot-Ansicht (Konfidenz, Pipeline, Wissensbasis) rechts.
- Das offizielle Logo nicht nachbauen; Platzhalter-Wortmarke verwenden.

## Arbeitsweise
- Phase 1 (Crawl) und Korpus-Inventar zuerst, dann Plan zur Freigabe. Nichts über den freigegebenen Schritt hinaus bauen.
- Befunde, die dem Brief widersprechen, in `PROGRESSION/` festhalten (Muster: INDEX.md + NNN-slug.md wie bei Schwyz).
- Offenes Thema der Schwyz-Arbeit: Evaluation war nie vollständig durchgelaufen. Für Zug von Anfang an einplanen (Testset, Label-Sheet, Kalibrierung).
