"""Offline unit tests for the pure, deterministic helpers.

No network access: we only exercise season-age arithmetic, the two-proportion
z-test used throughout the analysis, and season_metrics fed a small synthetic
pitch table (so every expected value below is hand-computable).

Run from the project root:  python3 -m unittest discover tests
"""
import math
import unittest

import pandas as pd

from src import config as C
from src.analysis import two_prop_test, two_sided_p
from src.statcast_metrics import season_metrics


class TestSeasonAge(unittest.TestCase):
    def test_duran_season_ages(self):
        # Born 1996-09-05: has not yet turned by June 30, so 2024 is his
        # age-27 season and 2026 his age-29 season (FanGraphs convention).
        self.assertEqual(C.season_age(2024), 27)
        self.assertEqual(C.season_age(2026), 29)
        self.assertEqual(C.season_age(2021), 24)


class TestTwoPropTest(unittest.TestCase):
    def test_two_sided_p_known_values(self):
        self.assertAlmostEqual(two_sided_p(0.0), 1.0, places=12)
        self.assertAlmostEqual(two_sided_p(1.96), 0.05, places=3)
        # symmetric in the sign of z
        self.assertAlmostEqual(two_sided_p(-1.96), two_sided_p(1.96), places=12)

    def test_identical_proportions_are_not_significant(self):
        r = two_prop_test(0.5, 100, 0.5, 100)
        self.assertAlmostEqual(r["diff"], 0.0, places=12)
        self.assertAlmostEqual(r["z"], 0.0, places=12)
        self.assertAlmostEqual(r["p"], 1.0, places=12)

    def test_large_gap_is_significant_and_ci_excludes_zero(self):
        r = two_prop_test(0.6, 1000, 0.4, 1000)
        self.assertAlmostEqual(r["diff"], 0.2, places=12)
        self.assertLess(r["p"], 0.001)
        self.assertGreater(r["ci_lo"], 0.0)  # 95% CI excludes zero

    def test_missing_denominator_returns_nans(self):
        r = two_prop_test(0.5, 0, 0.4, 100)
        self.assertTrue(math.isnan(r["z"]))
        self.assertTrue(math.isnan(r["p"]))


class TestSeasonMetrics(unittest.TestCase):
    def _synthetic_pitches(self):
        # 10 regular-season pitches with hand-checkable rates, plus one
        # spring-training pitch that must be filtered out.
        rows = [
            # desc, zone, type, ls, lsa, events, la, xba, game_type
            ("called_strike",   5, "S", None, None, None,      None, None, "R"),
            ("ball",           12, "B", None, None, None,      None, None, "R"),
            ("swinging_strike",13, "S", None, None, None,      None, None, "R"),
            ("foul",            5, "S", None, None, None,      None, None, "R"),
            ("hit_into_play",   5, "X", 101.0, 6,  "home_run", 28.0, 0.9,  "R"),
            ("hit_into_play",   6, "X",  97.0, 3,  "single",   10.0, 0.5,  "R"),
            ("hit_into_play",   4, "X",  85.0, 2,  "field_out",20.0, 0.1,  "R"),
            ("ball",           11, "B", None, None, None,      None, None, "R"),
            ("swinging_strike", 5, "S", None, None, None,      None, None, "R"),
            ("foul",           14, "S", None, None, None,      None, None, "R"),
            # spring training: must not count anywhere
            ("hit_into_play",   5, "X", 110.0, 6,  "home_run", 30.0, 0.99, "S"),
        ]
        return pd.DataFrame(rows, columns=[
            "description", "zone", "type", "launch_speed",
            "launch_speed_angle", "events", "launch_angle",
            "estimated_ba_using_speedangle", "game_type"])

    def test_rates_on_synthetic_season(self):
        m = season_metrics(self._synthetic_pitches(), 2024)
        self.assertEqual(m["season"], 2024)
        self.assertEqual(m["sc_pitches"], 10)          # spring pitch dropped
        self.assertEqual(m["sc_bip"], 3)
        self.assertAlmostEqual(m["sc_chase_pct"], 2 / 4)      # 2 of 4 out-of-zone
        self.assertAlmostEqual(m["sc_whiff_pct"], 2 / 7)      # 2 misses on 7 swings
        self.assertAlmostEqual(m["sc_zcontact_pct"], 4 / 5)   # 4 of 5 in-zone swings
        self.assertAlmostEqual(m["sc_swstr_pct"], 2 / 10)
        self.assertAlmostEqual(m["sc_hardhit_pct"], 2 / 3)    # 101, 97 >= 95 mph
        self.assertAlmostEqual(m["sc_barrel_pct"], 1 / 3)     # one launch_speed_angle == 6

    def test_babip_excludes_home_runs(self):
        m = season_metrics(self._synthetic_pitches(), 2024)
        # (hits_in_play - HR) / (BIP - HR) = (2 - 1) / (3 - 1)
        self.assertEqual(m["sc_babip_den"], 2)
        self.assertAlmostEqual(m["sc_babip"], 0.5)
        # xBABIP = mean xBA on the two non-HR balls in play
        self.assertAlmostEqual(m["sc_xbabip"], (0.5 + 0.1) / 2)

    def test_empty_season_returns_stub(self):
        m = season_metrics(pd.DataFrame(), 2022)
        self.assertEqual(m, {"season": 2022})


if __name__ == "__main__":
    unittest.main()
