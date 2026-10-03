# 003 – Phase 3 Chunking + Vector DB (2026-10-03)

## Ergebnis
- `ingest/chunk.py` → `data/index/chunks.jsonl`: **456 Chunks aus 42 Dokumenten** (Median 1046 Zeichen, max 2235; 9 Chunks < 100 Zeichen). Chunk-Typen: Erlass 101 (+13 Anhang), Web 103 + 16 Gebührentarif, Merkblatt-PDF 221, News 2.
- Chunking-Regeln: Erlass = 1 Chunk je § (bei >1400 Zeichen an Absatzgrenzen geteilt, Überlappung 150); Web = 1 Chunk je Abschnitt (nur Abschnitte < 140 Zeichen werden mit dem nächsten verbunden, damit z. B. "Nachtparkieren > Gebühren" nicht mit Velohaus gemischt wird); PDF = Seitenblöcke ~1400 Zeichen. Jeder Chunk trägt `embed_text` = "Titel | Pfad" + Text. Reine Fussnoten-Abschnitte und Navigationsreste ("Kontakt", "Formulare") entfernt.
- Metadaten je Chunk: chunk_id, doc_id, url, title, doc_type, relevance, srs, lang, modified, retrieved, has_fees, path.
- `ingest/index.py`: fastembed (lokal, ONNX) + FAISS IndexFlatIP auf normalisierten Vektoren; NaN-Prüfung (Assertion) eingebaut.

## Entscheide
- **Ausgeschlossen aus dem Index** (Planungs-/Fachdokumente, würden die Treffer dominieren): Handbuch Strassen und Plätze (3 Dubletten), Stadtraumkonzept 2050 (2 Titel), Räumliche Gesamtstrategie 2040, Charta öffentlicher Raum. Daten bleiben in `data/clean`. Umkehrbar über `EXCLUDE_TITLE` in `chunk.py`.
- **Embedding: `paraphrase-multilingual-MiniLM-L12-v2`** (fastembed, ONNX-quantisiert, 384d, 0.22 GB). Verglichen mit `paraphrase-multilingual-mpnet-base-v2` (768d, 1 GB): praktisch gleich (siehe unten), MiniLM ist 2× schneller und passt besser auf Streamlit Cloud. `multilingual-e5-large` (2.2 GB) nicht getestet (Hosting-Grenzen). Jina v2 de bewusst nicht (NaN, siehe CLAUDE.md).
- Vector Store: FAISS (Flat, 456 Vektoren, exakte Suche reicht). Index wird ins Repo eingecheckt (kein Neu-Embedden beim Start).

## Retrieval-Smoke-Test (`eval/eval_retrieval.py`, 27 Fragen in `eval/retrieval_testset.json`, DE + 2 EN)
| Modell | Hit@1 | Hit@3 | Hit@5 | Hit@10 |
|---|---|---|---|---|
| MiniLM-L12 | 16/27 | 23/27 | 26/27 | 26/27 |
| mpnet-base | 17/27 | 23/27 | 26/27 | 26/27 |
Hit = erwartetes Dokument UND erwartetes Textfragment im Top-k-Chunk. **Vorsicht:** Das Testset wurde von mir (dem Modell) geschrieben und ist nur ein Smoke-Test, kein Evaluationsset; Gold-Labels vor Phase 7 von René prüfen lassen.

## Schwächen, die Phase 4 adressieren muss
- Hit@1 nur 59 %: Reranker (Cross-Encoder, mehrsprachig) und evtl. Hybrid (BM25 + Embedding) nötig.
- Gebührenfragen: Webseite und Erlass konkurrieren (gewollt beide), aber Kurzfragen wie "Nachtparkieren Gebühr" landen auf Rang 4; "Gemeindestrassen zuständig" findet den Abschnitt nicht (Rang > 10, trifft Erlasse mit "öffentliche Anlagen").
- EN-Fragen werden mit der DE-Chunk-Basis gefunden (MiniLM ist multilingual); Befund gilt nur für 2 Fragen.

---

## Nachtrag 2026-10-03: Chunking korrigiert (Befund aus Phase 4)

Die Pipeline-Evaluation hat einen Fehler in der Web-Chunking-Regel aufgedeckt. Die alte Regel fasste
Abschnitte unter 140 Zeichen mit dem **nächsten** Abschnitt zusammen, unabhängig von der Gliederungsebene.
Folge: Der kurze Abschnitt «Zonen» (Unterabschnitt von «Parkkarten für Anwohnende») schluckte den Anfang
von «Gewerbeparkkarte» – einem Abschnitt auf gleicher Ebene. Der entstandene Chunk trug den Pfad
`Parkieren > Parkkarten für Anwohnende > Zonen`, enthielt aber den Satz «Sie ist in allen Gemeinden des
Kantons gültig». Pfad und Inhalt passten nicht zusammen, was den Embedding-Text verfälschte.

Messbare Folge: Bei «Die Gewerbeparkkarte gilt nur in der Stadt Zug, richtig?» lag der richtige
Erlass-Chunk (§ 14) im dichten Index auf **Rang 134**.

**Neue Regel:** Ein Abschnitt nimmt nur seine **eigenen Unterabschnitte** auf. Beginnt ein Abschnitt auf
gleicher oder höherer Ebene, wird abgeschlossen. Dadurch entspricht jeder Chunk einem Thema, und der
Pfad beschreibt den Inhalt zutreffend.

| | alt | neu |
|---|---|---|
| Chunks gesamt | 456 | 419 |
| Median Länge | 1046 | 1229 |
| Chunks der Seite «Parkieren» | 24, Themen vermischt | 10, je ein Thema |

Auf dem Retrieval-Smoke-Test sinken die Werte leicht (@1 16→14, @5 26→24). Ursache ist überwiegend ein
Artefakt des Messinstruments: Die Gewerbe-Gebühr liegt jetzt im übergeordneten Themen-Chunk statt in
einem eigenen «Gebühren»-Chunk und rutscht von Rang ≤5 auf Rang 7 – bei einem Kontext von k=10 ist sie
weiterhin dabei. Die beiden anderen Fragen scheiterten schon vorher. Bewertet wird deshalb auf der
Pipeline-Ebene, nicht am Smoke-Test.
