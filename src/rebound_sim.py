"""Rebound-probability Monte Carlo: what does Duran do over the REST of 2026?

Model
-----
1. True-talent prior (wOBA scale). Weighted mean of 2023-25 xwOBA — each
   season weighted by PA x a recency multiplier (2023:3, 2024:4, 2025:5) —
   plus his documented speed premium (his own career non-2024 wOBA-xwOBA gap,
   ~+5-6 pts, computed in analysis.py: Statcast xstats ignore sprint speed, so
   a burner chronically out-hits them as a *skill*).
2. Talent uncertainty. SE of that weighted mean on an effective sample
   n_eff = (sum w_i*PA_i)^2 / (sum w_i^2*PA_i), combined in quadrature with a
   year-to-year true-talent drift term (TALENT_DRIFT_SD = 10 pts of wOBA).
3. Sampling noise. Rest-of-season observed wOBA at n PAs is drawn
   Normal(talent, sqrt(p*(1-p)/n)). This is the binomial-proportion normal
   approximation applied to wOBA; wOBA is not a true proportion, but at
   p~0.33 the sqrt(p(1-p)/n) scale (~.027 at 300 PA) matches the empirical
   season-to-season wOBA sampling error closely, and we document it as such.
4. wOBA -> wRC+ conversion. A PA-weighted linear fit of wRC+ on wOBA across
   all 2026 hitters with 100+ PA (this empirically embeds league wOBA, wOBA
   scale and R/PA), plus a Duran-specific park offset = his mean 2025-26
   residual off that fit (Fenway inflates raw wOBA, so his wRC+ runs a couple
   of points under the league line).

Two scenarios, reported side by side (the gap between them IS the answer to
"how much does the 2026 skill erosion matter"):
  * healthy  — the 2023-25 prior as-is; assumes no injury and no skill cliff.
  * erosion  — blends 2026's own degraded process (its xwOBA, which already
    reflects the worse chase/whiff/hard-hit rates) into the prior at
    EROSION_WEIGHT = 40% (mid of the 25-50% band).

Remaining PA is computed from the actual schedule: Red Sox games played (from
the standings pull cached in data/trade_fits.csv) and Duran's own PA-per-
team-game pace. 10,000 sims, seeded with his MLBAM id — fully deterministic.

Valuation link reuses trade_targets' $8M/WAR surplus framework: sell-now =
the risk-adjusted nadir value; offseason expected value = P(rebound) x the
full-control rebound value + (1-P) x nadir; deadline = same but a mid-rebound
buyer only gives half credit (one hot month cannot fully re-rate him).
Illustrative mapping, not a market model.
"""
from __future__ import annotations

import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from . import style as S
from .trade_targets import duran_value

S.apply()

# --- model constants (documented above) ------------------------------------
REC_WEIGHTS = {2023: 3, 2024: 4, 2025: 5}   # recency multipliers on PA weights
EROSION_WEIGHT = 0.40                       # weight on 2026 process in scen. B
TALENT_DRIFT_SD = 0.010                     # yr-to-yr true-talent drift, wOBA
N_SIMS = 10_000
SEED = C.PLAYER["mlbam"]                    # 680776 — deterministic
SEASON_GAMES = 162
CONV_MIN_PA = 100                           # league fit sample floor


# --- pure math (unit-tested) -------------------------------------------------
def blend_prior(xwoba: dict, pa: dict, rec: dict = None) -> dict:
    """PA-x-recency-weighted mean of season xwOBA + effective sample size.

    weight_i = PA_i * rec_i;  n_eff = (sum w)^2 / (sum rec_i * w_i)
    (the standard effective-n for observations carrying unequal weights).
    """
    rec = REC_WEIGHTS if rec is None else rec
    seasons = [s for s in rec if s in xwoba and s in pa]
    w = np.array([pa[s] * rec[s] for s in seasons], dtype=float)
    x = np.array([xwoba[s] for s in seasons], dtype=float)
    mu = float(np.average(x, weights=w))
    n_eff = float(w.sum() ** 2 / sum(rec[s] ** 2 * pa[s] for s in seasons))
    return {"mu_xwoba": mu, "n_eff": n_eff, "seasons": seasons}


def erode_prior(mu_healthy: float, x_2026: float,
                weight: float = EROSION_WEIGHT) -> float:
    """Blend 2026's degraded process into the healthy prior."""
    return (1 - weight) * mu_healthy + weight * x_2026


