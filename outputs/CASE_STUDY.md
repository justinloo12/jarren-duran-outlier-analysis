# Case Study — Was Jarren Duran's 2024 an Outlier, and What Should Boston Do?

*A baseball-analytics decision project: from a testable thesis, through
Statcast/FanGraphs data, to a trade recommendation. Reproducible end-to-end
(`python run_all.py`).*

---

## TL;DR (the answer first)

I set out to test a specific claim: **Jarren Duran's 2024 All-Star season was a
lucky outlier, and his 2025–26 decline is his true level.** The data says the
thesis is **half right in a more interesting way than the premise assumed**:

- **2024 was his best year and modestly luck-aided — but not a mirage.** His
  underlying process (xwOBA .340, career-best swing decisions) was legitimate,
  and his 2024 BABIP was **not** significantly above his own career norm.
- **His true talent is a 2023–2025 plateau (~110 wRC+, an above-average
  regular)** — 2024 is the lucky top, **2026 is a partly *unlucky* bottom**
  (wOBA .265 below xwOBA .286; BABIP .244 vs .311 xBABIP) stacked on real but
  smaller skill erosion (chase, whiff and hard-hit all worsened significantly).
- **Decision:** don't value him at 2024 (overpay) *or* 2026 (sell-low). He's a
  ~$7.7M, controllable-through-2028 above-average regular blocked by a cheaper,
  younger core — so **trade him in the offseason from surplus, after a value
  rebound**. Because Boston's pitching (a top-10 rotation) is a strength, the
  return should be **controllable bats / young position talent**, not arms.
  Best-fit buyers: **Phillies, Rays**.

The most valuable thing I did was **let the data overturn my own framing** and
say so explicitly.

---

## 1. The question

The Red Sox have a real decision: is Duran a 6-WAR star having bad luck, or a
solid regular who got hot in 2024? The answer drives whether you extend him,
trade him, or build around him — and it's entangled with a roster logjam. A good
analysis has to separate **process** (did he actually hit the ball better?) from
**results** (did more balls fall in?), and be honest when the evidence cuts
against the headline.

## 2. Data & method

| Source | Used for |
|--------|----------|
| **Statcast** (pybaseball, pitch-level) | process metrics: xwOBA, barrel%, hard-hit%, chase/whiff/zone-contact, xBABIP |
| **FanGraphs API** (direct JSON) | season wOBA/wRC+/WAR/BABIP + league & OF frames |
| **MLB Stats API** | MLB + minor-league track record; 2026 standings |
| **Spotrac** (manual, web) | 2026 salaries/contracts |

**Method choices that matter (and the honesty behind them):**
- With only 6 seasons (one partial), I did **not** run an outlier test on six
  points. I treated each season's rate stats as estimates with **binomial
  standard error** on the correct denominator and ran two-proportion tests
  (2024 vs. a pooled *rest-of-career-minus-2024* baseline).
- Separated **results vs. process** everywhere (wOBA−xwOBA, BABIP−xBABIP).
- Built an **empirical delta-method aging curve** from the league data —
  survivorship-biased toward *smaller* declines, i.e. deliberately conservative.
- Salary has no free API, so figures are manually sourced with an as-of date and
  a re-verify caveat; unverifiable numbers were omitted, not guessed.

## 3. Findings (the analytical journey)

**a) Results outran process in 2024 — but only marginally, once you credit
his legs.** wOBA .357 vs xwOBA .340 (+17 pts); Savant agrees. But Statcast
xstats ignore sprint speed, and Duran's own non-2024 baseline is **+6 pts**
of wOBA over xwOBA (infield hits, stretched doubles — skill, not luck).
Against that personal norm, 2024's luck component is only **~+11 pts** —
enough to shave a ~130 wRC+ toward the low-120s, not enough to call it a
fluke. The same adjustment makes 2026 (raw −21 pts) a **−27-pt anomaly**
against his own norm — *more* unlucky, not less.
→ *[fig 02: wOBA vs xwOBA](../figures/02_woba_vs_xwoba.png)*

**b) The BABIP-luck story — the thesis's core — is weak.**
2024 BABIP .344 is **not** significantly above his own baseline (p=0.33) and
only +11 pts over his contact-quality xBABIP. He's a genuine high-BABIP
speed/contact hitter. The *big* BABIP anomaly is 2026's unsustainably low .244.
→ *[fig 01: BABIP vs league & xBABIP](../figures/01_babip_vs_league.png)*

**c) The real 2024 signal was skill, not luck: swing decisions.**
His best chase% and whiff% came in 2024, and that approach gain persisted into
2025. It **eroded in 2026** — the one genuine warning sign.
→ *[fig 03: plate-discipline trend](../figures/03_plate_discipline_trend.png)*

