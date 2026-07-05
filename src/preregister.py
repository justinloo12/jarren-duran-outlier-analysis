"""Freeze the falsifiable calls: write outputs/predictions.json, dated.

This is the commitment device. Everything the analysis claims about the rest
of 2026 — the two rebound distributions, the probability calls, the valuation
recommendation, and the physical-vs-approach verdict — is serialized here
with the exact wOBA→wRC+ conversion needed to grade it, so that
`python3 -m src.grade_predictions` can score every line after the season
with no wiggle room. The JSON is committed to the repo; the grade is the
grade.

Standalone: python3 -m src.preregister   (recomputes the sim; deterministic)
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from . import config as C
from . import rebound_sim

FREEZE_DATE = "2026-07-04"
QUANTILES = (5, 10, 25, 50, 75, 90, 95)
VALUATION_RANGE_MUSD = (18.0, 22.0)   # erosion-blended .. healthy offseason EV
SELL_NOW_MUSD = 10.0


# --- pure (unit-tested) ---------------------------------------------------------
def quantiles_from_draws(draws, qs=QUANTILES) -> dict:
    """Named quantiles of a simulation draw vector, e.g. {'q50': ...}."""
    a = np.asarray(draws, float)
    return {f"q{int(q):02d}": float(np.percentile(a, q)) for q in qs}


def binary_call(p: float, threshold: float = 0.5) -> bool:
    """The yes/no version of a probability call (graded alongside Brier)."""
    return bool(p >= threshold)


# --- assembly --------------------------------------------------------------------
def build() -> dict:
    resu = rebound_sim.compute()          # deterministic (seeded)
    conv = resu["inputs"]["conv"]
    scen = {}
    for name, sc in resu["scenarios"].items():
        scen[name] = {
            "ros_wrcplus_quantiles": quantiles_from_draws(
                sc["ros_wrcplus_draws"]),
            "p_ros_wrcplus_ge_100": sc["p_ros_wrcplus_100"],
            "p_ros_wrcplus_ge_110": sc["p_ros_wrcplus_110"],
            "median_ros_woba": sc["median_ros_woba"],
        }

    ero_p = C.DATA_DIR / "erosion_decomposition.json"
    ero = json.load(open(ero_p)) if ero_p.exists() else None
    bt_p = C.DATA_DIR / "luck_backtest.json"
    bt = json.load(open(bt_p)) if bt_p.exists() else None

    ph = scen["healthy"]["p_ros_wrcplus_ge_100"]
    pe = scen["erosion"]["p_ros_wrcplus_ge_100"]
    w = (ero or {}).get("reweight", {}).get("w_healthy", 0.5)
    p_blend = w * ph + (1 - w) * pe

    return {
        "frozen": FREEZE_DATE,
        "generated": dt.date.today().isoformat(),
        "player": C.PLAYER["name"],
        "mlbam": C.PLAYER["mlbam"],
        "definition": {
            "graded_quantity": "Duran's rest-of-2026 wRC+ (regular-season "
                               "games on/after the freeze date), computed as "
                               "ROS wOBA from pitch-level Statcast "
                               "(sum woba_value / sum woba_denom) mapped "
                               "through the frozen conversion below",
            "conversion_wrcplus_eq": "wRC+ = slope * wOBA + intercept + "
                                     "offset",
            "conversion": conv,
            "n_remaining_pa_at_freeze": resu["inputs"]["n_remaining_pa"],
            "min_ros_pa_to_grade": 100,
        },
        "predictions": {
            "scenarios": scen,
            "scenario_weighting": {
                "w_healthy": w,
                "rationale": "erosion-decomposition verdict (bat speed "
                             "intact -> approach) up-weights the healthy "
                             "prior from an agnostic 50/50",
                "p_blend_ros_wrcplus_ge_100": p_blend,
                "binary_call_ros_wrcplus_ge_100": binary_call(p_blend),
            },
            "valuation": {
                "call": "do NOT sell at the 2026 deadline; deal in the "
                        "offseason",
                "offseason_value_range_musd": list(VALUATION_RANGE_MUSD),
                "sell_now_value_musd": SELL_NOW_MUSD,
                "grading_note": "graded qualitatively in October: was he "
                                "traded before the deadline (call fails if "
                                "the return was clearly below the range)? "
                                "If dealt in the offseason, does the return "
                                "grade within/above 18-22 $M surplus "
                                "(~a 50-FV prospect package)?",
            },
            "erosion_verdict": None if ero is None else {
                "label": ero["verdict"]["label"],
                "bat_speed_delta_mph": ero["verdict"]["bat_speed_delta_mph"],
                "claim": "2026's decline is approach (intent/selectivity), "
                         "not physical: bat speed is up vs 2024-25, whiff "
                         "and chase erosion should be fixable; graded TRUE "
                         "if his 2026 final avg bat speed stays within 1 "
                         "mph of 2025 AND ROS chase improves vs H1",
            },
            "backtest_context": None if bt is None else {
                "cohort_mean_recovery_pts": round(
                    bt["cohort"]["mean_recovery"] * 1000, 1),
                "pct_closed_half": bt["cohort"]["pct_closed_half"],
                "duran_gap_pctile_all": bt["duran"]["pctile_all_h1"],
            },
        },
        "grading": {
            "how": "python3 -m src.grade_predictions (after the 2026 "
                   "regular season)",
            "binary": "Brier score on each P(ROS wRC+ >= 100) plus the "
                      "blended call",
            "quantiles": "coverage: does actual ROS wRC+ fall inside each "
                         "scenario's 50% (q25-q75) and 90% (q05-q95) "
                         "intervals?",
        },
    }


def run():
    pred = build()
    out = C.OUT_DIR / "predictions.json"
    out.write_text(json.dumps(pred, indent=2))
    print(f"  [preregister] wrote {out}")
    return pred


if __name__ == "__main__":
    run()
