"""Diagnose: welcher Fehler kommt wirklich von Gemini? Aufruf: python diagnose_llm.py
Probiert das konfigurierte Modell und Ausweichkandidaten, gibt HTTP-Status/Fehlertext aus (nie den Key)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag.llm import lade_env, MODELL
lade_env()
from google import genai
key = os.environ.get("GEMINI_API_KEY")
print("Key vorhanden:", bool(key), "| konfiguriertes Modell:", MODELL)
c = genai.Client(api_key=key)
for m in dict.fromkeys([MODELL, "gemini-3.5-flash-lite", "gemini-2.5-flash-lite"]):
    try:
        r = c.models.generate_content(model=m, contents="Antworte nur mit: ok")
        print(f"OK    {m}: {(r.text or '').strip()[:40]}")
    except Exception as e:
        print(f"FEHLER {m}: {type(e).__name__}: {str(e)[:300]}")