**d) Aging explains almost none of the drop.**
2024→2026 wRC+ fell ~70 points; a normal age 27→29 curve predicts ~7. The
residual is mean-reversion from an inflated peak **plus** a 2026 bad-luck tail.
→ *[fig 04: age-curve overlay](../figures/04_age_curve_overlay.png)*

**e) 2024 was a peak in every phase — and in 2026 the legs are fine.**
His 6.8 WAR rode career-best baserunning (+8.3 BsR) and a defensive spike
(+7.6 Def vs ~−4 in 2022–23) that regressed in 2025 — so part of the
2024→2025 WAR drop was glove regression, not bat decline. In 2026 his speed
score (6.8), prorated baserunning (~+6) and fielding (~+8) remain plus, and
no injury has been reported: the slump is entirely the bat, while the
athletic floor a trade partner would be buying is intact.

## 4. From analysis to decision

**Peer & market context.** In 2026 Duran ($7.7M) is the Red Sox' lowest-
producing regular OF at its second-highest OF salary, behind cheaper, younger
Abreu ($0.8M), Rafaela ($2.0M), and Anthony ($130M extension). Yoshida ($18.6M)
is the cautionary expensive-decline comp.
→ *[figs 05–06](../figures/06_salary_vs_output_scatter.png)* · *[peer memo](peer_and_salary_memo.md)*

**The outfield jam & the fix.** The jam is currently *masked* by Roman Anthony's
60-day IL stint, so it's really a **2027 problem**. Keep the cheap core, trade
Duran in the **offseason** (not at the 2026 deadline, when his value is
luck-depressed and the injury makes Boston need his bat), and **absorb** the
Yoshida contract.
→ *[fig 07](../figures/07_outfield_plan.png)* · *[outfield plan](outfield_plan.md)*

**Trade value & partners.** ~$10–15M of prospect value if sold at the nadir (a
45-FV bat) vs. ~$28M if sold after a rebound (a 50-FV, back-end top-100 bat) —
the one-grade jump that justifies waiting. Best-fit partners = contenders with
weak outfields: **Phillies, Rays, Marlins, Guardians.**
→ *[fig 08](../figures/08_trade_fit_targets.png)* · *[trade targets](trade_targets.md)*

## 5. Confidence & limitations

- **High confidence:** 2024 is an outlier *on results*; his true talent is
  clearly below it; aging doesn't explain the fall.
- **Lower confidence:** whether 2026's discipline erosion is real decline or
  noise (small partial-season sample) — this is the key open question.
- Luck components are measured against Duran's **own** career wOBA−xwOBA gap
  (+6 pts), since Statcast xstats ignore sprint speed and fast players beat
  them chronically as a skill — comparing to zero would overstate 2024's luck
  and understate 2026's.
- **Park factors:** wRC+ (the headline talent metric) is park-adjusted by
  construction. The luck analysis was additionally verified by venue: his
  career wOBA−xwOBA gap is +20 at Fenway vs +22 on the road — identical, so
  the overperformance is a speed skill, not a Green Monster artifact. 2024's
  gap was road-concentrated (+50 vs +14), the opposite of a park fluke.
- Roughly a dozen significance tests are reported without family-wise
  correction; isolated p≈.03–.05 results are directional. The whiff/chase
  findings are the only ones robust enough to survive a correction.
- Salary/standings are a July-2026 snapshot; the $8M/WAR market rate and
  prospect FV-to-dollar conversions follow FanGraphs' dollars-per-WAR and
  prospect-valuation research (Craig Edwards) — ballparks meant to rank
  decisions, not set asking prices.

## 6. What I'd do next

- Add a proper Marcel/ZiPS-style projection and monthly 2026 splits to test the
  "rebound vs. decline" question directly.
- Pull real org-specific top-prospect lists to name concrete return packages.
- Re-run at the deadline and in the offseason (standings/needs shift weekly).

## 7. Reproduce

```bash
pip install -r ../requirements.txt
python ../run_all.py            # full pipeline (or --no-fetch to reuse CSVs)
```

Artifacts: `data/` (CSVs + JSON), `figures/` (8 PNGs), `outputs/` (4 memos +
this case study). Module map is in the [README](../README.md).

## 8. Skills demonstrated

Data acquisition & API wrangling (routing around a deprecated FanGraphs
endpoint) · Statcast/sabermetric feature engineering with proper denominators ·
hypothesis testing on small samples · **intellectual honesty (overturning the
starting thesis)** · translating analysis into a business/roster decision with
explicit confidence · reproducible, modular project design · data visualization.
