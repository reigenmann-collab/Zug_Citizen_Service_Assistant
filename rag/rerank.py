"""Cross-Encoder-Reranking (lokal, ONNX via fastembed). Kandidaten siehe PROGRESSION/004."""
import functools, numpy as np
from fastembed.rerank.cross_encoder import TextCrossEncoder
RERANKERS = {
    "msmarco12": "Xenova/ms-marco-MiniLM-L-12-v2",
    "bge": "BAAI/bge-reranker-base",
    "jina2": "jinaai/jina-reranker-v2-base-multilingual",
}
@functools.lru_cache(maxsize=2)
def _model(name): return TextCrossEncoder(model_name=RERANKERS[name])
TRUNC = 400   # Zeichen je Passage; gemessen: 400 statt voller Laenge senkt 14 s auf 3.4 s ohne Qualitaetsverlust
CAND = 10     # Kandidaten, die reranked werden; 10 statt 20 senkt weiter auf 2.1 s

def rerank(q, hits, name, top_k=None, trunc=TRUNC, cand=CAND):
    """hits: [(chunk, score)] -> nach Cross-Encoder-Score absteigend. Prueft auf NaN/Inf.
    Es werden nur die ersten `cand` Treffer bewertet, je `trunc` Zeichen. Der Rest behaelt seine
    Reihenfolge und wird angehaengt, damit nichts verloren geht."""
    if not hits: return hits
    kopf, rest = hits[:cand], hits[cand:]
    docs = [c["embed_text"][:trunc] for c, _ in kopf]
    s = np.array(list(_model(name).rerank(q, docs)), dtype="float64")
    if not np.isfinite(s).all(): raise ValueError(f"Reranker {name}: NaN/Inf in Scores ({np.isnan(s).sum()}/{len(s)})")
    order = np.argsort(-s)
    out = [(kopf[i][0], float(s[i])) for i in order] + list(rest)
    return out[:top_k] if top_k else out
