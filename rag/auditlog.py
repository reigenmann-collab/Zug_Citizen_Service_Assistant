"""Audit-Log. Die Rohfrage wird nie gespeichert, nur ein gesalzenes SHA-256-Pseudonym (CLAUDE.md).

Zweck: Nachvollziehbarkeit (welche Quellen, welche Bewertung, welcher Entscheid) ohne Personenbezug.
Das Salz steht in der Umgebung (AUDIT_SALT), nicht im Code und nicht im Repo. Ohne Salz waere der
Hash einer kurzen Frage per Woerterbuchangriff trivial umkehrbar.

Restrisiko, das im Governance-Kapitel stehen muss: der Antworttext wird gespeichert, weil der Audit
Trail zeigen muss, was Buergerinnen und Buergern gesagt wurde. Enthaelt eine Frage Personendaten und
greift die Antwort sie auf, stehen sie im Log. Die Generierung ist darauf angelegt, nur aus den Quellen
zu antworten, was das unwahrscheinlich macht, aber nicht ausschliesst.
"""
import hashlib, json, os, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGDATEI = ROOT / "data" / "audit" / "auditlog.jsonl"


def salz() -> str:
    s = os.environ.get("AUDIT_SALT")
    if s:
        return s
    # Fallback nur fuer lokale Entwicklung: pro Installation einmalig erzeugt und abgelegt.
    p = ROOT / "data" / "audit" / ".salt"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(os.urandom(16).hex(), encoding="utf8")
    return p.read_text(encoding="utf8").strip()


def pseudonym(frage: str) -> str:
    return hashlib.sha256((salz() + "|" + (frage or "").strip().lower()).encode("utf8")).hexdigest()[:32]


def schreibe(eintrag: dict, datei=None) -> dict:
    p = Path(datei) if datei else LOGDATEI
    p.parent.mkdir(parents=True, exist_ok=True)
    eintrag = {"zeit": dt.datetime.now().isoformat(timespec="seconds"), **eintrag}
    with p.open("a", encoding="utf8") as f:
        f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    return eintrag


def lies(datei=None) -> list:
    p = Path(datei) if datei else LOGDATEI
    if not p.exists():
        return []
    return [json.loads(l) for l in p.open(encoding="utf8") if l.strip()]


def urteil_eintragen(antwort_id: str, urteil: str, bemerkung: str = None, von: str = None,
                     pseudonym_wert: str = None, datei=None) -> dict:
    """Menschliches Urteil zu einer protokollierten Antwort nachtragen.

    Das ist die Voraussetzung fuer eine echte Kalibrierung: Phase 5 hat gezeigt, dass 24 Testfragen
    nicht ausreichen, um eine Confidence-Schwelle zu bestimmen (PROGRESSION/005). Nur wenn
    Mitarbeitende im Pilotbetrieb Antworten als richtig oder falsch markieren, entstehen die
    Negativbeispiele, die dafuer fehlen.

    urteil: "richtig" | "falsch" | "teilweise" | "unklar"
    Bezug ueber antwort_id, nicht ueber das Pseudonym: das Pseudonym ist der Hash der Frage und bei
    wiederholter Frage identisch. Geschrieben wird eine eigene Zeile; der bestehende Eintrag bleibt
    unveraendert, damit das Protokoll append-only bleibt.
    """
    if urteil not in ("richtig", "falsch", "teilweise", "unklar"):
        raise ValueError(f"unbekanntes Urteil: {urteil}")
    return schreibe({"art": "menschliches_urteil", "antwort_id": antwort_id,
                     "pseudonym": pseudonym_wert, "urteil": urteil, "bemerkung": bemerkung,
                     "von": von}, datei)
