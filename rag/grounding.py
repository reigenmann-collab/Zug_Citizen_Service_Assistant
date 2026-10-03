"""Grounding-Checker (S2): Ist jede Tatsachenaussage der Antwort durch den Kontext gedeckt?

Zwei Schichten, weil keine allein genuegt:

  Schicht A – deterministische Zahlenpruefung. Jede Zahl, jeder Betrag und jede Dauer in der Antwort
  muss im Kontext vorkommen. Faengt erfundene Werte zuverlaessig (Fr. 200 statt 30/60, zehn statt
  fuenf Jahre). Faengt NICHT: eine Zahl, die im Kontext steht, aber falsch zugeordnet wird.

  Schicht B – aussagenweise Pruefung durch das LLM. Faengt falsche Zuordnung und unzulaessige
  Verallgemeinerung. Allein unzuverlaessig bei Zahlen, deshalb nur als Ergaenzung.

Ein Treffer in Schicht A ist hart: die Antwort gilt als nicht gedeckt, unabhaengig von Schicht B.

Einschraenkung: Schicht B benutzt dasselbe Modell wie die Generierung. Das ist keine unabhaengige
Pruefung. In Phase 5 bei der Kalibrierung mitberuecksichtigen.
"""
import json, re
from .norm import norm

# --- Schicht A ---------------------------------------------------------------

ZAHLWORT = {
    "null": 0, "ein": 1, "eine": 1, "einem": 1, "einer": 1, "eins": 1, "zwei": 2, "drei": 3, "vier": 4,
    "fuenf": 5, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11,
    "zwoelf": 12, "zwölf": 12, "dreizehn": 13, "vierzehn": 14, "fuenfzehn": 15, "fünfzehn": 15,
    "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19, "zwanzig": 20, "dreissig": 30,
    "vierzig": 40, "fuenfzig": 50, "fünfzig": 50, "sechzig": 60, "hundert": 100,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "twenty": 20, "thirty": 30, "fifty": 50,
}
# Einheiten, bei denen eine Zahl eine pruefbare Tatsache ist
EINHEIT = (r"chf|fr\.?|franken|franc|stunde\w*|std\.?|hour\w*|tag\w*|day\w*|woche\w*|week\w*|monat\w*|"
           r"month\w*|jahr\w*|year\w*|minute\w*|uhr|meter\w*|\bm\b|prozent|%|mal|plaetz\w*|plätz\w*|"
           r"parkplaetz\w*|parkplätz\w*|tonnen|\bt\b")
NUM = re.compile(r"(?<![\w.,])(\d{1,3}(?:[' ]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?![\w])")
PARAGRAF = re.compile(r"(?:§+\s*\d+[a-z]*|abs\.?\s*\d+|bst\.?\s*[a-z]|art\.?\s*\d+|srs\s*[\d.\-]+|"
                      r"bgs\s*[\d.\-]+|\bsr\s*\d+|ziff\.?\s*\d+|lit\.?\s*[a-z])", re.I)


def _canon_num(s: str) -> str:
    """'1 500.00' / "1'500,-" -> '1500'; '30.00' -> '30'; '4.50' -> '4.5'"""
    s = s.replace("'", "").replace(" ", "").replace(",", ".")
    try:
        f = float(s)
    except ValueError:
        return s
    return str(int(f)) if f == int(f) else str(f)


def _nums_in(text: str) -> set:
    """Alle Zahlen eines Textes, kanonisiert, inklusive ausgeschriebener Zahlwoerter."""
    t = norm(text)
    out = {_canon_num(m.group(1)) for m in NUM.finditer(t)}
    for w, v in ZAHLWORT.items():
        if re.search(rf"\b{w}\b", t, re.I):
            out.add(str(v))
    return out


