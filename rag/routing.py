"""Hard-Routing: Themen, die vor der Generierung an Menschen gehen.
Laeuft VOR dem LLM und ist von der Confidence-Eskalation getrennt (CLAUDE.md).
Alle Muster auf gefaltetem Text (Homoglyphen entschaerft, Umlaute aufgeloest)."""
import re
from .norm import fold

KONTAKT = {
    "stelle": "Abteilung Sicherheit und Verkehr, Stadt Zug",
    "parken": "Parkraumbewirtschaftung, +41 58 728 99 00, parkraumbewirtschaftung@stadtzug.ch",
    "ausserhalb": "die Stadtverwaltung Zug ueber stadtzug.ch (dieser Assistent deckt nur Mobilitaetsthemen ab)",
}
RULES = [
    ("rechtsmittel", re.compile(
        r"einsprache|einspruch|beschwerde fuehren|beschwerde einlegen|beschwerde gegen|rekurs|rechtsmittel|"
        r"anfechten|rechtlich vorgehen|wehre ich mich|wehren gegen|klage|verwaltungsgericht|gerichtlich|"
        r"\bappeal\b|contest (the|a|my)|legal action|take legal|sue\b|lawsuit")),
    ("busse", re.compile(
        r"\bbusse[nr]?\b|ordnungsbusse|parkbusse|verzeigung|gebuehrenstrafe|\bstrafe\b|bestraft|knoellchen|"
        r"parking fine|\bfine[sd]?\b|\bpenalty\b|parking ticket")),
    ("haftung", re.compile(
        r"haftung|haftet|haftbar|schadenersatz|schadensersatz|regress|"
        r"(schaden|beschaedig\w*|kaputt|demoliert|zerkratzt)[^.?!]{0,60}(wer zahlt|zahlt (die|wer)|ersetz\w*|"
        r"uebernimmt|verantwortlich|haft\w*)|"
        r"(wer (zahlt|kommt fuer|haftet|uebernimmt))[^.?!]{0,60}(schaden|beschaedig\w*)|"
        r"\bliable\b|liability|\bdamages\b|compensation|who pays for the damage")),
]
GRUND = {
    "rechtsmittel": ("Rechtsmittel", "Zu Rechtsmitteln und Verfahren gibt dieser Assistent keine Auskunft."),
    "busse": ("Bussen", "Zu Bussen und Strafverfahren gibt dieser Assistent keine Auskunft."),
    "haftung": ("Haftung", "Haftungs- und Schadenersatzfragen im Einzelfall beurteilt dieser Assistent nicht."),
}
GRUND_EN = {
    "rechtsmittel": ("legal remedies", "This assistant does not advise on legal remedies or proceedings."),
    "busse": ("fines", "This assistant does not advise on fines or penal proceedings."),
    "haftung": ("liability", "This assistant does not assess liability or compensation in individual cases."),
}

def hard_route(frage: str, lang: str = "de"):
    """-> None (weiter in der Pipeline) oder dict mit Eskalationsgrund."""
    f = fold(frage)
    treffer = [name for name, pat in RULES if pat.search(f)]
    if not treffer: return None
    g = (GRUND_EN if lang == "en" else GRUND)
    thema, text = g[treffer[0]]
    return {"eskalation": "hard_routing", "themen": treffer, "thema": thema, "begruendung": text,
            "kontakt": KONTAKT["stelle"], "quellen": []}
