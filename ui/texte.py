"""Oberflaechentexte DE/EN. Uebernommen aus dem freigegebenen Entwurf zg_rag_prototype.html,
dort wo die Umsetzung davon abweicht ist es im Kommentar vermerkt."""

# Beispielfragen je Oberflaechensprache. Die englischen sind bewusst englisch gestellt: die
# Antwortsprache richtet sich nach der Frage, nicht nach dieser Einstellung.
VORSCHLAEGE = {
    "de": [
        "Was kostet die Anwohnerparkkarte pro Monat?",
        "Wie bekomme ich eine Zufahrtsbewilligung?",
        "Was kostet eine Stunde parkieren in Zug?",
        "Wann räumt die Stadt Zug im Winter die Strassen?",
        "Kann ich gegen eine Parkbusse Einsprache erheben?",
    ],
    "en": [
        "How much is a resident parking permit per month?",
        "How do I get an access permit?",
        "What does one hour of parking cost in Zug?",
        "When does the city clear snow from the roads?",
        "Can I appeal against a parking fine?",
    ],
}

T = {
    "de": {
        "titel": "Mobilitäts-Assistent Stadt Zug",
        "proto": "PILOT · Antworten aus stadtzug.ch/mobilitaet und zug.tlex.ch · "
                 "Design angelehnt an zg.ch · Platzhalter-Wortmarke, nicht das offizielle Logo",
        "crumb": ["Stadt Zug", "Mobilität", "Assistent"],
        "h1": "Mobilität in der Stadt Zug",
        "lead": "Stellen Sie Ihre Frage zu Parkieren, Baustellen, Winterdienst, Zufahrtsbewilligungen "
                "oder Elektromobilität in eigenen Worten. Sie erhalten eine Antwort mit "
                "Quellenangaben aus den offiziellen Dokumenten.",
        "staff_toggle": "Pilot-Ansicht (Verwaltung) einblenden",
        "staff_tag": "Pilot-Ansicht",
        "hello": "Grüezi! Ich beantworte Fragen rund um Mobilität in der Stadt Zug – zum Beispiel zu "
                 "Parkkarten, Gebühren, Baustellen oder dem Winterdienst. Womit kann ich helfen?",
        "ph": "Was möchten Sie wissen?",
        "send": "Fragen",
        "note": "Dieser Assistent liefert Informationen, keine rechtsverbindlichen Entscheide. "
                "Antworten können Fehler enthalten – massgebend sind die verlinkten Originaldokumente.",
        "quellen": "Quellen",
        "vorschlaege": "Beispielfragen",
        "schritte": {"retrieval": "Suche in Dokumenten …",
                     "generierung": "Antwort wird formuliert …",
                     "grounding": "Antwort wird gegen die Quellen geprüft …"},
        "conf_h": "Konfidenz",
        "conf_warn": "Nicht kalibriert. Dieser Wert eignet sich nicht als Qualitätsmass "
                     "(siehe PROGRESSION/005).",
        "s1": "Retrieval", "s2": "Quellentreue", "s3": "Selbstbewertung", "gesamt": "Gesamt",
        "pipe_h": "Pipeline",
        "corp_h": "Wissensbasis",
        "gruende_h": "Prüfungen",
        "keine_anfrage": "Noch keine Anfrage.",
        "badge_ok": "Direkt beantwortet",
        "badge_hinweis": "Beantwortet, mit Vorbehalt",
        "badge_esk": "An Sachbearbeitung weitergeleitet",
        "p_sprache": "Sprache erkannt", "p_treffer": "Kontextblöcke", "p_netz": "BM25-Nachzug",
        "p_coverage": "Coverage", "p_routing": "Routing", "p_zeit": "Antwortzeit",
        "p_grounding": "Grounding", "p_modell": "Modell", "p_tokens": "Tokens (Prompt/Antwort)",
        "retr_warn": "Retrieval-Warnung: schwacher Spitzentreffer, Quelle könnte fehlen",
        "fb_h": "Beurteilung",
        "fb_lead": "War diese Antwort richtig? Die Beurteilung ist die Grundlage für die Kalibrierung "
                   "der Konfidenz – ohne sie fehlen dem Pilotbetrieb die Fehlerbeispiele.",
        "fb_richtig": "Richtig", "fb_teilweise": "Teilweise", "fb_falsch": "Falsch",
        "fb_unklar": "Unklar",
        "fb_bemerkung": "Bemerkung (optional)",
        "fb_speichern": "Beurteilung speichern",
        "fb_gespeichert": "Beurteilung gespeichert.",
        "fb_person": "Kürzel der beurteilenden Person",
        "footer": "© Stadt Zug · Pilot. Dieser Assistent ist keine amtliche Auskunft.",
        "fehler": "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
        "kein_key": "Kein API-Schlüssel konfiguriert. Hinterlegen Sie GEMINI_API_KEY in den "
                    "Streamlit-Secrets oder in einer lokalen .env-Datei.",
    },
    "en": {
        "titel": "Mobility assistant City of Zug",
        "proto": "PILOT · Answers from stadtzug.ch/mobilitaet and zug.tlex.ch · "
                 "Design inspired by zg.ch · Placeholder wordmark, not the official logo",
        "crumb": ["City of Zug", "Mobility", "Assistant"],
        "h1": "Mobility in the City of Zug",
        "lead": "Ask about parking, roadworks, winter service, access permits or electric mobility in "
                "your own words. You receive an answer with references to the official documents. "
                "The sources are German; an answer follows the language of your question.",
        "staff_toggle": "Show pilot view (administration)",
        "staff_tag": "Pilot view",
        "hello": "Hello! I answer questions about mobility in the City of Zug – parking cards, fees, "
                 "roadworks or winter service, for example. How can I help?",
        "ph": "What would you like to know?",
        "send": "Ask",
        "note": "This assistant provides information, not legally binding decisions. Answers may "
                "contain errors – the linked original documents are authoritative.",
        "quellen": "Sources",
        "vorschlaege": "Example questions",
        "schritte": {"retrieval": "Searching the documents …",
                     "generierung": "Drafting the answer …",
                     "grounding": "Checking the answer against the sources …"},
        "conf_h": "Confidence",
        "conf_warn": "Not calibrated. This value is not a measure of quality (see PROGRESSION/005).",
        "s1": "Retrieval", "s2": "Source fidelity", "s3": "Self-assessment", "gesamt": "Overall",
        "pipe_h": "Pipeline",
        "corp_h": "Knowledge base",
        "gruende_h": "Checks",
        "keine_anfrage": "No query yet.",
        "badge_ok": "Answered directly",
        "badge_hinweis": "Answered, with a caveat",
        "badge_esk": "Referred to staff",
        "p_sprache": "Language detected", "p_treffer": "Context blocks", "p_netz": "BM25 top-up",
        "p_coverage": "Coverage", "p_routing": "Routing", "p_zeit": "Response time",
        "p_grounding": "Grounding", "p_modell": "Model", "p_tokens": "Tokens (prompt/answer)",
        "retr_warn": "Retrieval warning: weak top hit, a source may be missing",
        "fb_h": "Assessment",
        "fb_lead": "Was this answer correct? The assessment is the basis for calibrating the "
                   "confidence – without it the pilot produces no error examples.",
        "fb_richtig": "Correct", "fb_teilweise": "Partly", "fb_falsch": "Wrong",
        "fb_unklar": "Unclear",
        "fb_bemerkung": "Remark (optional)",
        "fb_speichern": "Save assessment",
        "fb_gespeichert": "Assessment saved.",
        "fb_person": "Initials of the assessor",
        "footer": "© City of Zug · Pilot. This assistant is not an official statement.",
        "fehler": "An error occurred. Please try again.",
        "kein_key": "No API key configured. Set GEMINI_API_KEY in the Streamlit secrets or in a "
                    "local .env file.",
    },
}

GRUND_TEXT = {
    "de": {
        "hard_routing": "Hard-Routing (Rechtsmittel, Busse, Haftung)",
        "coverage": "Coverage-Lücke: gefragte Angabe nicht im Kontext",
        "grounding": "Grounding: Aussage nicht durch Quellen gedeckt",
        "unvollstaendig": "Antwort unvollständig",
        "betrag_unvollstaendig": "Weitere Beträge in der Rechtsgrundlage",
        "dienst": "Sprachdienst nicht erreichbar",
    },
    "en": {
        "hard_routing": "Hard routing (legal remedies, fines, liability)",
        "coverage": "Coverage gap: requested detail not in context",
        "grounding": "Grounding: statement not supported by sources",
        "unvollstaendig": "Answer incomplete",
        "betrag_unvollstaendig": "Further amounts in the legal basis",
        "dienst": "Language service unavailable",
    },
}
