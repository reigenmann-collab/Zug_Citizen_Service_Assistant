# 002 – Phase 2 Ingestion: Befunde (2026-10-03)

## Ergebnis
- `data/clean/docs.jsonl` (130 Dokumente, davon 47 kern/randthema = Index-Kandidaten), `data/clean/ingest_report.md`. Code: `crawler/crawl_extra.py`, `ingest/`.
- Zusatzcrawl: Erlasse 7.7.5-3 (Zufahrtsbewilligungen), 7.1-1.5 (Parkplatzreglement), 7.7.1-1 (+ .1 Gebührenordnung, öffentliche Anlagen), 9.5-4 (Taxireglement) + 2 Anhang-PDFs; News aus Sitemap (24 gefunden, nur 1 mobilitätsrelevant: DAB+ im Parkhaus; Baugesuche bewusst ausgeschlossen).
- Chunking-relevante Struktur: Web = Abschnitte mit Überschriften-Pfad (`Nachtparkieren > Gebühren`), Erlasse = ein Abschnitt je §, PDF = Seiten.

## Befunde, die dem Brief / ZG_scope widersprechen oder ihn ergänzen
1. **Gebühren stehen auch im Erlass.** SRS 7.7.5-2 §12 (Anwohnerkarte) und §18 (Parkhäuser: Dauer-/Tagesplatz, Stundentarife bis CHF 29/24h) nennen konkrete Beträge. Nur SRS 7.7.5-1 nennt keinen Betrag (Stadtrat legt fest; CHF 30/Mt. steht auf der Webseite).
2. **Webseite verkürzt §12:** Webseite "Anwohnerkarte CHF 30/Mt."; §12 Abs. 1: CHF 30/Mt. nur bei bereits bezahlter Nachtparkgebühr, Abs. 2: CHF 60/Mt. inkl. Nachtparkgebühr (Wochen-/2-Wochenkarten ebenfalls). Antwortlogik muss beide Quellen zeigen (Coverage-Test).
3. **Webseite Parkieren enthält mehr als ZG_scope:** Parkhaus-Mieten (Dauer CHF 210, Tagesplatz CHF 170), Kurztarife bis 8 Std., Parkleitsystem.
4. **Fussnoten** in Erlassen werden jetzt inline aufgelöst ("Stadtpolizei (Fussnote: heute: Abteilung Sicherheit und Verkehr)").
5. Handbuch Strassen und Plätze (121 S., 120k Zeichen, 3× unter verschiedenen URLs): Fachhandbuch für Planer, für Bürgerfragen kaum relevant; als `kern` markiert, in Phase 3 evtl. herabstufen. Stadtraumkonzept 2050 liegt unter zwei Titeln vor (nicht dedupliziert).

## Offene Punkte für Phase 3
- PDF-Textlayer: Ratgeber Ladesysteme (21/64 S.), Stadtraumkonzept (11/97 S.), Schulwegkonzept (3/24 S.) haben Seiten ohne Text (Grafiken/Cover); kein reiner Scan, OCR vorerst nicht nötig. Anhang "Zonen" zu 7.1-1.5 (1 Seite, 174 Zeichen) ist eine Karte: Inhalt nicht extrahiert.
- tlex-Nutzungsbedingungen nicht geprüft (robots.txt erlaubt die API).
- `modified` für Webseiten fehlt (Seiten liefern kein Änderungsdatum); Abrufdatum ist gesetzt.
