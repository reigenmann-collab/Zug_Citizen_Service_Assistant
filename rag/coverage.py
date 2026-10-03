"""Coverage-Check: Enthaelt der Kontext ueberhaupt die ART von Information, nach der gefragt wird?

Laeuft unabhaengig von der Confidence C (CLAUDE.md). Eine Antwort kann sprachlich sicher und gut
belegt klingen und trotzdem die gefragte Zahl nicht enthalten.

Befund aus Phase 2, der die Annahme im Brief praezisiert: Gebuehren stehen NICHT nur auf Webseiten.
SRS 7.7.5-2 nennt in § 12 und § 18 konkrete Betraege. Gefaehrlich ist der umgekehrte Fall: die
Webseite nennt bei der Anwohnerparkkarte nur CHF 30/Monat, der Erlass unterscheidet CHF 30 (Nachtpark-
gebuehr bezahlt) und CHF 60 (inklusive). Wer nur die Webseite im Kontext hat, antwortet unvollstaendig.
Darum wird bei Gebuehrenfragen beides erzwungen: Webseite und Erlass.
"""
import re
from .norm import fold

FRAGETYP = {
    "gebuehr": r"kostet|kosten|gebuehr|gebuehren|preis|tarif|betrag|teuer|chf|franken|"
               r"\bcost\b|\bcosts\b|price|\bfee\b|\bfees\b|how much|tariff",
    "dauer": r"wie lange|gueltig|gueltigkeit|dauer|frist|verlaenger|laeuft.{0,15}ab|"
             r"how long|valid|validity|duration|deadline",
    "zeit": r"wann|oeffnungszeit|uhrzeit|ab wann|bis wann|werktag|sonntag|samstag|feiertag|"
            r"\bwhen\b|opening hours|what time",
    "zustaendigkeit": r"wer ist zustaendig|zustaendig|wer macht|wer betreibt|wer vollzieht|wer entscheidet|"
                      r"welche stelle|welches amt|who is responsible|which (office|department)",
    "verfahren": r"wie bekomme|wie erhalte|wie beantrage|wo beantrage|antrag|gesuch|bestellen|beziehen|"
                 r"anmelden|voraussetzung|berechtigt|how do i (get|obtain|apply)|where can i (get|apply|order)",
}
TYP_RE = {k: re.compile(v) for k, v in FRAGETYP.items()}

ZEITMUSTER = re.compile(r"\d{1,2}[.:]\d{2}\s*(uhr)?|\d+\s*(stunde|std|tag|woche|monat|jahr|minute)"
                        r"|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|feiertag|werktag"
                        r"|hour|day|week|month|year")


def fragetypen(frage: str) -> list:
    f = fold(frage)
    return [k for k, p in TYP_RE.items() if p.search(f)]


def _hat_betrag(c) -> bool:
    return bool(c.get("has_fees")) or bool(re.search(r"\bchf\b|\bfr\.", fold(c["text"])))


def _art(c) -> str:
    return "erlass" if c["doc_type"].startswith("erlass") else "web"


def ergaenze_gegenstueck(frage, ausgewaehlt, kandidaten, max_extra=2):
    """Bei Gebuehrenfragen: sicherstellen, dass Webseite UND Erlass mit Betrag im Kontext sind.
    Fuellt fehlende Art aus den Retrieval-Kandidaten nach.
    -> (kontext_chunks, info)"""
    typen = fragetypen(frage)
    if "gebuehr" not in typen:
        return ausgewaehlt, {"typen": typen, "ergaenzt": [], "status": "nicht_anwendbar"}

    mit_betrag = [c for c in ausgewaehlt if _hat_betrag(c)]
    arten = {_art(c) for c in mit_betrag}
    if not mit_betrag:
        # Gar kein Betrag im Kontext: Versuch, ueberhaupt einen zu finden.
        extra = [c for c in kandidaten if _hat_betrag(c) and c["chunk_id"] not in {x["chunk_id"] for x in ausgewaehlt}][:max_extra]
        if not extra:
            return ausgewaehlt, {"typen": typen, "ergaenzt": [], "status": "kein_betrag_im_korpus"}
        return ausgewaehlt + extra, {"typen": typen, "ergaenzt": [c["chunk_id"] for c in extra],
                                     "status": "betrag_nachgeladen"}

    fehlend = {"erlass", "web"} - arten
    if not fehlend:
        return ausgewaehlt, {"typen": typen, "ergaenzt": [], "status": "beide_arten_vorhanden"}

    drin = {c["chunk_id"] for c in ausgewaehlt}
    extra = [c for c in kandidaten
             if _art(c) in fehlend and _hat_betrag(c) and c["chunk_id"] not in drin][:max_extra]
    if not extra:
        return ausgewaehlt, {"typen": typen, "ergaenzt": [], "status": "nur_eine_quellenart",
                             "vorhanden": sorted(arten), "fehlend": sorted(fehlend)}
    return ausgewaehlt + extra, {"typen": typen, "ergaenzt": [c["chunk_id"] for c in extra],
                                 "status": "gegenstueck_ergaenzt", "ergaenzte_art": sorted(fehlend)}


def pruefe(frage: str, kontext_chunks: list) -> dict:
    """-> {ok, typen, luecken:[...]}. ok=False heisst: eskalieren, unabhaengig von C."""
    typen = fragetypen(frage)
    text = fold(" ".join(c["text"] for c in kontext_chunks))
    luecken = []
    if "gebuehr" in typen and not re.search(r"\bchf\b|\bfr\.|kostenlos|gratis|unentgeltlich", text):
        luecken.append("gebuehr_nicht_im_kontext")
    if ("dauer" in typen or "zeit" in typen) and not ZEITMUSTER.search(text):
        luecken.append("zeitangabe_nicht_im_kontext")
    arten = {_art(c) for c in kontext_chunks if _hat_betrag(c)}
    teilweise = "gebuehr" in typen and len(arten) == 1
    return {"ok": not luecken, "typen": typen, "luecken": luecken,
            "nur_eine_quellenart": teilweise, "quellenarten_mit_betrag": sorted(arten)}


