"""Render the deadline article and the site landing page for GitHub Pages.

  outputs/ARTICLE.md  ->  deadline.html   (styled long-read, repo root)
  data/deadline.json  ->  index.html      (landing page, repo root)

Both pages are fully self-contained: figures are downscaled and embedded
as base64, fonts are system stacks, no external assets. The markdown
renderer below is deliberately tiny — it covers exactly the constructs
ARTICLE.md uses (headings, bold/italic/code, lists, images, rules,
links) and nothing else, so there is no dependency to break.

Standalone: python3 -m src.web_article
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys

from . import config as C

MAX_W = 1600  # px, matches web_deck.py


# ------------------------------------------------------------- figures
def _img64(path_str: str, alt: str) -> str:
    from .web_deck import _img64 as _w  # reuse the downscaling embedder
    return _w(path_str.split("/")[-1], alt)


# ------------------------------------------------- tiny markdown renderer
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITAL = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_CODE = re.compile(r"`([^`]+?)`")
_LINK = re.compile(r"\[([^\]]+?)\]\(([^)]+?)\)")
_IMG = re.compile(r"^!\[([^\]]*?)\]\(([^)]+?)\)\s*$")
_OL = re.compile(r"^\d+\. ")


def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITAL.sub(r"<em>\1</em>", s)
    s = _CODE.sub(r"<code>\1</code>", s)
    s = _LINK.sub(r'<a href="\2">\1</a>', s)
    return s


def md_to_html(md: str, embed_images: bool = True) -> dict:
    """Render ARTICLE.md. Returns {title, dek, meta, body_html}."""
    title = dek = meta = ""
    out: list[str] = []
    mode = None  # None | 'ul' | 'ol'

    def close():
        nonlocal mode
        if mode:
            out.append(f"</{mode}>")
            mode = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close()
            continue
        m = _IMG.match(line.strip())
        if m:
            close()
            alt, src = m.group(1), m.group(2)
            if embed_images:
                out.append(_img64(src, alt))  # returns a <figure> block
            else:
                out.append(f'<figure><img src="{src}" '
                           f'alt="{html.escape(alt)}"></figure>')
            continue
        if line.startswith("# ") and not title:
            title = _inline(line[2:])
            continue
        if line.startswith("### ") and not dek:
            dek = _inline(line[4:])
            continue
        if line.startswith("## "):
            close()
            out.append(f"<h2>{_inline(line[3:])}</h2>")
            continue
        if line.strip() in ("---", "***"):
            close()
            continue
        if line.startswith("- "):
            if mode != "ul":
                close()
                out.append("<ul>")
                mode = "ul"
            out.append(f"<li>{_inline(line[2:])}</li>")
            continue
        if _OL.match(line):
            if mode != "ol":
                close()
                out.append("<ol>")
                mode = "ol"
            out.append(f"<li>{_inline(_OL.sub('', line))}</li>")
            continue
        if line.startswith("> "):
            close()
            out.append(f"<blockquote>{_inline(line[2:])}</blockquote>")
            continue
        # first italic-only line under the title is the byline/meta
        if (not meta and line.startswith("*") and line.endswith("*")
                and not line.startswith("**")):
            meta = _inline(line.strip("*"))
            continue
        close()
        cls = ' class="aside"' if (line.startswith("*") and
                                   line.endswith("*")) else ""
        out.append(f"<p{cls}>{_inline(line.strip('*') if cls else line)}</p>")
    close()
    return {"title": title, "dek": dek, "meta": meta,
            "body": "\n".join(out)}


# ------------------------------------------------------------------ CSS
_CSS = """
  :root {
    --ink:#181a1f; --muted:#5c6470; --faint:#8a919c;
    --navy:#0C2340; --red:#BD3039; --green:#2E7D32;
    --rule:#e3e5e8; --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,Helvetica,Arial,sans-serif;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  html { -webkit-text-size-adjust:100%; }
  body { background:#fff; color:var(--ink); font:17px/1.65 var(--sans); }
  a { color:var(--navy); text-decoration:none; border-bottom:1px solid #c3cbd8; }
  a:hover { border-bottom-color:var(--navy); }
  .hero { background:var(--navy); color:#f3f5f8; padding:80px 24px 64px; }
  .hero-inner { max-width:820px; margin:0 auto; }
  .kicker { font:600 12px/1 var(--sans); letter-spacing:.22em;
    text-transform:uppercase; color:#93a3bc; }
  .hero h1 { font-family:var(--serif); font-weight:400; letter-spacing:-.01em;
    font-size:clamp(36px,6vw,56px); line-height:1.1; margin:24px 0 20px;
    color:#fff; }
  .dek { font-size:19px; line-height:1.55; color:#c2cddd; max-width:680px; }
  .herostats { display:flex; gap:52px; flex-wrap:wrap; margin-top:46px;
    border-top:1px solid rgba(255,255,255,.14); padding-top:28px; }
  .herostats .num { font-family:var(--serif); font-size:42px; line-height:1;
    color:#fff; }
  .herostats .lab { font-size:11.5px; letter-spacing:.14em;
    text-transform:uppercase; color:#8496b1; margin-top:8px; }
  .article { max-width:760px; margin:0 auto; padding:24px; }
  h2 { font-family:var(--serif); font-weight:400; font-size:30px;
    line-height:1.2; letter-spacing:-.01em; margin:64px 0 18px; }
  p { margin:0 0 18px; color:#2a2e35; }
  p strong, li strong { font-weight:650; color:var(--ink); }
  ul, ol { margin:0 0 18px 22px; color:#2a2e35; }
  li { margin-bottom:12px; }
  blockquote { border-left:2px solid var(--rule); padding-left:18px;
    color:var(--muted); margin:0 0 14px; }
  figure { margin:30px -60px; }
  figure img { width:100%; display:block; border:1px solid var(--rule);
    border-radius:2px; }
  @media (max-width:920px) { figure { margin:26px 0; } }
  .aside { font-style:italic; color:var(--faint); font-size:15px;
    line-height:1.6; margin:22px 0; }
  code { font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;
    background:rgba(127,140,160,.16); padding:1px 5px; border-radius:3px; }
  .meta { font-size:14px; color:#8496b1; margin-top:18px; }
  footer { max-width:760px; margin:0 auto; padding:30px 24px 60px;
    font-size:13.5px; color:var(--faint); line-height:1.7;
    border-top:1px solid var(--rule); }
  .cards { display:grid; gap:22px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    max-width:980px; margin:56px auto; padding:0 24px; }
  .card { border:1px solid var(--rule); border-radius:4px; padding:26px;
    display:block; }
  a.card { border-bottom:1px solid var(--rule); }
  .card:hover { border-color:var(--navy); }
  .card .tag { font:600 11px/1 var(--sans); letter-spacing:.18em;
    text-transform:uppercase; color:var(--red); }
  .card h3 { font-family:var(--serif); font-weight:400; font-size:22px;
    margin:12px 0 8px; color:var(--ink); }
  .card p { font-size:15px; color:var(--muted); margin:0; }
"""


def _page(title: str, body: str) -> str:
    return (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, '
            f'initial-scale=1">\n<title>{html.escape(title)}</title>\n'
            f"<style>{_CSS}</style></head><body>\n{body}\n</body></html>\n")


# ---------------------------------------------------------------- pages
def build_article() -> str:
    md = (C.OUT_DIR / "ARTICLE.md").read_text()
    r = md_to_html(md)
    body = f"""
<div class="hero"><div class="hero-inner">
  <div class="kicker">Boston Red Sox &middot; Trade Deadline 2026</div>
  <h1>{r['title']}</h1>
  <div class="dek">{r['dek']}</div>
  <div class="meta">{r['meta']}</div>
</div></div>
<div class="article">
{r['body']}
</div>
<footer>Generated by a reproducible pipeline (<code>python run_all.py</code>)
— data via Baseball Savant, FanGraphs and the MLB Stats API.
&nbsp;<a href="index.html">Project home</a> &middot;
<a href="https://github.com/justinloo12/jarren-duran-outlier-analysis">Code
on GitHub</a></footer>"""
    return _page(r["title"].replace("&amp;", "&"), body)


def build_index() -> str:
    d = json.load(open(C.DATA_DIR / "deadline.json"))
    bos, v = d["bos"], d["verdict"]
    days = max(0, (dt.date(2026, 8, 3) - dt.date.today()).days)
    stats = [
        (f"{int(bos['W'])}&ndash;{int(bos['L'])}", "record"),
        (f"+{int(bos['run_diff'])}", "run differential"),
        (f"{v['odds']*100:.0f}%", "playoff odds (10k sims)"),
        (v["call"], "verdict"),
        (f"{days}", "days to the deadline"),
    ]
    stat_html = "\n".join(
        f'<div><div class="num">{n}</div><div class="lab">{l}</div></div>'
        for n, l in stats)
    body = f"""
<div class="hero"><div class="hero-inner">
  <div class="kicker">A Reproducible Baseball Analytics Case Study</div>
  <h1>Red Sox Trade Deadline 2026, by the Numbers</h1>
  <div class="dek">Live data, custom models, and pre-registered
  predictions: the buy/sell call, a positional audit, who is
  outperforming their track record, and the trades that fit.</div>
  <div class="herostats">{stat_html}</div>
</div></div>
<div class="cards">
  <a class="card" href="deadline.html">
    <div class="tag">The deadline case</div>
    <h3>The deadline assessment</h3>
    <p>The buy/sell verdict, the positional audit, the overvalue
    check, three trades and a walk-away, and the deal already made.
    Every number generated from live data.</p>
  </a>
  <a class="card" href="outputs/duran_case.html">
    <div class="tag">The player study</div>
    <h3>Jarren Duran: was 2024 the outlier &mdash; or is 2026?</h3>
    <p>Luck decomposition against his own baseline, a rebound Monte
    Carlo, bat-tracking erosion analysis, and a 2016&ndash;25 backtest.</p>
  </a>
  <a class="card"
     href="https://github.com/justinloo12/jarren-duran-outlier-analysis">
    <div class="tag">The machinery</div>
    <h3>Models, tests, pipeline</h3>
    <p>A speed-aware expected-contact model, an adjusted catcher-battery
    model, 75 offline unit tests, CI, and one command to rebuild
    everything.</p>
  </a>
</div>
<footer>Predictions were frozen 2026-07-04 and get graded in October,
flattering or not. Data via Baseball Savant, FanGraphs and the MLB Stats
API; research/education.</footer>"""
    return _page("The Red Sox Deadline, by the Numbers", body)


def run():
    (C.ROOT / "deadline.html").write_text(build_article())
    print(f"  [web_article] wrote {C.ROOT / 'deadline.html'}")
    (C.ROOT / "index.html").write_text(build_index())
    print(f"  [web_article] wrote {C.ROOT / 'index.html'}")


if __name__ == "__main__":
    sys.exit(run())
