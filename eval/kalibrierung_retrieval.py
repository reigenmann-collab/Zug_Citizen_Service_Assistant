"""Phase 5, zweiter Teil: Laesst sich Retrieval-Versagen aus den Retrieval-Scores erkennen?

Warum diese Frage. Die Kalibrierung von C auf Antwort-Korrektheit scheitert an der Datenlage: In der
aktuellen Konfiguration liefert das System auf den 24 Dev-Fragen praktisch keine messbar falschen
Antworten, also fehlen die Negativbeispiele. Es gibt aber ein verwandtes Ziel, fuer das reichlich
Positiv- UND Negativbeispiele vorliegen und das **ohne Modellaufruf** bestimmbar ist: Ist die benoetigte
Quelle ueberhaupt im Kontext gelandet?

Das ist ein brauchbares Signal fuer sich. Fehlt die Quelle, kann die Antwort nur zufaellig richtig sein.
Datenbasis: die 24 Dev-Fragen (erwartete Quellen als Label) und die 27 Fragen des Retrieval-Smoke-Tests
(doc + Textfragment als Label). Der test-Split bleibt unberuehrt.

Usage: python eval/kalibrierung_retrieval.py [--k 10] [--bootstrap 2000]
"""
import argparse, json, random, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.retrieve import search, bm25_recall

P = Path(__file__).parent


def merkmale(frage, k, bm25_netz=2):
    """Retrieval-Merkmale, alle ohne Modellaufruf berechenbar."""
    hits = search(frage, k=max(k, 20), mode="dense")
    s = [sc for _, sc in hits]
    kontext = [c for c, _ in hits[:k]]
    netz = bm25_recall(frage, ausschluss=[c["chunk_id"] for c in kontext], n=bm25_netz)
    kontext = kontext + [c for c, _ in netz]
    top1 = s[0]
    return kontext, {
        "top1": round(top1, 4),
        "top3_mittel": round(sum(s[:3]) / 3, 4),
        "marge_1_4": round(top1 - s[3], 4),
        "marge_1_10": round(top1 - s[min(9, len(s) - 1)], 4),
        "marge_rel": round((top1 - s[min(9, len(s) - 1)]) / top1, 4) if top1 else 0.0,
        "streuung_top10": round(st.pstdev(s[:10]), 4),
        "netz_aktiv": 1 if netz else 0,
    }


def auc(pos, neg):
    if not pos or not neg:
        return None
    g = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return g / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--bootstrap", type=int, default=2000)
    a = ap.parse_args()

    punkte = []
    # a) Dev-Fragen: Label = alle erwarteten Quellen im Kontext
    for t in json.loads((P / "testset.json").read_text(encoding="utf8")):
        if t["split"] != "dev" or not t["erwartete_quellen"]:
            continue
        kontext, m = merkmale(t["frage"], a.k)
        ids = [c["chunk_id"] for c in kontext]
        gefunden = all(any(i.startswith(q) for i in ids) for q in t["erwartete_quellen"])
        punkte.append({"quelle": "dev", "id": t["id"], "sprache": t["sprache"], "ok": gefunden, **m})
    # b) Smoke-Test: Label = Zielchunk mit Textfragment im Kontext
    for i, t in enumerate(json.loads((P / "retrieval_testset.json").read_text(encoding="utf8"))):
        kontext, m = merkmale(t["q"], a.k)
        gefunden = any(c["doc_id"].startswith(g["doc"]) and g["must"] in c["text"]
                       for c in kontext for g in [t, *t.get("alt", [])])
        punkte.append({"quelle": "smoke", "id": f"S{i+1:02d}",
                       "sprache": "en" if t["q"].split()[0] in ("How", "Do", "Where", "Can", "Which", "What") else "de",
                       "ok": gefunden, **m})

    pos = [p for p in punkte if p["ok"]]
    neg = [p for p in punkte if not p["ok"]]
    print("=" * 78)
    print(f"Ziel: Ist die benoetigte Quelle im Kontext (k={a.k} + BM25-Netz)?")
    print(f"{len(punkte)} Fragen: {len(pos)} gefunden, {len(neg)} nicht gefunden "
          f"(dev {sum(1 for p in punkte if p['quelle']=='dev')}, smoke {sum(1 for p in punkte if p['quelle']=='smoke')})")
    if not neg:
        print("Keine Negativbeispiele – Trennschaerfe nicht bestimmbar."); return

    print(f"\n{'Merkmal':16s} {'AUC':>6s} {'Mittel gefunden':>16s} {'Mittel verfehlt':>16s}")
    ergebnis = {}
    for m in ("top1", "top3_mittel", "marge_1_4", "marge_1_10", "marge_rel", "streuung_top10"):
        A = auc([p[m] for p in pos], [p[m] for p in neg])
        ergebnis[m] = A
        print(f"{m:16s} {A:6.3f} {st.mean([p[m] for p in pos]):16.3f} {st.mean([p[m] for p in neg]):16.3f}")
    best = max(ergebnis, key=lambda m: abs(ergebnis[m] - 0.5))
    print(f"\nStaerkstes Merkmal: {best} (AUC {ergebnis[best]:.3f})")

    if a.bootstrap:
        rnd = random.Random(42); w = []
        for _ in range(a.bootstrap):
            A = auc([rnd.choice(pos)[best] for _ in pos], [rnd.choice(neg)[best] for _ in neg])
            if A is not None:
                w.append(A)
        w.sort(); lo, hi = w[int(.025 * len(w))], w[int(.975 * len(w))]
        print(f"  95%-Intervall: {lo:.3f} bis {hi:.3f}  "
              f"{'– schliesst 0.5 ein, kein belastbares Signal' if lo <= 0.5 <= hi else '– liegt neben 0.5'}")

    print(f"\n--- Schwellen-Durchlauf auf {best}")
    print(f"{'Schwelle':>9s} {'markiert':>9s} {'davon verfehlt':>15s} {'verfehlt uebersehen':>20s} {'Praezision':>11s}")
    werte = sorted({round(p[best], 2) for p in punkte})
    for s in werte[::max(1, len(werte) // 12)]:
        mark = [p for p in punkte if p[best] < s]
        tr = sum(1 for p in mark if not p["ok"])
        print(f"{s:9.2f} {len(mark):9d} {tr:15d} {len(neg)-tr:20d} "
              f"{(tr/len(mark)*100 if mark else 0):10.0f}%")

    print("\n--- Nach Sprache")
    for sp in ("de", "en"):
        g = [p for p in punkte if p["sprache"] == sp]
        if g:
            print(f"  {sp}: {sum(1 for p in g if p['ok'])}/{len(g)} gefunden "
                  f"({sum(1 for p in g if p['ok'])/len(g)*100:.0f}%)")

    print("\nVerfehlte Fragen:")
    for p in neg:
        print(f"  {p['id']:5s} [{p['quelle']:5s}/{p['sprache']}] top1={p['top1']} marge_1_10={p['marge_1_10']}")
    (P / "kalibrierung_retrieval.json").write_text(json.dumps(punkte, ensure_ascii=False, indent=1), encoding="utf8")
    print("\nRohdaten: eval/kalibrierung_retrieval.json")


if __name__ == "__main__":
    main()
