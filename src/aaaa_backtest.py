"""Backtesting the AAAA regression claim on 2016-2025 history.

The audit flags Boston's thin-track-record contributors running career
bests and argues that production like this fades. This module tests
that claim instead of asserting it:

  Cohort, per season S in 2016-2025 (2020 skipped): hitters aged 26+
  with 100-1000 career PA entering S whose first-half wOBA (through
  June 30, 100+ PA) beat their career mark by 40+ points. Same design
  for relievers on FIP (career 20-250 IP, first-half FIP 0.75+ runs
  better than career, 20+ IP).

  Outcome: the second half (50+ PA / 15+ IP). Retention = the share of
  the first-half surge still present in the second half.

Data: FanGraphs leaders API with custom date ranges, cached per pull
under data/fangraphs/aaaa_bt/. Career baselines are cumulative from
2011, so cohort members are required to have debuted 2012 or later.

Writes data/aaaa_backtest.json and figures/20_aaaa_backtest.png.
"""
from __future__ import annotations

import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from . import config as C
from . import style as S

S.apply()

CACHE = C.DATA_DIR / "fangraphs" / "aaaa_bt"
SEASONS = [y for y in range(2016, 2026) if y != 2020]
CAREER_FROM = 2011
SURGE_WOBA = 0.040
SURGE_FIP = 0.75
_API = "https://www.fangraphs.com/api/leaders/major-league/data"


def _pull(season: int, stats: str, d1: str | None = None,
          d2: str | None = None) -> pd.DataFrame:
    tag = f"{stats}_{season}" + (f"_{d1}_{d2}" if d1 else "_full")
    f = CACHE / (re.sub(r"[^A-Za-z0-9_]", "", tag) + ".csv")
    if f.exists():
        return pd.read_csv(f)
    p = {"pos": "all", "stats": stats, "lg": "all", "qual": 0,
         "season": season, "season1": season, "team": 0,
         "pageitems": 3000, "pagenum": 1, "ind": 0,
         "type": 8 if stats == "bat" else 1,
         "month": 1000 if d1 else 0}
    if d1:
        p["startdate"], p["enddate"] = d1, d2
    d = pd.DataFrame(requests.get(_API, params=p, headers=C.HTTP_HEADERS,
                                  timeout=C.HTTP_TIMEOUT).json()["data"])
    cols = (["playerid", "Name", "Age", "PA", "wOBA"] if stats == "bat"
            else ["playerid", "Name", "Age", "IP", "ERA", "FIP", "GS"])
    d = d[[c for c in cols if c in d.columns]].copy()
    for c in d.columns:
        if c not in ("Name",):
            d[c] = pd.to_numeric(d[c], errors="coerce")
    CACHE.mkdir(parents=True, exist_ok=True)
    d.to_csv(f, index=False)
    return d


