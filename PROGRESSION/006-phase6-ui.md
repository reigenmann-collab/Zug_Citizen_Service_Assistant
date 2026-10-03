# 006 – Phase 6 Oberfläche (2026-10-03)

Streamlit-App nach dem freigegebenen Entwurf `zg_rag_prototype.html`. Code: `app.py`, `ui/stil.py`,
`ui/texte.py`. Lokal geprüft im Browser, nicht nur gebaut.

## Umsetzung des Entwurfs
Übernommen: Farbtokens aus zg.ch (primary-650 #435075, primary-800 #252342, secondary-500 #0070b8,
support-100 #f5f9ff, Akzent #e07031, H1 34px/700 #150023), Inter, Platzhalter-Wortmarke statt des
offiziellen Logos, Breadcrumb, orange Pilot-Leiste, Chat links mit Sprechblasen, ausblendbare
Pilot-Ansicht rechts mit den drei Karten Konfidenz, Pipeline, Wissensbasis.

## Abweichungen vom Entwurf, mit Begründung

| Entwurf | Umsetzung | Grund |
|---|---|---|
| Karte «Konfidenz» mit Zeile **Schwelle** | Schwelle entfernt, stattdessen Karte **Prüfungen** | Es gibt keine Schwelle. C trennt nicht nachweisbar (PROGRESSION/005). An der Stelle stehen jetzt die strukturellen Gründe, die tatsächlich eskalieren. |
| Konfidenz ohne Vorbehalt | Konfidenz mit Warnhinweis «Nicht kalibriert» | Sonst liest die Verwaltung die Zahl als Qualitätsmass. |
| Wissensbasis fest verdrahtet («Chroma (lokal)», «Reglemente SRS 7.7.5») | aus dem Index berechnet: 7 Erlasse, 24 Webseiten, 10 PDFs, 419 Chunks, FAISS | Der Entwurf nannte Platzhalter; die echten Zahlen sind aussagekräftiger und veralten nicht. |
| Nur Parkieren | alle Mobilitätsthemen | Entscheid René (ZG_scope_and_corpus). |
| – | Fortschrittsanzeige in drei Schritten | Die Antwortzeit schwankt zwischen 3 und 35 Sekunden. Ohne Rückmeldung wirkt die App hängengeblieben. Dafür hat `antworte()` jetzt einen optionalen `fortschritt`-Haken. |
| – | Beispielfragen je Sprache | Englische Oberfläche mit deutschen Beispielfragen war inkonsequent. |

## Sprachsteuerung
Der DE/EN-Umschalter steuert **nur die Oberfläche**. Die Antwortsprache richtet sich nach der Sprache
der Frage (CLAUDE.md), unabhängig von dieser Einstellung. In der englischen Fassung steht das im
Einleitungstext. Englische Antworten tragen den festen Hinweis, dass sie nicht rechtsverbindlich sind;
er wird deterministisch angehängt, nicht vom Modell erzeugt.

## Beim Ausprobieren gefundene Fehler

Alle vier wären bei einer reinen Code-Durchsicht nicht aufgefallen:

1. **Leerer Chat-Rahmen.** `st.markdown('<div class="zg-chat">')` und die Nachrichten in getrennten
   Aufrufen: Streamlit kapselt jeden Aufruf in einen eigenen Container und schliesst offene Tags. Der
   Rahmen blieb leer, die Nachrichten standen darunter. Der ganze Verlauf wird jetzt in **einem**
   HTML-Block erzeugt (`chat_html`).
2. **«Kein API-Schlüssel konfiguriert»** trotz vorhandener `.env`. Die Prüfung lief, bevor
   `rag.llm.lade_env()` aufgerufen wurde. Jetzt wird `.env` beim Start geladen, vor jeder Prüfung.
3. **Doppelte SRS-Nummer** in der Quellenangabe («SRS 7.7.5-2 · SRS 7.7.5-2 Verordnung …»), weil der
   Titel die Nummer bereits enthält.
4. **Sprachumschalter ohne Wirkung.** `st.radio` in einer schmalen Spalte stapelte senkrecht und reagierte
   nicht zuverlässig. Ersetzt durch `st.segmented_control`, was auch dem Pillen-Paar des Entwurfs
   entspricht.

Die Lehre aus Schwyz zu den Leerzeilen im `<style>`-Block ist in `ui/stil.py` umgesetzt: `css()` entfernt
alle Leerzeilen, bevor der Block ausgegeben wird. Ein Kommentar erklärt, warum man das nicht
«aufräumen» darf.

## Geprüfte Fälle im Browser
- **Normale Frage** «Was kostet die Anwohnerparkkarte pro Monat?»: Antwort mit CHF 30 und CHF 60 samt
  § 12 Abs. 1 und 2, Badge «Direkt beantwortet», Konfidenz 0.94, zwei verlinkte Quellen (Webseite und
  Erlass), Pilot-Ansicht mit allen Komponenten, Pipeline-Details und 12 Kontextblöcken.
- **Hard-Routing** «Kann ich gegen eine Parkbusse Einsprache erheben?»: Eskalationskasten mit
  Akzentbalken, Badge «An Sachbearbeitung weitergeleitet», Antwortzeit 0.0 s, kein Modellaufruf,
  Prüfungen zeigen «Hard-Routing (Rechtsmittel, Busse, Haftung)».
- **Sprachumschaltung** auf Englisch: Oberfläche, Beispielfragen und Pilot-Ansicht vollständig englisch.
- **Schmale Ansicht** (759 px): Spalten stapeln, Pillen-Paar und Karten bleiben lesbar.

## Deployment
`README.md` enthält die Anleitung. Ins Repository gehören rund 2 MB (`app.py`, `rag/`, `ui/`,
`data/index/`, `requirements.txt`, `.streamlit/config.toml`); `data/raw/` mit 209 MB bleibt draussen.

Zwei Punkte, die im Pilotbetrieb beissen werden:
- **`AUDIT_SALT` muss in den Secrets stehen.** Sonst erzeugt jeder Neustart ein neues Salz und die
  Pseudonyme sind nicht mehr vergleichbar.
- **Das Audit-Log überlebt einen Neustart nicht.** `data/audit/` liegt im flüchtigen Container. Ohne
  externe Ablage entstehen keine Kalibrierungsdaten – und genau die fehlen nach Phase 5.

## Offen
- Die Antwort erscheint erst, wenn auch die Grounding-Prüfung fertig ist. Besser wäre, die Antwort
  sofort zu zeigen und die Prüfung nachzuliefern; dafür müsste `antworte()` in zwei Schritte zerfallen.
- Kein Feedback-Knopf in der Pilot-Ansicht. `rag.auditlog.urteil_eintragen()` ist vorbereitet, aber noch
  nicht mit der Oberfläche verbunden. Das wäre der direkteste Weg zu echten Kalibrierungsdaten.
- Barrierefreiheit nicht geprüft (Kontraste, Tastaturbedienung, Screenreader). Für eine
  Verwaltungsanwendung vor dem produktiven Einsatz nötig.

## Nachtrag: Frage erscheint sofort
Beim Klick auf eine Beispielfrage (oder beim Absenden) erschien die Frage erst, wenn die Antwort fertig
war – je nach Sprachdienst 3 bis 35 Sekunden lang nur ein kleiner Statuskasten am Seitenende. Ursache:
Die Frage wurde erst nach `antworte()` in den Verlauf geschrieben. Jetzt wird sie beim Klick als Eintrag
mit offener Antwort eingereiht; der Chat zeigt sie mit Ladeanzeige, die Pipeline füllt den Eintrag am
Seitenende. Im Browser geprüft: Frage und «…» stehen sofort im Verlauf. Die Antwortzeit selbst bleibt
unverändert und hängt am Sprachdienst.
