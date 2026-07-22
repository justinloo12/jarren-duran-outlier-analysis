"""Offline unit tests for the two custom models.

battery_model: WOWY pooling, fixed-effects estimation, empirical-Bayes
shrinkage — all on synthetic data with known ground truth.
xcontact: the pure spray-angle helper.

No network, no cached data files required.
"""
import unittest

import numpy as np
import pandas as pd

from src import battery
from src import battery_model as bm
from src.xcontact import spray_angle

NARV, WONG = bm.CATS  # ("Carlos Narváez", "Connor Wong")


def synth_pa(n_per=400, catcher_effect=-0.050, seed=7,
             per_pitcher=None) -> pd.DataFrame:
    """PA table with pitcher intercepts and a known Wong effect.
    per_pitcher optionally maps pitcher -> pitcher-specific Wong effect
    (adds true heterogeneity, so shrinkage has signal to preserve)."""
    rng = np.random.default_rng(seed)
    rows = []
    pitchers = {"Arm A": 0.30, "Arm B": 0.34, "Arm C": 0.38}
    for p, base in pitchers.items():
        eff = (per_pitcher or {}).get(p, catcher_effect)
        for cat in (NARV, WONG):
            mu = base + (eff if cat == WONG else 0.0)
            y = rng.normal(mu, 0.5, n_per)
            for i, yi in enumerate(y):
                rows.append({"game_pk": 1000 + i % 40,
                             "pitcher_name": p, "catcher": cat,
                             "opponent": "NYY" if i % 2 else "TOR",
                             "home": i % 2,
                             "wong": int(cat == WONG), "y": yi})
    return pd.DataFrame(rows)


class TestSprayAngle(unittest.TestCase):
    def test_straightaway_is_zero(self):
        self.assertAlmostEqual(
            float(spray_angle(125.42, 100.0, "R")), 0.0, places=6)

    def test_pull_positive_both_hands(self):
        # RHB pulls toward 3B/LF (hc_x below center)
        self.assertGreater(float(spray_angle(90.0, 100.0, "R")), 0)
        # LHB pulls toward 1B/RF (hc_x above center)
        self.assertGreater(float(spray_angle(160.0, 100.0, "L")), 0)

    def test_mirror_symmetry(self):
        r = float(spray_angle(90.0, 100.0, "R"))
        l = float(spray_angle(160.84, 100.0, "L"))
        self.assertAlmostEqual(r, l, places=5)


class TestOutEvents(unittest.TestCase):
    def test_out_credits(self):
        self.assertEqual(battery.OUT_EV["strikeout"], 1)
        self.assertEqual(battery.OUT_EV["double_play"], 2)
        self.assertEqual(battery.OUT_EV["triple_play"], 3)
        self.assertNotIn("single", battery.OUT_EV)


class TestWowy(unittest.TestCase):
    def test_recovers_known_effect(self):
        pa = synth_pa()
        w = bm.wowy(pa)
        self.assertEqual(w["n_pitchers"], 3)
        self.assertAlmostEqual(w["pooled_delta"], -0.050, delta=0.02)

    def test_min_pa_filter(self):
        pa = synth_pa(n_per=bm.MIN_PA - 1)
        self.assertEqual(bm.wowy(pa)["n_pitchers"], 0)


class TestFixedEffects(unittest.TestCase):
    def test_recovers_known_effect(self):
        est = bm._fe_fit(synth_pa())
        self.assertAlmostEqual(est, -0.050, delta=0.02)

    def test_confounded_assignment_still_recovered(self):
        # Wong catches mostly the bad arm; naive split is biased, FE isn't
        pa = synth_pa()
        keep = ~((pa["pitcher_name"] == "Arm C") & (pa["wong"] == 0)
                 & (np.arange(len(pa)) % 4 > 0))
        pa = pa[keep.values if hasattr(keep, "values") else keep]
        est = bm._fe_fit(pa)
        self.assertAlmostEqual(est, -0.050, delta=0.03)


class TestShrinkage(unittest.TestCase):
    def setUp(self):
        self.pa = synth_pa()
        self.rows = bm.shrink(self.pa, pooled=-0.050)

    def test_reliability_bounds(self):
        for r in self.rows:
            self.assertGreaterEqual(r["reliability"], 0.0)
            self.assertLessEqual(r["reliability"], 1.0)

    def test_shrunk_between_raw_and_pooled(self):
        for r in self.rows:
            lo, hi = sorted((r["raw_delta"], -0.050))
            self.assertGreaterEqual(r["shrunk_delta"], lo - 1e-9)
            self.assertLessEqual(r["shrunk_delta"], hi + 1e-9)

    def test_no_heterogeneity_means_full_shrinkage(self):
        # identical true effects + huge samples -> tau2 ~ 0 -> everything
        # collapses to the pooled estimate
        rows = bm.shrink(synth_pa(n_per=2000), pooled=-0.05)
        for r in rows:
            self.assertAlmostEqual(r["shrunk_delta"], -0.05, delta=0.01)

    def test_real_heterogeneity_survives_big_samples(self):
        hetero = {"Arm A": -0.15, "Arm B": -0.05, "Arm C": +0.05}
        rows = bm.shrink(synth_pa(n_per=4000, per_pitcher=hetero),
                         pooled=-0.05)
        by = {r["pitcher"]: r["shrunk_delta"] for r in rows}
        self.assertLess(by["Arm A"], by["Arm B"])
        self.assertLess(by["Arm B"], by["Arm C"])


if __name__ == "__main__":
    unittest.main()
