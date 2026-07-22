#!/usr/bin/env python3
"""Bundle the 8 figures + plain-language explanations into a downloadable pack.

Outputs (in the Duran folder):
  graphics_and_explanations/
    01..08_*.png                  (copies of the figures)
    EXPLANATIONS.md               (markdown, images referenced)
    Duran_report.html             (single self-contained file, images embedded)
  Duran_graphics_and_explanations.zip
"""
import base64
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
OUT = ROOT / "graphics_and_explanations"
OUT.mkdir(exist_ok=True)

TITLE = "Jarren Duran & the Red Sox Outfield — Graphics & Explanations"
INTRO = (
    "A visual summary of the analysis. Headline: Duran's 2024 was his genuine "
    "peak (only modestly luck-aided), his true talent is an above-average "
    "regular (~110 wRC+, his 2025 level), and his ugly 2026 is partly "
    "<b>unlucky</b> — bad batted-ball luck stacked on smaller, real skill "
    "erosion. For the team, the outfield is a <b>surplus</b> while "
    "the pitching is a <b>strength</b> (top-10 rotation) — so the move is to "
    "trade the redundant bat (Duran), from a position of depth and after a "
    "value rebound, for young hitting/position talent, and to absorb the "
    "Yoshida contract."
)

# (file, short title, explanation)
FIGS = [
    ("01_babip_vs_league.png",
     "1 · BABIP by season vs. league average",
     "How often Duran's balls in play fell for hits each year (bars), versus "
     "the league average (grey line) and versus what his own contact quality "
     "'deserved' (green, xBABIP). <b>2024's mark sits right on his xBABIP — "
     "largely earned, not lucky.</b> The real outlier is 2026: a BABIP "
     "running ~70 points below what his contact quality supports — bad luck "
     "stacked on a smaller, real decline. Exact values are on the chart."),
    ("02_woba_vs_xwoba.png",
     "2 · Results vs. contact quality (wOBA vs. xwOBA)",
     "Actual offensive output (red) against what his contact quality predicts "
     "(navy). One key adjustment: these expected stats ignore sprint speed, "
     "and a burner like Duran beats them in most seasons (+3 to +13 points, "
     "depending which years you average) by legging out hits. Against his "
     "own norm, <b>2024's gap (+17 raw) is only +5 to +14 points of true "
     "luck — modest</b>, and smaller than 2023's. In 2026 the lines flip: "
     "his results run far <i>below</i> his contact quality (34–43 points "
     "under his norm) — for a speedster, a strong sign of bad luck, not "
     "just lost skill."),
    ("03_plate_discipline_trend.png",
     "3 · Swing decisions & contact",
     "Chase% (swings at balls outside the zone), whiff%, and zone-contact% "
     "over time — the 'approach' metrics. A durable breakout shows a lasting "
     "improvement here. <b>Duran's discipline was best in 2023–24 and held in "
     "2025, then clearly eroded in 2026</b> (more chasing, more swinging "
     "through pitches) — the one genuine warning sign in his profile."),
    ("04_age_curve_overlay.png",
     "4 · Age-curve overlay",
     "His actual wRC+ by age (red) against what normal aging predicts from his "
     "2024 peak (blue/navy) and from his true-talent baseline (green). His "
     "2026 falls far below <i>every</i> aging path. <b>Aging explains only ~7 "
     "of the ~70-point drop</b> — the rest is regression from a lucky peak "
     "plus a 2026 down-tail, not a normal age decline."),
    ("05_redsox_of_comparison.png",
     "5 · Red Sox outfield — 2025 vs. 2026, with salary",
     "Each Red Sox outfielder/DH's wRC+ in 2025 (grey) and 2026 (navy), with "
     "2026 salary labeled. <b>Duran (red) fell from the unit's best bat to its "
     "worst regular — while carrying its second-highest salary ($7.7M).</b> "
     "Cheaper, younger Abreu and Rafaela now out-produce him; Yoshida "
     "($18.6M) is the expensive underperformer."),
    ("06_salary_vs_output_scatter.png",
     "6 · Salary vs. output across MLB outfielders",
     "Every notable outfielder plotted by 2026 salary (up) and output (right = "
     "better hitter). <b>Duran sits low-output, mid-salary today</b> — a poor "
     "value point, but only because 2026 is a luck-depressed partial season. "
     "Yoshida is the pricier bust; the cheap Red Sox kids (Abreu, Rafaela) are "
     "among the best values on the board."),
    ("07_outfield_plan.png",
     "7 · Outfield surplus value — keep / trade / absorb",
     "Estimated annual value each player provides over what he costs "
     "(projected WAR × $8M − salary). <b>The young core (Anthony, Rafaela, "
     "Abreu) are huge positives → keep.</b> Duran is a smaller positive and "
     "redundant → trade. Yoshida is deeply negative → absorb or salary-dump."),
    ("08_trade_fit_targets.png",
     "8 · Best-fit trade partners",
     "Teams plotted by winning % (up) and outfield production (right = "
     "stronger OF). <b>The best trade partners for Duran are winning teams "
     "with weak outfields (the shaded upper-left quadrant)</b> — contenders "
     "who would pay in young talent for an everyday outfielder. (Boston, "
     "with a top-6 rotation, should take back bats, not arms.)"),
    ("12_playoff_race.png",
     "12 · The AL playoff race — should Boston even sell?",
     "Simulated playoff odds for every AL team still alive (10,000 season "
     "simulations; talent estimated from regressed run differential). "
     "<b>Boston's run differential says it is far better than its record — "
     "and the wild-card race is weak enough that the sim keeps them squarely "
     "alive.</b> The team, like Duran, was producing worse results than its "
     "underlying process — and as the results catch up, the case against a "
     "fire sale (and against trading Duran at his nadir) only strengthens. "
     "Current record, gap and odds are labeled on the chart."),
    ("13_positional_audit.png",
     "13 · Where the roster actually leaks runs",
     "Boston's production at each position versus the league average at that "
     "position (PA-weighted wRC+). <b>The biggest hole is left field — the "
     "Duran slump itself — meaning the best deadline additions are internal "
     "and free: Duran's regression and Roman Anthony's eventual return.</b> "
     "Shortstop is the one true external target; the bullpen (whose FIP and "
     "reliever WAR rank well below its ERA) is the quiet weakness. And the "
     "awkward twist: Willson Contreras, a reported winter trade candidate, "
     "is their best hitter. Exact gaps are labeled on the chart."),
]


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


