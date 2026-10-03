"""Mobilitäts-Assistent Stadt Zug – Streamlit-Oberfläche (Phase 6).

Layout nach dem freigegebenen Entwurf zg_rag_prototype.html: Bürger-Ansicht links, ausblendbare
Pilot-Ansicht rechts. Abweichungen vom Entwurf sind in PROGRESSION/006 begründet; die wichtigste:
Der Entwurf zeigt eine Konfidenz-Schwelle. Es gibt keine, weil C nicht kalibrierbar war (Phase 5).
An ihrer Stelle stehen die strukturellen Prüfungen.

Start lokal:   streamlit run app.py
Deployment:    Streamlit Community Cloud, Secrets GEMINI_API_KEY und AUDIT_SALT
"""
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ui.stil import css, WORTMARKE
from ui.texte import T, GRUND_TEXT, VORSCHLAEGE

st.set_page_config(page_title="Mobilitäts-Assistent Stadt Zug", page_icon="🅿️",
                   layout="wide", initial_sidebar_state="collapsed")


# --- Secrets vor dem ersten Modellaufruf in die Umgebung spiegeln ----------------
# Auf Streamlit Cloud stehen die Schluessel in st.secrets, lokal in .env. rag.llm liest die Umgebung.
def _secrets_uebernehmen():
    for name in ("GEMINI_API_KEY", "AUDIT_SALT"):
        if os.environ.get(name):
            continue
        try:
            if name in st.secrets:
                os.environ[name] = str(st.secrets[name])
        except Exception:
            pass  # keine secrets.toml vorhanden – dann greift die lokale .env unten
    # Lokale Entwicklung: .env laden, bevor irgendwo auf GEMINI_API_KEY geprueft wird.
    from rag.llm import lade_env
    lade_env()


_secrets_uebernehmen()


@st.cache_resource(show_spinner=False)
def pipeline_laden():
    """Index und Embedding-Modell einmal pro Prozess laden, nicht pro Interaktion."""
    from rag.pipeline import antworte
    from rag.retrieve import chunks
    c = chunks()
    return antworte, c


@st.cache_data(show_spinner=False)
def wissensbasis(_n):
    """Kennzahlen für die Pilot-Ansicht, aus dem tatsächlichen Index statt fest verdrahtet."""
    from rag.retrieve import chunks
    import collections
    c = chunks()
    typen = collections.Counter(x["doc_type"] for x in c)
    srs = sorted({x["srs"] for x in c if x.get("srs")})
    seiten = len({x["doc_id"] for x in c if x["doc_id"].startswith("web:")})
    pdfs = len({x["doc_id"] for x in c if x["doc_id"].startswith("pdf:")})
    stand = max((x["retrieved"] for x in c), default="–")
    return {"chunks": len(c), "erlasse": srs, "seiten": seiten, "pdfs": pdfs,
            "typen": dict(typen), "stand": stand}


def _frage_einreihen(frage):
    """Frage sofort sichtbar machen. Die Antwort ist zunaechst offen (ergebnis=None) und wird im
    Verarbeitungsschritt am Seitenende nachgetragen. Ohne diesen Schritt erschien die Frage erst,
    wenn die Pipeline fertig war – 3 bis 35 Sekunden lang passierte sichtbar nichts."""
    st.session_state.verlauf.append({"frage": frage, "ergebnis": None})
    st.session_state.offene_frage = frage


