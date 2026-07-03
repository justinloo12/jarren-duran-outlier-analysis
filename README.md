# Jarren Duran — Was 2024 an Outlier?

A reproducible baseball-analytics project testing the thesis that Jarren
Duran's 2024 All-Star/Silver Slugger season was a statistical outlier relative
to his true talent, and what that implies for how the Red Sox should
value/trade him today.

**Short answer (see [`outputs/decision_memo.md`](outputs/decision_memo.md) for the full argument):**
2024 is a clear outlier *on results* (wOBA/wRC+/WAR) and should not be his
valuation anchor — **but the popular "2024 was a lucky mirage" framing is not
well supported.** His 2024 *process* (xwOBA .340, career-best swing decisions)
was legitimate and continuous with 2023 and 2025, and his 2024 BABIP is **not**
significantly above his own history. The truer story: **2023–2025 is an
above-average true-talent plateau (~110–125 wRC+); 2024 is the lucky top and
2026 is an *unlucky* bottom** (2026 wOBA .265 sits *below* its xwOBA .286, BABIP
.244 vs xBABIP .311 — doubly anomalous for a speedster who normally *beats*
his xstats by ~6 points via infield hits). His speed, baserunning and defense
remain plus in 2026; the slump is entirely the bat, with no injury reported.
So anchoring value to 2024 overpays, but selling on 2026
underpays — this is closer to a hold/buy-low than a sell.

## Quick start

```bash
pip install -r requirements.txt

python run_all.py              # full run: pull data -> analyze -> figures -> memo
python run_all.py --no-fetch   # reuse cached CSVs, just re-analyze
python run_all.py --fetch-only # only refresh raw data
```

Outputs land in `data/` (CSVs + JSON), `figures/` (4 PNGs), and
`outputs/decision_memo.md`.

## What it does

1. **Pulls** Duran's data for 2021–2026 plus his MiLB track record:
   - Pitch-level **Statcast** (`pybaseball.statcast_batter`) — authoritative
     source for process metrics.
   - Season **FanGraphs** advanced stats via the current JSON API (pybaseball's
     `batting_stats` targets a deprecated endpoint that now 403s, so we call the
     API directly) — also gives league-wide frames for league averages and the
     aging curve.
   - **Statcast expected-stats** leaderboard (est_wOBA/est_BA/est_SLG).
   - **MLB Stats API** for MLB + minor-league year-by-year (pre-MLB baseline).
2. **Tests 2024 as the outlier** (not 2025–26):
   - Results vs. process: wOBA − xwOBA, BABIP − xBABIP.
   - BABIP vs. his own non-2024 baseline, vs. league, vs. his xBABIP.
   - Process metrics (barrel/hard-hit/chase/whiff/zone-contact) 2024 vs. a
     pooled *rest-of-career-minus-2024* baseline, with two-proportion z-tests.
   - Plate-discipline persistence year over year (did an approach change stick?).
3. **Builds a rest-of-career-minus-2024 baseline** and tests 2025 vs. 2026 for
   consistency (mean-reversion vs. further decline).
4. **Age-curve context**: an empirical delta-method aging curve from the
   2021–26 FanGraphs league data (overall + a speed/contact-OF cohort),
   projecting Duran's expected age 27→29 path from both his 2024 peak and his
   true-talent baseline.
5. **Writes a decision memo** with explicit confidence levels, and **6
   figures**.
6. **Peer & market comparison** ([`src/comps.py`](src/comps.py) →
   [`outputs/peer_and_salary_memo.md`](outputs/peer_and_salary_memo.md)):
   Duran vs. all other Red Sox outfielders (incl. Yoshida and Eaton), vs.
   league-average OF, and a salary-vs-2026-output scatter of a ~20-player OF
   cohort. Output is from FanGraphs; 2026 salaries are manually sourced from
   Spotrac (no free API) with an as-of date and a re-verify caveat — any
   unverified salary is omitted rather than guessed.

   *Headline:* in 2026 Duran ($7.7M) is the Red Sox' lowest-producing regular
   OF at its second-highest OF salary, behind cheaper/younger Abreu ($0.8M),
   Rafaela ($2.0M), and Anthony (extension) — a roster surplus that reinforces
   the "trade from a position of strength, value him at the 2025 baseline"
   call. Yoshida ($18.6M) is the cautionary expensive-decline comp.
7. **Outfield-jam plan** ([`src/outfield_plan.py`](src/outfield_plan.py) →
   [`outputs/outfield_plan.md`](outputs/outfield_plan.md)): a surplus-value
   model ($8M/WAR) over the OF/DH group and a sequenced fix. Grounded in
   July-2026 roster reality — the jam is currently *masked* by Roman Anthony's
   60-day IL stint, so it's a 2027 problem. Recommendation: keep the cheap
   young core (Anthony/Rafaela/Abreu), **trade Duran in the offseason** (not at
   the 2026 deadline, when his value is luck-depressed and Anthony's injury
   makes the Sox need his bat), and **absorb** the Yoshida contract rather than
   pay to escape it.
