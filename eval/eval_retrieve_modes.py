"""Vergleicht dense / bm25 / hybrid auf dem Retrieval-Smoke-Test."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.retrieve import search
T = json.loads((Path(__file__).parent / "retrieval_testset.json").read_text(encoding="utf8"))
def hit_rank(t, res):
    for r, (c, _) in enumerate(res):
        if any(c["doc_id"].startswith(g["doc"]) and g["must"] in c["text"] for g in [t, *t.get("alt", [])]): return r + 1
    return None
for mode in ("dense", "bm25", "hybrid"):
    res = {1: 0, 3: 0, 5: 0, 10: 0}; miss = []
    for t in T:
        rk = hit_rank(t, search(t["q"], k=10, mode=mode))
        for k in res:
            if rk and rk <= k: res[k] += 1
        if not rk or rk > 3: miss.append((t["q"][:52], rk))
    print(f"{mode:7s}", {f"@{k}": f"{v}/{len(T)}" for k, v in res.items()})
    for m in miss: print("    MISS", m)
