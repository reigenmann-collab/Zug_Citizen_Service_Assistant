"""Retrieval: Embedding (FAISS) + optional BM25-Hybrid + optional Cross-Encoder-Reranking."""
import json, math, re, functools
from collections import Counter
from pathlib import Path
import numpy as np, faiss
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parent.parent; IDX = ROOT / "data" / "index"
EMB_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMB_NAME = "minilm"

@functools.lru_cache(maxsize=1)
def chunks():
    return [json.loads(l) for l in (IDX / "chunks.jsonl").open(encoding="utf8")]

@functools.lru_cache(maxsize=1)
def _dense():
    return faiss.read_index(str(IDX / f"{EMB_NAME}.faiss")), TextEmbedding(model_name=EMB_MODEL)

TOK = re.compile(r"[a-zäöüàéèêç0-9]+")
def tokens(s):
    s = s.lower().replace("ß", "ss")
    return [t for t in TOK.findall(s) if len(t) > 2]

@functools.lru_cache(maxsize=1)
def _bm25():
    docs = [tokens(c["embed_text"]) for c in chunks()]
    df = Counter(t for d in docs for t in set(d))
    N = len(docs); avgdl = sum(len(d) for d in docs) / N
    idf = {t: math.log(1 + (N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
    tf = [Counter(d) for d in docs]
    return tf, [len(d) for d in docs], avgdl, idf

def bm25_scores(q, k1=1.5, b=0.75):
    tf, dl, avgdl, idf = _bm25()
    qt = tokens(q); s = np.zeros(len(tf), dtype="float32")
    for t in qt:
        if t not in idf: continue
        w = idf[t]
        for i, c in enumerate(tf):
            f = c.get(t, 0)
            if f: s[i] += w * f * (k1 + 1) / (f + k1 * (1 - b + b * dl[i] / avgdl))
    return s

def dense_scores(q):
    ix, emb = _dense()
    v = np.array(list(emb.embed([q])), dtype="float32"); faiss.normalize_L2(v)
    S, I = ix.search(v, len(chunks()))
    out = np.zeros(len(chunks()), dtype="float32"); out[I[0]] = S[0]
    return out

def _rr(order):
    """Rang je Dokument-Index aus einer absteigend sortierten Indexliste."""
    r = {}
    for rank, i in enumerate(order): r[int(i)] = rank + 1
    return r

def bm25_recall(q, ausschluss=(), n=2, min_score=4.0):
    """Recall-Netz: bis zu n Chunks, die BM25 hoch bewertet und die noch nicht im Kontext sind.
    Kein Ranking-Faktor – RRF hat gemessen geschadet (PROGRESSION/004). Begruendung fuer das Netz:
    bei seltenen Komposita kann der dichte Index komplett versagen; "Gewerbeparkkarte" lag dort auf
    Rang 134, bei BM25 auf Rang 4 (Fall D12). min_score verhindert Zufallstreffer bei Fragen ohne
    seltene Begriffe und bei englischen Fragen, die lexikalisch nicht greifen."""
    C = chunks(); b = bm25_scores(q); aus = set(ausschluss); out = []
    for i in np.argsort(-b):
        if len(out) >= n or b[i] < min_score: break
        if C[i]["chunk_id"] in aus: continue
        out.append((C[i], float(b[i])))
    return out


def search(q, k=20, mode="dense", rrf_k=60, w_bm25=1.0):
    """mode:
      dense       – nur Embeddings
      bm25        – nur BM25
      hybrid      – Reciprocal Rank Fusion (gemessen schlechter, siehe PROGRESSION/004)
    Standard ist dense. Das BM25-Recall-Netz haengt die Pipeline ueber bm25_recall() separat an,
    damit k es nicht abschneidet.
    Gibt [(chunk, score)] zurueck."""
    C = chunks()
    if mode == "dense":
        s = dense_scores(q); order = np.argsort(-s)[:k]; return [(C[i], float(s[i])) for i in order]
    if mode == "bm25":
        s = bm25_scores(q); order = np.argsort(-s)[:k]; return [(C[i], float(s[i])) for i in order]
    d, bs = dense_scores(q), bm25_scores(q)
    rd, rb = _rr(np.argsort(-d)[:100]), _rr(np.argsort(-bs)[:100])
    fused = {i: 1 / (rrf_k + rd.get(i, 10**6)) + w_bm25 / (rrf_k + rb.get(i, 10**6)) for i in set(rd) | set(rb)}
    order = sorted(fused, key=lambda i: -fused[i])[:k]
    return [(C[i], fused[i]) for i in order]
