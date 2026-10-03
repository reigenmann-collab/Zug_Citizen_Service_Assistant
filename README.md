# Mobilitäts-Assistent Stadt Zug

RAG-Assistent für Mobilitätsthemen der Stadt Zug: Parkieren, Baustellen, Strassenverkehr,
Winterdienst, Zufahrtsbewilligungen, Elektromobilität, Gemeindestrassen. Quellen sind
stadtzug.ch/de/mobilitaet und die Erlasse auf zug.tlex.ch.

**Der Assistent gibt Auskunft, er entscheidet nicht.** Rechtsmittel, Bussen und Haftungsfragen werden
ohne Modellaufruf an die zuständige Stelle weitergeleitet.

## Schnellstart lokal

```bash
pip install -r requirements.txt
cp .env.example .env            # GEMINI_API_KEY eintragen
streamlit run app.py
```

Index und Embeddings liegen im Repo (`data/index/`), es muss nichts neu gecrawlt werden. Beim ersten
Start lädt `fastembed` das Embedding-Modell nach (~240 MB, einmalig, in den Cache).

## Aufbau

```
crawler/    Phase 1  Crawl stadtzug.ch + tlex-API -> data/raw/
ingest/     Phase 2  Extraktion -> data/clean/   Phase 3  Chunking + FAISS -> data/index/
rag/        Phase 4  Pipeline: Sprache -> Routing -> Retrieval -> Coverage -> Generierung -> Grounding
            Phase 5  confidence.py: strukturelle Eskalation statt Schwelle
ui/         Phase 6  Stil und Texte der Oberfläche
app.py      Phase 6  Streamlit-Oberfläche
eval/       Testsets, Evaluation, Kalibrierung
PROGRESSION/ Entscheide und Befunde je Phase, INDEX.md zuerst lesen
```

Pipeline neu aufbauen (nur nötig, wenn sich die Quellen geändert haben):

```bash
python crawler/crawl.py && python crawler/crawl_extra.py
python ingest/ingest.py && python ingest/chunk.py
python ingest/index.py sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 minilm
```

## Evaluation

```bash
python eval/eval_pipeline.py --split dev        # Pipeline, dev-Split (test ist für Phase 7 reserviert)
python eval/eval_grounding.py                   # Grounding-Checker gegen erfundene Werte
python eval/kalibrierung.py                     # Confidence auf allen protokollierten Zeilen
python eval/kalibrierung_retrieval.py           # Retrieval-Gesundheit, ohne Modellaufruf
python eval/label_sheet.py                      # Prüfblatt für die Gold-Labels erzeugen
python eval/urteile.py                          # Beurteilungen aus dem Pilotbetrieb auswerten
```

Der **test-Split ist reserviert** und wurde einmal ausgewertet (Phase 7, 16/17). Wer ihn erneut misst,
erhält keinen unabhängigen Wert mehr und sollte das im Bericht vermerken.

## Deployment auf Streamlit Community Cloud

1. **Eigenes Repository** anlegen (nicht das des Schwyz-Prototyps) und pushen. Mit muss:
   `app.py`, `rag/`, `ui/`, `data/index/`, `requirements.txt`, `.streamlit/config.toml` – zusammen rund 2 MB.
   `data/raw/` (209 MB) ist gitignored und wird im Betrieb nicht gebraucht.
2. Auf share.streamlit.io die App anlegen, Hauptdatei `app.py`.
3. Unter **Settings > Secrets** eintragen:

   ```toml
   GEMINI_API_KEY = "..."
   AUDIT_SALT = "..."     # langer Zufallswert, siehe unten
   ```

4. Streamlit Cloud deployt bei jedem Push automatisch. Wenn eine Änderung nicht erscheint: Browser hart
   neu laden (Lehre aus dem Schwyz-Prototyp).

### Was beim Deployment zu beachten ist

- **`AUDIT_SALT` zwingend setzen.** Ohne festen Wert erzeugt jeder Neustart ein neues Salz, und die
  Pseudonyme im Audit-Log sind nicht mehr über Neustarts hinweg vergleichbar. Das Dateisystem von
  Streamlit Cloud ist flüchtig.
- **Das Audit-Log ist auf Streamlit Cloud nicht dauerhaft.** `data/audit/` liegt im Container und ist nach
  einem Neustart weg. Für den Pilotbetrieb braucht es eine externe Ablage, sonst entstehen keine
  Kalibrierungsdaten (siehe PROGRESSION/005).
- **Arbeitsspeicher.** Embedding-Modell und FAISS-Index passen in den Free Tier (~1 GB). Ein
  Cross-Encoder-Reranker **nicht** – gemessen rund 3.1 GB, deshalb ist er abgeschaltet
  (PROGRESSION/004).
- **API-Kontingent.** Jede Frage kostet zwei Modellaufrufe (Generierung und Prüfung). Im Free Tier
  reicht das für Demonstrationen, nicht für mehrere gleichzeitige Nutzende.
- **Datenschutz.** Frage und Kontext gehen an Google (Gemini). Für einen produktiven Einsatz bei einer
  Schweizer Gemeinde ist das vorab zu klären; der Brief verlangt «Swiss deployment preferred».

## Was dieser Assistent nicht tut

- Keine Entscheide, keine Rechtsauskunft, keine Beurteilung von Einzelfällen.
- Keine Transaktionen. Der Online-Parkkartenschalter wird nur verlinkt.
- Keine Auskunft zu Rechtsmitteln, Bussen oder Haftung – diese Fragen gehen an einen Menschen.
- Englische Antworten sind nicht rechtsverbindlich; Amtssprache ist Deutsch.

## Stand und Grenzen

Siehe `PROGRESSION/INDEX.md`. Die wichtigsten offenen Punkte:

- Die Confidence ist **nicht kalibriert**. 24 Testfragen reichen dafür nicht; die Zahl wird angezeigt,
  aber nicht zur Eskalation benutzt (PROGRESSION/005).
- Die Testfragen stammen von Claude und sind nicht unabhängig vom geprüften System (`eval/README.md`).
- Der englische Pfad ist schwächer als der deutsche: Erlassquellen erreichen seltener den Kontext.
- Die Antwortzeit schwankt stark mit der Auslastung des Sprachdiensts (gemessen 3 bis 35 Sekunden).
- Das Audit-Log braucht auf Streamlit Cloud eine **externe Ablage**, sonst entstehen keine
  Kalibrierungsdaten (PROGRESSION/007).
