import re, html as H
from bs4 import BeautifulSoup
def _t(h): return re.sub(r"[ \t\xa0]+", " ", BeautifulSoup(H.unescape(h or ""), "html.parser").get_text(" ", strip=True)).strip()
def walk(node, trail, out):
    t = node.get("type"); txt = node.get("text", {}).get("de", "")
    if t == "article":
        num = _t(node["number"].get("de", "")).replace("�", "§"); title = _t(txt)
        body = []
        def rec(n):
            body.append(_t(n.get("html_content", {}).get("de", "")))
            for c in n.get("children", []): rec(c)
            body.append(_t((n.get("html_content_post") or {}).get("de", "")))
        for ch in node.get("children", []): rec(ch)
        out.append({"heading": f"{num} {title}".strip(), "path": " > ".join(trail + [f"{num} {title}".strip()]), "text": "\n".join(b for b in body if b), "unit": "artikel"})
        return
    nt = [*trail, _t(node.get("html_content", {}).get("de", "")) or _t(txt)] if t in ("title", "section", "chapter") and (_t(txt) or _t(node.get("html_content", {}).get("de", ""))) else trail
    for ch in node.get("children", []): walk(ch, nt, out)
def extract_law(j):
    tl = j["text_of_law"]; v = tl["selected_version"]; doc = v["json_content"]["document"]
    out = []; walk(doc["content"], [], out)
    fn_html = (v["json_content"].get("footnotes") or {}).get("de", "")
    fns = {m.group(1): m.group(2).strip() for m in re.finditer(r"\[(\d+)\]\s*(.+?)(?=\s*\[\d+\]|$)", _t(fn_html))}
    def resolve(t): return re.sub(r"\[(\d+)\]", lambda m: f" (Fussnote: {fns[m.group(1)]})" if m.group(1) in fns else m.group(0), t)
    for sec in out: sec["text"] = resolve(sec["text"])
    doc["header"]["de"] = resolve(_t(doc["header"].get("de", "")))
    if fns: out.append({"heading": "Fussnoten", "path": "Fussnoten", "text": chr(10).join(f"[{k}] {t}" for k, t in fns.items()), "unit": "fussnoten"})
    return {"title": tl["title"], "srs": tl["systematic_number"], "version": v["id"], "in_force": tl["current_version"]["version_dates_str"],
            "decision": tl["date_of_decision"], "header": doc["header"]["de"], "sections": out, "pdf": tl["pdf_link"], "url": tl["canonical_link"]}
