"""Pipeline: Sprache -> Hard-Routing -> Retrieval -> Rerank -> Coverage -> Generierung -> Grounding -> Log.

Phase 4. Die Confidence C wird berechnet und protokolliert, aber es wird KEINE Schwelle gesetzt:
die Schwelle ist in Phase 5 zu kalibrieren, nicht zu raten (CLAUDE.md). Eskaliert wird in Phase 4
ausschliesslich aus zwei harten Gruenden:
  1. Hard-Routing (Rechtsmittel, Busse, Haftung) – vor der Generierung, ohne LLM-Aufruf.
  2. Coverage-Luecke – der Kontext enthaelt die gefragte Art von Information nicht.
Beide sind von der Confidence getrennt.
"""
import time
import uuid
from . import confidence as conf
from . import coverage as cov
from . import generate as gen
from . import grounding
from .auditlog import pseudonym, schreibe
from .lang import detect, EN_DISCLAIMER
from .llm import frag, nur_json, LLMUeberlastet, FEHLER_DE, FEHLER_EN, MODELL
from .retrieve import search
from .routing import hard_route, KONTAKT

KANDIDATEN = 20      # aus dem Index geholt
KONTEXT_K = 10       # davon in den Prompt
BM25_NETZ = 2        # zusaetzliche Chunks aus dem BM25-Recall-Netz


def _s1(hits) -> dict:
    """Retrieval-Qualitaet aus den Kosinus-Scores: Spitzenwert, Mittel der Top-3, Abstand zum Rest."""
    s = [sc for _, sc in hits] or [0.0]
    top1 = max(0.0, min(1.0, s[0]))
    top3 = sum(s[:3]) / min(3, len(s))
    marge = s[0] - (s[3] if len(s) > 3 else 0.0)
    return {"s1": round(top1, 4), "top3_mittel": round(top3, 4), "marge": round(marge, 4)}


def _eskalation(grund, detail, lang, quellen=None, extra=None):
    txt = {
        "hard_routing": detail.get("begruendung", ""),
        "coverage": ("Zu dieser Frage liegen in der Wissensbasis keine ausreichenden Angaben vor."
                     if lang == "de" else
                     "The knowledge base does not contain sufficient information on this question."),
        "dienst": FEHLER_EN if lang == "en" else FEHLER_DE,
    }[grund]
    kontakt = detail.get("kontakt", KONTAKT["stelle"])
    nachsatz = (f"\n\nBitte wenden Sie sich an: {kontakt}" if lang == "de"
                else f"\n\nPlease contact: {kontakt}")
    antwort = txt + nachsatz
    if lang == "en":
        antwort += "\n\n" + EN_DISCLAIMER
    return {"entscheid": "eskaliert", "eskalationsgrund": grund, "antwort": antwort,
            "quellen": quellen or [], "sprache": lang, **(extra or {})}


