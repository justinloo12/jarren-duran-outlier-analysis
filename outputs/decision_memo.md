# Decision Memo — Is Jarren Duran's 2024 an Outlier?
*Generated 2026-07-04 · data via pybaseball (Statcast), FanGraphs API, MLB Stats API*

## Bottom line up front

- **2024 was his best year and only marginally luck-aided — not a fluke.** Its underlying process (xwOBA 0.340, elite swing decisions) was legitimate and continuous with 2023 and 2025. Results ran ~17 points of wOBA ahead of contact quality — but after crediting the ~6 points his speed *always* adds over xwOBA, the true luck component is closer to 10 points. And 2024 was a peak in every phase: career-best baserunning and defense, not just the bat.
- **His true talent is the 2023–2025 plateau — an above-average regular (~110–125 wRC+), not a 6-WAR star and not a replacement-level bust.** Both the 2024 high and the 2026 low are tails around that.
- **2026's collapse overstates his decline: it is partly *unlucky*** (wOBA 0.263 sits *below* xwOBA 0.287; BABIP 0.240 vs xBABIP 0.312, -72 points — and for a speedster who normally *beats* his xstats, running below them is doubly anomalous). There is real erosion in 2026 — chase, whiff and hard-hit rate all worsened significantly — but no injury has been reported, his speed/defense remain plus, and the batting line is worse than the erosion warrants.
- **Implication:** value him off ~his 2025 line. Anchoring to 2024 **over**pays; anchoring to 2026 **under**pays. The thesis is right that 2024 shouldn't be the anchor — but 'sell because value is cratering' misreads a down year that is depressed by bad luck.

## Season-by-season

| Season | Age | PA | wRC+ | wOBA | xwOBA | BABIP | xBABIP | Barrel% | HardHit% | Chase% | Whiff% |
|--------|----:|---:|-----:|-----:|------:|------:|-------:|--------:|---------:|-------:|-------:|
| 2021 | 24 | 112 | 48 | 0.247 | 0.246 | 0.318 | 0.346 | 4.4% | 39.7% | 34.8% | 31.1% |
| 2022 | 25 | 223 | 77 | 0.284 | 0.286 | 0.302 | 0.313 | 7.7% | 38.0% | 31.5% | 24.1% |
| 2023 | 26 | 362 | 122 | 0.354 | 0.321 | 0.381 | 0.355 | 5.3% | 46.3% | 30.0% | 21.7% |
| 2024 | 27 | 735 | 131 | 0.357 | 0.340 | 0.344 | 0.333 | 9.3% | 44.0% | 28.1% | 21.8% |
| 2025 | 28 | 696 | 111 | 0.335 | 0.326 | 0.326 | 0.326 | 9.7% | 46.9% | 31.1% | 26.2% |
| 2026 * | 29 | 343 | 59 | 0.263 | 0.287 | 0.240 | 0.312 | 10.6% | 39.0% | 35.8% | 32.8% |

*`*` = partial season, in progress as of the analysis date. xBABIP / xwOBA are Statcast contact-quality expectations.*

## 1. Did he hit the ball better in 2024, or did it just fall in?

- **wOBA − xwOBA, 2024:** +17 points (wOBA 0.357 vs xwOBA 0.340; Savant est_woba 0.340 agrees).
- **BABIP − xBABIP, 2024:** +11 points (BABIP 0.344 vs contact-quality xBABIP 0.333).

**A necessary speed adjustment.** Statcast expected stats are built from exit velocity and launch angle only — they ignore sprint speed. A burner like Duran legs out infield hits and stretches singles into doubles, so he *should* chronically out-hit his xwOBA as a skill, not luck. His own non-2024 career baseline gap is **+5 points** of wOBA over xwOBA. Measured against that personal norm rather than zero:
- 2024's gap was only **+12 points above his own baseline** — an even smaller luck component than the raw gap suggests.
- 2026's gap sits **-30 points below his own baseline** — for a player whose legs usually add ~6 points, running *negative* is a much larger anomaly than the raw number shows.