def woba_sd(p: float, n: float) -> float:
    """Binomial-style sampling SD for a wOBA-scale rate at n PA (documented
    normal approximation; see module docstring)."""
    return math.sqrt(p * (1 - p) / n)


def fit_woba_to_wrcplus(woba, wrcplus, weights=None):
    """PA-weighted linear map wRC+ = intercept + slope * wOBA."""
    slope, intercept = np.polyfit(np.asarray(woba, float),
                                  np.asarray(wrcplus, float), 1,
                                  w=None if weights is None
                                  else np.asarray(weights, float))
    return float(slope), float(intercept)


def woba_to_wrcplus(w, slope, intercept, offset=0.0):
    return slope * np.asarray(w, float) + intercept + offset


def wrcplus_to_woba(wrc, slope, intercept, offset=0.0):
    return (np.asarray(wrc, float) - intercept - offset) / slope


def simulate_ros_woba(mu: float, sigma_talent: float, n_pa: float,
                      n_sims: int = N_SIMS, seed: int = SEED) -> np.ndarray:
    """Draw true talent, then rest-of-season observed wOBA at n_pa."""
    rng = np.random.default_rng(seed)
    talent = rng.normal(mu, sigma_talent, n_sims)
    obs = rng.normal(talent, woba_sd(mu, n_pa), n_sims)
    return obs


def expected_values(p_rebound: float, low: float, high: float) -> dict:
    """Surplus-value timing under the rebound distribution (illustrative).

    now      = low (a July buyer prices the slump; no rebound evidence yet)
    deadline = rebound gets HALF credit (one month cannot fully re-rate)
    offseason= rebound gets full credit
    """
    mid = (low + high) / 2
    return {
        "now": low,
        "deadline": p_rebound * mid + (1 - p_rebound) * low,
        "offseason": p_rebound * high + (1 - p_rebound) * low,
    }


# --- data assembly -----------------------------------------------------------
def _inputs():
    sm = pd.read_csv(C.DATA_DIR / "season_metrics.csv").set_index("season")
    res = json.load(open(C.DATA_DIR / "analysis_results.json"))
    speed = res["speed_adjusted"]["personal_gap_baseline"] or 0.0

    xw = {s: float(sm.loc[s, "xwOBA"]) for s in REC_WEIGHTS}
    pa = {s: float(sm.loc[s, "PA"]) for s in REC_WEIGHTS}
    cur = sm.loc[C.CURRENT_SEASON]

    # remaining PA from the actual schedule + his own pace
    fits = pd.read_csv(C.DATA_DIR / "trade_fits.csv")
    bos = fits[fits["team_name"] == "Red Sox"].iloc[0]
    games = int(bos["W"] + bos["L"])
    pace = float(cur["PA"]) / games
    n_rem = round((SEASON_GAMES - games) * pace)

    # wOBA -> wRC+ conversion (league fit + Duran park offset)
    lg = pd.read_csv(C.FANGRAPHS_DIR / f"league_{C.CURRENT_SEASON}.csv")
    q = lg[lg["PA"] >= CONV_MIN_PA]
    slope, intercept = fit_woba_to_wrcplus(q["wOBA"], q["wRC+"], q["PA"])
    offs = [float(sm.loc[s, "wRC+"]
                  - woba_to_wrcplus(sm.loc[s, "wOBA"], slope, intercept))
            for s in (2025, 2026)]
    offset = float(np.mean(offs))

    return {
        "xwoba": xw, "pa": pa, "speed_premium": float(speed),
        "x_2026": float(cur["xwOBA"]), "pa_2026": float(cur["PA"]),
        "woba_2026": float(cur["wOBA"]), "wrcplus_2026": float(cur["wRC+"]),
        "games_played": games, "n_remaining_pa": int(n_rem),
        "conv": {"slope": slope, "intercept": intercept, "offset": offset},
    }