def _halves(season: int, stats: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    h1 = _pull(season, stats, f"{season}-03-01", f"{season}-06-30")
    h2 = _pull(season, stats, f"{season}-07-01", f"{season}-11-30")
    return h1, h2


def hitter_cohort() -> pd.DataFrame:
    """One row per journeyman-surge case: career, H1, H2 wOBA."""
    fulls = {y: _pull(y, "bat") for y in range(CAREER_FROM, 2026)}
    rows = []
    for s in SEASONS:
        # cumulative career entering season s
        hist = pd.concat([fulls[y] for y in range(CAREER_FROM, s)],
                         ignore_index=True)
        hist = hist[hist["PA"] > 0]
        car = hist.groupby("playerid").apply(
            lambda d: pd.Series({
                "car_pa": d["PA"].sum(),
                "car_woba": np.average(d["wOBA"], weights=d["PA"]),
                "first_season": len(d)}), include_groups=False)
        debut_ok = set(
            pd.concat([fulls[CAREER_FROM]], ignore_index=True)["playerid"])
        h1, h2 = _halves(s, "bat")
        m = (h1.merge(car, on="playerid")
               .merge(h2[["playerid", "PA", "wOBA"]],
                      on="playerid", suffixes=("", "_h2")))
        m = m[(m["Age"] >= 26)
              & (~m["playerid"].isin(debut_ok))       # debuted 2012+
              & (m["car_pa"].between(100, 1000))
              & (m["PA"] >= 100)
              & (m["wOBA"] >= m["car_woba"] + SURGE_WOBA)
              & (m["PA_h2"] >= 50)]
        m = m.assign(season=s)
        rows.append(m)
    out = pd.concat(rows, ignore_index=True)
    out["surge"] = out["wOBA"] - out["car_woba"]
    out["h2_delta"] = out["wOBA_h2"] - out["car_woba"]
    out["retention"] = out["h2_delta"] / out["surge"]
    return out


def arm_cohort() -> pd.DataFrame:
    fulls = {y: _pull(y, "pit") for y in range(CAREER_FROM, 2026)}
    rows = []
    for s in SEASONS:
        hist = pd.concat([fulls[y] for y in range(CAREER_FROM, s)],
                         ignore_index=True)
        hist = hist[hist["IP"] > 0]
        car = hist.groupby("playerid").apply(
            lambda d: pd.Series({
                "car_ip": d["IP"].sum(),
                "car_fip": np.average(d["FIP"], weights=d["IP"])}),
            include_groups=False)
        debut_ok = set(fulls[CAREER_FROM]["playerid"])
        h1, h2 = _halves(s, "pit")
        m = (h1.merge(car, on="playerid")
               .merge(h2[["playerid", "IP", "FIP"]],
                      on="playerid", suffixes=("", "_h2")))
        m = m[(m["Age"] >= 26)
              & (~m["playerid"].isin(debut_ok))
              & (m["GS"].fillna(0) == 0)
              & (m["car_ip"].between(20, 250))
              & (m["IP"] >= 20)
              & (m["FIP"] <= m["car_fip"] - SURGE_FIP)
              & (m["IP_h2"] >= 15)]
        m = m.assign(season=s)
        rows.append(m)
    out = pd.concat(rows, ignore_index=True)
    out["surge"] = out["car_fip"] - out["FIP"]          # positive = better
    out["h2_delta"] = out["car_fip"] - out["FIP_h2"]
    out["retention"] = out["h2_delta"] / out["surge"]
    return out


def _summ(d: pd.DataFrame) -> dict:
    return {
        "n": int(len(d)),
        "median_surge": round(float(d["surge"].median()), 3),
        "median_h2_delta": round(float(d["h2_delta"].median()), 3),
        "median_retention": round(float(d["retention"].median()), 2),
        "kept_half_pct": round(float((d["retention"] >= 0.5).mean()) * 100),
        "back_to_career_pct": round(
            float((d["h2_delta"] <= 0.010).mean()) * 100)
        if "wOBA" in d.columns else round(
            float((d["h2_delta"] <= 0.25).mean()) * 100),
    }


def fig_backtest(hit: pd.DataFrame, arm: pd.DataFrame, res: dict):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.6))
    for ax, d, xl, yl, ttl, mult in (
            (ax1, hit, "First-half surge over career (wOBA points)",
             "Second half vs career (wOBA points)",
             "Hitters: the surge mostly gives back", 1000),
            (ax2, arm, "First-half FIP improvement vs career (runs)",
             "Second half vs career (runs)",
             "Relievers: same shape", 1)):
        x = d["surge"] * mult
        y = d["h2_delta"] * mult
        ax.scatter(x, y, s=30, color=S.GREY, alpha=0.5, edgecolors="none",
                   zorder=2)
        lim = float(max(x.max(), abs(y.min()), y.max())) * 1.06
        ax.plot([0, lim], [0, lim], color=S.SPINE, lw=1.4, ls=":",
                zorder=1)
        ax.annotate("kept the whole surge", (lim * 0.97, lim * 0.97),
                    ha="right", va="top", fontsize=9.5, color=S.MUTED,
                    rotation=38)
        ax.axhline(0, color=S.SPINE, lw=1.4, zorder=1)
        ax.annotate("back to career level", (lim * 0.97, 0),
                    textcoords="offset points", xytext=(0, -13),
                    ha="right", fontsize=9.5, color=S.MUTED)
        med_x = float(x.median())
        med_y = float(y.median())
        ax.scatter([med_x], [med_y], s=170, color=S.RED, zorder=3,
                   marker="D")
        ax.annotate("median", (med_x, med_y), textcoords="offset points",
                    xytext=(10, -4), color=S.RED, fontsize=11,
                    fontweight="bold")
        ax.set_xlim(0, lim)
        S.style(ax)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(ttl, loc="left", fontsize=14, fontweight="bold")
    h, a = res["hitters"], res["arms"]
    fig.suptitle("Journeyman career-year first halves, 2016-2025: "
                 f"the median keeps about "
                 f"{h['median_retention']*100:.0f}% of the surge",
                 x=0.02, y=0.99, ha="left", fontsize=16, fontweight="bold")
    fig.text(0.02, 0.015,
             f"Hitters: n={h['n']}, age 26+, 100-1000 career PA, first "
             "half 40+ wOBA points over career. Relievers: "
             f"n={a['n']}, 20-250 career IP, first half 0.75+ FIP runs "
             "better than career. Points above the dotted line held the "
             "level; points below zero fell under their career mark.",
             fontsize=10, color=S.MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    out = C.FIG_DIR / "20_aaaa_backtest.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [aaaa_bt] wrote {out}")


def run() -> dict:
    hit = hitter_cohort()
    arm = arm_cohort()
    res = {"hitters": _summ(hit), "arms": _summ(arm),
           "seasons": f"{SEASONS[0]}-{SEASONS[-1]} (2020 skipped)",
           "surge_def": {"hitters_woba": SURGE_WOBA,
                         "arms_fip": SURGE_FIP}}
    (C.DATA_DIR / "aaaa_backtest.json").write_text(json.dumps(res, indent=2))
    print(f"  [aaaa_bt] wrote {C.DATA_DIR / 'aaaa_backtest.json'}")
    print(f"  [aaaa_bt] hitters n={res['hitters']['n']} "
          f"median retention {res['hitters']['median_retention']} | "
          f"arms n={res['arms']['n']} "
          f"median retention {res['arms']['median_retention']}")
    fig_backtest(hit, arm, res)
    return res
