"""Pipeline-Evaluation auf testset.json.

Standard ist der dev-Split. Der test-Split wird nur mit --split test ausgewertet und ist fuer Phase 7
reserviert (siehe eval/README.md).

Nicht jede Kategorie laesst sich automatisch bewerten. Faelle, bei denen das Urteil Ermessen braucht
(Rueckfrage angemessen? differenziert genug? Hinweis auf fehlende Deckung deutlich genug?), werden als
"manuell" ausgewiesen und NICHT in die Trefferquote gerechnet. Sonst misst man die eigene Heuristik.

Usage: python eval/eval_pipeline.py [--split dev|test|alle] [--reranker bge|jina2|msmarco12] [--k 5] [--ids D01,D02]
"""
import sys, json, re, time, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.pipeline import antworte
from rag.lang import EN_DISCLAIMER
from rag.norm import fold

P = Path(__file__).parent

AUTO_VERHALTEN = {"antworten", "antworten_mit_hinweis", "antworten_en_mit_hinweis", "korrigieren", "eskalieren"}
MANUELL_VERHALTEN = {"nicht_gedeckt_melden", "ausserhalb_scope", "rueckfrage",
                     "antworten_differenziert_oder_rueckfrage", "antworten_mit_vorbehalt"}


def verhalten_ok(soll, r):
    """-> True | False | None (None = braucht menschliches Urteil)"""
    e = r["entscheid"]
    if soll == "eskalieren":
        return e == "eskaliert"
    if soll in ("antworten", "antworten_mit_hinweis", "korrigieren"):
        return e in ("beantwortet", "beantwortet_mit_hinweis")
    if soll == "antworten_en_mit_hinweis":
        return (e in ("beantwortet", "beantwortet_mit_hinweis") and r.get("sprache") == "en"
                and EN_DISCLAIMER[:40] in r["antwort"])
    return None


def inhalt_ok(t, r):
    a = fold(r["antwort"])
    fehlt = [m for m in t["muss_enthalten"] if fold(m) not in a]
    verboten = [m for m in t.get("darf_nicht_enthalten", []) if re.search(rf"(?<!\d){re.escape(fold(m))}(?!\d)", a)]
    return (not fehlt and not verboten), fehlt, verboten


def quellen_ok(t, r):
    ids = r.get("kontext_ids", [])
    fehlt = [q for q in t["erwartete_quellen"] if not any(i.startswith(q) for i in ids)]
    return not fehlt, fehlt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "alle"])
    ap.add_argument("--reranker", default=None)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--pause", type=float, default=4.0, help="Sekunden zwischen Fragen (Free-Tier-Quota)")
    a = ap.parse_args()

    T = json.loads((P / "testset.json").read_text(encoding="utf8"))
    if a.split != "alle":
        T = [t for t in T if t["split"] == a.split]
    if a.ids:
        wunsch = {x.strip() for x in a.ids.split(",")}
        T = [t for t in T if t["id"] in wunsch]
    if a.split == "test":
        print("!! test-Split wird ausgewertet. Das ist fuer Phase 7 reserviert; im Bericht vermerken.\n")

    log = Path(a.out) if a.out else P / f"pipeline_{a.split}_{a.reranker or 'ohne'}.jsonl"
    if log.exists():
        log.unlink()
    zeilen, dauer = [], []
    for n_, t in enumerate(T):
        if n_ and a.pause: time.sleep(a.pause)
        r = antworte(t["frage"], reranker=a.reranker, k=a.k, frage_id=t["id"], logdatei=log)
        v = verhalten_ok(t["erwartetes_verhalten"], r)
        i_ok, fehlt, verboten = inhalt_ok(t, r)
        q_ok, q_fehlt = quellen_ok(t, r)
        auto = v is not None
        ok = (v and i_ok and q_ok) if auto else None
        dauer.append(r["dauer_s"])
        zeilen.append({"id": t["id"], "kat": t["kategorie"], "soll": t["erwartetes_verhalten"],
                       "ist": r["entscheid"] + (f"/{r['eskalationsgrund']}" if r.get("eskalationsgrund") else ""),
                       "verhalten": v, "inhalt": i_ok, "quellen": q_ok, "ok": ok, "auto": auto,
                       "fehlt": fehlt, "verboten": verboten, "quellen_fehlt": q_fehlt,
                       "grounding": r.get("grounding", {}).get("urteil"),
                       "c": r.get("confidence_vorlaeufig"), "s1": r.get("s1"), "s2": r.get("s2"),
                       "s3": r.get("s3"), "dauer": r["dauer_s"], "antwort": r["antwort"],
                       "rueckfrage": r.get("rueckfrage"), "unvollstaendig": r.get("unvollstaendig")})
        flag = {True: "OK  ", False: "FEHL", None: "man."}[ok]
        print(f"{flag} {t['id']} {t['kategorie'][:18]:18s} soll={t['erwartetes_verhalten'][:26]:26s} "
              f"ist={zeilen[-1]['ist'][:22]:22s} C={r.get('confidence_vorlaeufig')} {r['dauer_s']}s")
        if ok is False:
            if v is False: print(f"       Verhalten falsch")
            if fehlt: print(f"       fehlt im Text: {fehlt}")
            if verboten: print(f"       verbotener Inhalt: {verboten}")
            if q_fehlt: print(f"       Quelle nicht im Kontext: {q_fehlt}")

    auto = [z for z in zeilen if z["auto"]]
    man = [z for z in zeilen if not z["auto"]]
    n_ok = sum(1 for z in auto if z["ok"])
    print(f"\n--- Split {a.split}, Reranker {a.reranker or 'ohne'}, k={a.k}")
    print(f"automatisch bewertbar: {n_ok}/{len(auto)} korrekt")
    print(f"manuell zu beurteilen: {len(man)} ({', '.join(z['id'] for z in man)})")
    print(f"Dauer: Median {sorted(dauer)[len(dauer)//2]:.1f}s, max {max(dauer):.1f}s, "
          f"ueber 5s: {sum(d > 5 for d in dauer)}/{len(dauer)}")
    gr = [z for z in zeilen if z["grounding"] == "nicht_gedeckt"]
    if gr: print(f"Grounding nicht_gedeckt: {[z['id'] for z in gr]}")
    (P / f"ergebnis_{a.split}_{a.reranker or 'ohne'}.json").write_text(
        json.dumps(zeilen, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"Details: eval/ergebnis_{a.split}_{a.reranker or 'ohne'}.json, Log: {log.name}")


if __name__ == "__main__":
    main()
