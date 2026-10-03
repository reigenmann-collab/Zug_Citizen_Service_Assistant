# Phasenplan Stadt Zug RAG (Stand 2026-10-03)

Nach jeder Phase: kurzer Bericht, Freigabe abwarten.

| Phase | Inhalt | Ergebnis | Modell |
|-------|--------|----------|--------|
| 1 Crawl (erledigt) | Rohdaten holen (HTML, PDF, tlex-JSON), Inventar | `data/raw/`, `inventory.json` | Sonnet 5.5 |
| 2 Ingestion | Zusatzcrawl (Erlasse, News), Relevanz-Tagging, **Extraktion** (HTML→Text ohne Site-Chrome, PDF-Textlayer/OCR-Prüfung, tlex-JSON→Artikel), Metadaten | `data/clean/*.jsonl`, Ingestion-Report | Sonnet 5.5 High |
| 3 Chunking + Vector DB | Chunking (artikelweise bei Erlassen, Abschnitte bei Web), Embeddings lokal, Chroma/FAISS, Retrieval-Smoke-Test | Index, Chunk-Report | Sonnet 5.5 High |
| **→ Wechsel auf Opus Medium** | Zu Beginn von Phase 4. Vorher (Ende Phase 3) Testset-Entwurf in Opus anlegen. | | |
| 4 RAG | Spracherkennung, Retrieval, Reranker (Auswahl begründen), Generierung, Hard-Routing, EN-Hinweis, Grounding-Test Fr. 200/150 | Pipeline | Opus Medium |
| 5 Confidence | S1/S2/S3, Coverage-Check, Kalibrierung auf allen generierten Zeilen | Schwelle + Kalibrierbericht | Opus Medium |
| 6 UI | Streamlit nach `zg_rag_prototype.html`, Deployment auf Streamlit Cloud (eigenes Repo) | Demo | Sonnet 5.5 (Wechsel zurück möglich) |
| 7 Pilot/Evaluation | Testset, Label-Sheet, Auswertung | Evaluationsbericht | Opus Medium |

Antwort auf "Gehört Extraktion zum Inventar?": Nein. Phase 1 = was gibt es und woher (Inventar). Extraktion = Text daraus gewinnen, gehört zu Phase 2 Ingestion.
