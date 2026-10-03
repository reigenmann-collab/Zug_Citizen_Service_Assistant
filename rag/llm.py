"""Gemini-Anbindung. Retry mit Backoff bei Ueberlast, deutsche Fehlermeldung statt Traceback (CLAUDE.md)."""
import json, os, random, re, time
from pathlib import Path

MODELL = "gemini-3.1-flash-lite"
ROOT = Path(__file__).resolve().parent.parent


class LLMUeberlastet(RuntimeError):
    """Dienst nicht erreichbar oder ueberlastet. Die Pipeline eskaliert dann an einen Menschen."""


def lade_env(pfad=None):
    p = Path(pfad) if pfad else ROOT / ".env"
    if not p.exists():
        return
    for zeile in p.read_text(encoding="utf8").splitlines():
        if "=" in zeile and not zeile.lstrip().startswith("#"):
            k, v = zeile.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_client = None


def client():
    global _client
    if _client is None:
        lade_env()
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LLMUeberlastet("Kein API-Key gefunden. GEMINI_API_KEY in .env oder in den Hosting-Secrets setzen.")
        from google import genai
        _client = genai.Client(api_key=key)
    return _client


FEHLER_DE = ("Der Sprachdienst ist zurzeit nicht erreichbar. Bitte versuchen Sie es in einigen Minuten erneut "
             "oder wenden Sie sich an die Abteilung Sicherheit und Verkehr der Stadt Zug.")
FEHLER_EN = ("The language service is currently unavailable. Please try again in a few minutes or contact the "
             "Department of Safety and Traffic of the City of Zug.")

UEBERLAST = ("503", "overloaded", "unavailable", "429", "resource_exhausted", "rate limit", "500", "internal",
             "deadline", "timeout")


def _wartezeit(fehlertext: str, versuch: int) -> float:
    """Backoff. Bei 429 greift ein Minuten-Kontingent: kurze Wartezeiten helfen dort nicht.
    Falls die API retryDelay nennt, wird dieser Wert benutzt."""
    m = re.search(r"retrydelay['\"]?\s*[:=]\s*['\"]?(\d+)", fehlertext)
    if m:
        return min(float(m.group(1)) + 1, 70)
    if "429" in fehlertext or "resource_exhausted" in fehlertext:
        return min(25 * (versuch + 1) + random.random() * 5, 70)
    return min(2 ** versuch + random.random(), 20)


def frag(prompt, schema=None, temperature=0.0, versuche=4, modell=MODELL):
    """Ein Aufruf mit Backoff. schema gesetzt -> JSON zurueck, sonst Text.
    Wirft LLMUeberlastet, wenn alle Versuche scheitern."""
    from google.genai import types
    cfg = {"temperature": temperature}
    if schema:
        cfg |= {"response_mime_type": "application/json", "response_schema": schema}
    letzter = None
    for i in range(versuche):
        try:
            r = client().models.generate_content(model=modell, contents=prompt,
                                                 config=types.GenerateContentConfig(**cfg))
            txt = (r.text or "").strip()
            if not txt:
                raise RuntimeError("Leere Antwort vom Modell")
            out = json.loads(txt) if schema else txt
            tok = getattr(r, "usage_metadata", None)
            return out, {"prompt_tokens": getattr(tok, "prompt_token_count", None),
                         "output_tokens": getattr(tok, "candidates_token_count", None),
                         "versuche": i + 1, "modell": modell}
        except Exception as e:
            letzter = e
            txt = f"{type(e).__name__} {e}".lower()
            if i == versuche - 1 or not any(s in txt for s in UEBERLAST):
                break
            time.sleep(_wartezeit(txt, i))
    raise LLMUeberlastet(f"{type(letzter).__name__}: {letzter}") from letzter


def nur_json(prompt, schema):
    """Variante fuer den Grounding-Checker: gibt nur das JSON zurueck."""
    out, _ = frag(prompt, schema)
    return out
