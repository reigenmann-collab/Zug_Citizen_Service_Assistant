"""Phase 2 Zusatzcrawl: Anhänge der Erlasse (tlex annex PDFs) + Mobilitäts-News aus der Sitemap."""
import re, json, time, html as H
from pathlib import Path
import requests
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parent.parent; RAW = ROOT / "data" / "raw"
UA = "RAG-Zug-PoC-Crawler (research PoC; reigenmann@gmail.com)"
s = requests.Session(); s.headers["User-Agent"] = UA
def get(u):
    time.sleep(1.0); return s.get(u, timeout=60)
KW = re.compile(r"parkier|parkplatz|parkhaus|parkkarte|baustelle|strasse|strassen|sperr|verkehr|fahrverbot|winterdienst|schnee|velo|e-?mobil|ladestation|bus|zvb|tempo|zufahrt|fahrbahn|mobilit", re.I)
out = {"annexes": [], "news": []}
# Anhänge
for f in sorted((RAW / "law").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf8"))["text_of_law"]["selected_version"]["json_content"]["document"]["annex_documents"]
    for ch in d.get("children", []):
        for url in re.findall(r'href="([^"]+annex_document[^"]+)"', ch["html_content"]["de"]):
            r = get(url); fn = f"{f.stem}_{url.rstrip('/').split('/')[-1]}.pdf"
            (RAW / "docs").joinpath(fn).write_bytes(r.content)
            out["annexes"].append({"srs": f.stem, "title": ch["text"]["de"], "url": url, "file": fn, "status": r.status_code, "content_type": r.headers.get("content-type"), "bytes": len(r.content)})
# News
sm = get("https://stadtzug.ch/de/sitemap/default.xml").text
news = [u for u in re.findall(r"<loc>([^<]+)</loc>", sm) if "/de/news/" in u]
lst = get("https://stadtzug.ch/de/news?content_category=news").text
news += re.findall(r'href="(https://stadtzug.ch/de/news/[^"#]+)"', lst)
for u in sorted(set(news)):
    r = get(u)
    if r.status_code != 200: continue
    soup = BeautifulSoup(r.text, "html.parser"); h1 = soup.find("h1"); title = h1.get_text(" ", strip=True) if h1 else ""
    main = soup.find("main") or soup
    for t in main(["script", "style", "nav", "header", "footer"]): t.decompose()
    txt = main.get_text(" ", strip=True)
    hit = bool(KW.search(title)) or len(KW.findall(txt)) >= 3
    out["news"].append({"url": u, "title": title, "mobility_hit": hit})
    if hit: (RAW / "html" / ("news_" + re.sub(r"\W+", "_", u.split("/de/news/")[1])[:80] + ".html")).write_text(r.text, encoding="utf8")
(RAW / "inventory_extra.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
print(len(out["annexes"]), "annexes;", len(out["news"]), "news,", sum(n["mobility_hit"] for n in out["news"]), "hits")
for a in out["annexes"]: print(a["srs"], a["title"], a["status"], a["content_type"], a["bytes"])
for n in out["news"]:
    if n["mobility_hit"]: print("NEWS", n["title"])
