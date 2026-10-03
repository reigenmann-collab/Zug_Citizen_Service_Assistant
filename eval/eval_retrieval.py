"""Retrieval-Smoke-Test: Hit@k = erwartetes Dokument (und ggf. Textfragment) in den Top-k Chunks. Usage: python eval/eval_retrieval.py <model> [name]"""
import sys, json, numpy as np, faiss
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingest"))
from index import load, prefixes, IDX
model = sys.argv[1]; name = sys.argv[2] if len(sys.argv) > 2 else model.split("/")[-1]
rows = [json.loads(l) for l in (IDX / "chunks.jsonl").open(encoding="utf8")]
T = json.loads((Path(__file__).parent / "retrieval_testset.json").read_text(encoding="utf8"))
ix, emb = load(model, name); qp, _ = prefixes(model)
Q = np.array(list(emb.embed([qp + t["q"] for t in T])), dtype="float32"); faiss.normalize_L2(Q)
S, I = ix.search(Q, 10); res = {1: 0, 3: 0, 5: 0, 10: 0}; miss = []
for t, s, idx in zip(T, S, I):
    rank = None
    for r, i in enumerate(idx):
        c = rows[i]
        if any(c["doc_id"].startswith(g["doc"]) and g["must"] in c["text"] for g in [t, *t.get("alt", [])]): rank = r + 1; break
    for k in res:
        if rank and rank <= k: res[k] += 1
    if not rank or rank > 3: miss.append((t["q"], rank, [rows[i]["chunk_id"][:45] for i in idx[:3]]))
n = len(T); print(model, {f"Hit@{k}": f"{v}/{n}" for k, v in res.items()})
for m in miss: print(" MISS", m)
