"""Phase 2: Relevanz-Tagging + Extraktion -> data/clean/docs.jsonl + ingest_report.md. Kein Chunking."""
import json, re, sys, datetime as dt
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).parent))
from extract_html import extract_html
from extract_law import extract_law
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent; RAW = ROOT / "data" / "raw"; CLEAN = ROOT / "data" / "clean"; CLEAN.mkdir(exist_ok=True)
inv = json.loads((RAW / "inventory.json").read_text(encoding="utf8"))
extra = json.loads((RAW / "inventory_extra.json").read_text(encoding="utf8"))
NOW = dt.date.today().isoformat()

KERN_PATH = ("/de/mobilitaet", "/de/ueber-die-stadt-zug/ortspflege/strassen-wanderwege", "/de/ueber-die-stadt-zug/ortspflege/strassenbau-unterhalt",
             "/de/ueber-die-stadt-zug/ortspflege/strassenbeleuchtung", "/de/bauen/stadtplanung/verkehrsplanung", "/de/sicherheit/schulwegsicherheit",
             "/de/wirtschaftsstandort/bewilligungen/taxi-fahren", "/de/org-verwaltung/departement-sus/sicherheit-und-verkehr")
RAND_PATH = ("/de/ueber-die-stadt-zug/ortspflege/abfallentsorgung", "/de/ueber-die-stadt-zug/ortspflege/littering-hundekot", "/de/ueber-die-stadt-zug/ortspflege/gruenpflege",
             "/de/ueber-die-stadt-zug/nachhaltigkeit/energiefoerderprogramm", "/de/wirtschaftsstandort/bewilligungen/plakatstellen",
             "/de/freizeit/durchfuehren-veranstaltungen-anlaesse", "/de/bauen/stadtplanung/raumplanung", "/de/bauen/staedtebau", "/de/org-verwaltung/departement-sus")
def page_rel(url):
    p = urlparse(url).path
    if p.startswith(KERN_PATH): return "kern"
    if p.startswith(RAND_PATH): return "randthema"
    return "irrelevant"
KERN_DOC = re.compile(r"Handbuch Strassen|Ladestation|Ratgeber|Anschluss finden|Schulwegsicherheitskonzept|Notiqo|Taxipr", re.I)
RAND_DOC = re.compile(r"Entsorgungsmerkblatt|Energief.rderprogramm|Stadtraumkonzept|Charta .ffentlicher|Gesamtstrategie", re.I)
def doc_rel(txt): return "kern" if KERN_DOC.search(txt) else "randthema" if RAND_DOC.search(txt) else "irrelevant"

docs, rep = [], []
def add(d): docs.append(d)
def fee_flag(text): return bool(re.search(r"\bCHF\b|\bFr\.\s*\d", text))

# 1) Webseiten
for p in inv["pages"]:
    ex = extract_html((RAW / "html" / p["file"]).read_text(encoding="utf8"))
    txt = " ".join(s["text"] for s in ex["sections"]); rel = page_rel(p["url"])
    add({"doc_id": "web:" + urlparse(p["url"]).path.strip("/"), "url": p["url"], "title": ex["title"], "doc_type": "gebuehrentarif" if rel != "irrelevant" and fee_flag(txt) and "parkieren" in p["url"] else "webseite",
         "has_fees": fee_flag(txt), "lang": "de", "modified": ex["modified"], "retrieved": inv["crawled"][:10], "srs": None, "relevance": rel, "sections": ex["sections"], "chars": len(txt)})
# 2) Mobilitäts-News
for n in extra["news"]:
    if not n["mobility_hit"] or n["title"].startswith("Baugesuche"): continue
    f = RAW / "html" / ("news_" + re.sub(r"\W+", "_", n["url"].split("/de/news/")[1])[:80] + ".html")
    ex = extract_html(f.read_text(encoding="utf8")); txt = " ".join(s["text"] for s in ex["sections"])
    add({"doc_id": "news:" + n["url"].split("/de/news/")[1], "url": n["url"], "title": ex["title"], "doc_type": "news", "has_fees": fee_flag(txt), "lang": "de", "modified": ex["modified"],
         "retrieved": NOW, "srs": None, "relevance": "randthema", "sections": ex["sections"], "chars": len(txt)})
