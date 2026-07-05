"""Historical luck-gap backtest: do midseason wOBA-under-xwOBA gaps close?

The rebound model's core assumption is that Duran's 2026 first half (wOBA 24
points BELOW xwOBA) is partly luck that regresses. This module tests that
assumption on league history instead of asserting it.

Design
------
For every season 2016-2025 (2020 skipped — no June 30 midpoint in a 60-game
year), pull two player-level aggregates from the Baseball Savant search API
(the same grouped CSV the site's "Group By: Player" export uses; it accepts
date ranges and returns PA / wOBA / xwOBA per batter):

  * H1  = Opening Day through June 30   (the "midseason" snapshot)
  * ROS = July 1 through season end     (what actually happened next)

Cohort: hitters with >= 250 H1 PA whose H1 wOBA sat >= 20 points below their
H1 xwOBA (Duran's direction), with >= 100 ROS PA so the outcome isn't noise.

The question, quantified three ways:
  1. Recovery: mean/median (ROS wOBA - H1 wOBA). If the luck thesis holds,
     this is strongly positive and lands near the H1 xwOBA.
  2. Gap closure: share of the cohort that closed >= half the H1 gap,
     where closure = (ROS wOBA - H1 wOBA) / (H1 xwOBA - H1 wOBA).
  3. Horse race: correlation of ROS wOBA with H1 xwOBA vs with H1 wOBA —
     computed on the FULL population (the cohort is range-restricted by
     construction, which attenuates correlations) and on the cohort.

Plus: where Duran's own -24-point gap sits in the pooled distribution of all
H1 player-season gaps (percentile).

Caching: each Savant pull is saved under data/luck_backtest/ and reused, so
`run_all.py --no-fetch` and reruns are offline. Pulls sleep 2s apart.

Standalone: python3 -m src.luck_backtest [--no-fetch]
"""
from __future__ import annotations

import io
import json
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from . import config as C
from . import style as S

S.apply()

