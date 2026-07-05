"""Render outputs/duran_case.html — the self-contained editorial long-read.

Content mirrors outputs/decision_memo.md and outputs/rebound_probability.md
(regenerated 2026-07-04): same numbers, same season table, same two-scenario
rebound math, same honesty flags. Figures from figures/ are downscaled to
<=1600px wide and embedded as base64 so GitHub Pages serves a single file
with no external assets (system font stacks only).

Design register: editorial magazine — serif display headlines, restrained
sans body, near-black ink on white, Red Sox navy hero, Red Sox red used
sparingly for negative / key numbers.

Standalone: python3 -m src.web_deck
"""
from __future__ import annotations

import base64
import io
import sys

from . import config as C

MAX_W = 1600  # px — downscale embedded figures to keep the file lean


def _img64(name: str, alt: str) -> str:
    p = C.FIG_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"missing figure: {p}")
    raw = p.read_bytes()
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)),
                           Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            raw = buf.getvalue()
    except ImportError:
        pass  # embed at native size if PIL is unavailable
    b64 = base64.b64encode(raw).decode()
    return (f'<figure><img src="data:image/png;base64,{b64}" alt="{alt}">'
            f"</figure>")


# Season line table — from outputs/decision_memo.md (§ Season-by-season, § 6).
SEASONS = [
    # season, PA, wRC+, wOBA, xwOBA, BABIP, xBABIP, WAR, is_2024, is_2026
    ("2021", "112", "48", ".247", ".246", ".318", ".346", "-0.3", False, False),
    ("2022", "223", "77", ".284", ".286", ".302", ".313", "-0.1", False, False),
    ("2023", "362", "122", ".354", ".321", ".381", ".355", "2.5", False, False),
    ("2024", "735", "131", ".357", ".340", ".344", ".333", "6.8", True, False),
    ("2025", "696", "111", ".335", ".326", ".326", ".326", "3.9", False, False),
    ("2026&thinsp;*", "343", "59", ".263", ".287", ".240", ".312", "-0.0",
     False, True),
]


def _season_rows() -> str:
    rows = []
    for (yr, pa, wrc, woba, xwoba, babip, xbabip, war, hi, lo) in SEASONS:
        cls = ' class="hi"' if hi else (' class="lo"' if lo else "")
        wrc_cell = (f'<td class="neg">{wrc}</td>' if lo
                    else f"<td><b>{wrc}</b></td>" if hi else f"<td>{wrc}</td>")
        rows.append(
            f"<tr{cls}><td>{yr}</td><td>{pa}</td>{wrc_cell}<td>{woba}</td>"
            f"<td>{xwoba}</td><td>{babip}</td><td>{xbabip}</td><td>{war}</td>"
            f"</tr>")
    return "".join(rows)