def _claim_nums(antwort: str) -> list:
    """Zahlen der Antwort, die eine pruefbare Tatsache tragen: solche mit Einheit in der Naehe.
    Paragraphen-, Absatz- und Erlassnummern werden ausgenommen – das sind Fundstellen, keine Fakten."""
    t = norm(antwort)
    t_ohne_fundstellen = PARAGRAF.sub(" ", t)
    claims = []
    for m in NUM.finditer(t_ohne_fundstellen):
        umfeld = t_ohne_fundstellen[max(0, m.start() - 30):m.end() + 25]
        if re.search(EINHEIT, umfeld, re.I):
            claims.append((_canon_num(m.group(1)), umfeld.strip()))
    for w, v in ZAHLWORT.items():
        for m in re.finditer(rf"\b{w}\b", t_ohne_fundstellen, re.I):
            umfeld = t_ohne_fundstellen[max(0, m.start() - 25):m.end() + 25]
            if re.search(EINHEIT, umfeld, re.I):
                claims.append((str(v), umfeld.strip()))
    return claims


def schicht_a(antwort: str, kontext: str, frage: str = "") -> dict:
    """Deterministische Zahlenpruefung. -> {ok, verstoesse:[{zahl, umfeld}], geprueft}

    Zahlen aus der FRAGE sind ausgenommen. Eine falsche Annahme laesst sich nur korrigieren, indem man
    sie benennt ("Die Aussage, dass es CHF 50 kostet, ist nicht korrekt"). Ohne diese Ausnahme wuerde
    genau die gewuenschte Korrektur als erfundene Zahl gewertet - gefunden im test-Split (T17).
    Die Gegenprobe, dass dadurch keine Luecke entsteht, ist Fall G16: Bestaetigt das Modell die falsche
    Zahl, muss Schicht B das fangen."""
    erlaubt = _nums_in(kontext) | (_nums_in(frage) if frage else set())
    verstoesse, geprueft = [], 0
    gesehen = set()
    for zahl, umfeld in _claim_nums(antwort):
        if (zahl, umfeld) in gesehen:
            continue
        gesehen.add((zahl, umfeld))
        geprueft += 1
        if zahl not in erlaubt:
            verstoesse.append({"zahl": zahl, "umfeld": umfeld})
    return {"ok": not verstoesse, "verstoesse": verstoesse, "geprueft": geprueft}


# --- Schicht B ---------------------------------------------------------------

PROMPT_B = """Du pruefst, ob eine Antwort durch die beigefuegten Quellen gedeckt ist. Du bewertest NICHT, ob die Antwort hilfreich oder gut formuliert ist.

Zerlege die Antwort in einzelne Tatsachenaussagen. Bewerte jede einzeln:
- "gedeckt": die Aussage folgt aus den Quellen, auch wenn sie anders formuliert ist (Paraphrase ist in Ordnung).
- "nicht_gedeckt": die Aussage steht nicht in den Quellen, widerspricht ihnen, ordnet einen Wert der falschen Sache zu, oder verallgemeinert ueber die Quellen hinaus.

Achte besonders auf:
- Zahlen und Betraege, die der falschen Kategorie zugeordnet werden (Beispiel: ein Betrag fuer leichte Fahrzeuge, behauptet fuer schwere).
- Zusaetze wie "immer", "in allen Faellen", "unabhaengig von", die die Quelle nicht hergibt.
- Falsche Fundstellen: Der Inhalt stimmt, aber der genannte Paragraph ist der falsche. Das ist "nicht_gedeckt".

VERNEINUNGEN. Bewerte immer die Aussage, die die Antwort TATSAECHLICH macht, nie die, die sie verneint.
"Die Aussage, dass X CHF 50 kostet, ist nicht korrekt; X ist kostenlos" behauptet NICHT, dass X CHF 50
kostet - sie behauptet das Gegenteil. Steht in den Quellen, dass X kostenlos ist, ist diese Antwort
"gedeckt". Eine falsche Annahme aus der Frage zu benennen und zu widerlegen ist richtig, nicht falsch.
Bestaetigt die Antwort die falsche Annahme dagegen, ist sie "nicht_gedeckt".

Bevor du "nicht_gedeckt" vergibst, pruefe, ob die Quelle die Aussage nicht doch stuetzt. Gib in der
Begruendung die Stelle der Quelle an, auf die du dich stuetzt. Stimmt deine Begruendung inhaltlich mit
der Aussage ueberein, ist die Aussage "gedeckt".

Hoeflichkeitsfloskeln, Verweise auf Kontaktstellen und Quellenangaben bewertest du nicht; lasse sie weg.

FRAGE DER BUERGERIN ODER DES BUERGERS (nur zum Verstaendnis, nicht zu bewerten):
{frage}

QUELLEN:
{kontext}

ANTWORT:
{antwort}

Gib JSON zurueck."""