# 3) Erlasse
for f in sorted((RAW / "law").glob("*.json")):
    lw = extract_law(json.loads(f.read_text(encoding="utf8"))); txt = " ".join(s["text"] for s in lw["sections"])
    add({"doc_id": "law:" + lw["srs"], "url": lw["url"], "title": f'SRS {lw["srs"]} {lw["title"]}', "doc_type": "erlass", "has_fees": fee_flag(txt), "lang": "de", "modified": lw["decision"],
         "retrieved": NOW, "srs": lw["srs"], "version": lw["version"], "in_force": lw["in_force"], "pdf": lw["pdf"], "relevance": "kern", "header": lw["header"], "sections": lw["sections"], "chars": len(txt)})
# 4) PDFs
def pdf_extract(path):
    r = PdfReader(str(path)); pages = []
    for i, pg in enumerate(r.pages):
        try: pages.append(pg.extract_text() or "")
        except Exception: pages.append("")
    return pages
pdfs = [(d["file"], d["link_text"], d["url"], d["found_on"]) for d in inv["docs"] if d.get("status") == 200 and d.get("file", "").endswith(".pdf")]
pdfs += [(a["file"], a["title"], a["url"], f"law:{a['srs']}") for a in extra["annexes"]]
for fn, lt, url, found in pdfs:
    rel = "kern" if fn.startswith(("7.1-1.5", "7.7.1-1")) else doc_rel(lt + " " + found)
    entry = {"file": fn, "title": lt, "relevance": rel}
    if rel == "irrelevant": rep.append({**entry, "status": "übersprungen (irrelevant)"}); continue
    pages = pdf_extract(RAW / "docs" / fn); n = len(pages); chars = [len(p.strip()) for p in pages]
    ocr = [i + 1 for i, c in enumerate(chars) if c < 50]
    status = "ok" if n and len(ocr) <= 0.1 * n else ("OCR nötig" if n else "leer")
    rep.append({**entry, "pages": n, "pages_without_text": len(ocr), "chars": sum(chars), "status": status})
    if status == "OCR nötig" and sum(chars) < 200 * n: continue
    secs = [{"heading": f"Seite {i+1}", "path": f"{lt} > Seite {i+1}", "text": re.sub(r"[ \t]+", " ", p).strip()} for i, p in enumerate(pages) if len(p.strip()) >= 50]
    add({"doc_id": "pdf:" + fn, "url": url, "title": lt, "doc_type": "erlass-anhang" if fn.startswith(("7.1", "7.7")) else "merkblatt", "has_fees": fee_flag(" ".join(s["text"] for s in secs)), "lang": "de",
         "modified": None, "retrieved": NOW, "srs": found.split(":")[1] if found.startswith("law:") else None, "relevance": rel, "found_on": found, "sections": secs, "chars": sum(chars)})

import hashlib
seen_h, dd = {}, []
for d in docs:
    h = d["title"] + d["doc_type"] if d["doc_id"].startswith("pdf:") else hashlib.md5(" ".join(x["text"] for x in d["sections"]).encode()).hexdigest()
    if h in seen_h: seen_h[h].setdefault("duplicate_urls", []).append(d["url"]); continue
    seen_h[h] = d; dd.append(d)
print("Duplikate entfernt:", len(docs) - len(dd)); docs = dd
with (CLEAN / "docs.jsonl").open("w", encoding="utf8") as fh:
    for d in docs: fh.write(json.dumps(d, ensure_ascii=False) + "\n")
keep = [d for d in docs if d["relevance"] in ("kern", "randthema")]
L = [f"# Ingest-Report ({NOW})", "", f"Dokumente gesamt: {len(docs)}, davon kern/randthema (für Index): {len(keep)}", "", "## Nach Relevanz/Typ"]
import collections
for k, v in sorted(collections.Counter((d["relevance"], d["doc_type"]) for d in docs).items()): L.append(f"- {k[0]} / {k[1]}: {v}")
L += ["", "## Kern + Randthema", "| doc_id | Typ | Relevanz | Abschnitte | Zeichen | Gebühren |", "|---|---|---|---|---|---|"]
for d in keep: L.append(f"| {d['doc_id']} | {d['doc_type']} | {d['relevance']} | {len(d['sections'])} | {d['chars']} | {'ja' if d['has_fees'] else ''} |")
L += ["", "## PDF-Prüfung (Textlayer)", "| Datei | Titel | Relevanz | Seiten | ohne Text | Status |", "|---|---|---|---|---|---|"]
for r in rep: L.append(f"| {r['file'][:40]} | {r['title'][:45]} | {r['relevance']} | {r.get('pages','')} | {r.get('pages_without_text','')} | {r['status']} |")
(CLEAN / "ingest_report.md").write_text("\n".join(L), encoding="utf8")
print("\n".join(L))