8. **Trade value & best-fit partners** ([`src/trade_targets.py`](src/trade_targets.py)
   → [`outputs/trade_targets.md`](outputs/trade_targets.md)): converts Duran's
   surplus into a prospect-tier return (~$10–15M / 45-FV if sold at the nadir,
   ~$28M / 50-FV after a rebound) and ranks trade partners by fit = 2026
   contention (MLB Stats API standings) × outfield need (FanGraphs team OF
   production). Top fits: **Phillies, Rays, Marlins, Guardians**.

A capstone narrative ties it all together in
[`outputs/CASE_STUDY.md`](outputs/CASE_STUDY.md), and a 10-slide presentation
deck (`deck/build_deck.py` → `outputs/Red_Sox_Outfield_Strategy.pptx`) reframes
it as a team-level plan: **the pitching is a strength (top-10 rotation), so the
outfield surplus should be cashed for bats/youth, not arms.** Build the deck
with `python deck/build_deck.py` (needs `python-pptx`).

## Method notes / honesty caveats

- **n = 6 seasons (2026 partial).** We do *not* run an outlier test on six
  season-points. Instead each season's rate stats are treated as estimates with
  binomial standard error on their natural denominators (balls-in-play for
  BABIP/barrel/hard-hit, out-of-zone pitches for chase, swings for whiff,
  in-zone swings for zone-contact), and we test differences. With large
  pitch/BIP denominators, significance flags should be read as *directional*.
- **xBABIP / xwOBA** are Statcast contact-quality expectations
  (`estimated_ba/woba_using_speedangle`). Because they ignore sprint speed —
  and fast players beat them chronically as a skill — luck components are
  measured against Duran's **own** career wOBA−xwOBA gap (+6 pts), not zero.
- **Park factors:** wRC+ (used for all talent-level and peer comparisons) is
  park-adjusted by construction. The luck analysis is verified by venue: his
  career wOBA−xwOBA gap is +20 at Fenway vs +22 on the road — identical — so
  the xstat overperformance travels and is not a Green Monster artifact. Raw
  counting stats do carry a Fenway boost (career home wOBA .350 vs road
  .325); the trade memo flags this for park translation.
- **Multiple comparisons:** ~a dozen significance tests are reported without
  family-wise correction; isolated p≈.03–.05 results are directional. Only
  the whiff/chase findings would survive a correction.
- **Defense/baserunning** (BsR, Def, Fld, Spd from FanGraphs) are analyzed in
  the memo's §6 — 2024 was a peak in every phase, and 2026's speed/defense
  remain plus.
- **Aging curve** uses the delta method, which is survivorship-biased *toward
  smaller declines* — a deliberately conservative (Duran-friendly) benchmark.
- The memo is generated from the computed numbers and is written to flag where
  the data contradicts the original thesis rather than force the conclusion.

## Layout

```
src/
  config.py            # player id, seasons, paths (swap PLAYER to reuse)
  fetch_fangraphs.py   # FanGraphs JSON API -> season + league tables
  fetch_statcast.py    # pitch-level Statcast + expected-stats leaderboard
  fetch_milb.py        # MLB Stats API: MLB + MiLB year-by-year
  statcast_metrics.py  # season process metrics from pitch data (+ SEs)
  analysis.py          # outlier tests, baselines, 2025-vs-2026 consistency
  age_curve.py         # empirical aging curve + projected trajectories
  fetch_cohort.py      # Red Sox OF + league-wide OF from FanGraphs
  comps.py             # peer/salary comparison + figures 05-06 + peer memo
  outfield_plan.py     # surplus-value model + figure 07 + jam-fix plan memo
  trade_targets.py     # trade value + fit-ranked partners + figure 08 + memo
  viz.py               # figures 01-04
  memo.py              # decision memo generator
run_all.py             # orchestrator
data/  figures/  outputs/
```

### Figures

1. `01_babip_vs_league.png` — BABIP by season vs. league avg and his xBABIP.
2. `02_woba_vs_xwoba.png` — results vs. contact quality, gap labeled per year.
3. `03_plate_discipline_trend.png` — chase% / whiff% / zone-contact% trend.
4. `04_age_curve_overlay.png` — actual wRC+ vs. expected aging paths.
5. `05_redsox_of_comparison.png` — Red Sox OF/DH 2025 vs 2026 wRC+ + salary.
6. `06_salary_vs_output_scatter.png` — OF salary vs. 2026 output, Duran located.
7. `07_outfield_plan.png` — surplus value by player, keep/trade/absorb verdicts.
8. `08_trade_fit_targets.png` — trade partners by contention × outfield need.

*Data via [pybaseball](https://github.com/jldbc/pybaseball) (Statcast/Baseball
Savant), the FanGraphs API, and the MLB Stats API. For research/education.*