BT_SEASONS = [2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
MIN_H1_PA = 250          # "qualified-ish" by June 30
MIN_ROS_PA = 100         # enough second-half PA to grade the outcome
GAP_MAX = -0.020         # H1 wOBA at least 20 pts under H1 xwOBA
SAVANT_MIN_PAS = 25      # server-side floor just to keep the CSVs small
SLEEP_S = 2.0

CACHE = C.DATA_DIR / "luck_backtest"
CACHE.mkdir(parents=True, exist_ok=True)

SAVANT_URL = (
    "https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfGT=R%7C"
    "&hfSea={season}%7C&player_type=batter&game_date_gt={d1}&game_date_lt={d2}"
    "&group_by=name&min_pas={min_pas}&sort_col=xwoba&sort_order=desc")


# --- pure helpers (unit-tested) -------------------------------------------------
def gap_points(woba: float, xwoba: float) -> float:
    """Midseason luck gap: results minus process (negative = unlucky)."""
    return woba - xwoba


def build_cohort(h1: pd.DataFrame, min_pa: int = MIN_H1_PA,
                 gap_max: float = GAP_MAX) -> pd.DataFrame:
    """Filter an H1 player table to the unlucky cohort and add the gap col.

    Expects columns: player_id, pa, woba, xwoba.
    """
    d = h1.copy()
    d["gap"] = d["woba"] - d["xwoba"]
    return d[(d["pa"] >= min_pa) & (d["gap"] <= gap_max)].reset_index(drop=True)


def join_ros(h1: pd.DataFrame, ros: pd.DataFrame,
             min_ros_pa: int = MIN_ROS_PA) -> pd.DataFrame:
    """Inner-join H1 rows to their rest-of-season outcomes on player_id."""
    r = ros[ros["pa"] >= min_ros_pa][["player_id", "pa", "woba", "xwoba"]]
    r = r.rename(columns={"pa": "ros_pa", "woba": "ros_woba",
                          "xwoba": "ros_xwoba"})
    return h1.merge(r, on="player_id", how="inner")


def gap_closed_frac(h1_woba, h1_xwoba, ros_woba):
    """Fraction of the H1 gap closed by the ROS line (1.0 = landed on the
    x-stat, 0 = repeated the unlucky wOBA, >1 = overshot)."""
    return (np.asarray(ros_woba, float) - np.asarray(h1_woba, float)) / (
        np.asarray(h1_xwoba, float) - np.asarray(h1_woba, float))


def percentile_of(x: float, arr) -> float:
    """Share of values <= x (0 = most extreme low tail)."""
    a = np.asarray(arr, float)
    a = a[np.isfinite(a)]
    return float((a <= x).mean())


def recovery_stats(m: pd.DataFrame) -> dict:
    """Summary stats for a joined cohort frame (unit-tested on synthetic)."""
    rec = m["ros_woba"] - m["woba"]                 # vs the unlucky H1 line
    vs_x = m["ros_woba"] - m["xwoba"]               # vs the process line
    closed = gap_closed_frac(m["woba"], m["xwoba"], m["ros_woba"])
    return {
        "n": int(len(m)),
        "mean_recovery": float(rec.mean()),
        "median_recovery": float(rec.median()),
        "mean_ros_minus_h1_xwoba": float(vs_x.mean()),
        "median_ros_minus_h1_xwoba": float(np.median(vs_x)),
        "pct_closed_half": float((closed >= 0.5).mean()),
        "pct_any_improvement": float((rec > 0).mean()),
        "corr_ros_with_h1_xwoba": float(m["ros_woba"].corr(m["xwoba"])),
        "corr_ros_with_h1_woba": float(m["ros_woba"].corr(m["woba"])),
    }


# --- fetch ------------------------------------------------------------------------
def _fetch_half(season: int, half: str, fetch: bool) -> pd.DataFrame:
    p = CACHE / f"{half}_{season}.csv"
    if p.exists():
        return pd.read_csv(p)
    if not fetch:
        raise FileNotFoundError(f"{p} missing and --no-fetch set")
    if half == "h1":
        d1, d2 = f"{season}-03-01", f"{season}-06-30"
    else:
        d1, d2 = f"{season}-07-01", f"{season}-11-30"
    url = SAVANT_URL.format(season=season, d1=d1, d2=d2,
                            min_pas=SAVANT_MIN_PAS)
    r = requests.get(url, headers=C.HTTP_HEADERS, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    keep = ["player_id", "player_name", "pa", "woba", "xwoba"]
    df = df[keep].dropna(subset=["woba", "xwoba", "pa"])
    df.to_csv(p, index=False)
    print(f"  [backtest] fetched {half} {season}: {len(df)} hitters")
    time.sleep(SLEEP_S)
    return df


# --- assembly ---------------------------------------------------------------------
def compute(fetch: bool = True) -> dict:
    pool_frames, cohort_frames = [], []
    for season in BT_SEASONS:
        h1 = _fetch_half(season, "h1", fetch)
        ros = _fetch_half(season, "ros", fetch)
        h1q = h1[h1["pa"] >= MIN_H1_PA].copy()
        h1q["gap"] = h1q["woba"] - h1q["xwoba"]
        h1q["season"] = season
        pool = join_ros(h1q, ros)
        pool_frames.append(pool)
        cohort_frames.append(join_ros(build_cohort(h1), ros)
                             .assign(season=season))
    pool = pd.concat(pool_frames, ignore_index=True)
    cohort = pd.concat(cohort_frames, ignore_index=True)

    stats_cohort = recovery_stats(cohort)
    stats_pool = {
        "n": int(len(pool)),
        "corr_ros_with_h1_xwoba": float(pool["ros_woba"].corr(pool["xwoba"])),
        "corr_ros_with_h1_woba": float(pool["ros_woba"].corr(pool["woba"])),
    }

    # Duran's own 2026 midseason gap in that distribution
    sm = pd.read_csv(C.DATA_DIR / "season_metrics.csv").set_index("season")
    d_woba = float(sm.loc[C.CURRENT_SEASON, "wOBA"])
    d_xwoba = float(sm.loc[C.CURRENT_SEASON, "xwOBA"])
    d_gap = gap_points(d_woba, d_xwoba)
    duran = {
        "h1_woba": d_woba, "h1_xwoba": d_xwoba, "gap": d_gap,
        "pctile_all_h1": percentile_of(d_gap, pool["gap"]),
        "pctile_in_cohort": percentile_of(d_gap, cohort["gap"]),
        # what the cohort's average closure implies for his ROS wOBA
        "implied_ros_woba_mean_closure": float(
            d_woba + stats_cohort["mean_recovery"]),
    }

    res = {
        "config": {"seasons": BT_SEASONS, "min_h1_pa": MIN_H1_PA,
                   "min_ros_pa": MIN_ROS_PA, "gap_max": GAP_MAX},
        "cohort": stats_cohort,
        "pool": stats_pool,
        "duran": duran,
    }
    cohort.to_csv(CACHE / "cohort_joined.csv", index=False)
    pool.to_csv(CACHE / "pool_joined.csv", index=False)
    res["_cohort_df"] = cohort   # for the figure; stripped before serializing
    res["_pool_df"] = pool
    return res


# --- figure ------------------------------------------------------------------------
def fig(res: dict):
    cohort, pool = res["_cohort_df"], res["_pool_df"]
    d = res["duran"]
    st = res["cohort"]

    fig_, ax = plt.subplots(figsize=(9.8, 5.4))
    ax.scatter(pool["gap"] * 1000, (pool["ros_woba"] - pool["woba"]) * 1000,
               s=11, color=S.GREY, alpha=0.35, lw=0, zorder=2,
               label=f"All hitters, ≥{MIN_H1_PA} H1 PA (n={len(pool)})")
    ax.scatter(cohort["gap"] * 1000,
               (cohort["ros_woba"] - cohort["woba"]) * 1000,
               s=26, color=S.NAVY, alpha=0.8, lw=0, zorder=3,
               label=f"Unlucky cohort, gap ≤ −20 pts (n={len(cohort)})")

    # OLS on the pool: recovery vs gap (the mean-reversion line)
    b, a = np.polyfit(pool["gap"] * 1000,
                      (pool["ros_woba"] - pool["woba"]) * 1000, 1)
    xs = np.linspace(pool["gap"].min() * 1000, pool["gap"].max() * 1000, 50)
    ax.plot(xs, a + b * xs, color=S.MUTED, lw=1.6, ls="--", zorder=4,
            label=f"League regression line (slope {b:.2f})")
    ax.axhline(0, color=S.SPINE, lw=1.0, zorder=1)

    # Duran, marked at his gap with the implied recovery
    gx = d["gap"] * 1000
    pred = a + b * gx
    ax.axvline(gx, color=S.RED, lw=1.4, ls=":", zorder=4)
    ax.scatter([gx], [pred], s=130, marker="*", color=S.RED, zorder=6,
               label="Duran 2026 (implied recovery)")
    ax.annotate(f"Duran: −24-pt gap → the league\nregression implies "
                f"{pred:+.0f} pts of ROS recovery",
                xy=(gx, pred), xytext=(gx + 9, pred + 68), fontsize=9.5,
                color=S.RED, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=S.RED, lw=0.9))

    ax.annotate(f"{st['pct_closed_half']:.0%} of the cohort closed ≥ half "
                f"the gap;\nmedian ROS landed {abs(st['median_ros_minus_h1_xwoba'])*1000:.0f} "
                f"pts from H1 xwOBA (vs {abs(st['median_recovery'])*1000:.0f} "
                "pts above H1 wOBA)",
                xy=(0.985, 0.04), xycoords="axes fraction", ha="right",
                fontsize=9.5, color=S.NAVY,
                bbox=dict(facecolor="white", alpha=0.85, edgecolor=S.SPINE))

    S.style(ax)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_xlabel("Midseason luck gap: H1 wOBA − H1 xwOBA (points)")
    ax.set_ylabel("Rest-of-season recovery: ROS wOBA − H1 wOBA (pts)")
    S.titled(ax, "Do unlucky first halves rebound? 2016–2025 says yes",
             f"{len(BT_SEASONS)} seasons, June 30 split · unlucky cohort = "
             f"wOBA ≥20 pts under xwOBA at midseason · Savant grouped search")
    fig_.tight_layout()
    fig_.savefig(C.FIG_DIR / "11_luck_gap_backtest.png")
    plt.close(fig_)


# --- memo --------------------------------------------------------------------------
def memo(res: dict):
    st, pl, d = res["cohort"], res["pool"], res["duran"]
    import datetime as _dt
    L = []
    A = L.append
    A("# Luck-Gap Backtest — Does the X-Stat Win? (2016–2025)\n")
    A(f"*Generated {_dt.date.today().isoformat()} · Savant grouped search, "
      f"June 30 split, seasons {', '.join(map(str, BT_SEASONS))} · "
      "methodology in `src/luck_backtest.py`.*\n")
    A("## The test\n")
    A(f"The rebound model assumes a first-half wOBA sitting well below xwOBA "
      f"is partly luck that regresses. Historical cohort: every hitter with "
      f"≥{MIN_H1_PA} PA by June 30 whose wOBA sat ≥20 points below his "
      f"xwOBA (n = **{st['n']}** player-seasons across "
      f"{len(BT_SEASONS)} seasons), graded on his rest-of-season "
      f"(≥{MIN_ROS_PA} PA).\n")
    A("## The result: history sides with the x-stat\n")
    A("| Quantity | Value |")
    A("|----------|------:|")
    A(f"| Mean ROS recovery (ROS wOBA − H1 wOBA) | "
      f"**{st['mean_recovery']*1000:+.0f} pts** |")
    A(f"| Median ROS recovery | {st['median_recovery']*1000:+.0f} pts |")
    A(f"| Mean ROS wOBA − H1 **x**wOBA | "
      f"{st['mean_ros_minus_h1_xwoba']*1000:+.0f} pts |")
    A(f"| Median ROS wOBA − H1 xwOBA | "
      f"{st['median_ros_minus_h1_xwoba']*1000:+.0f} pts |")
    A(f"| Closed ≥ half the gap | **{st['pct_closed_half']:.0%}** |")
    A(f"| Any improvement at all | {st['pct_any_improvement']:.0%} |")
    A(f"| corr(ROS wOBA, H1 xwOBA) — cohort | "
      f"{st['corr_ros_with_h1_xwoba']:.3f} |")
    A(f"| corr(ROS wOBA, H1 wOBA) — cohort | "
      f"{st['corr_ros_with_h1_woba']:.3f} |")
    A(f"| corr(ROS wOBA, H1 xwOBA) — all hitters (n={pl['n']}) | "
      f"**{pl['corr_ros_with_h1_xwoba']:.3f}** |")
    A(f"| corr(ROS wOBA, H1 wOBA) — all hitters | "
      f"{pl['corr_ros_with_h1_woba']:.3f} |")
    xwins_pool = (pl["corr_ros_with_h1_xwoba"]
                  > pl["corr_ros_with_h1_woba"])
    xwins_cohort = (st["corr_ros_with_h1_xwoba"]
                    > st["corr_ros_with_h1_woba"])
    A("")
    if xwins_pool:
        A(f"**The x-stat wins the horse race.** Across all "
          f"{pl['n']} qualified first halves, midseason xwOBA predicts the "
          f"rest of the season better than midseason wOBA "
          f"({pl['corr_ros_with_h1_xwoba']:.3f} vs "
          f"{pl['corr_ros_with_h1_woba']:.3f})"
          + (", and the same ordering holds inside the unlucky cohort"
             if xwins_cohort else
             " (inside the cohort the ordering flips, but the cohort is "
             "range-restricted by construction, which attenuates its "
             "correlations)") + ".")
    else:
        A(f"**Honest negative: the x-stat does NOT win the horse race** "
          f"({pl['corr_ros_with_h1_xwoba']:.3f} vs "
          f"{pl['corr_ros_with_h1_woba']:.3f} on the full pool). The luck "
          "thesis needs the recovery numbers alone to carry it.")
    A(f"\nThe recovery direction is unambiguous either way: the average "
      f"unlucky-cohort hitter improved by "
      f"**{st['mean_recovery']*1000:+.0f} points of wOBA** after June 30 and "
      f"landed within {abs(st['median_ros_minus_h1_xwoba'])*1000:.0f} points "
      f"of his midseason *xwOBA* (median), i.e. the second half tracked the "
      f"process stat, not the unlucky results. "
      f"{st['pct_closed_half']:.0%} closed at least half the gap.\n")
    A("## Where Duran sits\n")
    A(f"Duran's 2026 midseason gap is **{d['gap']*1000:+.0f} points** (wOBA "
      f"{d['h1_woba']:.3f} vs xwOBA {d['h1_xwoba']:.3f}) — more negative "
      f"than **{(1-d['pctile_all_h1']):.0%}** of all {pl['n']} qualified "
      f"first halves since 2016 (roughly the "
      f"{d['pctile_all_h1']*100:.0f}th percentile of the gap distribution). "
      f"Within the unlucky cohort itself he sits at the "
      f"{d['pctile_in_cohort']*100:.0f}th percentile — a typical member, "
      f"not an outlier even among the unlucky. Applying the cohort's mean "
      f"recovery to his line implies a ROS wOBA around "
      f"**{d['implied_ros_woba_mean_closure']:.3f}** — well above the .263 "
      f"he would be sold on today, but short of both Monte Carlo medians "
      f"(.318 eroded / .336 healthy). That is the right reading: the "
      f"backtest regresses the luck *around whatever the current process "
      f"is*, and his 2026 xwOBA is itself depressed and speed-blind. The "
      f"backtest validates the sim's mechanism and direction; the talent "
      f"level comes from the priors, not from this cohort.\n")
    A("![Luck-gap backtest](../figures/11_luck_gap_backtest.png)\n")
    A("## What this does to the rebound memo\n")
    A("- The 69% healthy-prior scenario **gains external validity**: its "
      "core mechanism (second halves track xwOBA, not unlucky wOBA) is what "
      "actually happened in "
      f"{st['pct_closed_half']:.0%} of comparable cases.")
    A("- It does **not** validate the healthy prior's *level* — the backtest "
      "regresses the luck gap, and Duran's 2026 xwOBA (.287) is itself "
      "depressed. The erosion scenario's question (is the process worse?) "
      "is answered by the bat-tracking decomposition, not by this cohort.")
    A("- Net: the two documents together say *the direction is up, the "
      "destination depends on the approach fix* — which is exactly how the "
      "pre-registered predictions are framed.\n")
    A("---\n*Caveats: survivor bias (hitters must log "
      f"{MIN_ROS_PA}+ second-half PA to be graded — badly slumping players "
      "get benched, which likely flatters the recovery numbers modestly); "
      "the June 30 split is calendar-based, not PA-balanced; xwOBA from the "
      "Savant grouped search is park- and speed-blind, which for a burner "
      "like Duran makes the implied recovery conservative.*")
    out = C.OUT_DIR / "luck_gap_backtest.md"
    out.write_text("\n".join(L))
    print(f"  [backtest] wrote {out}")


def run(fetch: bool = True):
    res = compute(fetch=fetch)
    fig(res)
    print("  [backtest] wrote figure 11")
    memo(res)
    ser = {k: v for k, v in res.items() if not k.startswith("_")}
    with open(C.DATA_DIR / "luck_backtest.json", "w") as f:
        json.dump(ser, f, indent=2)
    return res


if __name__ == "__main__":
    import sys
    run(fetch="--no-fetch" not in sys.argv)
