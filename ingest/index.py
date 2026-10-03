"""Phase 3b: chunks.jsonl -> Embeddings (fastembed, lokal) -> FAISS (cosine/IP). Usage: python ingest/index.py <model> [outname]"""
import sys, json, time, numpy as np, faiss
from pathlib import Path
from fastembed import TextEmbedding
ROOT = Path(__file__).resolve().parent.parent; IDX = ROOT / "data" / "index"
E5 = ("query: ", "passage: ")
def prefixes(model): return E5 if "e5" in model else ("", "")
def build(model, name):
    rows = [json.loads(l) for l in (IDX / "chunks.jsonl").open(encoding="utf8")]
    emb = TextEmbedding(model_name=model); qp, pp = prefixes(model)
    t = time.time(); V = np.array(list(emb.embed([pp + r["embed_text"] for r in rows], batch_size=16)), dtype="float32")
    assert np.isfinite(V).all(), "NaN/Inf in Embeddings"
    faiss.normalize_L2(V); ix = faiss.IndexFlatIP(V.shape[1]); ix.add(V)
    faiss.write_index(ix, str(IDX / f"{name}.faiss")); print(f"{model}: {V.shape} in {time.time()-t:.0f}s, finite=True"); return ix
def load(model, name):
    return faiss.read_index(str(IDX / f"{name}.faiss")), TextEmbedding(model_name=model)
if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1].split("/")[-1])
