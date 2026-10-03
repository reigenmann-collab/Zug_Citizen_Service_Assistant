"""Confidence und Eskalationsentscheid.

Ergebnis der Kalibrierung in Phase 5 (eval/kalibrierung.py, PROGRESSION/005):

  C trennt richtige von falschen Antworten NICHT nachweisbar. Auf 63 generierten Zeilen mit 8 falschen
  Antworten ergibt sich AUC = 0.620 mit 95%-Intervall 0.432 bis 0.809 – das Intervall schliesst 0.5 ein.
  Ursache ist Saettigung: S2 ist in 98% der Zeilen genau 1.0, S3 in 84% genau 1.0. C ist damit praktisch
  eine Konstante um 0.91 mit Rauschen aus S1.

  Deshalb gibt es KEINE Confidence-Schwelle. Eskaliert wird ausschliesslich aus strukturellen Gruenden,
  die deterministisch, pruefbar und im Audit-Log nachvollziehbar sind. Das entspricht auch der
  Governance-Anforderung besser als eine undurchsichtige Punktzahl.

  C wird weiter berechnet und protokolliert, weil der Brief es verlangt und weil erst die
  Pilotdaten eine echte Kalibrierung erlauben. Es ist als Anzeigewert zu behandeln, nicht als
  Qualitaetsgarantie: `kalibriert=False` sagt das explizit.

Warum keine Gewichtung angepasst wurde: Gewichte lassen sich nur an Daten anpassen, die zwischen
richtig und falsch trennen. Solche Daten liegen nicht vor. Eine Umgewichtung waere Rauschen angepasst.
"""

GEWICHTE = {"s1": 0.3, "s2": 0.4, "s3": 0.3}

# Warnschwelle fuer die Retrieval-Qualitaet, NICHT fuer die Eskalation.
# Hergeleitet in eval/kalibrierung_retrieval.py: top1 erkennt fehlende Quellen im Kontext mit
# AUC 0.706 (95% 0.562-0.850, schliesst 0.5 nicht ein). Bei 0.69 werden alle 4 Fehlschlaege erkannt,
# dafuer schlaegt die Warnung bei 18 von 44 Fragen an (Praezision 22%). Fuer eine Anzeige im
# Pilot-Bereich tragbar, fuer eine Weiterleitung nicht. Beruht auf nur 4 Negativbeispielen und ist
# mit Pilotdaten zu revidieren.
RETRIEVAL_WARNUNG = 0.69


def berechne(s1: float, s2: float, s3: float) -> dict:
    c = round(GEWICHTE["s1"] * s1 + GEWICHTE["s2"] * s2 + GEWICHTE["s3"] * s3, 4)
    return {"c": c, "s1": round(s1, 4), "s2": round(s2, 4), "s3": round(s3, 4),
            "gewichte": dict(GEWICHTE), "kalibriert": False,
            "hinweis": "C ist nicht kalibriert und keine Qualitaetsgarantie. Eskaliert wird nach "
                       "strukturellen Gruenden, nicht nach C (siehe PROGRESSION/005)."}


def eskalationsgruende(*, hard_routing=None, coverage=None, grounding=None,
                       unvollstaendig=False, dienstfehler=False, betrag_fehlt=None) -> list:
    """Alle strukturellen Gruende, die eine Weiterleitung an einen Menschen ausloesen.
    Reihenfolge entspricht der Prueffolge in der Pipeline."""
    g = []
    if hard_routing:
        g.append({"grund": "hard_routing", "detail": hard_routing,
                  "erklaerung": "Rechtsmittel, Bussen oder Haftung. Entschieden vor der Generierung."})
    if dienstfehler:
        g.append({"grund": "dienst", "detail": dienstfehler,
                  "erklaerung": "Sprachdienst nicht erreichbar."})
    if coverage and not coverage.get("ok", True):
        g.append({"grund": "coverage", "detail": coverage.get("luecken"),
                  "erklaerung": "Der Kontext enthaelt die gefragte Art von Information nicht."})
    if grounding == "nicht_gedeckt":
        g.append({"grund": "grounding", "detail": grounding,
                  "erklaerung": "Eine Aussage der Antwort ist durch die Quellen nicht gedeckt. "
                                "Praezision auf den Testdaten 100%, allerdings nur 1 Treffer."})
    if betrag_fehlt and not betrag_fehlt.get("ok", True):
        g.append({"grund": "betrag_unvollstaendig", "detail": betrag_fehlt.get("fehlend"),
                  "erklaerung": "Die Quelle nennt fuer die gefragte Zeiteinheit mehrere Betraege in "
                                "verschiedenen Absaetzen, die Antwort nur einen. Deterministische "
                                "Pruefung; auf 84 protokollierten Antworten 2 Treffer, 0 Fehlalarme."})
    if unvollstaendig:
        g.append({"grund": "unvollstaendig", "detail": True,
                  "erklaerung": "Das Modell hat die Frage nur teilweise beantwortet. Fehlerquote auf "
                                "den Testdaten 19% – deshalb Hinweis mit Kontaktangabe, keine "
                                "Unterdrueckung der Antwort."})
    return g


# Welche Gruende die Antwort ersetzen und welche sie nur begleiten.
UNTERDRUECKT = {"hard_routing", "dienst", "coverage"}
BEGLEITET = {"grounding", "unvollstaendig", "betrag_unvollstaendig"}


def entscheid(gruende: list) -> dict:
    """-> {entscheid, eskalationsgrund, begleithinweise}

    'eskaliert'   – es wird keine inhaltliche Antwort ausgegeben.
    'beantwortet_mit_hinweis' – Antwort wird ausgegeben, aber mit Hinweis und Kontaktangabe.
    'beantwortet' – Antwort ohne Vorbehalt.

    Begruendung fuer die Zweiteilung: Bei 'grounding nicht_gedeckt' und 'unvollstaendig' ist die
    Antwort oft brauchbar und das Verschweigen waere der schlechtere Dienst; die Pruefung im
    Pilotbereich und die Kontaktangabe sind die angemessene Reaktion. Bei Hard-Routing, Coverage-Luecke
    und Dienstfehler fehlt die Grundlage fuer eine Auskunft ganz.
    """
    harte = [g for g in gruende if g["grund"] in UNTERDRUECKT]
    weiche = [g for g in gruende if g["grund"] in BEGLEITET]
    if harte:
        return {"entscheid": "eskaliert", "eskalationsgrund": harte[0]["grund"],
                "alle_gruende": gruende, "begleithinweise": weiche}
    if weiche:
        return {"entscheid": "beantwortet_mit_hinweis", "eskalationsgrund": None,
                "alle_gruende": gruende, "begleithinweise": weiche}
    return {"entscheid": "beantwortet", "eskalationsgrund": None,
            "alle_gruende": [], "begleithinweise": []}
