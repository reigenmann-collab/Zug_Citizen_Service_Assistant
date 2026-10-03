"""Phase 1 crawl: Stadt Zug Mobilität (stadtzug.ch) + Rechtstexte (zug.tlex.ch). Raw only, no chunking."""
import json, re, time, hashlib, sys, datetime as dt
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = "RAG-Zug-PoC-Crawler (research PoC; reigenmann@gmail.com)"
DELAY = 1.0
MAX_DEPTH = 4
MAX_PAGES = 250
SEEDS = [
    "https://stadtzug.ch/de/mobilitaet",
    "https://stadtzug.ch/de/ueber-die-stadt-zug/ortspflege/strassen-wanderwege",
]
SKIP_PATH = ("/de/news",)  # time-bound news: recorded as candidates, not followed
DOC_EXT = (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".zip")
LAWS = ["7.7.5-1", "7.7.5-2"]

s = requests.Session(); s.headers["User-Agent"] = UA
def get(url, **kw):
    time.sleep(DELAY)
    for i in range(3):
        try:
            r = s.get(url, timeout=40, **kw)
            if r.status_code in (429, 503): time.sleep(5 * (i + 1)); continue
            return r
        except requests.RequestException as e:
            err = e; time.sleep(3)
    raise err

def slug(u):
    p = urlparse(u); base = re.sub(r"[^A-Za-z0-9]+", "_", (p.path or "root").strip("/"))[:80]
    return f"{base}_{hashlib.md5(u.encode()).hexdigest()[:6]}"

def norm(u):
    u, _ = urldefrag(u); p = urlparse(u)
    return u.rstrip("/") if not p.query else u

def main():
    inv = {"crawled": dt.datetime.now().isoformat(timespec="seconds"), "pages": [], "docs": [], "external": {}, "skipped_news": {}, "errors": []}
    seen, queue = set(), [(norm(u), 0, None) for u in SEEDS]
    docs = {}
    while queue and len(inv["pages"]) < MAX_PAGES:
        url, d, parent = queue.pop(0)
        if url in seen: continue
        seen.add(url)
        try: r = get(url)
        except Exception as e: inv["errors"].append((url, str(e))); continue
        if r.status_code != 200: inv["errors"].append((url, r.status_code)); continue
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        main_el = soup.find("main") or soup
        links = [(urljoin(url, a["href"]), a.get_text(" ", strip=True)) for a in main_el.find_all("a", href=True)]
        for t in main_el(["script", "style", "nav", "header", "footer", "noscript", "svg"]): t.decompose()
        title = (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else (soup.title.get_text(strip=True) if soup.title else ""))
        mod = re.search(r'(?:article:modified_time|last-?modified)[^>]*content="([^"]+)"', html)
        f = RAW / "html" / (slug(url) + ".html")
        f.write_text(html, encoding="utf8")
        text = main_el.get_text("\n", strip=True)
        inv["pages"].append({"url": url, "depth": d, "parent": parent, "title": title, "file": f.name, "chars_main_text": len(text), "modified": mod.group(1) if mod else None})
        for h, lt in links:
            hn = norm(h); p = urlparse(hn)
            if p.scheme not in ("http", "https"): continue
            is_doc = p.path.lower().endswith(DOC_EXT) or "/dam/" in p.path
            host = p.netloc.replace("www.", "")
            if is_doc:
                docs.setdefault(hn, {"url": hn, "link_text": lt, "found_on": url}); continue
            if host == "stadtzug.ch":
                if p.path.startswith(SKIP_PATH): inv["skipped_news"][hn] = lt; continue
                if not p.path.startswith("/de") or p.path == "/de": continue
                if "?" in hn: continue
                if d + 1 <= MAX_DEPTH and hn not in seen: queue.append((hn, d + 1, url))
            else:
                inv["external"].setdefault(hn, {"link_text": lt, "found_on": url})
        print(f"[{d}] {url} ({len(text)} chars)", flush=True)
    # documents
    for u, meta in docs.items():
        try:
            r = get(u, stream=True)
            ct = r.headers.get("content-type", ""); cd = r.headers.get("content-disposition", "")
            ext = ".pdf" if "pdf" in ct else (Path(urlparse(u).path).suffix or ".bin")
            fn = slug(u) + ext
            if r.status_code == 200 and "text/html" not in ct:
                (RAW / "docs" / fn).write_bytes(r.content)
            meta.update(status=r.status_code, content_type=ct, disposition=cd, file=fn, bytes=len(r.content), last_modified=r.headers.get("last-modified"))
        except Exception as e: meta.update(status="error", error=str(e))
        inv["docs"].append(meta)
    # laws via JSON API
    inv["laws"] = []
    for srs in LAWS:
        u = f"https://zug.tlex.ch/api/de/texts_of_law/{srs}/show_as_json"
        r = get(u); (RAW / "law" / f"{srs}.json").write_bytes(r.content)
        j = r.json()["text_of_law"]
        inv["laws"].append({"srs": srs, "title": j["title"], "status": r.status_code, "version": j["current_version"]["id"], "in_force": j["current_version"]["version_dates_str"], "abrogated": j["abrogated"], "pdf": j.get("pdf_link"), "url": j["canonical_link"]})
    (ROOT / "data" / "raw" / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf8")
    print("pages", len(inv["pages"]), "docs", len(inv["docs"]), "external", len(inv["external"]), "errors", len(inv["errors"]))

if __name__ == "__main__": main()
