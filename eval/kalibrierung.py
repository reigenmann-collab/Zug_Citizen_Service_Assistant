"""Phase 5: Kalibrierung der Confidence.

Grundsatz aus CLAUDE.md: Die Schwelle wird kalibriert, nicht gesetzt – und zwar auf **allen generierten
Zeilen**, nicht nur auf denen, die das System automatisch beantwortet hat. In Schwyz war genau das der
Fehler: kalibriert wurde auf der Teilmenge, die ohnehin gut lief.

Datenbasis sind deshalb alle Laeufe in eval/pipeline_*.jsonl zusammen, auch die mit aelterer
Konfiguration. Die Frage dieser Auswertung ist nicht «welche Konfiguration ist besser», sondern
«traegt die Zahl C ueberhaupt Information darueber, ob eine Antwort richtig ist». Dafuer sind auch
Zeilen aus frueheren Konfigurationen gueltige Beobachtungen – sie liefern die Negativbeispiele.

Die Korrektheit wird ohne Modellaufruf neu bestimmt, mit denselben Regeln wie eval_pipeline.py.
Ermessensfaelle tragen das Urteil aus PROGRESSION/004 und sind als solche markiert.

Usage: python eval/kalibrierung.py [--bootstrap 2000]
"""
import argparse, json, random, re, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.lang import EN_DISCLAIMER
from rag.norm import fold

P = Path(__file__).parent

# Urteil zu den Ermessensfaellen, dokumentiert in PROGRESSION/004. Nicht automatisch pruefbar.
MANUELL = {"D02": True, "D16": True, "D17": True, "D18": True, "D19": True}


def korrekt(t, r):
    """-> (ok, quelle_des_urteils). ok=None, wenn kein Urteil vorliegt."""
    if t["id"] in MANUELL:
        return MANUELL[t["id"]], "manuell"
    soll, e = t["erwartetes_verhalten"], r["entscheid"]
    if soll == "eskalieren":
        v = e == "eskaliert"
    elif soll in ("antworten", "antworten_mit_hinweis", "korrigieren"):
        v = e in ("beantwortet", "beantwortet_mit_hinweis")
    elif soll == "antworten_en_mit_hinweis":
        v = (e in ("beantwortet", "beantwortet_mit_hinweis") and r.get("sprache") == "en"
             and EN_DISCLAIMER[:40] in r.get("antwort", ""))
    else:
        return None, "kein_urteil"
    a = fold(r.get("antwort", ""))
    inhalt = (all(fold(m) in a for m in t["muss_enthalten"])
              and not any(re.search(rf"(?<!\d){re.escape(fold(m))}(?!\d)", a)
                          for m in t.get("darf_nicht_enthalten", [])))
    ids = r.get("quellen", [])
    quellen = all(any(i.startswith(q) for i in ids) for q in t["erwartete_quellen"])
    return bool(v and inhalt and quellen), "automatisch"


