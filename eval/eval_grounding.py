"""Unit-Test fuer den Grounding-Checker auf eval/grounding_adversarial.json."""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.grounding import pruefe, schicht_a
from rag.retrieve import chunks
from rag.llm import nur_json
C = {c["chunk_id"]: c for c in chunks()}
def ctx(ids):
    out = []
    for i in ids:
        out += ([C[i]["embed_text"]] if i in C else [c["embed_text"] for c in chunks() if c["chunk_id"].startswith(i)])
    return "\n\n".join(out)
G = json.loads((Path(__file__).parent / "grounding_adversarial.json").read_text(encoding="utf8"))
mit_llm = "--a" not in sys.argv
ok_a = ok = 0; t0 = time.time()
for g in G:
    k = ctx(g["kontext_chunks"]); soll = g["erwartet"]
    r = pruefe(g["behauptung"], k, llm=nur_json if mit_llm else None, b_trotz_a=True,
               frage=g.get("frage", ""))
    a = "nicht_gedeckt" if not r["a"]["ok"] else "gedeckt"
    treffer_a = (a == soll) or (a == "gedeckt" and soll.startswith("gedeckt"))
    treffer = (r["urteil"] == soll) or (r["urteil"] == "gedeckt" and soll.startswith("gedeckt"))
    ok_a += treffer_a; ok += treffer
    nd = [x["aussage"][:45] for x in r["b"].get("nicht_gedeckt", [])]
    print(f"  {g['id']} soll={soll:22s} A={a:14s} A+B={r['urteil']:14s} s2={r['s2']:<5} {'OK ' if treffer else 'FEHLT'} {r['grund']}")
    if nd: print(f"       B beanstandet: {nd}")
print(f"\nSchicht A allein: {ok_a}/{len(G)}   A+B: {ok}/{len(G)}   {(time.time()-t0)/len(G):.1f} s/Pruefung")
