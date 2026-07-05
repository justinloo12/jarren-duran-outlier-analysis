"""Offline unit tests for the pre-registration + grading pure logic.

Run from the project root:  python3 -m unittest discover tests
"""
import unittest

import numpy as np
import pandas as pd

from src.grade_predictions import (brier, grade_scenarios, quantile_coverage,
                                   ros_woba_from_pitches, to_wrcplus)
from src.preregister import binary_call, quantiles_from_draws


class TestQuantiles(unittest.TestCase):
    def test_named_quantiles_of_a_known_vector(self):
        q = quantiles_from_draws(np.arange(101, dtype=float))  # 0..100
        self.assertAlmostEqual(q["q50"], 50.0, places=9)
        self.assertAlmostEqual(q["q05"], 5.0, places=9)
        self.assertAlmostEqual(q["q95"], 95.0, places=9)
        self.assertEqual(set(q), {"q05", "q10", "q25", "q50", "q75",
                                  "q90", "q95"})

    def test_binary_call_threshold(self):
        self.assertTrue(binary_call(0.60))
        self.assertTrue(binary_call(0.50))
        self.assertFalse(binary_call(0.49))


class TestGradingMath(unittest.TestCase):
    def test_brier_extremes(self):
        self.assertAlmostEqual(brier(1.0, True), 0.0)
        self.assertAlmostEqual(brier(0.0, True), 1.0)
        self.assertAlmostEqual(brier(0.5, False), 0.25)   # the coin flip

    def test_quantile_coverage_bands(self):
        q = {"q05": 65.0, "q10": 72.0, "q25": 85.0, "q50": 98.0,
             "q75": 112.0, "q90": 124.0, "q95": 131.0}
        c = quantile_coverage(100.0, q)
        self.assertTrue(c["in_50pct_interval"])
        self.assertTrue(c["in_90pct_interval"])
        self.assertFalse(c["below_median"])
        c2 = quantile_coverage(60.0, q)
        self.assertFalse(c2["in_50pct_interval"])
        self.assertFalse(c2["in_90pct_interval"])
        self.assertTrue(c2["below_median"])

    def test_conversion_matches_frozen_formula(self):
        conv = {"slope": 671.455, "intercept": -113.123, "offset": -2.214}
        self.assertAlmostEqual(
            to_wrcplus(0.336, conv),
            671.455 * 0.336 - 113.123 - 2.214, places=9)

    def test_grade_scenarios_end_to_end(self):
        pred = {"predictions": {
            "scenarios": {
                "healthy": {"p_ros_wrcplus_ge_100": 0.69,
                            "ros_wrcplus_quantiles": {
                                "q05": 76.0, "q10": 84.0, "q25": 96.0,
                                "q50": 110.0, "q75": 124.0, "q90": 136.0,
                                "q95": 143.0}},
                "erosion": {"p_ros_wrcplus_ge_100": 0.47,
                            "ros_wrcplus_quantiles": {
                                "q05": 65.0, "q10": 72.0, "q25": 85.0,
                                "q50": 98.0, "q75": 112.0, "q90": 124.0,
                                "q95": 131.0}},
            },
            "scenario_weighting": {"p_blend_ros_wrcplus_ge_100": 0.60,
                                   "binary_call_ros_wrcplus_ge_100": True},
        }}
        g = grade_scenarios(pred, actual_wrcplus=105.0)
        self.assertTrue(g["outcome_wrcplus_ge_100"])
        # brier of the 69% call on a hit: (0.69-1)^2
        self.assertAlmostEqual(g["scenarios"]["healthy"]["brier_ge_100"],
                               (0.69 - 1) ** 2, places=12)
        self.assertTrue(g["blended"]["binary_call_correct"])
        # 105 is inside both 50% bands
        for sc in g["scenarios"].values():
            self.assertTrue(sc["coverage"]["in_50pct_interval"])
        # a miss flips everything
        g2 = grade_scenarios(pred, actual_wrcplus=70.0)
        self.assertFalse(g2["outcome_wrcplus_ge_100"])
        self.assertFalse(g2["blended"]["binary_call_correct"])
        self.assertLess(g2["scenarios"]["erosion"]["brier_ge_100"],
                        g2["scenarios"]["healthy"]["brier_ge_100"])


class TestRosWobaFromPitches(unittest.TestCase):
    def _pitches(self):
        return pd.DataFrame({
            "game_date": ["2026-07-01", "2026-07-05", "2026-07-06",
                          "2026-07-07", "2026-07-08"],
            "game_type": ["R", "R", "R", "R", "S"],
            # walk (0.7), out (0), single (0.9); spring single excluded;
            # July 1 row excluded by the freeze date
            "woba_value": [0.9, 0.7, 0.0, 0.9, 0.9],
            "woba_denom": [1, 1, 1, 1, 1],
        })

    def test_freeze_date_and_game_type_filters(self):
        r = ros_woba_from_pitches(self._pitches(), "2026-07-04")
        self.assertEqual(r["pa"], 3)
        self.assertAlmostEqual(r["woba"], (0.7 + 0.0 + 0.9) / 3, places=12)

    def test_non_pa_rows_do_not_count(self):
        df = self._pitches()
        df["woba_denom"] = [1, 1, 0, 1, 1]   # row 3 no longer a wOBA PA
        r = ros_woba_from_pitches(df, "2026-07-04")
        self.assertEqual(r["pa"], 2)
        self.assertAlmostEqual(r["woba"], (0.7 + 0.9) / 2, places=12)

    def test_empty(self):
        r = ros_woba_from_pitches(pd.DataFrame(), "2026-07-04")
        self.assertEqual(r, {"woba": None, "pa": 0})


if __name__ == "__main__":
    unittest.main()
