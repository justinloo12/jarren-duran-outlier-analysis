"""Offline unit tests for the luck-gap backtest's pure logic.

Synthetic player tables only — no network, no cache files.

Run from the project root:  python3 -m unittest discover tests
"""
import unittest

import numpy as np
import pandas as pd

from src.luck_backtest import (build_cohort, gap_closed_frac, gap_points,
                               join_ros, percentile_of, recovery_stats)


def h1_frame():
    return pd.DataFrame({
        "player_id": [1, 2, 3, 4],
        "player_name": ["a", "b", "c", "d"],
        "pa": [300, 300, 200, 300],
        "woba": [0.300, 0.320, 0.250, 0.360],
        "xwoba": [0.330, 0.330, 0.300, 0.350],
    })


class TestCohortFilter(unittest.TestCase):
    def test_gap_and_pa_filters(self):
        c = build_cohort(h1_frame(), min_pa=250, gap_max=-0.020)
        # player 1: gap -30, 300 PA -> in. player 2: gap -10 -> out.
        # player 3: gap -50 but 200 PA -> out. player 4: gap +10 -> out.
        self.assertEqual(list(c["player_id"]), [1])
        self.assertAlmostEqual(c["gap"].iloc[0], -0.030, places=12)

    def test_boundary_inclusive(self):
        d = h1_frame()
        d.loc[1, "woba"] = 0.310            # player 2 gap exactly -0.020
        c = build_cohort(d, min_pa=250, gap_max=-0.020)
        self.assertIn(2, list(c["player_id"]))

    def test_gap_points_sign(self):
        self.assertAlmostEqual(gap_points(0.263, 0.287), -0.024, places=12)
        self.assertGreater(gap_points(0.360, 0.350), 0)


class TestJoinRos(unittest.TestCase):
    def test_join_and_min_pa(self):
        h1 = build_cohort(h1_frame(), min_pa=250, gap_max=-0.020)
        ros = pd.DataFrame({"player_id": [1, 2], "pa": [200, 50],
                            "woba": [0.330, 0.400], "xwoba": [0.335, 0.390]})
        m = join_ros(h1, ros, min_ros_pa=100)
        self.assertEqual(len(m), 1)
        self.assertAlmostEqual(m["ros_woba"].iloc[0], 0.330)

    def test_player_missing_from_ros_is_dropped(self):
        h1 = build_cohort(h1_frame(), min_pa=250, gap_max=-0.020)
        m = join_ros(h1, pd.DataFrame({"player_id": [99], "pa": [300],
                                       "woba": [0.3], "xwoba": [0.3]}))
        self.assertEqual(len(m), 0)


class TestGapMath(unittest.TestCase):
    def test_closure_fractions(self):
        # H1: .300 vs x .330 (gap -30). ROS .315 closes exactly half.
        f = gap_closed_frac(0.300, 0.330, 0.315)
        self.assertAlmostEqual(float(f), 0.5, places=12)
        # landing on the x-stat closes it fully; repeating the wOBA closes 0
        self.assertAlmostEqual(float(gap_closed_frac(0.300, 0.330, 0.330)),
                               1.0, places=12)
        self.assertAlmostEqual(float(gap_closed_frac(0.300, 0.330, 0.300)),
                               0.0, places=12)
        # overshooting the x-stat is > 1
        self.assertGreater(float(gap_closed_frac(0.300, 0.330, 0.350)), 1.0)

    def test_percentile_of(self):
        arr = [-0.05, -0.03, -0.01, 0.00, 0.02]
        self.assertAlmostEqual(percentile_of(-0.03, arr), 2 / 5)
        self.assertAlmostEqual(percentile_of(-0.06, arr), 0.0)
        self.assertAlmostEqual(percentile_of(0.05, arr), 1.0)
        # NaNs are ignored
        self.assertAlmostEqual(percentile_of(0.0, arr + [np.nan]), 4 / 5)


class TestRecoveryStats(unittest.TestCase):
    def _merged(self):
        # two unlucky hitters: one fully recovers to his x-stat, one repeats
        return pd.DataFrame({
            "player_id": [1, 2],
            "pa": [300, 300],
            "woba": [0.300, 0.280],
            "xwoba": [0.340, 0.320],
            "gap": [-0.040, -0.040],
            "ros_pa": [250, 250],
            "ros_woba": [0.340, 0.280],
            "ros_xwoba": [0.335, 0.300],
        })

    def test_hand_computed_summary(self):
        s = recovery_stats(self._merged())
        self.assertEqual(s["n"], 2)
        self.assertAlmostEqual(s["mean_recovery"], 0.020, places=12)
        self.assertAlmostEqual(s["pct_closed_half"], 0.5, places=12)
        self.assertAlmostEqual(s["pct_any_improvement"], 0.5, places=12)
        # player 1 lands on his x-stat, player 2 lands 40 under
        self.assertAlmostEqual(s["mean_ros_minus_h1_xwoba"], -0.020,
                               places=12)

    def test_xstat_wins_on_synthetic_luck_world(self):
        # construct a world where ROS = H1 xwOBA + tiny noise: the x-stat
        # correlation must dominate the wOBA correlation
        rng = np.random.default_rng(0)
        x = rng.normal(0.320, 0.025, 400)
        luck = rng.normal(0, 0.020, 400)
        m = pd.DataFrame({
            "player_id": np.arange(400), "pa": 300,
            "woba": x + luck, "xwoba": x, "gap": luck,
            "ros_pa": 250, "ros_woba": x + rng.normal(0, 0.008, 400),
            "ros_xwoba": x,
        })
        s = recovery_stats(m)
        self.assertGreater(s["corr_ros_with_h1_xwoba"],
                           s["corr_ros_with_h1_woba"])


if __name__ == "__main__":
    unittest.main()