def antworte(frage: str, *, reranker=None, k=KONTEXT_K, kandidaten=KANDIDATEN,
             mit_grounding=True, bm25_netz=BM25_NETZ, frage_id=None, logdatei=None,
             fortschritt=None) -> dict:
    """fortschritt: optionales Callable(schritt: str), damit eine UI den Stand anzeigen kann.
    Die Antwortzeit liegt je nach Auslastung des Sprachdiensts zwischen 3 und 30 Sekunden
    (gemessen in Phase 5), deshalb lohnt die Rueckmeldung."""
    melde = fortschritt or (lambda _s: None)
    t0 = time.time()
    lang = detect(frage)
    # Eigene Kennung je Antwort. Das Pseudonym allein genuegt nicht: es ist der Hash der Frage,
    # bei wiederholter Frage also identisch. Ein menschliches Urteil muss aber genau einer Antwort
    # zugeordnet werden koennen (Kalibrierung, siehe PROGRESSION/005).
    antwort_id = uuid.uuid4().hex[:16]
    basis = {"antwort_id": antwort_id, "pseudonym": pseudonym(frage), "frage_id": frage_id,
             "sprache": lang, "modell": MODELL, "reranker": reranker, "k": k}

    # 1. Hard-Routing vor allem anderen, ohne LLM-Aufruf
    hr = hard_route(frage, lang)
    if hr:
        erg = _eskalation("hard_routing", hr, lang, extra={"routing_themen": hr["themen"]})
        erg.update({"antwort_id": antwort_id, "dauer_s": round(time.time() - t0, 2)})
        schreibe({**basis, **{x: erg[x] for x in ("entscheid", "eskalationsgrund", "antwort", "dauer_s")},
                  "routing_themen": hr["themen"], "quellen": []}, logdatei)
        return erg

    # 2. Retrieval (+ optionales Reranking)
    melde("retrieval")
    hits = search(frage, k=kandidaten, mode="dense")
    s1 = _s1(hits)
    if reranker:
        from .rerank import rerank
        gereiht = rerank(frage, hits, reranker)
    else:
        gereiht = hits
    ausgewaehlt = [c for c, _ in gereiht[:k]]
    kandidaten_chunks = [c for c, _ in hits]

    # BM25-Recall-Netz: Chunks, die der dichte Index gar nicht gefunden hat, aber lexikalisch
    # eindeutig passen. Sie werden dem Kontext ZUSAETZLICH beigegeben, nicht in die Rangliste
    # gemischt - sonst schneidet k sie wieder ab (gemessen, siehe PROGRESSION/004).
    if bm25_netz:
        from .retrieve import bm25_recall
        nachzug = bm25_recall(frage, ausschluss=[c["chunk_id"] for c in ausgewaehlt], n=bm25_netz)
        ausgewaehlt = ausgewaehlt + [c for c, _ in nachzug]
        kandidaten_chunks = kandidaten_chunks + [c for c, _ in nachzug]
    else:
        nachzug = []

    # 3. Coverage: bei Gebuehrenfragen Webseite UND Erlass erzwingen
    ausgewaehlt, erg_info = cov.ergaenze_gegenstueck(frage, ausgewaehlt, kandidaten_chunks)
    cv = cov.pruefe(frage, ausgewaehlt)
    quellen_ids = [c["chunk_id"] for c in ausgewaehlt]

    if not cv["ok"]:
        erg = _eskalation("coverage", {}, lang, quellen=[])
        erg.update({"antwort_id": antwort_id, "coverage": cv, "coverage_ergaenzung": erg_info, **s1,
                    "dauer_s": round(time.time() - t0, 2)})
        schreibe({**basis, "entscheid": "eskaliert", "eskalationsgrund": "coverage",
                  "antwort": erg["antwort"], "coverage": cv, "quellen": quellen_ids, **s1,
                  "dauer_s": erg["dauer_s"]}, logdatei)
        return erg

    hinweis = None
    if cv["nur_eine_quellenart"]:
        hinweis = ("Zu dieser Gebuehrenfrage liegt nur eine Quellenart vor "
                   f"({', '.join(cv['quellenarten_mit_betrag'])}). Weise darauf hin, dass die "
                   "rechtliche Grundlage beziehungsweise die Webseite zusaetzlich zu pruefen ist.")

    # 4. Generierung
    melde("generierung")
    try:
        res, meta = frag(gen.prompt(frage, ausgewaehlt, lang, hinweis), gen.SCHEMA)
    except LLMUeberlastet as e:
        erg = _eskalation("dienst", {}, lang, quellen=quellen_ids)
        erg.update({"antwort_id": antwort_id, "fehler": str(e), "dauer_s": round(time.time() - t0, 2)})
        schreibe({**basis, "entscheid": "eskaliert", "eskalationsgrund": "dienst",
                  "fehler": str(e), "quellen": quellen_ids, "dauer_s": erg["dauer_s"]}, logdatei)
        return erg

    antwort = (res.get("antwort") or "").strip()
    benutzt = gen.quellen_aus_markern(res.get("verwendete_quellen", []), ausgewaehlt)
    s3 = max(0.0, min(1.0, float(res.get("selbstbewertung", 0.0))))

    # 5. Grounding (S2) gegen genau den Kontext, der im Prompt stand
    melde("grounding")
    kontext_text = gen.quellenblock(ausgewaehlt)
    gr = grounding.pruefe(antwort, kontext_text, llm=nur_json if mit_grounding else None, frage=frage)
    s2 = gr["s2"]

    # 6. Confidence berechnen (Anzeigewert) und Eskalation strukturell entscheiden.
    # Es gibt bewusst KEINE Schwelle auf C: die Kalibrierung in Phase 5 hat gezeigt, dass C nicht
    # nachweisbar zwischen richtigen und falschen Antworten trennt (AUC 0.620, 95% 0.432-0.809).
    konf = conf.berechne(s1["s1"], s2, s3)
    c = konf["c"]
    vollst = cov.pruefe_vollstaendigkeit(frage, antwort, benutzt or ausgewaehlt)
    gruende = conf.eskalationsgruende(coverage=cv, grounding=gr["urteil"],
                                      unvollstaendig=bool(res.get("unvollstaendig")),
                                      betrag_fehlt=vollst)
    ent = conf.entscheid(gruende)
    retrieval_warnung = s1["s1"] < conf.RETRIEVAL_WARNUNG

    # Kontaktangabe deterministisch anhaengen, nicht vom Modell erzeugen lassen: eine halluzinierte
    # Telefonnummer waere ein schwerer Fehler, und Nummern aus dem Prompt wuerden Schicht A ausloesen,
    # weil sie nicht im Kontext stehen. Das Anhaengen erfolgt NACH der Grounding-Pruefung (Zeile oben),
    # damit nur der vom Modell erzeugte Text geprueft wird.
    if ent["begleithinweise"] or cv["nur_eine_quellenart"] or res.get("ausserhalb_scope"):
        if res.get("ausserhalb_scope"):
            kontakt = KONTAKT["ausserhalb"]
        else:
            kontakt = KONTAKT["parken"] if "park" in frage.lower() else KONTAKT["stelle"]
        if not vollst.get("ok", True):
            betraege = ", ".join("CHF " + b for b in vollst["fehlend"])
            antwort += (
                f"\n\nHinweis: Die Rechtsgrundlage nennt fuer diesen Zeitraum weitere Betraege "
                f"({betraege}). Bitte pruefen Sie, welcher Fall auf Sie zutrifft."
                if lang == "de" else
                f"\n\nNote: the legal basis states further amounts for this period "
                f"({betraege}). Please check which case applies to you.")
        if gr["urteil"] == "nicht_gedeckt":
            antwort += ("\n\nHinweis: Diese Antwort konnte nicht vollstaendig gegen die Quellen "
                        "abgesichert werden. Bitte lassen Sie sie bestaetigen."
                        if lang == "de" else
                        "\n\nNote: this answer could not be fully verified against the sources. "
                        "Please have it confirmed.")
        antwort += (f"\n\nWeiter hilft Ihnen: {kontakt}" if lang == "de"
                    else f"\n\nFor further help please contact: {kontakt}")
    if lang == "en" and EN_DISCLAIMER not in antwort:
        antwort = antwort + "\n\n" + EN_DISCLAIMER

    erg = {
        "antwort_id": antwort_id,
        "bm25_nachzug": [c["chunk_id"] for c, _ in nachzug],
        "entscheid": ent["entscheid"], "eskalationsgrund": None, "antwort": antwort, "sprache": lang,
        "eskalationsgruende": ent["alle_gruende"], "begleithinweise": ent["begleithinweise"],
        "confidence": konf, "retrieval_warnung": retrieval_warnung, "vollstaendigkeit": vollst,
        "quellen": [{"chunk_id": c_["chunk_id"], "titel": c_["title"], "srs": c_.get("srs"),
                     "url": c_["url"], "pfad": c_.get("path"), "typ": c_["doc_type"]}
                    for c_ in (benutzt or ausgewaehlt)],
        "kontext_ids": quellen_ids, "coverage": cv, "coverage_ergaenzung": erg_info,
        "grounding": gr, "s1": s1["s1"], "s2": s2, "s3": s3, "confidence_vorlaeufig": c,
        "retrieval": s1, "rueckfrage": bool(res.get("rueckfrage")),
        "unvollstaendig": bool(res.get("unvollstaendig")),
        "unvollstaendig_grund": res.get("unvollstaendig_grund"),
        "tokens": meta, "dauer_s": round(time.time() - t0, 2),
        "hinweis": konf["hinweis"],
    }
    schreibe({**basis, "entscheid": ent["entscheid"], "antwort": antwort, "quellen": quellen_ids,
              "bm25_nachzug": [c["chunk_id"] for c, _ in nachzug],
              "benutzte_quellen": [c_["chunk_id"] for c_ in benutzt], "s1": s1["s1"], "s2": s2, "s3": s3,
              "confidence_vorlaeufig": c, "confidence_kalibriert": False,
              "eskalationsgruende": [g["grund"] for g in ent["alle_gruende"]],
              "retrieval_warnung": retrieval_warnung, "retrieval": s1, "vollstaendigkeit": vollst,
              "grounding_urteil": gr["urteil"], "grounding_grund": gr["grund"],
              "coverage": cv, "coverage_ergaenzung": erg_info, "rueckfrage": erg["rueckfrage"],
              "unvollstaendig": erg["unvollstaendig"], "tokens": meta, "dauer_s": erg["dauer_s"]}, logdatei)
    return erg
