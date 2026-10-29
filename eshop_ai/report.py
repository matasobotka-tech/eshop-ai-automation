"""Self-contained HTML reports (one file, no external assets) for review before anything goes live.

Every value is HTML-escaped: e-mail text and model output are untrusted input.
"""
from datetime import datetime
from html import escape
from pathlib import Path

from eshop_ai.descriptions import META_MAX, SEO_TITLE_MAX
from eshop_ai.inbox import CATEGORIES

URGENCY_LABELS = {"vysoka": "vysoká", "stredni": "střední", "nizka": "nízká"}

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2433;--muted:#667085;--line:#e4e7ec;--accent:#0f766e;
--hi:#b42318;--hi-bg:#fef3f2;--mid:#b54708;--mid-bg:#fffaeb;--lo:#067647;--lo-bg:#ecfdf3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:0 0 8px}
.sub{color:var(--muted);margin:0 0 24px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:140px}
.stat b{display:block;font-size:22px}.stat span{color:var(--muted);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:16px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
.tag{font-size:12px;font-weight:600;padding:2px 8px;border-radius:999px;background:#eef2f6;color:#344054}
.vysoka{background:var(--hi-bg);color:var(--hi)}.stredni{background:var(--mid-bg);color:var(--mid)}
.nizka{background:var(--lo-bg);color:var(--lo)}.human{background:#f4f3ff;color:#5925dc}
.serp{border:1px solid var(--line);border-radius:8px;padding:12px;margin:12px 0;background:#fcfcfd}
.serp .t{color:#1a0dab;font-size:18px}.serp .u{color:#006621;font-size:13px}.serp .d{color:#4d5156;font-size:14px}
.len{font-size:12px;color:var(--muted)}.over{color:var(--hi);font-weight:600}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:760px){.grid{grid-template-columns:1fr}}
.box{background:#f9fafb;border:1px solid var(--line);border-radius:8px;padding:12px;white-space:pre-wrap}
.label{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:12px 0 4px}
.err{border-color:#fda29b;background:var(--hi-bg)}ul{margin:4px 0 0;padding-left:20px}
footer{color:var(--muted);font-size:13px;margin-top:32px}
"""


def page(title, subtitle, body):
    stamp = datetime.now().strftime("%d. %m. %Y %H:%M")
    return (f'<!doctype html><html lang="cs"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>'
            f'<style>{CSS}</style></head><body><main><h1>{escape(title)}</h1>'
            f'<p class="sub">{escape(subtitle)} · vygenerováno {stamp}</p>{body}'
            f'<footer>Návrhy vytvořila AI, před zveřejněním nebo odesláním je schvaluje člověk.</footer>'
            f'</main></body></html>')


def stat(value, label):
    return f'<div class="stat"><b>{escape(str(value))}</b><span>{escape(label)}</span></div>'


def length(text, limit):
    cls = "len over" if len(text) > limit else "len"
    return f'<span class="{cls}">{len(text)}/{limit} znaků</span>'


def products_html(results):
    ok = [r for r in results if "copy" in r]
    cards = []
    for r in results:
        name = r["row"].get("nazev") or r["row"].get("name") or "Produkt"
        if "error" in r:
            cards.append(f'<div class="card err"><h2>{escape(name)}</h2>Chyba: {escape(r["error"])}</div>')
            continue
        c = r["copy"]
        bullets = "".join(f"<li>{escape(b)}</li>" for b in c["bullets"])
        cards.append(
            f'<div class="card"><h2>{escape(name)}</h2>'
            f'<div class="serp"><div class="u">vas-eshop.cz › {escape(r["row"].get("kategorie", "produkty"))}</div>'
            f'<div class="t">{escape(c["seo_title"])}</div><div class="d">{escape(c["meta_description"])}</div></div>'
            f'<div class="row">{length(c["seo_title"], SEO_TITLE_MAX)} {length(c["meta_description"], META_MAX)}</div>'
            f'<div class="label">Krátký popis</div><div>{escape(c["short_description"])}</div>'
            f'<div class="label">Výhody</div><ul>{bullets}</ul>'
            f'<div class="label">Dlouhý popis</div><div class="box">{escape(c["long_description"])}</div>'
            f'<div class="label">Klíčová slova</div><div class="row">'
            + "".join(f'<span class="tag">{escape(k)}</span>' for k in c["keywords"]) + "</div></div>")
    stats = f'<div class="stats">{stat(len(results), "produktů")}{stat(len(ok), "hotových popisků")}' \
            f'{stat(len(results) - len(ok), "chyb")}</div>'
    return page("Popisky produktů", "AI texty pro produktové stránky a vyhledávače", stats + "".join(cards))


def inbox_html(results):
    tri = [r["triage"] for r in results if "triage" in r]
    cards = []
    for r in results:
        email = r["email"]
        if "error" in r:
            cards.append(f'<div class="card err"><h2>{escape(email["id"])}</h2>Chyba: {escape(r["error"])}</div>')
            continue
        t = r["triage"]
        details = [(lbl, t[k]) for k, lbl in (("order_number", "Objednávka"), ("product", "Produkt"),
                                              ("dimensions", "Rozměry")) if t[k]]
        missing = "".join(f"<li>{escape(m)}</li>" for m in t["missing_info"])
        cards.append(
            f'<div class="card"><div class="row"><span class="tag {escape(t["urgency"])}">'
            f'naléhavost: {URGENCY_LABELS[t["urgency"]]}</span><span class="tag">{escape(CATEGORIES[t["category"]])}</span>'
            + ('<span class="tag human">předat člověku</span>' if t["needs_human"] else "") + "</div>"
            f'<h2>{escape(t["summary"])}</h2>'
            + "".join(f'<div class="row"><span class="len">{escape(l)}:</span> {escape(v)}</div>' for l, v in details)
            + (f'<div class="label">Chybí od zákazníka</div><ul>{missing}</ul>' if missing else "")
            + f'<div class="grid"><div><div class="label">E-mail zákazníka</div><div class="box">{escape(email["text"])}'
            f'</div></div><div><div class="label">Návrh odpovědi</div><div class="box">{escape(t["draft_reply"])}'
            f'</div></div></div></div>')
    stats = (f'<div class="stats">{stat(len(results), "e-mailů")}'
             f'{stat(sum(t["urgency"] == "vysoka" for t in tri), "naléhavých")}'
             f'{stat(sum(t["needs_human"] for t in tri), "pro člověka")}'
             f'{stat(len(results) - len(tri), "chyb")}</div>')
    return page("Třídění dotazů zákazníků", "Kategorie, naléhavost a návrh odpovědi ke schválení", stats + "".join(cards))


def save(html, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(html, encoding="utf-8")