**Park robustness check (is this just Fenway?).** The headline talent metric, wRC+, is park-adjusted by construction, but the luck analysis above is not — and the Green Monster inflates exactly the kind of contact Duran makes. Splitting his career by venue: his wOBA−xwOBA gap is **+20 at Fenway vs +20 on the road — essentially identical**. The overperformance travels, which is what a speed skill (not a park effect) looks like.
- 2024's gap was actually **road-concentrated** (+50 road vs +14 home) — the opposite of a Monster-driven fluke.
- 2026 is negative in **both** venues (-13 home, -34 road) — the underperformance is not a schedule artifact.

> **Read:** after crediting his speed, 2024's luck component shrinks to ~10 points of wOBA — real but minor. Enough to shave a ~130 wRC+ toward the low-120s of true talent, **not** enough to call 2024 a mirage. The batted-ball luck specifically (BABIP vs xBABIP) is negligible. Meanwhile the same adjustment makes 2026 look *more* unlucky, not less.

## 2. BABIP — did variance prop 2024 up?

- 2024 BABIP **0.344** vs his own non-2024 baseline **0.321** (+23 pts, not significant (p=0.31)).
- 2024 BABIP vs 2024 league average (300+ PA) **0.294** (significant (p<0.05)).
- 2024 BABIP vs his *own* xBABIP **0.333**: only +11 pts.

