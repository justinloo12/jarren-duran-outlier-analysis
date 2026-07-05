"""Offline unit tests for the rebound simulation's pure math.

No network and no data files: every function is exercised on synthetic inputs
with hand-computable expected values.

Run from the project root:  python3 -m unittest discover tests
"""
import math
import unittest

import numpy as np

from src.rebound_sim import (blend_prior, erode_prior, expected_values,
                             fit_woba_to_wrcplus, simulate_ros_woba, woba_sd,
                             woba_to_wrcplus, wrcplus_to_woba)


class TestPriorBlending(unittest.TestCase):
    XW = {2023: 0.320, 2024: 0.340, 2025: 0.330}
    PA = {2023: 100.0, 2024: 200.0, 2025: 300.0}
    REC = {2023: 3, 2024: 4, 2025: 5}

    def test_weighted_mean_by_hand(self):
        # weights = PA*rec = 300, 800, 1500 (sum 2600)
        expect = (300 * 0.320 + 800 * 0.340 + 1500 * 0.330) / 2600
        p = blend_prior(self.XW, self.PA, self.REC)
        self.assertAlmostEqual(p["mu_xwoba"], expect, places=12)

    def test_effective_n_by_hand(self):
        # n_eff = (sum w_i*PA_i)^2 / sum(w_i^2*PA_i)
        num = (3 * 100 + 4 * 200 + 5 * 300) ** 2
        den = 9 * 100 + 16 * 200 + 25 * 300
        p = blend_prior(self.XW, self.PA, self.REC)
        self.assertAlmostEqual(p["n_eff"], num / den, places=9)
        # effective n is less than raw PA (weighting costs information)
        self.assertLess(p["n_eff"], sum(self.PA.values()))

    def test_equal_weights_reduce_to_pa_weighted_mean(self):
        rec = {s: 1 for s in self.XW}
        p = blend_prior(self.XW, self.PA, rec)
        expect = float(np.average(list(self.XW.values()),
                                  weights=list(self.PA.values())))
        self.assertAlmostEqual(p["mu_xwoba"], expect, places=12)
        self.assertAlmostEqual(p["n_eff"], sum(self.PA.values()), places=9)

    def test_missing_season_is_skipped(self):
        p = blend_prior({2024: 0.340, 2025: 0.330},
                        {2024: 200.0, 2025: 300.0}, self.REC)
        self.assertEqual(p["seasons"], [2024, 2025])


class TestErosionScenario(unittest.TestCase):
    def test_blend_arithmetic(self):
        # 60/40 blend of .330 healthy and .290 2026-process
        self.assertAlmostEqual(erode_prior(0.330, 0.290, 0.4),
                               0.6 * 0.330 + 0.4 * 0.290, places=12)

    def test_zero_weight_is_identity(self):
        self.assertAlmostEqual(erode_prior(0.330, 0.290, 0.0), 0.330)

    def test_scenarios_separate_when_2026_is_worse(self):
        healthy = 0.336
        eroded = erode_prior(healthy, 0.287, 0.4)
        self.assertLess(eroded, healthy)
        # and the gap scales with the erosion weight
        self.assertLess(erode_prior(healthy, 0.287, 0.5), eroded)


class TestWobaMath(unittest.TestCase):
    def test_sampling_sd_formula(self):
        self.assertAlmostEqual(woba_sd(0.5, 100), 0.05, places=12)
        self.assertAlmostEqual(woba_sd(0.33, 300),
                               math.sqrt(0.33 * 0.67 / 300), places=12)

    def test_conversion_round_trip(self):
        slope, intercept, offset = 671.5, -113.1, -2.2
        w = 0.336
        wrc = woba_to_wrcplus(w, slope, intercept, offset)
        self.assertAlmostEqual(
            float(wrcplus_to_woba(wrc, slope, intercept, offset)), w,
            places=12)

    def test_fit_recovers_exact_linear_relation(self):
        woba = np.array([0.250, 0.300, 0.320, 0.350, 0.400])
        wrc = -113.1 + 671.5 * woba   # exact line -> fit must recover it
        slope, intercept = fit_woba_to_wrcplus(woba, wrc)
        self.assertAlmostEqual(slope, 671.5, places=6)
        self.assertAlmostEqual(intercept, -113.1, places=6)


class TestSimulation(unittest.TestCase):
    def test_seeded_determinism(self):
        a = simulate_ros_woba(0.336, 0.015, 300, n_sims=2000, seed=42)
        b = simulate_ros_woba(0.336, 0.015, 300, n_sims=2000, seed=42)
        self.assertTrue(np.array_equal(a, b))

    def test_different_seeds_differ(self):
        a = simulate_ros_woba(0.336, 0.015, 300, n_sims=2000, seed=42)
        b = simulate_ros_woba(0.336, 0.015, 300, n_sims=2000, seed=43)
        self.assertFalse(np.array_equal(a, b))

    def test_mean_and_spread_are_sane(self):
        mu, sig, n = 0.336, 0.015, 300
        draws = simulate_ros_woba(mu, sig, n, n_sims=50_000, seed=1)
        self.assertAlmostEqual(float(draws.mean()), mu, delta=0.001)
        expect_sd = math.sqrt(sig ** 2 + woba_sd(mu, n) ** 2)
        self.assertAlmostEqual(float(draws.std()), expect_sd, delta=0.001)

    def test_worse_prior_means_lower_rebound_probability(self):
        kw = dict(sigma_talent=0.015, n_pa=300, n_sims=20_000, seed=7)
        thresh = 0.320  # a "league-average" wOBA cutoff
        p_h = (simulate_ros_woba(0.336, **kw) >= thresh).mean()
        p_e = (simulate_ros_woba(0.319, **kw) >= thresh).mean()
        self.assertGreater(p_h, p_e)
        self.assertGreater(p_h - p_e, 0.10)   # a material, not cosmetic, gap


class TestValuationTiming(unittest.TestCase):
    def test_expected_value_arithmetic(self):
        v = expected_values(0.5, low=10.0, high=30.0)
        self.assertAlmostEqual(v["now"], 10.0)
        self.assertAlmostEqual(v["deadline"], 0.5 * 20.0 + 0.5 * 10.0)
        self.assertAlmostEqual(v["offseason"], 0.5 * 30.0 + 0.5 * 10.0)

    def test_ordering_now_le_deadline_le_offseason(self):
        for p in (0.0, 0.25, 0.75, 1.0):
            v = expected_values(p, low=9.6, high=27.9)
            self.assertLessEqual(v["now"], v["deadline"] + 1e-12)
            self.assertLessEqual(v["deadline"], v["offseason"] + 1e-12)

    def test_certain_rebound_hits_the_high_anchor(self):
        v = expected_values(1.0, low=9.6, high=27.9)
        self.assertAlmostEqual(v["offseason"], 27.9)


if __name__ == "__main__":
    unittest.main()