def h(s):
    """Minimales Escaping für Text, der in eigene HTML-Bausteine geht."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def absatz_html(text):
    teile = [h(p).replace("\n", "<br>") for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in teile)


# --- Zustand ---------------------------------------------------------------------
if "verlauf" not in st.session_state:
    st.session_state.verlauf = []
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "de"
if "offene_frage" not in st.session_state:
    st.session_state.offene_frage = None
if "urteile" not in st.session_state:
    st.session_state.urteile = {}

st.markdown(css(), unsafe_allow_html=True)
t = T[st.session_state.ui_lang]

# --- Kopf ------------------------------------------------------------------------
st.markdown(f'<div class="zg-proto">{t["proto"]}</div>', unsafe_allow_html=True)
kopf_l, kopf_r = st.columns([6, 1])
with kopf_l:
    st.markdown(
        f'<div class="zg-kopf"><span class="wortmarke">{WORTMARKE}<span>Stadt Zug</span></span></div>',
        unsafe_allow_html=True)
with kopf_r:
    # Pillen-Paar wie im Entwurf. Steuert NUR die Oberflaechensprache; die Antwortsprache richtet
    # sich nach der Sprache der Frage (CLAUDE.md), unabhaengig von dieser Einstellung.
    neu = st.segmented_control("Sprache", ["de", "en"], default=st.session_state.ui_lang,
                               format_func=str.upper, label_visibility="collapsed",
                               key="lang_wahl")
    if neu and neu != st.session_state.ui_lang:
        st.session_state.ui_lang = neu
        st.rerun()

st.markdown(f'<div class="zg-crumb">{" › ".join(h(x) for x in t["crumb"])}</div>',
            unsafe_allow_html=True)
st.markdown(f'<div class="zg-h1">{h(t["h1"])}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="zg-lead">{h(t["lead"])}</div>', unsafe_allow_html=True)

pilot = st.checkbox(t["staff_toggle"], value=True)

spalten = st.columns([1, 0.42], gap="large") if pilot else [st.container()]
links = spalten[0]

# --- Bürger-Ansicht --------------------------------------------------------------
def chat_html(verlauf, t):
    """Der gesamte Gespraechsverlauf als EIN HTML-Block.

    Streamlit kapselt jeden st.markdown-Aufruf in einen eigenen Container und schliesst dabei offene
    Tags. Ein geoeffnetes <div class="zg-chat"> ueber mehrere Aufrufe hinweg funktioniert deshalb nicht
    – der Rahmen bliebe leer und die Nachrichten landeten darunter.
    """
    teile = ['<div class="zg-chat">']
    if not verlauf:
        teile.append(f'<div class="zg-m b"><p>{h(t["hello"])}</p></div>')
    for eintrag in verlauf:
        teile.append(f'<div class="zg-m u">{h(eintrag["frage"])}</div>')
        r = eintrag["ergebnis"]
        if r is None:
            teile.append('<div class="zg-m b"><p class="zg-empty">…</p></div>')
            continue
        # Eskalation bekommt den eigenen Kasten aus dem Entwurf (Akzentbalken links)
        rumpf = (f'<div class="zg-esk">{absatz_html(r["antwort"])}</div>'
                 if r["entscheid"] == "eskaliert" else absatz_html(r["antwort"]))
        teile.append(f'<div class="zg-m b">{rumpf}')
        klasse, beschriftung = {"beantwortet": ("ok", t["badge_ok"]),
                                "beantwortet_mit_hinweis": ("warn", t["badge_hinweis"]),
                                "eskaliert": ("esk", t["badge_esk"])}[r["entscheid"]]
        badges = [f'<span class="zg-badge {klasse}">{h(beschriftung)}</span>']
        if r.get("confidence"):
            badges.append(f'<span class="zg-badge">{h(t["conf_h"])} {r["confidence"]["c"]:.2f}</span>')
        teile.append(f'<div class="zg-badges">{"".join(badges)}</div>')
        quellen = [q for q in (r.get("quellen") or []) if isinstance(q, dict)]
        if quellen:
            zeilen = []
            for q in quellen:
                bez = q["titel"]
                if q.get("srs") and f'SRS {q["srs"]}' not in bez:
                    bez = f'SRS {q["srs"]} · {bez}'
                pfad = q.get("pfad") or ""
                if pfad and pfad != q["titel"]:
                    bez += f' – {pfad.split(" > ")[-1]}'
                zeilen.append(f'<a href="{h(q["url"])}" target="_blank" rel="noopener">'
                              f'<span>{h(bez)}</span><small>{h(q["typ"])}</small></a>')
            teile.append(f'<div class="zg-src"><h4>{h(t["quellen"])}</h4>{"".join(zeilen)}</div>')
        teile.append("</div>")
    teile.append("</div>")
    return "".join(teile)


with links:
    st.markdown(chat_html(st.session_state.verlauf, t), unsafe_allow_html=True)

    st.caption(t["vorschlaege"])
    vorschlaege = VORSCHLAEGE[st.session_state.ui_lang]
    knopf_spalten = st.columns(len(vorschlaege))
    for sp, frage in zip(knopf_spalten, vorschlaege):
        with sp:
            if st.button(frage, key=f"v_{frage[:22]}", use_container_width=True):
                _frage_einreihen(frage)
                st.rerun()

    with st.form("frageform", clear_on_submit=True):
        fs = st.columns([5, 1])
        eingabe = fs[0].text_input(t["ph"], placeholder=t["ph"], label_visibility="collapsed")
        gesendet = fs[1].form_submit_button(t["send"], type="primary", use_container_width=True)
    if gesendet and eingabe.strip():
        _frage_einreihen(eingabe.strip())
        st.rerun()

    st.markdown(f'<div class="zg-note">{h(t["note"])}</div>', unsafe_allow_html=True)

# --- Pilot-Ansicht ---------------------------------------------------------------
if pilot:
    with spalten[1]:
        st.markdown(f'<span class="zg-tag">{h(t["staff_tag"])}</span>', unsafe_allow_html=True)
        letzte = st.session_state.verlauf[-1]["ergebnis"] if st.session_state.verlauf else None

        # Konfidenz
        teile = [f'<div class="zg-card"><h3>{h(t["conf_h"])}</h3>']
        if letzte and letzte.get("confidence"):
            k = letzte["confidence"]
            for name, wert, klasse in ((t["s1"], k["s1"], ""), (t["s2"], k["s2"], ""),
                                       (t["s3"], k["s3"], ""), (t["gesamt"], k["c"], "gesamt")):
                teile.append(f'<div class="zg-bar"><span>{h(name)}</span>'
                             f'<i><b class="{klasse}" style="width:{wert*100:.0f}%"></b></i>'
                             f'<span>{wert:.2f}</span></div>')
            teile.append(f'<div class="zg-warnbox">{h(t["conf_warn"])}</div>')
            if letzte.get("retrieval_warnung"):
                teile.append(f'<div class="zg-warnbox">{h(t["retr_warn"])}</div>')
        else:
            teile.append(f'<p class="zg-empty">{h(t["keine_anfrage"])}</p>')
        teile.append("</div>")
        st.markdown("".join(teile), unsafe_allow_html=True)

        # Prüfungen (an der Stelle, wo der Entwurf die Schwelle zeigte)
        teile = [f'<div class="zg-card"><h3>{h(t["gruende_h"])}</h3>']
        if letzte:
            gr = letzte.get("eskalationsgruende") or []
            if letzte.get("eskalationsgrund"):
                gr = gr or [{"grund": letzte["eskalationsgrund"]}]
            if gr:
                for g in gr:
                    name = GRUND_TEXT[st.session_state.ui_lang].get(g["grund"], g["grund"])
                    detail = g.get("detail")
                    zusatz = f' <span>{h(detail)}</span>' if isinstance(detail, (str, list)) else ""
                    teile.append(f'<div class="zg-kv"><div><span>{h(name)}</span>'
                                 f'<b>{h(g.get("grund"))}</b></div></div>')
            else:
                teile.append('<div class="zg-kv"><div><span>—</span><b>ohne Befund</b></div></div>')
        else:
            teile.append(f'<p class="zg-empty">{h(t["keine_anfrage"])}</p>')
        teile.append("</div>")
        st.markdown("".join(teile), unsafe_allow_html=True)

        # Beurteilung durch die Sachbearbeitung.
        # Phase 5 hat gezeigt, dass 24 Testfragen für eine Kalibrierung der Confidence nicht reichen –
        # es fehlen Fehlerbeispiele. Nur hier entstehen sie, im laufenden Betrieb.
        if letzte and letzte.get("antwort_id"):
            aid = letzte["antwort_id"]
            schon = st.session_state.urteile.get(aid)
            st.markdown(f'<div class="zg-card"><h3>{h(t["fb_h"])}</h3>'
                        f'<p class="zg-empty">{h(t["fb_lead"])}</p></div>', unsafe_allow_html=True)
            if schon:
                st.success(f'{t["fb_gespeichert"]} ({schon})')
            else:
                wahl = st.radio(t["fb_h"], ["richtig", "teilweise", "falsch", "unklar"],
                                horizontal=True, label_visibility="collapsed", key=f"fb_{aid}",
                                format_func=lambda x: t[f"fb_{x}"], index=None)
                person = st.text_input(t["fb_person"], key=f"fbp_{aid}", max_chars=12)
                bem = st.text_input(t["fb_bemerkung"], key=f"fbb_{aid}")
                if st.button(t["fb_speichern"], key=f"fbs_{aid}", disabled=wahl is None):
                    from rag.auditlog import urteil_eintragen
                    urteil_eintragen(aid, wahl, bemerkung=bem or None,
                                     von=person or None, pseudonym_wert=letzte.get("pseudonym"))
                    st.session_state.urteile[aid] = wahl
                    st.rerun()

        # Pipeline
        teile = [f'<div class="zg-card"><h3>{h(t["pipe_h"])}</h3><div class="zg-kv">']
        if letzte:
            cv = letzte.get("coverage") or {}
            rows = [
                (t["p_sprache"], letzte.get("sprache", "–")),
                (t["p_treffer"], len(letzte.get("kontext_ids") or [])),
                (t["p_netz"], len(letzte.get("bm25_nachzug") or [])),
                (t["p_coverage"], ", ".join(cv.get("typen") or []) or "–"),
                (t["p_grounding"], (letzte.get("grounding") or {}).get("urteil", "–")),
                (t["p_routing"], letzte.get("eskalationsgrund") or "–"),
                (t["p_modell"], (letzte.get("tokens") or {}).get("modell", "–")),
                (t["p_tokens"], f'{(letzte.get("tokens") or {}).get("prompt_tokens", "–")} / '
                                f'{(letzte.get("tokens") or {}).get("output_tokens", "–")}'),
                (t["p_zeit"], f'{letzte.get("dauer_s", "–")} s'),
            ]
            for name, wert in rows:
                teile.append(f'<div><span>{h(name)}</span><b>{h(wert)}</b></div>')
        else:
            teile.append(f'<p class="zg-empty">{h(t["keine_anfrage"])}</p>')
        teile.append("</div></div>")
        st.markdown("".join(teile), unsafe_allow_html=True)

        # Wissensbasis
        wb = wissensbasis(1)
        teile = [f'<div class="zg-card"><h3>{h(t["corp_h"])}</h3><div class="zg-kv">']
        for name, wert in (("Erlasse (SRS)", ", ".join(wb["erlasse"])),
                           ("Webseiten", wb["seiten"]),
                           ("PDF-Dokumente", wb["pdfs"]),
                           ("Chunks", wb["chunks"]),
                           ("Vector Store", "FAISS (lokal)"),
                           ("Embedding", "MiniLM-L12 (lokal)"),
                           ("Stand", wb["stand"])):
            teile.append(f'<div><span>{h(name)}</span><b>{h(wert)}</b></div>')
        teile.append("</div></div>")
        st.markdown("".join(teile), unsafe_allow_html=True)

st.markdown(f'<div class="zg-foot">{h(t["footer"])}</div>', unsafe_allow_html=True)

# --- Anfrage verarbeiten ---------------------------------------------------------
if st.session_state.offene_frage:
    frage = st.session_state.offene_frage
    st.session_state.offene_frage = None
    if not os.environ.get("GEMINI_API_KEY"):
        st.error(t["kein_key"])
    else:
        platz = st.empty()
        try:
            with platz.container():
                stand = st.status(t["schritte"]["retrieval"], expanded=False)
            antworte, _ = pipeline_laden()
            r = antworte(frage, fortschritt=lambda s: stand.update(label=t["schritte"].get(s, s)))
            stand.update(label="✓", state="complete")
            platz.empty()
            offen = st.session_state.verlauf[-1]
            offen["ergebnis"] = r
        except Exception as e:  # noqa: BLE001 – der Nutzerin keinen Traceback zeigen
            platz.empty()
            st.session_state.verlauf[-1]["ergebnis"] = {
                "entscheid": "eskaliert", "eskalationsgrund": "dienst", "antwort": t["fehler"],
                "quellen": [], "sprache": st.session_state.ui_lang}
            st.error(f'{t["fehler"]} ({type(e).__name__})')
        st.rerun()