> **This is where the original thesis is weakest.** The hypothesis was that 2024 BABIP sits *well above* both his career and league norms. It is above *league* (expected — he's a genuine speed / hard-contact, high-BABIP hitter), but it is **not** significantly above his own baseline and barely above his own xBABIP. 2024 BABIP was largely earned, not a fluke. The bigger BABIP story is 2026's *unsustainably low* mark.

## 3. Process metrics: 2024 vs. rest-of-career-minus-2024

| Metric | 2024 | Baseline | Diff (pts) | Verdict |
|--------|-----:|---------:|-----------:|---------|
| Barrel% | 9.3% | 8.4% | +10 | not significant (p=0.52) |
| Hard-Hit% | 44.0% | 43.7% | +3 | not significant (p=0.92) |
| Chase% | 28.1% | 32.1% | -40 | significant (p<0.01) |
| Whiff% | 21.8% | 26.5% | -47 | significant (p<0.01) |
| Zone-Contact% | 87.4% | 86.5% | +9 | not significant (p=0.48) |
| BABIP | 34.4% | 31.8% | +26 | not significant (p=0.31) |

*Multiple-comparisons caution: ~a dozen tests are reported across this memo, so isolated p-values in the .03–.05 range should be read as directional; only the whiff/chase findings (p<0.01–0.05, consistent across seasons) would survive a family-wise correction.*

> **Read:** the standout 2024 signal is *swing decisions*, not raw contact — he chased and whiffed **significantly less** than his career norm (chase% a career best; whiff% essentially tied with 2023), while barrel/hard-hit were in line with his baseline. That is a genuine skill signal, so 2024 was a real step forward — arguing **against** the pure-luck framing. (Note the pooled baseline is dragged up by ugly 2021–22 rookie whiff rates; vs 2023 alone his 2024 discipline is similar, not better.)

## 4. Approach change — and did it persist?

| Season | Chase% | Whiff% | Zone-Contact% |
|--------|-------:|-------:|--------------:|
| 2021 | 34.8% | 31.1% | 81.2% |
| 2022 | 31.5% | 24.1% | 87.0% |
| 2023 | 30.0% | 21.7% | 89.2% |
| 2024 | 28.1% | 21.8% | 87.4% |
| 2025 | 31.1% | 26.2% | 86.9% |
| 2026 | 35.8% | 32.8% | 83.5% |

> The 2022→2024 improvement in chase/whiff **did** persist into 2023 and held reasonably in 2025 — consistent with a real approach gain that underpins the 2023–25 plateau. It then **regressed in 2026** (chase and whiff both jump), which is the first genuine warning sign of decline — see §5.

## 5. Are 2025 and 2026 the same player? (mean-reversion vs. decline)

- wRC+ **111 → 59**; wOBA 0.335 → 0.263.
- Chase%: 2026 vs 2025 +47 pts (significant (p<0.05)).
- Whiff%: 2026 vs 2025 +66 pts (significant (p<0.01)).
- Barrel%: 2026 vs 2025 +10 pts (not significant (p=0.69)).
- Hard-Hit%: 2026 vs 2025 -79 pts (marginal (p<0.10)).
- BABIP: 2026 vs 2025 -86 pts (significant (p<0.05)).

> **Two things are true at once.** (a) *Real* signal: chase%, whiff% **and hard-hit%** all moved significantly the wrong way in 2026 — both the plate discipline and part of the contact quality that powered the 2023–25 plateau are eroding (barrel% is a career high, but EV and hard-hit rate are down). (b) *Luck* signal on top: even against that diminished contact quality, results underperform — BABIP cratered to 0.240 vs an xBABIP of 0.312, and wOBA (0.263) sits **below** xwOBA (0.287). So 2026 reflects real erosion *and* bad luck; the batting line is worse than the (declining) player underneath it. Net: 2025 and 2026 are **not** a stable shared level — and treating 2026 as 'the new true level' is as much a mistake as treating 2024 as one.

## 6. The rest of the game: defense, baserunning, speed

Duran's value case has never been bat-only — and his 2024 WAR peak was not either.

| Season | BsR | Def | Fld | Spd | WAR |
|--------|----:|----:|----:|----:|----:|
| 2021 | +0.5 | -0.4 | -0.8 | 7.4 | -0.3 |
| 2022 | +2.2 | -4.8 | -5.2 | 7.3 | -0.1 |
| 2023 | +7.2 | -4.1 | -4.0 | 7.0 | 2.5 |
| 2024 | +8.3 | +7.6 | +9.3 | 8.0 | 6.8 |
| 2025 | +7.2 | -2.1 | +3.6 | 7.2 | 3.9 |
| 2026 * | +3.1 | +0.8 | +4.3 | 6.8 | -0.0 |

*BsR = baserunning runs, Def = defensive runs (positional-adjusted), Fld = fielding runs, Spd = FanGraphs speed score. 2026 counting stats are a partial season (roughly half); prorate accordingly.*

> **Two findings.** (a) *2024's 6.8 WAR was a peak in every phase*: career-best baserunning (+8.3) and a defensive spike (+7.6 Def, +9.3 Fld) versus roughly −4 Def in 2022–23. The defense regressed in 2025 — so part of the 2024→2025 WAR drop was glove-related regression, not bat decline, which further softens the 'collapse' framing. (b) *In 2026 the legs are fine*: speed score is still elite (6.8), prorated baserunning (~+6) and fielding (~+8) remain plus. The slump is **entirely the bat** — no injury has been reported, and his athletic foundation (the floor a trade partner is buying) is intact.

## 7. Age-curve context (season age 27→29)

- 2024 wRC+ **131** came at age 27 — his *peak age*, so there is no 'more growth coming' argument.
- A normal age 27→29 curve (delta-method, biased *toward* smaller declines; a speed/contact cohort actually projects roughly flat) predicts only a **7**-point wRC+ dip.
- Actual drop 2024→2026 was **71** points — **64** beyond what aging explains.

> Aging explains almost none of the 2024→2026 fall. The residual is mean-reversion from an inflated peak **plus** 2026's bad-luck tail — not a clean age-decline curve. Aging matters going forward (he's now past peak and his discipline is slipping), but it is not what drove the raw numbers down.

## 8. Will he rebound? A 10,000-run Monte Carlo on the rest of 2026

Rest-of-season (303 PA at his current pace) simulated from a true-talent prior built on 2023–25 xwOBA (PA × 3/4/5 recency weights) plus his +5-pt speed premium — the healthy prior lands at **0.336 wOBA ≈ 110 wRC+**, independently confirming the ~110 plateau. Because §5 shows *real* 2026 process erosion, a second scenario blends 2026's degraded process (xwOBA 0.287) in at 40%. Full model + valuation math in `outputs/rebound_probability.md`; distribution in `figures/09_rebound_probability.png`.

