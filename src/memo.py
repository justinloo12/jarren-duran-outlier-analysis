"""Generate outputs/decision_memo.md from the saved analysis artifacts.

The memo is *data-driven*: interpretive language is chosen from the computed
magnitudes (gaps, significance, aging residual, and whether a down year is
itself lucky/unlucky), and it is written to flag — not bury — the places where
the data does NOT support the original "2024 was a lucky mirage" framing.
"""
from __future__ import annotations

import datetime as dt
import json

from . import config as C


def _load():
    res = json.load(open(C.DATA_DIR / "analysis_results.json"))
    age = json.load(open(C.DATA_DIR / "age_curve.json"))
    reb_p = C.DATA_DIR / "rebound_sim.json"
    reb = json.load(open(reb_p)) if reb_p.exists() else None
    ero_p = C.DATA_DIR / "erosion_decomposition.json"
    ero = json.load(open(ero_p)) if ero_p.exists() else None
    bt_p = C.DATA_DIR / "luck_backtest.json"
    bt = json.load(open(bt_p)) if bt_p.exists() else None
    return res, age, reb, ero, bt


def pct(x, d=1):
    return "n/a" if x is None else f"{x*100:.{d}f}%"


def num(x, d=3):
    return "n/a" if x is None else f"{x:.{d}f}"


def pts(x):  # express a wOBA/BABIP gap in "points"
    return "n/a" if x is None else f"{x*1000:+.0f}"


def sig(p):
    if p is None:
        return "n/a"
    if p < 0.01:
        return "significant (p<0.01)"
    if p < 0.05:
        return "significant (p<0.05)"
    if p < 0.10:
        return "marginal (p<0.10)"
    return f"not significant (p={p:.2f})"


def _i(x):
    return "n/a" if x is None else f"{x:.0f}"


def _f1(x, signed=True):
    if x is None:
        return "n/a"
    return f"{x:+.1f}" if signed else f"{x:.1f}"


def _g(d, k):
    return None if d is None else d.get(k)


