"""Phase 3a: docs.jsonl -> data/index/chunks.jsonl (kein Embedding)."""
import json, re, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; CLEAN = ROOT / "data" / "clean"; IDX = ROOT / "data" / "index"; IDX.mkdir(parents=True, exist_ok=True)
MAX, MIN, OVERLAP = 1400, 140, 150
EXCLUDE_TITLE = re.compile(r"Handbuch Strassen und Pl|Stadtraumkonzept|Gesamtstrategie|Charta .ffentlicher", re.I)  # Planungs-/Fachdokumente: Phase-3-Entscheid, siehe PROGRESSION/003

def split_long(text, limit=MAX):
    if len(text) <= limit: return [text]
    parts, cur = [], ""
    for ln in text.split("\n"):
        if cur and len(cur) + len(ln) + 1 > limit: parts.append(cur); cur = cur[-OVERLAP:].split("\n", 1)[-1] if OVERLAP else ""
        cur += ("\n" if cur else "") + ln
    if cur.strip(): parts.append(cur)
    return parts

def doc_label(d):
    return d["title"] if d["doc_type"] != "erlass" else d["title"]

def chunks_for(d):
    out = []
    secs = [s for s in d["sections"] if s["text"].strip() and s["heading"] != "Fussnoten"]
    if d["doc_type"] == "erlass":
        for s in secs:
            for i, part in enumerate(split_long(s["text"])):
                out.append((s["path"], part, f'§-Einheit: {s["heading"]}'))
    elif d["doc_id"].startswith("pdf:"):
        buf, p0 = "", None
        for k, s in enumerate(secs):
            pg = int(re.search(r"\d+", s["heading"]).group())
            if buf and len(buf) + len(s["text"]) > MAX: out.append((f"{d['title']} > S. {p0}" + (f"-{last}" if last != p0 else ""), buf, None)); buf = buf[-OVERLAP:]; p0 = pg
            if p0 is None: p0 = pg
            buf = (buf + "\n" if buf else "") + s["text"]; last = pg
            while len(buf) > MAX * 1.6: out.append((f"{d['title']} > S. {p0}", buf[:MAX], None)); buf = buf[MAX - OVERLAP:]
        if buf.strip(): out.append((f"{d['title']} > S. {p0}" + (f"-{last}" if last != p0 else ""), buf, None))
    else:  # Web/News: kurze Abschnitte nur mit ihren EIGENEN Unterabschnitten zusammenfassen.
        # Nicht ueber Themengrenzen hinweg: beginnt ein Abschnitt auf gleicher oder hoeherer Ebene,
        # wird abgeschlossen. Sonst wandert z. B. der Anfang von "Gewerbeparkkarte" in den Chunk
        # "Anwohnende > Zonen" und traegt dessen Pfad - gemessen in Phase 4 (Fall D12).
        buf_path, buf, buf_tiefe = None, "", None
        def flush():
            nonlocal buf, buf_path, buf_tiefe
            if buf.strip():
                for part in split_long(buf): out.append((buf_path, part, None))
            buf, buf_path, buf_tiefe = "", None, None
        for s in secs:
            block = (f"{s['heading']}\n" if s["heading"] != d["title"] else "") + s["text"]
            tiefe = s["path"].count(" > ")
            geschwister = buf_tiefe is not None and tiefe <= buf_tiefe
            if buf and (len(buf) + len(block) > MAX or geschwister): flush()
            if buf_path is None: buf_path, buf_tiefe = s["path"], tiefe
            buf += ("\n\n" if buf else "") + block
        flush()
    return out

def main():
    docs = [json.loads(l) for l in (CLEAN / "docs.jsonl").open(encoding="utf8")]
    rows, excl = [], []
    for d in docs:
        if d["relevance"] == "irrelevant": continue
        if EXCLUDE_TITLE.search(d["title"]): excl.append(d["title"]); continue
        for n, (path, text, extra) in enumerate(c for c in chunks_for(d) if len(re.sub(r"Kontakt|Formulare|\s", "", c[1])) >= 40):
            ctx = f"{doc_label(d)} | {path}" if path and path != d["title"] else doc_label(d)
            rows.append({"chunk_id": f'{d["doc_id"]}#{n}', "doc_id": d["doc_id"], "url": d["url"], "title": d["title"], "doc_type": d["doc_type"], "relevance": d["relevance"],
                         "srs": d.get("srs"), "lang": "de", "modified": d.get("modified"), "retrieved": d["retrieved"], "has_fees": bool(re.search(r"\bCHF\b", text)),
                         "path": path, "text": text, "embed_text": f"{ctx}\n{text}"})
    with (IDX / "chunks.jsonl").open("w", encoding="utf8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    L = [len(r["text"]) for r in rows]
    print(f"{len(rows)} Chunks aus {len({r['doc_id'] for r in rows})} Dokumenten; Länge min/median/max: {min(L)}/{sorted(L)[len(L)//2]}/{max(L)}; <100 Zeichen: {sum(l<100 for l in L)}")
    print("Ausgeschlossen:", sorted(set(excl)))
    import collections; print(collections.Counter(r["doc_type"] for r in rows))
if __name__ == "__main__": main()
