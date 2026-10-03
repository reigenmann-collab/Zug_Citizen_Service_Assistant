"""Textnormalisierung vor jedem Regex-Matching.
Grund (Lehre aus Schwyz, CLAUDE.md): ein kyrillisches 'е' in 'busse' hat das Routing gebrochen.
Homoglyphen werden deshalb auf Latin abgebildet, bevor Muster greifen."""
import unicodedata
HOMOGLYPH = str.maketrans({
    # Kyrillisch -> Latin
    "а": "a", "в": "b", "е": "e", "ё": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p",
    "с": "c", "т": "t", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "У": "Y", "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S",
    # Griechisch -> Latin
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t",
    "υ": "y", "χ": "x", "Α": "A", "Β": "B", "Ε": "E", "Ι": "I", "Κ": "K", "Ν": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Χ": "X",
    # Typografie
    " ": " ", " ": " ", " ": " ", "⁠": "", "​": "", "‌": "", "‍": "",
    "–": "-", "—": "-", "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
})
def norm(s: str) -> str:
    """NFKC + Homoglyphen -> Latin. Umlaute und ß bleiben erhalten."""
    return unicodedata.normalize("NFKC", s or "").translate(HOMOGLYPH)
def fold(s: str) -> str:
    """norm + lowercase + Umlaute/ß aufgelöst, für robustes Matching."""
    s = norm(s).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")): s = s.replace(a, b)
    return s
