"""Menschliche Urteile aus dem Audit-Log auswerten und in die Kalibrierung einspeisen.

Phase 5 hat gezeigt: Die Confidence lässt sich an 24 selbst geschriebenen Testfragen nicht kalibrieren,
weil die Fehlerbeispiele fehlen. Die Beurteilungen aus dem Pilotbetrieb sind der einzige Weg dorthin.
Dieses Skript zeigt, wie weit man ist, und liefert die Datenbasis, sobald genug beisammen ist.

Usage: python eval/urteile.py [--log data/audit/auditlog.jsonl] [--min 30]
"""
import argparse, collections, json, statistics as st, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.auditlog import lies

P = Path(__file__).parent

# So viele von Menschen als falsch markierte Antworten braucht es mindestens, bevor eine Schwelle
# überhaupt sinnvoll bestimmt werden kann. Begründung in PROGRESSION/005: Bei 9 Negativbeispielen lag
# das 95%-Intervall der AUC bei 0.452 bis 0.791 – unbrauchbar breit. Die Zahl ist eine Untergrenze,
# keine Garantie; ob es reicht, zeigt erst die Breite des Intervalls auf den echten Daten.
MIN_NEGATIV = 30


def auc(pos, neg):
    if not pos or not neg:
        return None
    g = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return g / (len(pos) * len(neg))


def sammle(logdatei=None):
    """-> (zeilen, urteile) aus dem Audit-Log, zusammengeführt über antwort_id."""
    alle = lies(logdatei)
    antworten = {r["antwort_id"]: r for r in alle
                 if r.get("art") != "menschliches_urteil" and r.get("antwort_id")}
    urteile = {}
    for r in alle:
        if r.get("art") == "menschliches_urteil" and r.get("antwort_id"):
            urteile[r["antwort_id"]] = r          # späteres Urteil ersetzt ein früheres
    paare = [{**antworten[a], "urteil": u["urteil"], "bemerkung": u.get("bemerkung"),
              "beurteilt_von": u.get("von"), "beurteilt_am": u.get("zeit")}
             for a, u in urteile.items() if a in antworten]
    return antworten, paare


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    ap.add_argument("--min", type=int, default=MIN_NEGATIV)
    a = ap.parse_args()

    antworten, paare = sammle(a.log)
    print("=" * 72)
    print(f"Protokollierte Antworten: {len(antworten)}")
    print(f"Davon beurteilt:          {len(paare)}")
    if not paare:
        print("\nNoch keine Beurteilungen. In der Pilot-Ansicht der App eintragen.")
        return

    verteilung = collections.Counter(p["urteil"] for p in paare)
    print(f"Verteilung: {dict(verteilung)}")
    beurteiler = collections.Counter(p.get("beurteilt_von") or "ohne Kürzel" for p in paare)
    print(f"Beurteilende: {dict(beurteiler)}")

    # Nur generierte Zeilen mit Confidence sind für die Kalibrierung brauchbar.
    mit_c = [p for p in paare if p.get("confidence_vorlaeufig") is not None]
    pos = [p["confidence_vorlaeufig"] for p in mit_c if p["urteil"] == "richtig"]
    neg = [p["confidence_vorlaeufig"] for p in mit_c if p["urteil"] == "falsch"]
    print(f"\nMit Confidence: {len(mit_c)} (richtig {len(pos)}, falsch {len(neg)}, "
          f"übrige {len(mit_c)-len(pos)-len(neg)})")

    if len(neg) < a.min:
        print(f"\n→ Für eine Kalibrierung fehlen noch {a.min - len(neg)} als falsch markierte Antworten.")
        print("  Bis dahin bleibt die Eskalation strukturell (PROGRESSION/005). Keine Schwelle setzen.")
    else:
        A = auc(pos, neg)
        print(f"\nAUC auf Pilotdaten: {A:.3f}  (Mittel richtig {st.mean(pos):.3f}, falsch {st.mean(neg):.3f})")
        import random
        rnd = random.Random(42)
        w = sorted(x for x in (auc([rnd.choice(pos) for _ in pos], [rnd.choice(neg) for _ in neg])
                               for _ in range(2000)) if x is not None)
        lo, hi = w[int(.025 * len(w))], w[int(.975 * len(w))]
        print(f"95%-Intervall: {lo:.3f} bis {hi:.3f}")
        if lo <= 0.5 <= hi:
            print("→ Das Intervall schliesst 0.5 ein. C trennt weiterhin nicht nachweisbar; keine Schwelle.")
        else:
            print("→ C trennt. Jetzt Schwellen-Durchlauf rechnen und die Betriebskosten abwägen:")
            print(f"{'Schwelle':>9s} {'blockiert':>10s} {'davon richtig':>14s} {'falsch gefangen':>16s}")
            for s in [round(x, 2) for x in [i / 20 for i in range(10, 20)]]:
                unten = [p for p in mit_c if p["confidence_vorlaeufig"] < s and p["urteil"] in ("richtig", "falsch")]
                print(f"{s:9.2f} {len(unten):10d} {sum(1 for p in unten if p['urteil']=='richtig'):14d} "
                      f"{sum(1 for p in unten if p['urteil']=='falsch'):16d}")

    # Welche strukturellen Signale haben die als falsch markierten Antworten getroffen?
    falsch = [p for p in paare if p["urteil"] == "falsch"]
    if falsch:
        print(f"\nStrukturelle Signale bei den {len(falsch)} falschen Antworten:")
        for name, pred in (("grounding nicht_gedeckt", lambda p: p.get("grounding_urteil") == "nicht_gedeckt"),
                           ("unvollstaendig", lambda p: bool(p.get("unvollstaendig"))),
                           ("retrieval_warnung", lambda p: bool(p.get("retrieval_warnung"))),
                           ("ohne jedes Signal", lambda p: not any(
                               [p.get("grounding_urteil") == "nicht_gedeckt", p.get("unvollstaendig"),
                                p.get("retrieval_warnung")]))):
            print(f"  {name:24s} {sum(1 for p in falsch if pred(p)):3d}")
        print("  «ohne jedes Signal» sind die Fälle, die heute unbemerkt durchgehen – die wichtigsten.")

    ziel = P / "pilot_urteile.json"
    ziel.write_text(json.dumps(paare, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"\nZusammengeführte Daten: {ziel.relative_to(P.parent)}")


if __name__ == "__main__":
    main()