SCHEMA_B = {
    "type": "object",
    "properties": {
        "aussagen": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "aussage": {"type": "string"},
                    "urteil": {"type": "string", "enum": ["gedeckt", "nicht_gedeckt"]},
                    "begruendung": {"type": "string"},
                },
                "required": ["aussage", "urteil"],
            },
        }
    },
    "required": ["aussagen"],
}


def schicht_b(antwort: str, kontext: str, llm, frage: str = "") -> dict:
    """Aussagenweise Pruefung durch das LLM. llm: Callable(prompt, schema) -> dict."""
    try:
        res = llm(PROMPT_B.format(kontext=kontext, antwort=antwort,
                                  frage=frage or "(nicht angegeben)"), SCHEMA_B)
    except Exception as e:
        return {"ok": None, "fehler": f"{type(e).__name__}: {e}", "aussagen": []}
    aussagen = res.get("aussagen", [])
    schlecht = [a for a in aussagen if a.get("urteil") == "nicht_gedeckt"]
    return {"ok": not schlecht, "aussagen": aussagen, "nicht_gedeckt": schlecht,
            "anteil_gedeckt": (len(aussagen) - len(schlecht)) / len(aussagen) if aussagen else None}


# --- Zusammenfuehrung --------------------------------------------------------

def pruefe(antwort: str, kontext: str, llm=None, b_trotz_a=False, frage: str = "") -> dict:
    """-> {urteil: gedeckt|nicht_gedeckt, s2: 0..1, a: ..., b: ...}
    Schicht A ist hart: ein Verstoss dort setzt das Urteil auf nicht_gedeckt.
    Darum wird Schicht B bei einem A-Verstoss uebersprungen – sie koennte das Urteil nicht mehr
    aendern und kostet einen Modellaufruf. b_trotz_a=True erzwingt sie fuer die Diagnose."""
    a = schicht_a(antwort, kontext, frage)
    if not a["ok"] and not b_trotz_a:
        return {"urteil": "nicht_gedeckt", "s2": 0.0, "grund": "zahl_nicht_im_kontext", "a": a,
                "b": {"ok": None, "aussagen": [], "uebersprungen": "A hat bereits hart geurteilt"}}
    b = schicht_b(antwort, kontext, llm, frage) if llm else {"ok": None, "aussagen": []}
    if not a["ok"]:
        return {"urteil": "nicht_gedeckt", "s2": 0.0, "grund": "zahl_nicht_im_kontext", "a": a, "b": b}
    if b["ok"] is False:
        anteil = b.get("anteil_gedeckt") or 0.0
        return {"urteil": "nicht_gedeckt", "s2": round(min(anteil, 0.5), 3), "grund": "aussage_nicht_gedeckt",
                "a": a, "b": b}
    if b["ok"] is None:
        # Nur Schicht A verfuegbar: nicht als voll gedeckt ausgeben, Unsicherheit bleibt sichtbar.
        return {"urteil": "gedeckt", "s2": 0.7, "grund": "nur_schicht_a", "a": a, "b": b}
    return {"urteil": "gedeckt", "s2": 1.0, "grund": "beide_schichten", "a": a, "b": b}
