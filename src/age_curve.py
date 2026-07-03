"""Aging-curve context for a 27->29 season window.

We build an *empirical* aging curve with the delta method from the same
FanGraphs league frames we already pulled (2021-2026): every player who logged
>=200 PA in consecutive seasons contributes a wRC+ (and wOBA) change keyed to
his starting age. We average those changes by age, both league-wide and for a
speed/contact-outfielder cohort resembling Duran's profile.

Caveats (documented, not hidden):
  * Delta method has survivorship bias -> it *understates* real decline
    (the worst agers drop out of the sample), so it is a conservative,
    friendly-to-Duran benchmark.
  * Only a 6-year window, so age cells are thin. Treat as directional.

We then draw two expected trajectories for Duran:
  * anchored at his 2024 peak (age 27) -> what "normal aging alone" predicts
    for 2025/2026 if 2024 were his true level;
  * anchored at his non-2024 true-talent baseline -> the "2024 was inflated"
    world.
Comparing actuals to each separates aging from regression.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config as C


def _league_panel() -> pd.DataFrame:
    frames = []
    for s in C.SEASONS:
        p = C.FANGRAPHS_DIR / f"league_{s}.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["season"] = s
            frames.append(df)
    panel = pd.concat(frames, ignore_index=True)
    return panel[["Name", "season", "Age", "PA", "wRC+", "wOBA",
                  "Spd", "ISO"]].dropna(subset=["Age", "wRC+"])


def empirical_curve(min_pa: int = 200):
    """Delta-method wRC+/wOBA change by starting age, league + speed cohort."""
    panel = _league_panel()
    # drop ambiguous names (two players sharing a name in one season, e.g.
    # the two Max Muncys) so the self-merge below can't create bogus pairs
    panel = panel[~panel.duplicated(subset=["Name", "season"], keep=False)]
    nxt = panel.copy()
    nxt["season"] = nxt["season"] - 1  # align y+1 onto y
    pairs = panel.merge(
        nxt, on=["Name", "season"], suffixes=("", "_next"))
    pairs = pairs[(pairs["PA"] >= min_pa) & (pairs["PA_next"] >= min_pa)].copy()
    pairs["age0"] = pairs["Age"].round().astype(int)
    pairs["d_wrc"] = pairs["wRC+_next"] - pairs["wRC+"]
    pairs["d_woba"] = pairs["wOBA_next"] - pairs["wOBA"]

    # Speed/contact cohort: above-median Spd, moderate power (ISO <= 70th pct).
    spd_cut = panel["Spd"].median()
    iso_cut = panel["ISO"].quantile(0.70)
    cohort = pairs[(pairs["Spd"] >= spd_cut) & (pairs["ISO"] <= iso_cut)]

    def by_age(d):
        g = d.groupby("age0")
        return pd.DataFrame({
            "n": g.size(),
            "d_wrc": g["d_wrc"].mean(),
            "d_woba": g["d_woba"].mean(),
        }).reset_index()

    return {
        "league": by_age(pairs),
        "cohort": by_age(cohort),
        "spd_cut": float(spd_cut),
        "iso_cut": float(iso_cut),
    }


def _delta(curve_df: pd.DataFrame, age: int, col: str) -> float:
    row = curve_df[curve_df["age0"] == age]
    if len(row):
        return float(row[col].iloc[0])
    # fall back to nearest available age
    if curve_df.empty:
        return np.nan
    i = (curve_df["age0"] - age).abs().idxmin()
    return float(curve_df.loc[i, col])


def project(anchor_age: int, anchor_val: float, to_age: int,
            curve_df: pd.DataFrame, col: str = "d_wrc") -> dict:
    """Apply per-age deltas forward from an anchor."""
    val = anchor_val
    path = {anchor_age: anchor_val}
    a = anchor_age
    while a < to_age:
        val = val + _delta(curve_df, a, col)
        a += 1
        path[a] = val
    return path


def run(save: bool = True) -> dict:
    curves = empirical_curve()
    league = curves["league"]
    cohort = curves["cohort"]

    season_tbl = pd.read_csv(C.DATA_DIR / "season_metrics.csv")
    actual = {int(r.age): _num(r["wRC+"]) for _, r in season_tbl.iterrows()
              if not pd.isna(r.get("wRC+"))}

    # Duran ages: 2024=27, 2025=28, 2026=29.
    peak_age = C.season_age(C.OUTLIER_SEASON)          # 27
    end_age = C.season_age(C.CURRENT_SEASON)           # 29
    peak_val = float(season_tbl[season_tbl.season == C.OUTLIER_SEASON]
                     ["wRC+"].iloc[0])

    # True-talent baseline wRC+ (PA-weighted, non-2024).
    base = season_tbl[season_tbl.season.isin(C.BASELINE_ESTABLISHED)]
    w = base["PA"].fillna(0).to_numpy()
    v = base["wRC+"].to_numpy(dtype=float)
    m = ~np.isnan(v) & (w > 0)
    baseline_val = float(np.average(v[m], weights=w[m])) if m.any() else np.nan

    out = {
        "peak_age": peak_age, "end_age": end_age,
        "duran_2024_wrcplus": peak_val,
        "baseline_wrcplus_established": baseline_val,
        "actual_by_age": actual,
        "league_curve": league.to_dict("records"),
        "cohort_curve": cohort.to_dict("records"),
        # expected paths (wRC+)
        "expected_from_2024_league": project(peak_age, peak_val, end_age,
                                             league),
        "expected_from_2024_cohort": project(peak_age, peak_val, end_age,
                                             cohort),
        "expected_from_baseline_league": project(peak_age, baseline_val,
                                                 end_age, league),
    }
    # How much of the 2024->2026 drop does normal aging explain?
    exp26 = out["expected_from_2024_league"].get(end_age)
    act26 = actual.get(end_age)
    if exp26 is not None and act26 is not None:
        out["aging_explains"] = {
            "total_drop_2024_to_2026": peak_val - act26,
            "aging_predicted_drop": peak_val - exp26,
            "residual_beyond_aging": exp26 - act26,
        }
    if save:
        with open(C.DATA_DIR / "age_curve.json", "w") as f:
            json.dump(out, f, indent=2, default=float)
        league.to_csv(C.DATA_DIR / "aging_curve_league.csv", index=False)
        cohort.to_csv(C.DATA_DIR / "aging_curve_cohort.csv", index=False)
    return out


def _num(x):
    return None if pd.isna(x) else float(x)


if __name__ == "__main__":
    import pprint
    pprint.pprint(run())