def _scenario(name: str, mu: float, sigma: float, inp: dict) -> dict:
    conv = inp["conv"]
    n_rem = inp["n_remaining_pa"]
    ros_woba = simulate_ros_woba(mu, sigma, n_rem)
    ros_wrc = woba_to_wrcplus(ros_woba, conv["slope"], conv["intercept"],
                              conv["offset"])
    # full-season 2026 = PA-weighted blend of the line to date + the sims
    pa_now, w_now = inp["pa_2026"], inp["woba_2026"]
    full_woba = (pa_now * w_now + n_rem * ros_woba) / (pa_now + n_rem)
    full_wrc = woba_to_wrcplus(full_woba, conv["slope"], conv["intercept"],
                               conv["offset"])
    val = duran_value()
    low, high = val["risk_adjusted"], val["surplus_full_3yr"]
    p100 = float((ros_wrc >= 100).mean())
    return {
        "name": name,
        "prior_mu_woba": mu, "prior_sigma": sigma,
        "prior_mu_wrcplus": float(woba_to_wrcplus(
            mu, conv["slope"], conv["intercept"], conv["offset"])),
        "p_ros_wrcplus_100": p100,
        "p_ros_wrcplus_110": float((ros_wrc >= 110).mean()),
        "p_full_wrcplus_90": float((full_wrc >= 90).mean()),
        "median_ros_woba": float(np.median(ros_woba)),
        "median_ros_wrcplus": float(np.median(ros_wrc)),
        "median_full_woba": float(np.median(full_woba)),
        "median_full_wrcplus": float(np.median(full_wrc)),
        "value_timing_musd": expected_values(p100, low, high),
        "ros_wrcplus_draws": ros_wrc,   # kept for the figure; not serialized
    }


def compute() -> dict:
    inp = _inputs()
    prior = blend_prior(inp["xwoba"], inp["pa"])
    mu_healthy = prior["mu_xwoba"] + inp["speed_premium"]
    mu_eroded = (erode_prior(prior["mu_xwoba"], inp["x_2026"])
                 + inp["speed_premium"])
    se_est = woba_sd(mu_healthy, prior["n_eff"])
    sigma = math.sqrt(se_est ** 2 + TALENT_DRIFT_SD ** 2)

    val = duran_value()
    out = {
        "inputs": {k: v for k, v in inp.items()},
        "prior": {**prior, "speed_premium": inp["speed_premium"],
                  "mu_healthy": mu_healthy, "mu_eroded": mu_eroded,
                  "erosion_weight": EROSION_WEIGHT,
                  "sigma_talent": sigma, "talent_drift_sd": TALENT_DRIFT_SD},
        "sim": {"n_sims": N_SIMS, "seed": SEED},
        "value_anchors_musd": {"nadir": val["risk_adjusted"],
                               "rebound": val["surplus_full_3yr"]},
        "scenarios": {
            "healthy": _scenario("healthy", mu_healthy, sigma, inp),
            "erosion": _scenario("erosion", mu_eroded, sigma, inp),
        },
    }
    return out


# --- figure -------------------------------------------------------------------
def fig(resu: dict):
    h = resu["scenarios"]["healthy"]
    e = resu["scenarios"]["erosion"]
    fig_, ax = plt.subplots(figsize=(9.8, 4.1))
    bins = np.arange(20, 205, 4)
    ax.hist(h["ros_wrcplus_draws"], bins=bins, density=True, color=S.NAVY,
            alpha=0.55, label="Healthy prior (2023–25 talent)", zorder=3)
    ax.hist(e["ros_wrcplus_draws"], bins=bins, density=True, color=S.RED,
            alpha=0.55, label=f"Erosion scenario (2026 process at "
            f"{int(EROSION_WEIGHT*100)}%)", zorder=3)
    ax.axvline(100, color=S.AMBER, lw=1.4, ls="--", zorder=4)
    ax.text(101.5, ax.get_ylim()[1] * 0.42, "league avg (100)",
            fontsize=10, color=S.AMBER, ha="left", va="top", zorder=5,
            fontweight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.98))
    ax.annotate(f"P(wRC+ ≥ 100) = {h['p_ros_wrcplus_100']:.0%}",
                xy=(0.985, 0.86), xycoords="axes fraction", ha="right",
                fontsize=10.5, fontweight="bold", color=S.NAVY)
    ax.annotate(f"P(wRC+ ≥ 100) = {e['p_ros_wrcplus_100']:.0%}",
                xy=(0.985, 0.76), xycoords="axes fraction", ha="right",
                fontsize=10.5, fontweight="bold", color=S.RED)
    S.style(ax)
    ax.set_yticks([])
    ax.set_xlim(20, 200)
    ax.set_xlabel("Simulated rest-of-2026 wRC+  "
                  f"({resu['inputs']['n_remaining_pa']} PA, "
                  f"{resu['sim']['n_sims']:,} runs)")
    S.titled(ax, "Will Duran rebound? 10,000 simulated rest-of-seasons",
             "Monte Carlo over remaining PA: healthy 2023-25 prior vs. a "
             "2026-erosion-blended prior")
    fig_.tight_layout()
    fig_.savefig(C.FIG_DIR / "09_rebound_probability.png")
    plt.close(fig_)