def build_html() -> str:
    figs = {
        "babip": _img64("01_babip_vs_league.png",
                        "Duran BABIP vs xBABIP and league average by season"),
        "woba": _img64("02_woba_vs_xwoba.png",
                       "Duran wOBA vs xwOBA (results vs process) by season"),
        "disc": _img64("03_plate_discipline_trend.png",
                       "Chase, whiff and zone-contact trends, 2021-2026"),
        "age": _img64("04_age_curve_overlay.png",
                      "Duran vs an empirical league aging curve, age 27-29"),
        "sox": _img64("05_redsox_of_comparison.png",
                      "Red Sox outfield production vs salary comparison"),
        "salary": _img64("06_salary_vs_output_scatter.png",
                         "2026 outfielder salary vs output cohort scatter"),
        "plan": _img64("07_outfield_plan.png",
                       "Red Sox outfield surplus-value plan"),
        "market": _img64("08_trade_fit_targets.png",
                         "Best-fit trade partners: contenders with weak OF"),
        "sim": _img64("09_rebound_probability.png",
                      "Monte Carlo rest-of-season wRC+ distributions, "
                      "healthy prior vs erosion-blended"),
    }

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jarren Duran: Was 2024 the Outlier &mdash; or Is 2026?</title>
<style>
  :root {{
    --ink:#181a1f; --muted:#5c6470; --faint:#8a919c;
    --navy:#0C2340; --red:#BD3039; --green:#2E7D32;
    --rule:#e3e5e8; --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,Helvetica,Arial,sans-serif;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  html {{ -webkit-text-size-adjust:100%; }}
  body {{ background:#fff; color:var(--ink); font:17px/1.65 var(--sans); }}
  a {{ color:var(--navy); text-decoration:none; border-bottom:1px solid #c3cbd8; }}
  a:hover {{ border-bottom-color:var(--navy); }}

  /* ---- hero ---- */
  .hero {{ background:var(--navy); color:#f3f5f8; padding:88px 24px 72px; }}
  .hero-inner {{ max-width:820px; margin:0 auto; }}
  .kicker {{ font:600 12px/1 var(--sans); letter-spacing:.22em;
    text-transform:uppercase; color:#93a3bc; }}
  .hero h1 {{ font-family:var(--serif); font-weight:400; letter-spacing:-.01em;
    font-size:clamp(38px,6.4vw,60px); line-height:1.08; margin:26px 0 22px;
    color:#fff; }}
  .dek {{ font-size:19px; line-height:1.55; color:#c2cddd; max-width:660px; }}
  .herostats {{ display:flex; gap:56px; flex-wrap:wrap; margin-top:52px;
    border-top:1px solid rgba(255,255,255,.14); padding-top:30px; }}
  .herostats .num {{ font-family:var(--serif); font-size:44px; line-height:1;
    color:#fff; }}
  .herostats .lab {{ font-size:11.5px; letter-spacing:.14em;
    text-transform:uppercase; color:#8496b1; margin-top:9px; }}

  /* ---- article ---- */
  .article {{ max-width:760px; margin:0 auto; padding:24px; }}
  section {{ margin:72px 0; }}
  .slug {{ font:600 12px/1 var(--sans); letter-spacing:.2em;
    text-transform:uppercase; color:var(--navy); margin-bottom:14px; }}
  h2 {{ font-family:var(--serif); font-weight:400; font-size:31px;
    line-height:1.2; letter-spacing:-.01em; margin-bottom:18px; }}
  p {{ margin:0 0 18px; color:#2a2e35; }}
  p b, p strong {{ font-weight:650; color:var(--ink); }}
  .neg {{ color:var(--red); font-weight:650; }}
  .pos {{ color:var(--green); font-weight:650; }}
  figure {{ margin:30px -60px; }}
  figure img {{ width:100%; display:block; border:1px solid var(--rule);
    border-radius:2px; }}
  @media (max-width:920px) {{ figure {{ margin:26px 0; }} }}
  .bignum {{ margin:34px 0; padding-left:22px; border-left:2px solid var(--rule); }}
  .bignum .n {{ font-family:var(--serif); font-size:46px; line-height:1.05;
    color:var(--navy); }}
  .bignum .n.down {{ color:var(--red); }}
  .bignum .c {{ font-size:14.5px; color:var(--muted); margin-top:6px;
    max-width:56ch; }}
  .aside {{ font-style:italic; color:var(--faint); font-size:15px;
    line-height:1.6; margin:22px 0; }}
  table {{ width:100%; border-collapse:collapse; margin:26px 0;
    font-size:15px; font-variant-numeric:tabular-nums; }}
  th {{ font:600 11.5px/1.3 var(--sans); letter-spacing:.12em;
    text-transform:uppercase; color:var(--faint); text-align:right;
    padding:0 0 10px 14px; border-bottom:1px solid var(--ink); }}
  th:first-child {{ text-align:left; padding-left:0; }}
  td {{ padding:10px 0 10px 14px; border-bottom:1px solid var(--rule);
    text-align:right; }}
  td:first-child {{ text-align:left; padding-left:0; }}
  tr.hi td {{ background:#f6f8fb; }}
  tr.lo td {{ background:#fdf5f5; }}
  .rule {{ border:0; border-top:1px solid var(--rule); margin:0; }}

  /* ---- closer ---- */
  .closer {{ background:var(--navy); color:#e6ebf2; padding:72px 24px;
    margin-top:88px; }}
  .closer-inner {{ max-width:760px; margin:0 auto; }}
  .closer .slug {{ color:#93a3bc; }}
  .closer h3 {{ font-family:var(--serif); font-weight:400; font-size:24px;
    line-height:1.3; color:#fff; margin:30px 0 8px; }}
  .closer p {{ color:#b4c1d4; font-size:16.5px; }}
  .closer .aside {{ color:#8496b1; border-top:1px solid rgba(255,255,255,.14);
    padding-top:24px; margin-top:44px; }}
  footer {{ max-width:760px; margin:0 auto; padding:34px 24px 60px;
    font-size:13.5px; color:var(--faint); line-height:1.7; }}
</style></head><body>

<div class="hero"><div class="hero-inner">
  <div class="kicker">A Data Case Study &middot; July 2026</div>
  <h1>Jarren Duran: Was 2024 the Outlier &mdash; or Is&nbsp;2026?</h1>
  <p class="dek">Boston's 2024 All-Star has cratered to a 59 wRC+, and the
  easy story is that the breakout was a fluke all along. Six seasons of
  Statcast process data say the easy story is wrong &mdash; in both
  directions.</p>
  <div class="herostats">
    <div><div class="num">131 &rarr; 59</div><div class="lab">wRC+, 2024 to 2026</div></div>
    <div><div class="num">&minus;72 pts</div><div class="lab">2026 BABIP vs expected</div></div>
    <div><div class="num">69% / 47%</div><div class="lab">Rebound odds, intact vs eroded</div></div>
  </div>
</div></div>

<div class="article">

<section>
  <div class="slug">01 &mdash; The Question</div>
  <h2>A testable thesis: 2024 was luck, and the decline is real</h2>
  <p>In 2024, at age 27, Jarren Duran hit for a <b>131 wRC+</b> with a
  league-leading motor and a 6.8-WAR season &mdash; a genuine star year. In
  2026 he is hitting .196 with a <span class="neg">59 wRC+</span>, worth
  roughly zero WAR at the season's halfway mark. The thesis this project set
  out to test is the one you hear on sports radio: <b>2024 was a lucky
  outlier, and the 2025&ndash;26 slide is the real player.</b></p>
  <p>The answer drives a real roster decision &mdash; extend him, trade him,
  or bench him &mdash; and it is entangled with a Red Sox outfield that has
  five bats for four spots. Getting it right requires separating
  <b>process</b> (did he actually hit the ball better?) from <b>results</b>
  (did more balls fall in?), and being honest when the evidence cuts against
  the headline. It does, repeatedly.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">02 &mdash; Results vs Process</div>
  <h2>2024 was mostly earned</h2>
  <table>
    <tr><th>Season</th><th>PA</th><th>wRC+</th><th>wOBA</th><th>xwOBA</th>
        <th>BABIP</th><th>xBABIP</th><th>WAR</th></tr>
    {_season_rows()}
  </table>
  <p class="aside">* 2026 is a partial season, through July 3. xwOBA and
  xBABIP are Statcast contact-quality expectations &mdash; what the batted
  balls &ldquo;should&rdquo; have produced.</p>
  <p>The luck case against 2024 is thinner than it looks. His wOBA ran
  <b>+17 points ahead of his xwOBA</b> &mdash; but Statcast expected stats
  ignore sprint speed, and a burner like Duran legs out infield hits as a
  skill, not luck. Against his own career norm (+5 points of chronic
  overperformance), the true luck component shrinks to <b>roughly 10&ndash;12
  points of wOBA</b>. His 2024 BABIP (.344) sat just 11 points above his own
  contact-quality expectation and was <b>not</b> statistically distinguishable
  from his career baseline.</p>
  <p>Meanwhile the underlying process was a real step forward: career-best
  chase rate (28.1%), whiff rate essentially tied with 2023 &mdash; both
  significantly better than his career norm (p&nbsp;&lt;&nbsp;.01) &mdash;
  on top of unchanged barrel and hard-hit rates. And 2024 peaked in every
  phase: career-best baserunning (+8.3 runs) and a defensive spike (+9.3
  fielding runs) inflated the WAR alongside the bat.</p>
  {figs['woba']}
  <p class="aside">Park check: this is not a Green Monster artifact. His
  career wOBA&minus;xwOBA gap is +20 points at Fenway and +20 on the road
  &mdash; identical &mdash; and the 2024 overperformance was actually
  road-concentrated (+50 road vs +14 home).</p>
  <p><b>Verdict on 2024:</b> the best year of a real 2023&ndash;25 plateau
  (~110&ndash;125 wRC+), with maybe ten points of good fortune on top.
  A lucky top, not a mirage.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">03 &mdash; The 2026 Anomaly</div>
  <h2>The season that actually breaks the model is this one</h2>
  <div class="bignum"><div class="n down">.240 vs .312</div>
  <div class="c">2026 BABIP against contact-quality xBABIP &mdash; 72 points
  below expectation, for a player whose speed normally puts him <i>above</i>
  it.</div></div>
  <p>Duran's 2026 wOBA (.263) sits <b>below</b> his xwOBA (.287). For most
  hitters that is mild bad luck; for a speedster who has out-hit his
  expected stats his whole career, running <b>30 points under his own
  baseline</b> is a much larger anomaly than the raw gap shows. The
  underperformance appears in both venues (&minus;13 at home, &minus;34 on
  the road), so it is not a schedule artifact. No injury has been reported,
  and the legs still grade out fine.</p>
  {figs['babip']}
  <p>Nor is this what aging looks like. An empirical age 27&rarr;29 curve
  &mdash; built to be conservative &mdash; predicts about a <b>7-point</b>
  wRC+ decline. The actual 2024&rarr;2026 drop is <span class="neg">71
  points</span>. Aging explains almost none of it; the rest is
  mean-reversion from an inflated peak plus a bad-luck tail.</p>
  {figs['age']}
</section>

<hr class="rule">

<section>
  <div class="slug">04 &mdash; The Real Erosion</div>
  <h2>What the luck framing cannot explain away</h2>
  <p>Honesty requires the other half of the story. Three process metrics
  moved significantly the wrong way in 2026, and none of them is luck:</p>
  <p><b>Chase rate: 31.1% &rarr; <span class="neg">35.8%</span></b>
  (p&nbsp;&lt;&nbsp;.05) &mdash; back above even his rookie-year
  indiscipline. <b>Whiff rate: 26.2% &rarr; <span class="neg">32.8%</span></b>
  (p&nbsp;&lt;&nbsp;.01) &mdash; a career worst. <b>Hard-hit rate: 46.9%
  &rarr; <span class="neg">39.0%</span></b> (marginal,
  p&nbsp;&lt;&nbsp;.10). The swing decisions that powered the 2023&ndash;25
  plateau are eroding, and part of the contact quality with them.</p>
  {figs['disc']}
  <p>So two things are true at once: the 2026 batting line is <b>worse than
  the player underneath it</b> (the luck signal), and the player underneath
  it is <b>worse than he was</b> (the erosion signal). Treating 2026 as the
  new true level is as much a mistake as treating 2024 as one.</p>
  <p class="aside">The rest of the game is intact: his speed score is still
  elite (6.8), and prorated baserunning (~+6 runs) and fielding (~+8) remain
  plus. The slump is entirely the bat. Barrel rate is even a career-high
  10.6% &mdash; the erosion is in discipline and average contact, not the
  top end.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">05 &mdash; The Rebound Simulation</div>
  <h2>Two priors, 10,000 seasons, one honest gap</h2>
  <p>To turn the luck-vs-erosion argument into a number, a Monte Carlo
  simulates his remaining 303 plate appearances 10,000 times under two
  priors. The <b>healthy prior</b> assumes the 2023&ndash;25 player is
  intact: true talent built from recency-weighted xwOBA plus his speed
  premium, landing at .336 wOBA &asymp; 110 wRC+ &mdash; independently
  confirming the plateau. The <b>erosion scenario</b> blends 2026's degraded
  process (xwOBA .287) in at 40% weight.</p>
  <table>
    <tr><th>Quantity</th><th>Healthy prior</th><th>Erosion-blended</th></tr>
    <tr><td>P(rest-of-season wRC+ &ge; 100)</td><td><b>69%</b></td>
        <td class="neg">47%</td></tr>
    <tr><td>P(rest-of-season wRC+ &ge; 110)</td><td>50%</td><td>29%</td></tr>
    <tr><td>Median rest-of-season wRC+</td><td>110</td><td>99</td></tr>
    <tr><td>P(full-season 2026 wRC+ &ge; 90)</td><td>27%</td><td>11%</td></tr>
    <tr><td>Median full-season 2026 wRC+</td><td>84</td><td>79</td></tr>
  </table>
  {figs['sim']}
  <p>If the plateau player is intact, a league-average-or-better second half
  is a <b>69%</b> proposition &mdash; the &ldquo;hold, he'll rebound&rdquo;
  case. If the erosion is 40% real, it drops to <span class="neg">47%</span>
  &mdash; a coin flip. <b>That 22-point gap is the answer to the whole
  question:</b> it is the measured price of the worse chase, whiff and
  hard-hit rates.</p>
  <p class="aside">Either way, the full-season line stays ugly: even the
  healthy prior finishes below 90 wRC+ in roughly three-quarters of
  simulations (median &asymp; 84). The first-half hole is too deep &mdash;
  which matters for the timing math below, because a buyer staring at the
  season line will still see a down year.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">06 &mdash; What He's Worth</div>
  <h2>The same player, three different prices</h2>
  <p>Duran is on a one-year, <b>$7.7M</b> deal and arbitration-controllable
  through 2028 &mdash; exactly the profile a contender pays prospects for.
  A $/WAR surplus model (~$8M per win) prices his full remaining control at
  <b>&asymp;$28M</b> at true talent, but a July buyer bids on the .196
  average: selling now fetches <b>&asymp;$10M</b>, roughly a 45-FV prospect.
  Running the rebound distribution through those anchors:</p>
  <table>
    <tr><th>Timing</th><th>Healthy prior</th><th>Erosion-blended</th></tr>
    <tr><td>Sell now (July)</td><td class="neg">$10M</td>
        <td class="neg">$10M</td></tr>
    <tr><td>Sell at the deadline</td><td>$16M</td><td>$14M</td></tr>
    <tr><td>Sell in the offseason</td><td><b>$22M</b></td><td><b>$18M</b></td></tr>
  </table>
  <p><b>Waiting dominates in both scenarios.</b> The offseason expectation
  beats the July nadir by ~$13M under the healthy prior and still by ~$9M
  if the erosion is 40% real &mdash; because the downside of waiting is
  roughly the nadir you would accept today anyway. One grade of prospect
  return (45-FV &rarr; 50-FV) is the reason to wait.</p>
  {figs['salary']}
  <p>The market exists: the Phillies (49-39, an <b>86</b> team OF wRC+) and
  Rays (52-33, 90) are contenders with genuine outfield holes, with the
  Marlins and Guardians behind them.</p>
  {figs['market']}
</section>

<hr class="rule">

<section>
  <div class="slug">07 &mdash; The Outfield Context</div>
  <h2>Five bats, four spots &mdash; and he's the movable one</h2>
  <p>This is not a player decision in isolation. Boston has <b>five bats for
  four spots</b>: Roman Anthony ($2.6M, 8yr/$130M extension), Ceddanne
  Rafaela ($2.0M, elite CF glove), Wilyer Abreu ($0.8M, the best surplus on
  the roster), Duran ($7.7M), and the DH-only Masataka Yoshida
  (<span class="neg">$18.6M</span> through 2027, negative trade value).
  Duran is currently the lowest-producing regular outfielder at the
  second-highest outfield salary &mdash; redundant behind a cheaper,
  younger, controllable core.</p>
  {figs['sox']}
  <p>The timing wrinkle that changes everything: the jam is <b>masked right
  now</b> because Anthony is on the 60-day IL. Duran, Abreu and Rafaela are
  the current starters, and the Sox actually need Duran's at-bats through
  2026. The crunch is a <b>2027 problem</b> &mdash; which argues against a
  deadline fire-sale and for a winter deal, once Anthony is healthy and the
  jam returns.</p>
  {figs['plan']}
  <p>The plan: keep the core three (they are the 2027 outfield), quarantine
  the Yoshida contract rather than pay to escape it, and cash Duran &mdash;
  the one everyday, controllable outfielder a contender will pay real
  prospects for &mdash; from a position of surplus. With a top-10 rotation
  already carrying the club, the return should be controllable bats and
  young position talent, not arms.</p>
</section>

</div>

<div class="closer"><div class="closer-inner">
  <div class="slug">08 &mdash; Bottom Line</div>
  <h3>2024 was the lucky top of a real plateau, not a mirage.</h3>
  <p>Its process &mdash; the swing decisions, the contact quality &mdash;
  was legitimate and continuous with 2023 and 2025. Anchoring his value to
  it overpays.</p>
  <h3>2026 is the unlucky bottom, sitting on real erosion.</h3>
  <p>A &minus;72-point BABIP gap will regress upward; the worse chase, whiff
  and hard-hit rates may not. The line is worse than the player, and the
  player is worse than he was.</p>
  <h3>Hold through 2026. Deal him in the offseason.</h3>
  <p>Both scenarios price a winter trade ($22M / $18M) above the July nadir
  (~$10M). Value him off 2025 &mdash; an above-average, speed-and-defense
  regular &mdash; not either tail.</p>
  <p class="aside">Stated with reduced confidence, on purpose: the erosion
  scenario cuts the rebound to a coin flip, so the rebound narrative
  deserves less conviction than the luck numbers alone imply. Track xwOBA,
  chase and whiff &mdash; not batting average. A second-half BABIP rebound
  confirms the hold; chase and whiff staying elevated into 2027 says take a
  good deadline offer and move on.</p>
</div></div>

<footer>Jarren Duran outlier analysis &middot; built from a reproducible,
unit-tested pipeline (Statcast via pybaseball, FanGraphs API, MLB Stats API;
seasons 2021&ndash;2026, data through July 3, 2026; salaries via Spotrac).
Receipts, memos, and code:
<a href="https://github.com/justinloo12/jarren-duran-outlier-analysis">
github.com/justinloo12/jarren-duran-outlier-analysis</a> &middot; regenerated
by src/web_deck.py.</footer>
</body></html>"""
    return html


def run() -> None:
    out = C.OUT_DIR / "duran_case.html"
    out.write_text(build_html(), encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    run()
    sys.exit(0)