| Quantity | Healthy prior | Erosion-blended |
|----------|--------------:|----------------:|
| P(rest-of-season wRC+ ≥ 100) | **69%** | **47%** |
| P(rest-of-season wRC+ ≥ 110) | 50% | 29% |
| P(full-season 2026 ≥ 90 wRC+) | 27% | 11% |
| Median rest-of-season wRC+ | 110 | 99 |
| Expected offseason trade value | $22M | $18M |

> **Read:** if the 2023–25 player is intact, a league-average-or-better second half is a 69% bet; if the process erosion is ~40% real it is a coin flip (47%) — that 22-point gap is what the eroded chase/whiff/hard-hit rates cost. Either way the full-season line likely stays under 90 wRC+ (the first-half hole is too deep), and either way waiting beats selling at today's ~$10M nadir — so the sim supports hold-through-2026, while lowering confidence in the rebound narrative itself.

## Verdict — with explicit confidence

**Is 2024 statistically distinguishable as an outlier from 2025–26 and from what came before?**
- *On results (wOBA, wRC+, WAR):* **yes** — 2024 is the high point and should not be treated as his true level. **Confidence: high.**
- *On process (xwOBA, contact quality, swing decisions):* **no** — 2024 is continuous with 2023 and 2025; its underlying skill was legitimate. So the specific claim that *2024 was a luck-driven mirage* is **not** well supported. **Confidence that 2024's process was legit: high; confidence that 2024 was 'lucky': low.**

**Which year(s) mislead?**
- **2024 misleads on the high side** (~15–20 pts of wOBA of good fortune on top of a genuine career year).
- **2026 misleads on the low side** (bad BABIP luck stacked on top of real — but smaller — erosion in discipline and hard contact).
- **2025 is the least misleading single season** and the best one-line proxy for current true talent.

**Where the data does *not* support the original framing (stated plainly):** 2024's process metrics — xwOBA, barrel/hard-hit, and especially plate discipline — are legitimately good, and its BABIP is not a significant outlier against his own history. The clean story of '2024 lucky, 2025–26 = true level' does not hold; the truer story is '2023–25 = an above-average true level, with 2024 the lucky top and 2026 the unlucky bottom.'

## Value / trade / roster implications (today)

- **Center his valuation on ~2025 (≈110–120 wRC+, ~2.5–3.5 WAR regular).** Not 2024 (right tail → overpay), not 2026 (left tail, luck-depressed → underpay/sell-low trap).
- **This is closer to a hold / buy-low than a sell.** His trade value is currently *suppressed* by a visibly unlucky 2026 (wOBA < xwOBA); selling now cashes a down year, not a peak. If anything, a rival using xstats will see through the .196 average.
- **The genuine risk to underwrite is the skill erosion, not the batting average.** Rising chase%/whiff% and falling hard-hit% in 2026 are the real age-29 warning signs; his BABIP will regress **up**, but if the underlying skills keep slipping, the plateau moves down a tier.
- **Roster role:** a valuable everyday, speed/defense-supported above-average regular — worth keeping at a fair (non-2024) price, not a cornerstone to extend at star money.
- **What would move the estimate:** a 2026 second-half BABIP rebound (confirms bad luck → hold), or chase/whiff staying elevated into a full 2027 sample (confirms decline → sell). Track **xwOBA, chase%, whiff%** — not batting average.
- **Quantified (§8):** the rebound Monte Carlo puts a league-average-or-better rest of season at **69%** (healthy prior) vs **47%** (erosion-blended), and expected offseason trade value at $22M vs $18M — both above the ~$10M a July sale fetches. Hold-through-2026 survives the erosion stress test.

---
*Method:* rate stats tested with two-proportion z-tests on their natural denominators (BIP, out-of-zone pitches, swings, in-zone swings); xBABIP/xwOBA from Statcast estimated stats, with luck components measured against Duran's own career wOBA−xwOBA gap (Statcast xstats ignore sprint speed, so fast players chronically out-hit them as a skill); BsR/Def/Fld/Spd from FanGraphs. Aging curve is an empirical delta-method curve from 2021–26 FanGraphs data (survivorship-biased toward smaller declines, i.e. conservative). Roughly a dozen significance tests are reported without family-wise correction; isolated p≈.03–.05 results are directional, and n = 6 seasons (2026 partial). Figures in `figures/`, source data in `data/`.