# --- Vollstaendigkeit der Betraege ------------------------------------------
# Gegenstueck zum Grounding-Checker: Schicht A dort faengt Betraege in der Antwort, die NICHT im
# Kontext stehen. Hier wird das Umgekehrte geprueft - Betraege im Kontext, die in der Antwort FEHLEN.
#
# Anlass: Die Anforderung "nennt die Quelle zwei Varianten, nenne beide" haengt sonst allein am Prompt.
# Gemessen in Phase 5: Dieselbe Frage (D24, Anwohnerparkkarte auf Englisch) wurde bei identischem Code
# und Temperatur 0 einmal vollstaendig (CHF 30 und CHF 60) und einmal verkuerzt (nur CHF 30) beantwortet.
# Modellvarianz darf eine Gebuehrenauskunft nicht entscheiden.
#
# Die Pruefung ist bewusst eng: Sie greift nur, wenn ein und derselbe zitierte Abschnitt mehrere
# Betraege fuer die in der Frage genannte Zeiteinheit nennt. Sie loest einen Hinweis aus, keine
# Unterdrueckung der Antwort - Fehlalarme kosten damit einen Pruefhinweis, keine verweigerte Auskunft.

PERIODEN = {
    "monat": r"(?:pro\s+)?monat|monatlich|1\s*monat|per month|monthly",
    "jahr": r"(?:pro\s+)?jahr|jaehrlich|12\s*monate|per year|annual",
    "tag": r"(?:pro\s+)?tag|taeglich|1\s*tag|tagespauschale|per day|daily",
    "woche": r"(?:pro\s+)?woche|1\s*woche|2\s*wochen|per week",
    "stunde": r"(?:pro\s+)?stunde|std\.?|je stunde|per hour|hourly",
}
BETRAG = re.compile(r"(?:chf|fr\.)\s*([0-9]{1,4}(?:[' ]?[0-9]{3})*(?:[.,][0-9]{1,2})?)", re.I)


def _norm_betrag(s):
    s = s.replace("'", "").replace(" ", "").replace(",", ".")
    try:
        f = float(s)
    except ValueError:
        return s
    return f"{f:.2f}"


def gefragte_periode(frage):
    f = fold(frage)
    for name, pat in PERIODEN.items():
        if re.search(pat, f):
            return name
    return None


ABSATZ = re.compile(r"^\s*(\d+)\s*(?:bis|ter|quater)?\s+(?=[A-ZÄÖÜ])", re.M)


def _absaetze(text):
    """Erlasstext in Absaetze zerlegen. Absatznummern stehen am Zeilenanfang vor dem Satz
    ("1 Die Gebuehren ... betragen:"). Ohne mindestens zwei Treffer gilt der ganze Text als ein Absatz."""
    marken = [m.start() for m in ABSATZ.finditer(text)]
    if len(marken) < 2:
        return [text]
    grenzen = marken + [len(text)]
    return [text[grenzen[i]:grenzen[i + 1]] for i in range(len(marken))]


def _betraege_je_absatz(text, periode):
    """-> Liste von Betragsmengen, eine je Absatz, in dem die Zeiteinheit vorkommt."""
    pat = PERIODEN[periode]
    out = []
    for abs_ in _absaetze(text):
        menge = set()
        for zeile in fold(abs_).split("\n"):
            if not re.search(pat, zeile):
                continue
            for m in BETRAG.finditer(zeile):
                menge.add(_norm_betrag(m.group(1)))
        if menge:
            out.append(menge)
    return out


def pruefe_vollstaendigkeit(frage, antwort, zitierte_chunks):
    """-> {ok, periode, fehlend, gefunden}. ok=True auch dann, wenn die Pruefung nicht anwendbar ist."""
    if "gebuehr" not in fragetypen(frage):
        return {"ok": True, "status": "keine_gebuehrenfrage"}
    periode = gefragte_periode(frage)
    if not periode:
        return {"ok": True, "status": "keine_zeiteinheit_in_der_frage"}
    in_antwort = {_norm_betrag(m.group(1)) for m in BETRAG.finditer(fold(antwort))}
    # Nur das Muster "parallele Alternativen": dieselbe Zeiteinheit kommt in MEHREREN Absaetzen
    # desselben Paragraphen mit unterschiedlichem Betrag vor (§ 12 Abs. 1 gegen Abs. 2).
    # Mehrere Betraege innerhalb EINES Absatzes sind dagegen verschiedene Sachen - die Stundenstufen
    # in § 18 Abs. 2 oder die Mietarten - und werden nicht verlangt.
    fehlend = set()
    for c in zitierte_chunks:
        je_absatz = _betraege_je_absatz(c["text"], periode)
        if len(je_absatz) < 2:
            continue
        alle = set().union(*je_absatz)
        if len(alle) >= 2 and any(a != b for a in je_absatz for b in je_absatz):
            fehlend |= (alle - in_antwort)
    if not fehlend:
        return {"ok": True, "status": "vollstaendig", "periode": periode,
                "in_antwort": sorted(in_antwort)}
    return {"ok": False, "status": "betrag_fehlt", "periode": periode,
            "fehlend": sorted(fehlend), "in_antwort": sorted(in_antwort)}