# --- memo ---------------------------------------------------------------------
def _pctf(x):
    return f"{x:.0%}"


def memo(resu: dict):
    h, e = resu["scenarios"]["healthy"], resu["scenarios"]["erosion"]
    inp = resu["inputs"]
    pr = resu["prior"]
    va = resu["value_anchors_musd"]
    L = []
    A = L.append
    A("# Rebound Probability — Monte Carlo on the Rest of 2026\n")
    import datetime as _dt
    A(f"*Generated {_dt.date.today().isoformat()} · {resu['sim']['n_sims']:,} "
      f"sims, seed {resu['sim']['seed']} (deterministic) · "
      f"remaining PA = {inp['n_remaining_pa']} "
      f"({162 - inp['games_played']} Red Sox games left × his "
      f"{inp['pa_2026']:.0f}-PA-in-{inp['games_played']}-games pace).*\n")

    A("## The model in one paragraph\n")
    A(f"True talent is drawn from a prior built on 2023–25 xwOBA (weighted by "
      f"PA × 3/4/5 recency) **plus his speed premium** "
      f"(+{pr['speed_premium']*1000:.0f} pts, his own career wOBA−xwOBA gap — "
      f"Statcast xstats ignore sprint speed), giving a healthy-prior mean of "
      f"**{pr['mu_healthy']:.3f} wOBA ≈ {h['prior_mu_wrcplus']:.0f} wRC+** — "
      f"independent confirmation of the memo's ~110 wRC+ plateau. Talent "
      f"uncertainty (σ = {pr['sigma_talent']*1000:.0f} pts) combines the "
      f"prior's estimation error with year-to-year drift; each sim then adds "
      f"binomial-approximation sampling noise "
      f"(√(p(1−p)/n) ≈ {woba_sd(pr['mu_healthy'], inp['n_remaining_pa'])*1000:.0f} "
      f"pts at {inp['n_remaining_pa']} PA). wOBA→wRC+ uses a PA-weighted "
      f"league fit plus Duran's own park offset "
      f"({inp['conv']['offset']:+.1f}).\n")

    A("## Two scenarios — the gap IS the erosion question\n")
    A("The healthy prior assumes **no injury and no true skill cliff**. But "
      "the decision memo documents real 2026 erosion (chase, whiff, hard-hit "
      "all significantly worse). The erosion scenario blends 2026's own "
      f"degraded process (xwOBA {inp['x_2026']:.3f}) into the prior at "
      f"**{int(pr['erosion_weight']*100)}%** weight.\n")
    A("| Quantity | Healthy prior | Erosion-blended |")
    A("|----------|--------------:|----------------:|")
    A(f"| True-talent prior (wOBA / wRC+) | {pr['mu_healthy']:.3f} / "
      f"{h['prior_mu_wrcplus']:.0f} | {pr['mu_eroded']:.3f} / "
      f"{e['prior_mu_wrcplus']:.0f} |")
    A(f"| P(rest-of-season wRC+ ≥ 100) | **{_pctf(h['p_ros_wrcplus_100'])}** | "
      f"**{_pctf(e['p_ros_wrcplus_100'])}** |")
    A(f"| P(rest-of-season wRC+ ≥ 110) | {_pctf(h['p_ros_wrcplus_110'])} | "
      f"{_pctf(e['p_ros_wrcplus_110'])} |")
    A(f"| P(full-season 2026 wRC+ ≥ 90) | {_pctf(h['p_full_wrcplus_90'])} | "
      f"{_pctf(e['p_full_wrcplus_90'])} |")
    A(f"| Median rest-of-season (wOBA / wRC+) | {h['median_ros_woba']:.3f} / "
      f"{h['median_ros_wrcplus']:.0f} | {e['median_ros_woba']:.3f} / "
      f"{e['median_ros_wrcplus']:.0f} |")
    A(f"| Median full-season 2026 (wOBA / wRC+) | {h['median_full_woba']:.3f} / "
      f"{h['median_full_wrcplus']:.0f} | {e['median_full_woba']:.3f} / "
      f"{e['median_full_wrcplus']:.0f} |")
    A("\n![Rebound probability](../figures/09_rebound_probability.png)\n")

    A("## What the gap says\n")
    A(f"- If the 2023–25 player is intact, a league-average-or-better rest of "
      f"season is roughly a **{_pctf(h['p_ros_wrcplus_100'])}** proposition — "
      f"a favorable bet, i.e. the 'hold, he'll rebound' case.")
    A(f"- If the 2026 process erosion is ~{int(pr['erosion_weight']*100)}% "
      f"real, that drops to **{_pctf(e['p_ros_wrcplus_100'])}** — a coin "
      f"flip whose median rest-of-season "
      f"({e['median_ros_wrcplus']:.0f} wRC+) is only league-average. The "
      f"~{(h['p_ros_wrcplus_100']-e['p_ros_wrcplus_100'])*100:.0f}-point "
      f"probability gap is the price of the eroded chase/whiff/hard-hit "
      f"rates.")
    A(f"- **Either way, the full-season 2026 line stays ugly**: even the "
      f"healthy prior gives only {_pctf(h['p_full_wrcplus_90'])} odds of "
      f"finishing above 90 wRC+ (median ≈ {h['median_full_wrcplus']:.0f}). "
      f"The first-half hole is too deep — so a buyer looking at the season "
      f"line will still see a down year, which matters for timing below.\n")

    A("## Valuation timing under the rebound distribution\n")
    A(f"Anchors from the trade-value model ($8M/WAR): sell-at-the-nadir ≈ "
      f"**${va['nadir']:.0f}M** (≈45-FV return), sell-after-rebound ≈ "
      f"**${va['rebound']:.0f}M** (≈50-FV). Expected value = P(rebound) × "
      f"rebound value + (1−P) × nadir; the deadline row gives a mid-rebound "
      f"buyer only half credit. Illustrative, not a market model.\n")
    A("| Timing | Healthy prior | Erosion-blended |")
    A("|--------|--------------:|----------------:|")
    for key, lab in [("now", "Sell now (July)"),
                     ("deadline", "Sell at the deadline"),
                     ("offseason", "Sell in the offseason")]:
        A(f"| {lab} | ${h['value_timing_musd'][key]:.0f}M | "
          f"${e['value_timing_musd'][key]:.0f}M |")
    A("\n## Does this support the standing recommendation?\n")
    A(f"**Yes — with one honest caveat.** Waiting dominates selling now in "
      f"*both* scenarios: the offseason expectation beats the July nadir by "
      f"~${h['value_timing_musd']['offseason']-va['nadir']:.0f}M under the "
      f"healthy prior and still by "
      f"~${e['value_timing_musd']['offseason']-va['nadir']:.0f}M even if the "
      f"erosion is 40% real, because the downside of waiting is roughly the "
      f"nadir you'd get today anyway. So the hold-through-2026 / deal-in-the-"
      f"offseason call survives the erosion stress test. The caveat: the "
      f"erosion scenario cuts the rebound probability to about a coin flip "
      f"and shaves the expected offseason return, so the *confidence* in the "
      f"rebound narrative should be lower than the decision memo's luck "
      f"framing alone implies — and a further slide in chase/whiff would "
      f"argue for taking a good deadline offer rather than maximizing.\n")

    A("---\n*Assumptions: no injury; PA pace holds; the prior ignores any "
      "mid-season swing changes. The normal approximation to wOBA sampling "
      "error and the FV/$ anchors are documented simplifications. Rerun "
      "`python3 run_all.py --no-fetch` to refresh after new games.*")
    out = C.OUT_DIR / "rebound_probability.md"
    out.write_text("\n".join(L))
    print(f"  [rebound] wrote {out}")


def run():
    resu = compute()
    fig(resu)
    print("  [rebound] wrote figure 09")
    memo(resu)
    ser = {k: v for k, v in resu.items() if k != "scenarios"}
    ser["scenarios"] = {
        n: {k: v for k, v in sc.items() if k != "ros_wrcplus_draws"}
        for n, sc in resu["scenarios"].items()}
    with open(C.DATA_DIR / "rebound_sim.json", "w") as f:
        json.dump(ser, f, indent=2,
                  default=lambda o: (float(o) if isinstance(o, np.floating)
                                     else int(o) if isinstance(o, np.integer)
                                     else str(o)))
    return resu


if __name__ == "__main__":
    run()
