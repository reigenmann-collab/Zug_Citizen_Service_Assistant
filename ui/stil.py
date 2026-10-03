"""CSS fuer die Streamlit-Oberflaeche, Tokens aus zg.ch (wie im freigegebenen Entwurf).

WICHTIG, Lehre aus dem Schwyz-Prototyp (CLAUDE.md): Eine Leerzeile innerhalb eines <style>-Blocks
beendet Streamlits Raw-HTML-Block, der Rest des CSS landet dann als Text auf der Seite. Deshalb
entfernt `css()` alle Leerzeilen, bevor der Block ausgegeben wird. Nicht "aufraeumen".
"""

TOKENS = """
:root{
  --primary-50:#eaebf0;--primary-100:#d5d7e6;--primary-500:#2d4487;--primary-600:#353f72;
  --primary-650:#435075;--primary-700:#2e335c;--primary-800:#252342;--primary-900:#150023;
  --secondary-500:#0070b8;--secondary-100:#d1e1f0;--secondary-50:#e8f0f7;
  --support-100:#f5f9ff;--support-300:#e0eef6;--support-500:#d1e1f0;--support-700:#7a8890;
  --accent-500:#e07031;--ok:#2f7d4f;--ok-bg:#e6f3ec;--warn:#9a5b00;--warn-bg:#fdf1dc;--err:#c53030;
  --text:#353f72;--head:#150023;--line:#d5d7e6;
  --font:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
"""

ROH = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="st-"],.stMarkdown,.stButton button,input,textarea{font-family:var(--font)!important}
body,.stApp{background:#fff;color:var(--text)}
.block-container{max-width:1180px;padding-top:0.6rem;padding-bottom:2rem}
header[data-testid="stHeader"]{background:transparent;height:0}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{visibility:hidden;height:0}
h1,h2,h3,h4{color:var(--head)!important;font-weight:700!important}
.zg-proto{background:var(--accent-500);color:#fff;text-align:center;padding:6px 10px;font-size:13px;font-weight:600;border-radius:4px;margin-bottom:14px}
.zg-kopf{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:10px}
.zg-kopf .wortmarke{display:flex;align-items:center;gap:11px;color:var(--head);font-size:17px;font-weight:600}
.zg-crumb{font-size:13px;color:var(--support-700);margin:10px 0 4px}
.zg-h1{font-size:34px;line-height:1.15;color:var(--head);font-weight:700;margin:12px 0 0}
.zg-lead{max-width:760px;font-size:16px;margin:10px 0 18px;color:var(--text)}
.zg-m{padding:12px 15px;border-radius:12px;margin-bottom:14px;max-width:92%}
.zg-m.u{background:var(--primary-650);color:#fff;border-bottom-right-radius:3px;margin-left:auto}
.zg-m.b{background:#fff;border:1px solid var(--line);border-bottom-left-radius:3px;color:var(--head)}
.zg-m.b p{margin:0 0 8px}
.zg-m.b p:last-child{margin:0}
.zg-chat{border:1px solid var(--line);border-radius:12px;background:var(--support-100);padding:18px;min-height:300px}
.zg-badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.zg-badge{font-size:12px;font-weight:600;padding:3px 9px;border-radius:99px;background:var(--primary-50);color:var(--primary-700)}
.zg-badge.ok{background:var(--ok-bg);color:var(--ok)}
.zg-badge.warn{background:var(--warn-bg);color:var(--warn)}
.zg-badge.esk{background:var(--warn-bg);color:var(--accent-500)}
.zg-src{margin-top:12px;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:13px;background:#fff}
.zg-src h4{margin:0;padding:7px 12px;background:var(--support-300);color:var(--head);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.zg-src a{display:flex;gap:10px;align-items:baseline;padding:8px 12px;border-top:1px solid var(--line);text-decoration:none;color:var(--secondary-500)}
.zg-src a:hover{background:var(--support-100)}
.zg-src small{color:var(--support-700);margin-left:auto;white-space:nowrap;padding-left:10px}
.zg-legal{margin-top:10px;padding:8px 10px;font-size:12px;border-radius:6px;background:var(--support-300);color:var(--primary-700)}
.zg-esk{border-left:4px solid var(--accent-500);background:var(--warn-bg);padding:12px 14px;border-radius:6px;margin-top:10px;color:var(--head)}
.zg-note{font-size:12px;color:var(--support-700);margin-top:12px}
.zg-tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:#fff;background:var(--primary-800);padding:2px 8px;border-radius:4px;margin-bottom:10px}
.zg-card{border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px;background:#fff}
.zg-card h3{font-size:15px;margin:0 0 10px}
.zg-bar{display:grid;grid-template-columns:104px 1fr 42px;gap:8px;align-items:center;margin:7px 0;font-size:13px}
.zg-bar i{display:block;height:8px;border-radius:4px;background:var(--primary-50);overflow:hidden}
.zg-bar i b{display:block;height:100%;background:var(--secondary-500)}
.zg-bar i b.gesamt{background:var(--primary-650)}
.zg-kv{font-size:13px}
.zg-kv div{display:flex;justify-content:space-between;gap:10px;padding:3px 0;border-bottom:1px dotted var(--primary-50)}
.zg-kv div:last-child{border-bottom:0}
.zg-kv span{color:var(--support-700)}
.zg-kv b{color:var(--head);text-align:right}
.zg-empty{color:var(--support-700);font-size:13px}
.zg-warnbox{font-size:12px;background:var(--warn-bg);color:var(--warn);padding:7px 9px;border-radius:6px;margin-top:8px}
.zg-foot{background:var(--primary-800);color:#fff;padding:18px 20px;border-radius:8px;margin-top:22px;font-size:13px}
.stButton button{background:#fff;color:var(--text);border:1px solid var(--primary-100);border-radius:99px;padding:5px 13px;font-size:13px;font-weight:400}
.stButton button:hover{background:var(--support-300);border-color:var(--primary-650);color:var(--head)}
.stButton button[kind="primary"]{background:var(--primary-650);color:#fff;border:0;border-radius:6px;font-weight:600;padding:9px 22px}
.stButton button[kind="primary"]:hover{background:var(--primary-700);color:#fff}
.stTextInput input{border:1px solid var(--line);border-radius:8px;padding:12px 15px;font-size:16px;color:var(--text)}
.stTextInput input:focus{border-color:var(--primary-500);box-shadow:none}
@media(max-width:900px){.zg-h1{font-size:26px}}
"""


def css() -> str:
    """Fertiger <style>-Block ohne Leerzeilen (siehe Modulkommentar)."""
    roh = TOKENS + ROH
    zeilen = [z for z in roh.splitlines() if z.strip()]
    return "<style>" + "\n".join(zeilen) + "</style>"


WORTMARKE = (
    '<svg width="36" height="26" viewBox="0 0 36 26" aria-hidden="true">'
    '<rect y="0" width="36" height="2" fill="#0070b8"/>'
    '<rect y="7" width="36" height="2" fill="#0070b8"/>'
    '<rect y="14" width="36" height="12" fill="#0070b8"/></svg>'
)
