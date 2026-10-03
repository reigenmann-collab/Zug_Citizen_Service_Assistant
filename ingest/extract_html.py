import re
from bs4 import BeautifulSoup, NavigableString
BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "tr", "dt", "dd", "summary", "figcaption"}
def extract_html(html):
    """-> dict(title, modified, sections[{heading,text}]). Entfernt Site-Chrome; Tabellen zeilenweise 'a | b'."""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
    m = re.search(r'(?:article:modified_time|dateModified|last-?modified)["\']?[^>]*?content="([^"]+)"', html)
    main = soup.find("main") or soup
    for t in main(["script", "style", "nav", "header", "footer", "noscript", "svg", "form", "button", "iframe"]): t.decompose()
    for t in main.find_all(attrs={"aria-hidden": "true"}): t.decompose()
    sections, cur, stack = [], {"heading": title, "path": title, "lines": []}, {}
    seen_line = set()
    for el in main.find_all(list(BLOCK)):
        if el.name in ("li", "p", "dd", "dt") and el.find(list(BLOCK - {"li", "p"})) is not None: pass
        if el.name == "tr":
            cells = [c.get_text(" ", strip=True) for c in el.find_all(["th", "td"])]
            txt = " | ".join(c for c in cells if c)
        else:
            if el.name in ("p", "li") and el.find_parent(["tr"]): continue
            if el.name == "li" and el.find(["li"]): continue
            txt = el.get_text(" ", strip=True)
            if el.name == "li": txt = "- " + txt
        txt = re.sub(r"\s+", " ", txt).strip()
        if not txt: continue
        if el.name in ("h1", "h2", "h3", "h4", "h5", "summary"):
            if cur["lines"]: sections.append(cur)
            lvl = 2 if el.name == "summary" else int(el.name[1])
            stack = {k: v for k, v in stack.items() if k < lvl}; stack[lvl] = txt
            cur = {"heading": txt, "path": " > ".join([title] + [stack[k] for k in sorted(stack) if k > 1]), "lines": []}; continue
        if txt in seen_line and len(txt) < 60: continue
        seen_line.add(txt); cur["lines"].append(txt)
    if cur["lines"]: sections.append(cur)
    return {"title": title, "modified": m.group(1) if m else None,
            "sections": [{"heading": s["heading"], "path": s["path"], "text": "\n".join(s["lines"])} for s in sections]}
