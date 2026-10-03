"""Reranker-Vergleich auf dem Retrieval-Smoke-Test. Usage: python eval/eval_rerank.py <name> [cand_k]"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.retrieve import search
from rag.rerank import rerank, RERANKERS
name = sys.argv[1]; cand = int(sys.argv[2]) if len(sys.argv) > 2 else 20
T = json.loads((Path(__file__).parent / "retrieval_testset.json").read_text(encoding="utf8"))
def hr(t, res):
    for r, (c, _) in enumerate(res):
        if any(c["doc_id"].startswith(g["doc"]) and g["must"] in c["text"] for g in [t, *t.get("alt", [])]): return r + 1
    return None
rerank(T[0]["q"], search(T[0]["q"], k=cand, mode="dense"), name)  # Warmup: Modell laden
base = {1: 0, 3: 0, 5: 0}; re_ = {1: 0, 3: 0, 5: 0}; moved = []; t0 = time.time(); t_re = 0.0
for t in T:
    hits = search(t["q"], k=cand, mode="dense")
    rb = hr(t, hits[:10]); _t = time.time(); rl = rerank(t["q"], hits, name); t_re += time.time() - _t; rr = hr(t, rl)
    for k in base:
        if rb and rb <= k: base[k] += 1
        if rr and rr <= k: re_[k] += 1
    if (rb or 99) != (rr or 99): moved.append((t["q"][:50], rb, rr))
n = len(T); dt = time.time() - t0
print(f"{name} ({RERANKERS[name]}), cand={cand}, rerank {t_re/n*1000:.0f} ms/Frage (ohne Laden), total {dt/n*1000:.0f} ms")
print("  dense   ", {f"@{k}": f"{v}/{n}" for k, v in base.items()})
print("  rerankt ", {f"@{k}": f"{v}/{n}" for k, v in re_.items()})
for m in sorted(moved, key=lambda x: (x[2] or 99)): print(f"    {m[0]:52s} {m[1]} -> {m[2]}")