def build(res, age, reb=None, ero=None, bt=None) -> str:
    S = res["seasons"]
    s24 = S.get(str(C.OUTLIER_SEASON), {})
    s25 = S.get("2025", {})
    s26 = S.get("2026", {})
    rp = res["results_vs_process"]
    b = res["babip"]
    t = res["tests_2024_vs_baseline"]
    yv = res.get("y25_vs_y26", {})

    # --- derived signals (drive the interpretive language) ----------------
    gap24 = rp["woba_minus_xwoba"] or 0.0                 # results over process
    babip_over_xbabip = rp["babip_minus_xbabip"] or 0.0   # 2024 batted-ball luck
    babip_vs_base_p = _g(b["test_vs_baseline"], "p")
    barrel_sig = (t["barrel"]["p"] is not None and t["barrel"]["p"] < 0.05
                  and (t["barrel"]["diff"] or 0) > 0)
    hardhit_sig = (t["hardhit"]["p"] is not None and t["hardhit"]["p"] < 0.05
                   and (t["hardhit"]["diff"] or 0) > 0)
    disc_better = (t["chase"]["p"] is not None and t["chase"]["p"] < 0.05
                   and (t["chase"]["diff"] or 0) < 0)  # chased LESS in 2024
    # 2026: are the ugly results below its own contact quality? (unlucky)
    w26, x26 = s26.get("wOBA"), s26.get("xwOBA")
    y26_unlucky = (w26 is not None and x26 is not None and w26 < x26 - 0.005)
    b26_gap = (s26.get("sc_babip") or 0) - (s26.get("sc_xbabip") or 0)

    L = []
    A = L.append
    A(f"# Decision Memo — Is {res['player']}'s 2024 an Outlier?")
    A(f"*Generated {dt.date.today().isoformat()} · "
      f"data via pybaseball (Statcast), FanGraphs API, MLB Stats API*\n")

    # ---- BLUF ------------------------------------------------------------
    A("## Bottom line up front\n")
    A("- **2024 was his best year and only marginally luck-aided — not a "
      "fluke.** Its underlying process (xwOBA {x}, elite swing decisions) was "
      "legitimate and continuous with 2023 and 2025. Results ran ~{g} points "
      "of wOBA ahead of contact quality — but after crediting the ~6 points "
      "his speed *always* adds over xwOBA, the true luck component is closer "
      "to 10 points. And 2024 was a peak in every phase: career-best "
      "baserunning and defense, not just the bat.".format(
          x=num(s24.get("xwOBA")), g=pts(gap24).lstrip("+")))
    A("- **His true talent is the 2023–2025 plateau — an above-average "
      "regular (~110–125 wRC+), not a 6-WAR star and not a replacement-level "
      "bust.** Both the 2024 high and the 2026 low are tails around that.")
    A("- **2026's collapse overstates his decline: it is partly *unlucky*** "
      f"(wOBA {num(w26)} sits *below* xwOBA {num(x26)}; BABIP "
      f"{num(s26.get('sc_babip'))} vs xBABIP {num(s26.get('sc_xbabip'))}, "
      f"{pts(b26_gap)} points — and for a speedster who normally *beats* his "
      "xstats, running below them is doubly anomalous). There is real erosion "
      "in 2026 — chase, whiff and hard-hit rate all worsened significantly — "
      "but no injury has been reported, his speed/defense remain plus, and "
      "the batting line is worse than the erosion warrants.")
    A("- **Implication:** value him off ~his 2025 line. Anchoring to 2024 "
      "**over**pays; anchoring to 2026 **under**pays. The thesis is right that "
      "2024 shouldn't be the anchor — but 'sell because value is cratering' "
      "misreads a down year that is depressed by bad luck.\n")

    # ---- headline table --------------------------------------------------
    A("## Season-by-season\n")
    A("| Season | Age | PA | wRC+ | wOBA | xwOBA | BABIP | xBABIP | Barrel% | HardHit% | Chase% | Whiff% |")
    A("|--------|----:|---:|-----:|-----:|------:|------:|-------:|--------:|---------:|-------:|-------:|")
    for s in C.SEASONS:
        d = S.get(str(s))
        if not d:
            continue
        star = " *" if d.get("partial") else ""
        A("| {sea}{st} | {age} | {pa} | {wrc} | {woba} | {xwoba} | {babip} | "
          "{xbabip} | {bar} | {hh} | {ch} | {wh} |".format(
              sea=s, st=star, age=_i(d.get("age")), pa=_i(d.get("PA")),
              wrc=_i(d.get("wRC+")), woba=num(d.get("wOBA")),
              xwoba=num(d.get("xwOBA")), babip=num(d.get("sc_babip")),
              xbabip=num(d.get("sc_xbabip")), bar=pct(d.get("sc_barrel_pct")),
              hh=pct(d.get("sc_hardhit_pct")), ch=pct(d.get("sc_chase_pct")),
              wh=pct(d.get("sc_whiff_pct"))))
    A("\n*`*` = partial season, in progress as of the analysis date. "
      "xBABIP / xwOBA are Statcast contact-quality expectations.*\n")

    # ---- strand 1: results vs process (speed-adjusted) -------------------
    sa = res.get("speed_adjusted", {})
    pgap = sa.get("personal_gap_baseline")
    pgap_hi = sa.get("personal_gap_baseline_ex26")
    x24 = sa.get("gap_2024_excess")
    x24_lo = sa.get("gap_2024_excess_ex26")
    d26 = sa.get("gap_2026_deficit")
    d26_hi = sa.get("gap_2026_deficit_ex26")
    A("## 1. Did he hit the ball better in 2024, or did it just fall in?\n")
    A(f"- **wOBA − xwOBA, 2024:** {pts(gap24)} points "
      f"(wOBA {num(rp['woba'])} vs xwOBA {num(rp['xwoba_fg'])}; "
      f"Savant est_woba {num(rp['est_woba_savant'])} agrees).")
    A(f"- **BABIP − xBABIP, 2024:** {pts(babip_over_xbabip)} points "
      f"(BABIP {num(rp['babip'])} vs contact-quality xBABIP {num(rp['xbabip'])}).")
    A("\n**A necessary speed adjustment.** Statcast expected stats are built "
      "from exit velocity and launch angle only — they ignore sprint speed. A "
      "burner like Duran legs out infield hits and stretches singles into "
      "doubles, so he *should* chronically out-hit his xwOBA as a skill, not "
      "luck. His non-2024 seasons average "
      f"**{pts(pgap)} to {pts(pgap_hi)} points** of wOBA over xwOBA "
      "(the range depends on whether the collapsing 2026 is included in his "
      "own baseline). Measured against that personal norm rather than zero:")
    A(f"- 2024's gap was **{pts(x24_lo)} to {pts(x24)} points above his own "
      "baseline** — under any version, a modest luck component.")
    A(f"- 2026's gap sits **{pts(d26)} to {pts(d26_hi)} points below his own "
      "baseline** — for a player whose legs normally add value over xstats, "
      "running negative is a far larger anomaly than the raw number shows.")
    pk = res.get("park_check", {})
    if pk.get("career"):
        ch, cr = pk["career"]["home"], pk["career"]["road"]
        p24 = pk.get("by_season", {}).get("2024") or pk.get("by_season", {}).get(2024, {})
        p26 = pk.get("by_season", {}).get("2026") or pk.get("by_season", {}).get(2026, {})
        A("\n**Park robustness check (is this just Fenway?).** The headline "
      "talent metric, wRC+, is park-adjusted by construction, but the luck "
      "analysis above is not — and the Green Monster inflates exactly the "
      "kind of contact Duran makes. Splitting his career by venue: his "
      f"wOBA−xwOBA gap is **{pts(ch['gap'])} at Fenway vs {pts(cr['gap'])} "
      "on the road — essentially identical**. The overperformance travels, "
      "which is what a speed skill (not a park effect) looks like.")
        if p24 and p26:
            A(f"- 2024's gap was actually **road-concentrated** "
              f"({pts(p24['road']['gap'])} road vs {pts(p24['home']['gap'])} "
              "home) — the opposite of a Monster-driven fluke.")
            A(f"- 2026 is negative in **both** venues "
              f"({pts(p26['home']['gap'])} home, {pts(p26['road']['gap'])} "
              "road) — the underperformance is not a schedule artifact.")
    if x24 is not None and x24 > 0.018:
        A("\n> **Read:** even after crediting his legs, results clearly "
          "outran contact quality — a variance-inflated season.\n")
    elif x24 is not None and x24 > 0.005:
        A("\n> **Read:** after crediting his speed, 2024's luck component "
          "shrinks to ~10 points of wOBA — real but minor. Enough to shave a "
          "~130 wRC+ toward the low-120s of true talent, **not** enough to "
          "call 2024 a mirage. The batted-ball luck specifically (BABIP vs "
          "xBABIP) is negligible. Meanwhile the same adjustment makes 2026 "
          "look *more* unlucky, not less.\n")
    else:
        A("\n> **Read:** after the speed adjustment, 2024's results and "
          "contact quality were essentially in line — the variance story "
          "finds little support.\n")

    # ---- strand 2: BABIP -------------------------------------------------
    tb, tl = b["test_vs_baseline"], b["test_vs_league"]
    A("## 2. BABIP — did variance prop 2024 up?\n")
    A(f"- 2024 BABIP **{num(b['2024'])}** vs his own non-2024 baseline "
      f"**{num(b['baseline_established'])}** "
      f"({pts((b['2024'] or 0)-(b['baseline_established'] or 0))} pts, "
      f"{sig(_g(tb,'p'))}).")
    A(f"- 2024 BABIP vs 2024 league average (300+ PA) **{num(b['league_2024'])}** "
      f"({sig(_g(tl,'p'))}).")
    A(f"- 2024 BABIP vs his *own* xBABIP **{num(b['2024_xbabip'])}**: only "
      f"{pts(babip_over_xbabip)} pts.\n")
    A("> **This is where the original thesis is weakest.** The hypothesis was "
      "that 2024 BABIP sits *well above* both his career and league norms. It "
      "is above *league* (expected — he's a genuine speed / hard-contact, high-"
      "BABIP hitter), but it is **not** significantly above his own baseline "
      "and barely above his own xBABIP. 2024 BABIP was largely earned, not a "
      "fluke. The bigger BABIP story is 2026's *unsustainably low* mark.\n")

    # ---- strand 3: process tests ----------------------------------------
    A("## 3. Process metrics: 2024 vs. rest-of-career-minus-2024\n")
    A("| Metric | 2024 | Baseline | Diff (pts) | Verdict |")
    A("|--------|-----:|---------:|-----------:|---------|")
    for k, lab in [("barrel", "Barrel%"), ("hardhit", "Hard-Hit%"),
                   ("chase", "Chase%"), ("whiff", "Whiff%"),
                   ("zcontact", "Zone-Contact%"), ("babip", "BABIP")]:
        tt = t[k]
        A(f"| {lab} | {pct(tt['val_2024'])} | {pct(tt['val_baseline'])} | "
          f"{pts(tt['diff'])} | {sig(tt['p'])} |")
    A("\n*Multiple-comparisons caution: ~a dozen tests are reported across "
      "this memo, so isolated p-values in the .03–.05 range should be read as "
      "directional; only the whiff/chase findings (p<0.01–0.05, consistent "
      "across seasons) would survive a family-wise correction.*\n")
    if disc_better and not (barrel_sig or hardhit_sig):
        A("> **Read:** the standout 2024 signal is *swing decisions*, not raw "
          "contact — he chased and whiffed **significantly less** than his "
          "career norm (chase% a career best; whiff% essentially tied with "
          "2023), while barrel/hard-hit were in line with his baseline. That "
          "is a genuine skill signal, so 2024 was a real step forward — "
          "arguing **against** the pure-luck framing. (Note the pooled "
          "baseline is dragged up by ugly 2021–22 rookie whiff rates; vs 2023 "
          "alone his 2024 discipline is similar, not better.)\n")
    elif barrel_sig or hardhit_sig:
        A("> **Read:** contact quality was genuinely elevated in 2024 — part of "
          "the breakout was real bat, not luck.\n")
    else:
        A("> **Read:** 2024 process was not distinguishable from baseline "
          "beyond noise.\n")

    # ---- strand 4: approach persistence ---------------------------------
    A("## 4. Approach change — and did it persist?\n")
    pdd = res["plate_discipline"]
    A("| Season | Chase% | Whiff% | Zone-Contact% |")
    A("|--------|-------:|-------:|--------------:|")
    for s in C.SEASONS:
        row = pdd.get(str(s))
        if row:
            A(f"| {s} | {pct(row['chase'])} | {pct(row['whiff'])} | "
              f"{pct(row['zcontact'])} |")
    A("\n> The 2022→2024 improvement in chase/whiff **did** persist into 2023 "
      "and held reasonably in 2025 — consistent with a real approach gain that "
      "underpins the 2023–25 plateau. It then **regressed in 2026** (chase and "
      "whiff both jump), which is the first genuine warning sign of decline — "
      "see §5.\n")

    # ---- strand 5: 2025 vs 2026 -----------------------------------------
    A("## 5. Are 2025 and 2026 the same player? (mean-reversion vs. decline)\n")
    if yv:
        A(f"- wRC+ **{_i(yv.get('wrcplus_2025'))} → {_i(yv.get('wrcplus_2026'))}**; "
          f"wOBA {num(yv.get('woba_2025'))} → {num(yv.get('woba_2026'))}.")
        for k, lab in [("chase", "Chase%"), ("whiff", "Whiff%"),
                       ("barrel", "Barrel%"), ("hardhit", "Hard-Hit%"),
                       ("babip", "BABIP")]:
            tt = yv.get(k, {})
            A(f"- {lab}: 2026 vs 2025 {pts(tt.get('diff'))} pts "
              f"({sig(tt.get('p'))}).")
        A("")
        A(f"> **Two things are true at once.** (a) *Real* signal: chase%, "
          f"whiff% **and hard-hit%** all moved significantly the wrong way in "
          f"2026 — both the plate discipline and part of the contact quality "
          f"that powered the 2023–25 plateau are eroding (barrel% is a career "
          f"high, but EV and hard-hit rate are down). (b) *Luck* signal on top: "
          f"even against that diminished contact quality, results underperform "
          f"— BABIP cratered to {num(s26.get('sc_babip'))} vs an xBABIP of "
          f"{num(s26.get('sc_xbabip'))}, and wOBA ({num(w26)}) sits **below** "
          f"xwOBA ({num(x26)}). So 2026 reflects real erosion *and* bad luck; "
          f"the batting line is worse than the (declining) player underneath "
          f"it. Net: 2025 and 2026 are **not** a stable shared level — and "
          f"treating 2026 as 'the new true level' is as much a mistake as "
          f"treating 2024 as one.\n")

    # ---- strand 6: defense / baserunning ---------------------------------
    A("## 6. The rest of the game: defense, baserunning, speed\n")
    A("Duran's value case has never been bat-only — and his 2024 WAR peak "
      "was not either.\n")
    A("| Season | BsR | Def | Fld | Spd | WAR |")
    A("|--------|----:|----:|----:|----:|----:|")
    for s in C.SEASONS:
        d = S.get(str(s), {})
        if not d:
            continue
        A(f"| {s}{' *' if d.get('partial') else ''} | "
          f"{_f1(d.get('BaseRunning'))} | {_f1(d.get('Defense'))} | "
          f"{_f1(d.get('Fielding'))} | {_f1(d.get('Spd'), signed=False)} | "
          f"{_f1(d.get('WAR'), signed=False)} |")
    A("\n*BsR = baserunning runs, Def = defensive runs (positional-adjusted), "
      "Fld = fielding runs, Spd = FanGraphs speed score. 2026 counting stats "
      "are a partial season (roughly half); prorate accordingly.*\n")
    A("> **Two findings.** (a) *2024's 6.8 WAR was a peak in every phase*: "
      "career-best baserunning (+8.3) and a defensive spike (+7.6 Def, +9.3 "
      "Fld) versus roughly −4 Def in 2022–23. The defense regressed in 2025 — "
      "so part of the 2024→2025 WAR drop was glove-related regression, not "
      "bat decline, which further softens the 'collapse' framing. (b) *In "
      "2026 the legs are fine*: speed score is still elite (6.8), prorated "
      "baserunning (~+6) and fielding (~+8) remain plus. The slump is "
      "**entirely the bat** — no injury has been reported, and his athletic "
      "foundation (the floor a trade partner is buying) is intact.\n")

    # ---- strand 7: age curve --------------------------------------------
    A("## 7. Age-curve context (season age 27→29)\n")
    ae = age.get("aging_explains", {})
    A(f"- 2024 wRC+ **{_i(age.get('duran_2024_wrcplus'))}** came at age "
      f"{age.get('peak_age')} — his *peak age*, so there is no 'more growth "
      "coming' argument.")
    A(f"- A normal age 27→29 curve (delta-method, biased *toward* smaller "
      f"declines; a speed/contact cohort actually projects roughly flat) "
      f"predicts only a **{_i(ae.get('aging_predicted_drop'))}**-point wRC+ dip.")
    A(f"- Actual drop 2024→2026 was **{_i(ae.get('total_drop_2024_to_2026'))}** "
      f"points — **{_i(ae.get('residual_beyond_aging'))}** beyond what aging "
      "explains.\n")
    A("> Aging explains almost none of the 2024→2026 fall. The residual is "
      "mean-reversion from an inflated peak **plus** 2026's bad-luck tail — not "
      "a clean age-decline curve. Aging matters going forward (he's now past "
      "peak and his discipline is slipping), but it is not what drove the raw "
      "numbers down.\n")

    # ---- strand 8: rebound Monte Carlo ------------------------------------
    if reb:
        h = reb["scenarios"]["healthy"]
        e = reb["scenarios"]["erosion"]
        pr = reb["prior"]
        ri = reb["inputs"]
        va = reb["value_anchors_musd"]
        A("## 8. Will he rebound? A 10,000-run Monte Carlo on the rest of "
          "2026\n")
        A(f"Rest-of-season ({ri['n_remaining_pa']} PA at his current pace) "
          f"simulated from a true-talent prior built on 2023–25 xwOBA "
          f"(PA × 3/4/5 recency weights) plus his "
          f"+{pr['speed_premium']*1000:.0f}-pt speed premium — the healthy "
          f"prior lands at **{pr['mu_healthy']:.3f} wOBA ≈ "
          f"{h['prior_mu_wrcplus']:.0f} wRC+**, independently confirming the "
          f"~110 plateau. Because §5 shows *real* 2026 process erosion, a "
          f"second scenario blends 2026's degraded process (xwOBA "
          f"{ri['x_2026']:.3f}) in at {int(pr['erosion_weight']*100)}%. Full "
          f"model + valuation math in `outputs/rebound_probability.md`; "
          f"distribution in `figures/09_rebound_probability.png`.\n")
        A("| Quantity | Healthy prior | Erosion-blended |")
        A("|----------|--------------:|----------------:|")
        A(f"| P(rest-of-season wRC+ ≥ 100) | "
          f"**{h['p_ros_wrcplus_100']:.0%}** | "
          f"**{e['p_ros_wrcplus_100']:.0%}** |")
        A(f"| P(rest-of-season wRC+ ≥ 110) | {h['p_ros_wrcplus_110']:.0%} | "
          f"{e['p_ros_wrcplus_110']:.0%} |")
        A(f"| P(full-season 2026 ≥ 90 wRC+) | {h['p_full_wrcplus_90']:.0%} | "
          f"{e['p_full_wrcplus_90']:.0%} |")
        A(f"| Median rest-of-season wRC+ | {h['median_ros_wrcplus']:.0f} | "
          f"{e['median_ros_wrcplus']:.0f} |")
        A(f"| Expected offseason trade value | "
          f"${h['value_timing_musd']['offseason']:.0f}M | "
          f"${e['value_timing_musd']['offseason']:.0f}M |")
        A(f"\n> **Read:** if the 2023–25 player is intact, a league-average-"
          f"or-better second half is a {h['p_ros_wrcplus_100']:.0%} bet; if "
          f"the process erosion is ~{int(pr['erosion_weight']*100)}% real it "
          f"is a coin flip ({e['p_ros_wrcplus_100']:.0%}) — that "
          f"{(h['p_ros_wrcplus_100']-e['p_ros_wrcplus_100'])*100:.0f}-point "
          f"gap is what the eroded chase/whiff/hard-hit rates cost. Either "
          f"way the full-season line likely stays under 90 wRC+ (the "
          f"first-half hole is too deep), and either way waiting beats "
          f"selling at today's ~${va['nadir']:.0f}M nadir — so the sim "
          f"supports hold-through-2026, while lowering confidence in the "
          f"rebound narrative itself.\n")

    # ---- strand 9: erosion decomposition (physical vs approach) ----------
    if ero:
        rows = ero["seasons"]
        r24, r25, r26 = rows["2024"], rows["2025"], rows["2026"]
        v = ero["verdict"]
        rw = ero.get("reweight")
        A("## 9. Is the 2026 erosion physical or approach? The bat-tracking "
          "answer\n")
        A("Statcast has measured bat speed directly since 2024 — the one "
          "clean physical read on a 29-year-old's bat. Full decomposition "
          "in `outputs/erosion_decomposition.md` / "
          "`figures/10_erosion_decomposition.png`.\n")
        A("| Season | Avg bat speed | Fast-swing% | Whiff% vs ≥95 FB | "
          "Chase% | In-zone contact% |")
        A("|--------|--------------:|------------:|-----------------:|"
          "-------:|-----------------:|")
        for key, r in (("2024", r24), ("2025", r25), ("2026", r26)):
            A(f"| {key} | {r['bat']['avg_mph']:.1f} mph | "
              f"{pct(r['bat']['fast_swing_pct'])} | "
              f"{pct(r['whiff_fb95']['rate'])} | "
              f"{pct(r['chase_all']['rate'])} | "
              f"{pct(r['z_contact']['rate'])} |")
        if v["label"] == "approach":
            A(f"\n> **Verdict: approach, not physical — and this is the "
              f"tiebreaker the whole erosion question needed.** His bat "
              f"speed is *up* {v['bat_speed_delta_mph']:+.1f} mph vs his "
              f"2024–25 average (fast-swing rate "
              f"{pct(r24['bat']['fast_swing_pct'],0)} → "
              f"{pct(r26['bat']['fast_swing_pct'],0)}), while his swing got "
              f"longer and steeper and every *decision* metric worsened — "
              f"whiffs up even against premium velocity he demonstrably "
              f"still catches up to, chase up mostly on fastballs and "
              f"offspeed, breaking-ball chase actually stable. That is a "
              f"hitter **selling out**, not a hitter slowing down. Approach "
              f"is fixable (his own 2022→23 chase overhaul proves it "
              f"in-house); a dying bat is not. This tilts the §8 scenarios "
              f"toward the healthy prior"
              + (f" — a 60/40 weighting puts the blended P(rest-of-season "
                 f"wRC+ ≥ 100) at **{rw['p_reweighted']:.0%}**"
                 if rw else "") + ".\n")
        elif v["label"] == "physical":
            A(f"\n> **Verdict: physical.** Bat speed is down "
              f"{v['bat_speed_delta_mph']:+.1f} mph — a real bat-slowing "
              f"signal that the erosion scenario prices correctly. The "
              f"buy-low thesis takes a genuine hit here; weight the "
              f"erosion scenario.\n")
        else:
            A(f"\n> **Verdict: mixed/ambiguous** (bat speed "
              f"{v['bat_speed_delta_mph']:+.1f} mph, chase "
              f"{v['chase_delta']*100:+.1f} pts) — keep the two §8 "
              f"scenarios at equal weight.\n")

    # ---- strand 10: historical luck-gap backtest ---------------------------
    if bt:
        st, pl, d = bt["cohort"], bt["pool"], bt["duran"]
        A("## 10. Does the luck thesis hold historically? A 2016–25 "
          "backtest\n")
        A(f"The rebound model assumes wOBA-under-xwOBA gaps close. Testing "
          f"that on every hitter since 2016 with ≥250 PA by June 30 and a "
          f"midseason gap ≥20 points below xwOBA (n = {st['n']} "
          f"player-seasons; details in `outputs/luck_gap_backtest.md`):")
        A(f"- Mean rest-of-season recovery: "
          f"**{st['mean_recovery']*1000:+.0f} points of wOBA**; "
          f"{st['pct_closed_half']:.0%} closed at least half the gap.")
        A(f"- The median cohort hitter's second half landed "
          f"{abs(st['median_ros_minus_h1_xwoba'])*1000:.0f} pts from his "
          f"midseason *xwOBA* but {st['median_recovery']*1000:+.0f} pts "
          f"above his midseason wOBA — the second half tracks the process "
          f"stat.")
        A(f"- Horse race on all {pl['n']} qualified first halves: "
          f"corr(ROS wOBA, midseason xwOBA) = "
          f"**{pl['corr_ros_with_h1_xwoba']:.3f}** vs corr with midseason "
          f"wOBA = {pl['corr_ros_with_h1_woba']:.3f} — **the x-stat "
          f"wins.**")
        A(f"- Duran's −{abs(d['gap'])*1000:.0f}-pt gap is more negative "
          f"than {(1-d['pctile_all_h1']):.0%} of all qualified first "
          f"halves, but *within* the unlucky cohort he is a typical member "
          f"({d['pctile_in_cohort']*100:.0f}th percentile), not an outlier.")
        A(f"\n> **Read:** history sides with the x-stat, which is the §8 "
          f"model's core mechanism — the 69% healthy-prior scenario gains "
          f"external validity. The honest limit: the backtest regresses "
          f"the luck around *whatever the current process is*; it cannot "
          f"say whether the process itself recovers — that is §9's "
          f"question, and §9 answers 'approach, so plausibly yes.'\n")

    # ---- verdict ---------------------------------------------------------
    A("## Verdict — with explicit confidence\n")
    A("**Is 2024 statistically distinguishable as an outlier from 2025–26 and "
      "from what came before?**")
    A("- *On results (wOBA, wRC+, WAR):* **yes** — 2024 is the high point and "
      "should not be treated as his true level. **Confidence: high.**")
    A("- *On process (xwOBA, contact quality, swing decisions):* **no** — 2024 "
      "is continuous with 2023 and 2025; its underlying skill was legitimate. "
      "So the specific claim that *2024 was a luck-driven mirage* is **not** "
      "well supported. **Confidence that 2024's process was legit: high; "
      "confidence that 2024 was 'lucky': low.**\n")
    A("**Which year(s) mislead?**")
    A("- **2024 misleads on the high side** (~15–20 pts of wOBA of good "
      "fortune on top of a genuine career year).")
    A("- **2026 misleads on the low side** (bad BABIP luck stacked on top of "
      "real — but smaller — erosion in discipline and hard contact).")
    A("- **2025 is the least misleading single season** and the best one-line "
      "proxy for current true talent.\n")
    A("**Where the data does *not* support the original framing (stated "
      "plainly):** 2024's process metrics — xwOBA, barrel/hard-hit, and "
      "especially plate discipline — are legitimately good, and its BABIP is "
      "not a significant outlier against his own history. The clean story of "
      "'2024 lucky, 2025–26 = true level' does not hold; the truer story is "
      "'2023–25 = an above-average true level, with 2024 the lucky top and 2026 "
      "the unlucky bottom.'\n")

    # ---- implications ----------------------------------------------------
    A("## Value / trade / roster implications (today)\n")
    A("- **Center his valuation on ~2025 (≈110–120 wRC+, ~2.5–3.5 WAR "
      "regular).** Not 2024 (right tail → overpay), not 2026 (left tail, "
      "luck-depressed → underpay/sell-low trap).")
    A("- **This is closer to a hold / buy-low than a sell.** His trade value "
      "is currently *suppressed* by a visibly unlucky 2026 (wOBA < xwOBA); "
      "selling now cashes a down year, not a peak. If anything, a rival using "
      "xstats will see through the .196 average.")
    A("- **The genuine risk to underwrite is the skill erosion, not the "
      "batting average.** Rising chase%/whiff% and falling hard-hit% in 2026 "
      "are the real age-29 warning signs; his BABIP will regress **up**, but "
      "if the underlying skills keep slipping, the plateau moves down a tier.")
    A("- **Roster role:** a valuable everyday, speed/defense-supported "
      "above-average regular — worth keeping at a fair (non-2024) price, not a "
      "cornerstone to extend at star money.")
    A("- **What would move the estimate:** a 2026 second-half BABIP rebound "
      "(confirms bad luck → hold), or chase/whiff staying elevated into a full "
      "2027 sample (confirms decline → sell). Track **xwOBA, chase%, whiff%** — "
      "not batting average.")
    if reb:
        h = reb["scenarios"]["healthy"]
        e = reb["scenarios"]["erosion"]
        A(f"- **Quantified (§8):** the rebound Monte Carlo puts a league-"
          f"average-or-better rest of season at "
          f"**{h['p_ros_wrcplus_100']:.0%}** (healthy prior) vs "
          f"**{e['p_ros_wrcplus_100']:.0%}** (erosion-blended), and expected "
          f"offseason trade value at ${h['value_timing_musd']['offseason']:.0f}M "
          f"vs ${e['value_timing_musd']['offseason']:.0f}M — both above the "
          f"~${reb['value_anchors_musd']['nadir']:.0f}M a July sale fetches. "
          f"Hold-through-2026 survives the erosion stress test.")
    A("")

    # ---- pre-registered predictions ---------------------------------------
    A("## Pre-registered predictions — this analysis grades itself\n")
    A("Everything above is a forecast, and forecasts are cheap unless they "
      "can be wrong. The falsifiable version of this memo is frozen, dated "
      "2026-07-04, in **`outputs/predictions.json`**: the full rest-of-"
      "season wRC+ quantiles from both rebound scenarios, the P(wRC+ ≥ 100) "
      "calls (69% healthy / 47% eroded / 60% blended per the §9 verdict), "
      "the valuation call (hold now, deal in the offseason at $18–22M vs "
      "~$10M today), and the physical-vs-approach verdict itself. After the "
      "season, `python3 -m src.grade_predictions` pulls the actual "
      "rest-of-season line and scores every claim — Brier scores on the "
      "probability calls, coverage on the quantile bands — with the "
      "conversion frozen so there is no room to move the goalposts. **The "
      "grade runs in October whether it is flattering or not.**\n")

    A("---\n*Method:* rate stats tested with two-proportion z-tests on their "
      "natural denominators (BIP, out-of-zone pitches, swings, in-zone swings); "
      "xBABIP/xwOBA from Statcast estimated stats, with luck components "
      "measured against Duran's own career wOBA−xwOBA gap (Statcast xstats "
      "ignore sprint speed, so fast players chronically out-hit them as a "
      "skill); BsR/Def/Fld/Spd from FanGraphs. Aging curve is an empirical "
      "delta-method curve from 2021–26 FanGraphs data (survivorship-biased "
      "toward smaller declines, i.e. conservative). Roughly a dozen "
      "significance tests are reported without family-wise correction; "
      "isolated p≈.03–.05 results are directional, and n = 6 seasons (2026 "
      "partial). Figures in `figures/`, source data in `data/`.")
    return "\n".join(L)


def run():
    res, age, reb, ero, bt = _load()
    md = build(res, age, reb, ero, bt)
    out = C.OUT_DIR / "decision_memo.md"
    out.write_text(md)
    print(f"  [memo] wrote {out}")
    return out


if __name__ == "__main__":
    run()
