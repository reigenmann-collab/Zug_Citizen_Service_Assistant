# 001 – Phase 1 Crawl: Befunde (2026-10-03)

## Abweichungen vom Brief
- Brief: "Kanton Zug / zg.ch / Parkieren" → Umsetzung: Stadt Zug, stadtzug.ch + zug.tlex.ch, alle Mobilitätsthemen (Entscheid René).
- SRS 7.7.5-2 ist die **Verordnung über die Parkraumbewirtschaftung** (v984, in Kraft seit 01.05.2025). Wichtigste Quelle für Gebühren/Anwohnerkarten, ergänzt 7.7.5-1 (Reglement nächtliches Dauerparkieren, v985). Annahme in ZG_scope: Gebühren stünden nur auf der Webseite – gegen 7.7.5-2 prüfen.

## Technisch
- robots.txt stadtzug.ch: nur /.magnolia gesperrt; Sitemaps vorhanden. zug.tlex.ch: nur Such-Endpunkte gesperrt, `/api/de/texts_of_law/<SRS>/show_as_json` erlaubt. Nutzungsbedingungen tlex noch nicht geprüft.
- Sitemap de/default.xml: nur 7 Seiten unter /de/mobilitaet (keine Unterseiten). Links werden aus dem `<main>`-Inhalt gelesen (Kacheln liegen in `<nav>` innerhalb main → Links vor dem Entfernen sammeln).
- Link-Following ab Mobilität driftet nach Tiefe 2 auf die ganze Website ab (Nachhaltigkeit, Stellen, Stadtmagazin …). Rohdaten sind komplett gespeichert, die Relevanz wird im Inventar markiert, nicht beim Crawl gefiltert.
- Rohdaten: data/raw/html, data/raw/docs, data/raw/law, data/raw/inventory.json. Crawler: crawler/crawl.py (UA identifiziert, 1 s Delay).
