"""Grade the pre-registered predictions after the 2026 season.

Run in October:  python3 -m src.grade_predictions
It pulls Duran's pitch-level Statcast from the freeze date forward, computes
his actual rest-of-season wOBA (sum woba_value / sum woba_denom, regular
season only), maps it through the conversion frozen in
outputs/predictions.json, and scores:

  * each scenario's P(ROS wRC+ >= 100) with a Brier score
    (0 = clairvoyant, 0.25 = coin flip), plus the blended call;
  * quantile coverage — did the actual land inside each scenario's 50%
    (q25-q75) and 90% (q05-q95) intervals?
  * the erosion-verdict and valuation calls are printed with their frozen
    grading criteria for a manual yes/no (they depend on bat-speed data and
    trade outcomes, not just the batting line).

Kept deliberately simple: quantile coverage + Brier is the whole rubric, as
promised in the pre-registration. Writes outputs/prediction_grades.md.
"""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from . import config as C

SEASON_END_GUARD = dt.date(2026, 9, 27)   # last scheduled day of the season


# --- pure helpers (unit-tested) --------------------------------------------------
def ros_woba_from_pitches(df: pd.DataFrame, start_date: str) -> dict:
    """Actual wOBA over regular-season PAs ending on/after start_date.

    Statcast rows carry woba_value / woba_denom on PA-ending pitches;
    wOBA = sum(value) / sum(denom). PA count = sum(denom is 1 per PA that
    counts toward wOBA; BB/HBP/AB all carry denom 1, sac bunts 0).
    """
    if df.empty:
        return {"woba": None, "pa": 0}
    d = df.copy()
    if "game_type" in d.columns:
        d = d[d["game_type"] == "R"]
    d = d[pd.to_datetime(d["game_date"]) >= pd.to_datetime(start_date)]
    den = pd.to_numeric(d["woba_denom"], errors="coerce").fillna(0)
    val = pd.to_numeric(d["woba_value"], errors="coerce").fillna(0)
    n = float(den.sum())
    return {"woba": (float(val.sum()) / n if n else None), "pa": int(n)}


def to_wrcplus(woba: float, conv: dict) -> float:
    """Apply the frozen linear conversion."""
    return conv["slope"] * woba + conv["intercept"] + conv["offset"]


def brier(p: float, outcome: bool) -> float:
    """Brier score of a probability call: (p - 1{outcome})^2."""
    return (p - (1.0 if outcome else 0.0)) ** 2


def quantile_coverage(actual: float, q: dict) -> dict:
    """Interval hits for a named-quantile dict ({'q05': .., 'q95': ..})."""
    return {
        "actual": actual,
        "in_50pct_interval": bool(q["q25"] <= actual <= q["q75"]),
        "in_80pct_interval": bool(q["q10"] <= actual <= q["q90"]),
        "in_90pct_interval": bool(q["q05"] <= actual <= q["q95"]),
        "below_median": bool(actual < q["q50"]),
    }


def grade_scenarios(pred: dict, actual_wrcplus: float) -> dict:
    """Score every frozen probabilistic claim against the actual ROS wRC+."""
    outcome_100 = actual_wrcplus >= 100.0
    out = {"actual_ros_wrcplus": actual_wrcplus,
           "outcome_wrcplus_ge_100": bool(outcome_100), "scenarios": {}}
    for name, sc in pred["predictions"]["scenarios"].items():
        out["scenarios"][name] = {
            "p_ge_100": sc["p_ros_wrcplus_ge_100"],
            "brier_ge_100": brier(sc["p_ros_wrcplus_ge_100"], outcome_100),
            "coverage": quantile_coverage(actual_wrcplus,
                                          sc["ros_wrcplus_quantiles"]),
        }
    wgt = pred["predictions"]["scenario_weighting"]
    out["blended"] = {
        "p_ge_100": wgt["p_blend_ros_wrcplus_ge_100"],
        "brier_ge_100": brier(wgt["p_blend_ros_wrcplus_ge_100"],
                              outcome_100),
        "binary_call_correct": bool(
            wgt["binary_call_ros_wrcplus_ge_100"] == outcome_100),
        "coin_flip_brier": 0.25,
    }
    return out


# --- main -------------------------------------------------------------------------
def run():
    pred = json.load(open(C.OUT_DIR / "predictions.json"))
    freeze = pred["frozen"]
    today = dt.date.today()
    if today <= SEASON_END_GUARD:
        print(f"NOTE: season not over (today {today}); grading a partial "
              "rest-of-season. Final grades should be run in October.")

    from pybaseball import statcast_batter
    df = statcast_batter(freeze, f"{C.CURRENT_SEASON}-11-15", pred["mlbam"])
    ros = ros_woba_from_pitches(df if df is not None else pd.DataFrame(),
                                freeze)
    if ros["woba"] is None:
        print("No rest-of-season PAs found; nothing to grade.")
        return None
    if ros["pa"] < pred["definition"]["min_ros_pa_to_grade"]:
        print(f"WARNING: only {ros['pa']} ROS PA "
              f"(< {pred['definition']['min_ros_pa_to_grade']} floor "
              "frozen in the pre-registration) — grades are indicative "
              "only.")

    actual = to_wrcplus(ros["woba"], pred["definition"]["conversion"])
    g = grade_scenarios(pred, actual)

    L = [f"# Prediction Grades — frozen {freeze}, graded "
         f"{today.isoformat()}\n",
         f"Actual rest-of-season: **{ros['pa']} PA, wOBA {ros['woba']:.3f} "
         f"≈ {actual:.0f} wRC+** (frozen conversion). Outcome wRC+ ≥ 100: "
         f"**{g['outcome_wrcplus_ge_100']}**.\n",
         "| Claim | P(≥100) | Brier | In 50% band | In 90% band |",
         "|-------|--------:|------:|:-----------:|:-----------:|"]
    for name, sc in g["scenarios"].items():
        cv = sc["coverage"]
        L.append(f"| {name} prior | {sc['p_ge_100']:.0%} | "
                 f"{sc['brier_ge_100']:.3f} | "
                 f"{'yes' if cv['in_50pct_interval'] else 'no'} | "
                 f"{'yes' if cv['in_90pct_interval'] else 'no'} |")
    b = g["blended"]
    L.append(f"| blended call | {b['p_ge_100']:.0%} | "
             f"{b['brier_ge_100']:.3f} (coin flip = 0.250) | — | — |")
    L.append(f"\nBinary blended call "
             f"({'≥' if pred['predictions']['scenario_weighting']['binary_call_ros_wrcplus_ge_100'] else '<'}100) "
             f"was **{'CORRECT' if b['binary_call_correct'] else 'WRONG'}**.\n")
    ev = pred["predictions"].get("erosion_verdict")
    if ev:
        L.append(f"**Erosion verdict to hand-grade:** {ev['claim']}")
    val = pred["predictions"]["valuation"]
    L.append(f"\n**Valuation call to hand-grade:** {val['call']} — "
             f"{val['grading_note']}")
    md = "\n".join(L)
    out = C.OUT_DIR / "prediction_grades.md"
    out.write_text(md)
    print(md)
    print(f"\nwrote {out}")
    return g


if __name__ == "__main__":
    run()