# --- copy PNGs + write markdown --------------------------------------------
md = [f"# {TITLE}\n", INTRO.replace("<b>", "**").replace("</b>", "**")
      .replace("<i>", "*").replace("</i>", "*"), ""]
for fname, htitle, expl in FIGS:
    shutil.copy2(FIG / fname, OUT / fname)
    md.append(f"## {htitle}\n")
    md.append(f"![{htitle}]({fname})\n")
    md.append(expl.replace("<b>", "**").replace("</b>", "**")
              .replace("<i>", "*").replace("</i>", "*") + "\n")
(OUT / "EXPLANATIONS.md").write_text("\n".join(md))

# --- self-contained HTML ----------------------------------------------------
cards = []
for fname, htitle, expl in FIGS:
    data = b64(OUT / fname)
    cards.append(f"""
  <section class="card">
    <h2>{htitle}</h2>
    <img src="data:image/png;base64,{data}" alt="{htitle}"/>
    <p>{expl}</p>
  </section>""")

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<style>
  :root {{ --navy:#0C2340; --red:#BD3039; --ink:#20232A; --muted:#5b6472;
          --bg:#f4f5f7; --line:#e2e5ea; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    line-height:1.5; }}
  header {{ background:var(--navy); color:#fff; padding:40px 32px; }}
  header h1 {{ margin:0 0 10px; font-size:26px; }}
  header p {{ margin:0; max-width:900px; color:#d3d9e6; font-size:15px; }}
  header .tag {{ color:var(--red); font-weight:700; letter-spacing:.06em;
    font-size:12px; text-transform:uppercase; margin-bottom:12px; }}
  main {{ max-width:980px; margin:0 auto; padding:28px 20px 60px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:12px;
    padding:22px 24px; margin:20px 0;
    box-shadow:0 1px 3px rgba(16,24,40,.06); }}
  .card h2 {{ margin:0 0 14px; font-size:19px; color:var(--navy); }}
  .card img {{ width:100%; height:auto; border-radius:8px;
    border:1px solid var(--line); }}
  .card p {{ margin:14px 2px 2px; font-size:15px; color:#333; }}
  .card p b {{ color:var(--navy); }}
  header b {{ color:#ffffff; }}
  footer {{ max-width:980px; margin:0 auto; padding:0 20px 50px;
    color:var(--muted); font-size:12px; }}
</style></head><body>
<header>
  <div class="tag">Boston Red Sox · Roster Analysis</div>
  <h1>{TITLE}</h1>
  <p>{INTRO}</p>
</header>
<main>{''.join(cards)}</main>
<footer>Data: Statcast (pybaseball), FanGraphs API, MLB Stats API; salary via
Spotrac. Generated July 2026. 2026 is a partial, luck-affected season — read it
with that caveat.</footer>
</body></html>"""
(OUT / "Duran_report.html").write_text(html)

# --- zip --------------------------------------------------------------------
zip_path = ROOT / "Duran_graphics_and_explanations.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        z.write(p, f"graphics_and_explanations/{p.name}")

print(f"Wrote {OUT}/ ({len(list(OUT.iterdir()))} files)")
print("  - Duran_report.html  (self-contained: graphics + explanations)")
print("  - EXPLANATIONS.md")
print("  - 8 PNG figures")
print(f"Zipped -> {zip_path}")