def auc(pos, neg):
    """Mann-Whitney-U / ROC-AUC: Wahrscheinlichkeit, dass eine richtige Antwort ein hoeheres C hat
    als eine falsche. 0.5 = kein Informationsgehalt."""
    if not pos or not neg:
        return None
    g = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return g / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", type=int, default=2000)
    a = ap.parse_args()

    T = {t["id"]: t for t in json.loads((P / "testset.json").read_text(encoding="utf8"))}
    zeilen = []
    for f in sorted(P.glob("pipeline_*.jsonl")):
        for l in f.open(encoding="utf8"):
            r = json.loads(l)
            t = T.get(r.get("frage_id"))
            if not t:
                continue
            ok, quelle = korrekt(t, r)
            zeilen.append({**r, "lauf": f.stem, "kat": t["kategorie"], "ok": ok, "urteil_quelle": quelle})

    gen = [z for z in zeilen if z["entscheid"].startswith("beantwortet")]
    esk = [z for z in zeilen if z["entscheid"] == "eskaliert"]
    bewertbar = [z for z in gen if z["ok"] is not None]
    richtig = [z for z in bewertbar if z["ok"]]
    falsch = [z for z in bewertbar if not z["ok"]]

    print("=" * 78)
    print(f"Datenbasis: {len(zeilen)} protokollierte Zeilen aus {len(set(z['lauf'] for z in zeilen))} Laeufen")
    print(f"  generiert: {len(gen)}   eskaliert (ohne Generierung): {len(esk)}")
    print(f"  mit Urteil: {len(bewertbar)}  davon richtig {len(richtig)}, falsch {len(falsch)}")
    print(f"  Urteilsquelle: automatisch {sum(1 for z in bewertbar if z['urteil_quelle']=='automatisch')}, "
          f"manuell {sum(1 for z in bewertbar if z['urteil_quelle']=='manuell')}")

    print("\n--- Verteilung der Komponenten auf allen generierten Zeilen")
    print(f"{'':12s} {'min':>6s} {'p25':>6s} {'median':>7s} {'p75':>6s} {'max':>6s} {'Spannweite':>11s} {'konstant?':>10s}")
    for name in ("s1", "s2", "s3", "confidence_vorlaeufig"):
        w = sorted(z[name] for z in gen if z.get(name) is not None)
        if not w:
            continue
        q = lambda p: w[min(len(w) - 1, int(p * len(w)))]
        spann = w[-1] - w[0]
        anteil_mod = max(w.count(x) for x in set(w)) / len(w)
        print(f"{name:12s} {w[0]:6.3f} {q(.25):6.3f} {st.median(w):7.3f} {q(.75):6.3f} {w[-1]:6.3f} "
              f"{spann:11.3f} {anteil_mod*100:9.0f}%")
    print("  Letzte Spalte: Anteil des haeufigsten Einzelwerts. Hoch = die Komponente ist gesaettigt")
    print("  und traegt kaum Information.")

    print("\n--- Trennschaerfe: unterscheidet C richtige von falschen Antworten?")
    for name in ("s1", "s2", "s3", "confidence_vorlaeufig"):
        p = [z[name] for z in richtig if z.get(name) is not None]
        n = [z[name] for z in falsch if z.get(name) is not None]
        A = auc(p, n)
        if A is None:
            print(f"  {name:22s} nicht berechenbar (keine Negativbeispiele)")
            continue
        print(f"  {name:22s} AUC={A:.3f}   Mittel richtig={st.mean(p):.3f}  falsch={st.mean(n):.3f}")

    if falsch and a.bootstrap:
        print(f"\n--- Stabilitaet der AUC ({a.bootstrap} Bootstrap-Ziehungen)")
        rnd = random.Random(42); werte = []
        for _ in range(a.bootstrap):
            rp = [rnd.choice(richtig)["confidence_vorlaeufig"] for _ in richtig]
            rn = [rnd.choice(falsch)["confidence_vorlaeufig"] for _ in falsch]
            A = auc(rp, rn)
            if A is not None:
                werte.append(A)
        werte.sort()
        lo, hi = werte[int(.025 * len(werte))], werte[int(.975 * len(werte))]
        print(f"  AUC 95%-Intervall: {lo:.3f} bis {hi:.3f}  (0.5 = wertlos)")
        print(f"  {'Das Intervall schliesst 0.5 ein: C trennt nicht nachweisbar.' if lo <= 0.5 <= hi else 'Das Intervall liegt neben 0.5.'}")

    print("\n--- Schwellen-Durchlauf auf C (was wuerde eine Schwelle bewirken?)")
    print(f"{'Schwelle':>9s} {'blockiert':>10s} {'davon richtig':>14s} {'falsch gefangen':>16s} {'falsch durch':>13s}")
    for s in [round(x, 2) for x in [i / 20 for i in range(10, 20)]]:
        unten = [z for z in bewertbar if z["confidence_vorlaeufig"] < s]
        print(f"{s:9.2f} {len(unten):10d} {sum(1 for z in unten if z['ok']):14d} "
              f"{sum(1 for z in unten if not z['ok']):16d} {sum(1 for z in falsch if z['confidence_vorlaeufig'] >= s):13d}")
    print("  «davon richtig» sind Antworten, die eine Schwelle unnoetig an Menschen weiterleiten wuerde.")

    print("\n--- Was die strukturellen Signale leisten (ohne C)")
    for name, pred in (("grounding_urteil == nicht_gedeckt", lambda z: z.get("grounding_urteil") == "nicht_gedeckt"),
                       ("unvollstaendig == true", lambda z: bool(z.get("unvollstaendig"))),
                       ("rueckfrage == true", lambda z: bool(z.get("rueckfrage"))),
                       ("coverage nur eine Quellenart", lambda z: bool((z.get("coverage") or {}).get("nur_eine_quellenart")))):
        tr = [z for z in bewertbar if pred(z)]
        n_falsch = sum(1 for z in tr if not z["ok"])
        quote = f"{n_falsch / len(tr) * 100:.0f}% Fehlerquote" if tr else "kein Signal"
        print(f"  {name:34s} trifft {len(tr):3d} Zeilen, davon falsch {n_falsch:2d} ({quote})")

    falsch_ids = sorted({z["frage_id"] for z in falsch})
    print(f"\nFalsche Antworten betreffen: {falsch_ids}")
    for z in sorted(falsch, key=lambda x: x["frage_id"]):
        print(f"  {z['frage_id']} [{z['lauf'][9:]:14s}] C={z['confidence_vorlaeufig']} "
              f"s1={z['s1']} s2={z['s2']} s3={z['s3']} grounding={z.get('grounding_urteil')}")

    (P / "kalibrierung_daten.json").write_text(json.dumps(
        [{k: z.get(k) for k in ("frage_id", "lauf", "kat", "ok", "urteil_quelle", "entscheid",
                                "eskalationsgrund", "s1", "s2", "s3", "confidence_vorlaeufig",
                                "grounding_urteil", "unvollstaendig", "rueckfrage", "dauer_s")}
         for z in zeilen], ensure_ascii=False, indent=1), encoding="utf8")
    print("\nRohdaten: eval/kalibrierung_daten.json")


if __name__ == "__main__":
    main()
