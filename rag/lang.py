"""Sprachenerkennung DE/EN ohne externe Abhängigkeit.
Quellen sind Deutsch. DE -> deutsche Antwort. EN -> englische Antwort plus festem Hinweis (CLAUDE.md)."""
import re
from .norm import fold
DE = {"wie", "was", "wer", "wo", "wann", "warum", "welche", "welcher", "welches", "wieviel", "ich", "mein",
      "meine", "meinen", "ist", "sind", "kann", "darf", "muss", "soll", "habe", "hat", "der", "die", "das",
      "den", "dem", "des", "ein", "eine", "einen", "einem", "fuer", "und", "oder", "nicht", "kein", "keine",
      "mit", "von", "vom", "zum", "zur", "auf", "bei", "aus", "nach", "ueber", "gibt", "es", "man", "sich",
      "stimmt", "richtig", "brauche", "bekomme", "koennen", "wird", "werden", "pro", "noch", "dann", "auch"}
EN = {"how", "what", "who", "where", "when", "why", "which", "much", "many", "the", "and", "or", "not",
      "is", "are", "can", "do", "does", "did", "may", "must", "should", "have", "has", "need", "want",
      "my", "me", "for", "with", "from", "about", "there", "please", "a", "an", "of", "in", "on", "at",
      "cost", "costs", "price", "permit", "parking", "card", "pay", "online", "would", "could", "get", "obtain"}
GERMAN_ONLY = re.compile(r"[äöüß]|\b(parkkarte|gebuehr|anwohner|zufahrt|strasse|bewilligung)")
def detect(q: str) -> str:
    """-> 'de' | 'en'. Bei Gleichstand oder zu kurzem Text: 'de' (Amtssprache, konservativ)."""
    f = fold(q); words = re.findall(r"[a-z]+", f)
    de = sum(w in DE for w in words); en = sum(w in EN for w in words)
    if GERMAN_ONLY.search(f): de += 2
    if de == en: return "de"
    return "en" if en > de else "de"
EN_DISCLAIMER = (
    "Please note: this English answer is not legally binding. The official language of the City of Zug is "
    "German; the German sources cited above are authoritative."
)
