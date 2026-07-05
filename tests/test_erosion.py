"""Offline unit tests for the erosion-decomposition pure logic.

Synthetic inputs only — no data files, no network. Every expected value is
hand-computable.

Run from the project root:  python3 -m unittest discover tests
"""
import unittest

import numpy as np
import pandas as pd

from src.erosion import (attack_zone, bat_speed_summary, classify_verdict,
                         down_and_away_mask, pitch_group, rate, reweighted_p,
                         season_decomposition)


class TestPitchGroup(unittest.TestCase):
    def test_fastballs(self):
        for pt in ("FF", "SI", "FC"):
            self.assertEqual(pitch_group(pt), "fastball")

    def test_breaking_and_offspeed(self):
        for pt in ("SL", "ST", "CU", "KC"):
            self.assertEqual(pitch_group(pt), "breaking")
        for pt in ("CH", "FS"):
            self.assertEqual(pitch_group(pt), "offspeed")

    def test_unknown_and_missing(self):
        self.assertEqual(pitch_group("PO"), "other")
        self.assertEqual(pitch_group(None), "other")
        self.assertEqual(pitch_group(float("nan")), "other")


class TestAttackZone(unittest.TestCase):
    # a standard zone: sz_bot 1.5, sz_top 3.5 -> mid 2.5, half-height 1.0
    TOP, BOT = 3.5, 1.5

    def _z(self, px, pz):
        return attack_zone([px], [pz], [self.TOP], [self.BOT])[0]

    def test_dead_center_is_heart(self):
        self.assertEqual(self._z(0.0, 2.5), "heart")

    def test_zone_edge_is_shadow(self):
        # exactly on the horizontal edge: u = 1 -> shadow band (2/3, 4/3]
        self.assertEqual(self._z(0.83, 2.5), "shadow")
        self.assertEqual(self._z(0.0, 3.5), "shadow")

    def test_chase_band(self):
        # 1.5x the half-extent vertically -> chase (4/3 < u <= 2)
        self.assertEqual(self._z(0.0, 2.5 + 1.5), "chase")

    def test_waste(self):
        self.assertEqual(self._z(3.0, 2.5), "waste")

    def test_missing_coordinates_are_unknown(self):
        self.assertEqual(self._z(np.nan, 2.5), "unknown")


class TestBatSpeedSummary(unittest.TestCase):
    def test_competitive_filter_and_rates(self):
        # 40 mph checked swing dropped; comp swings 70, 76, 80
        s = bat_speed_summary([40.0, 70.0, 76.0, 80.0, np.nan])
        self.assertEqual(s["n_swings"], 3)
        self.assertAlmostEqual(s["avg_mph"], (70 + 76 + 80) / 3, places=9)
        self.assertAlmostEqual(s["fast_swing_pct"], 2 / 3, places=12)

    def test_empty_input(self):
        s = bat_speed_summary([np.nan, 30.0])
        self.assertEqual(s["n_swings"], 0)
        self.assertIsNone(s["avg_mph"])

    def test_rate_zero_denominator(self):
        self.assertIsNone(rate(3, 0))
        self.assertAlmostEqual(rate(3, 4), 0.75)


class TestVerdictClassifier(unittest.TestCase):
    def test_bat_speed_down_a_full_mph_is_physical(self):
        v = classify_verdict(-1.2, 0.03, 0.05, -0.02)
        self.assertEqual(v["label"], "physical")

    def test_bat_speed_up_and_chase_up_is_approach(self):
        v = classify_verdict(+1.1, 0.047, 0.09, -0.034)   # Duran's 2026
        self.assertEqual(v["label"], "approach")
        self.assertTrue(v["selling_out"])   # faster bat + more hard-FB whiffs

    def test_bat_speed_flat_chase_flat_is_ambiguous(self):
        v = classify_verdict(0.0, 0.005, 0.0, 0.0)
        self.assertEqual(v["label"], "ambiguous")

    def test_intermediate_drop_is_mixed(self):
        v = classify_verdict(-0.6, 0.03, 0.02, -0.01)
        self.assertEqual(v["label"], "mixed")

    def test_reweighted_probability(self):
        self.assertAlmostEqual(reweighted_p(0.69, 0.47, 0.6),
                               0.6 * 0.69 + 0.4 * 0.47, places=12)
        self.assertAlmostEqual(reweighted_p(0.69, 0.47, 0.5), 0.58, places=12)


class TestDownAndAway(unittest.TestCase):
    def test_lefty_away_is_negative_x(self):
        df = pd.DataFrame({"plate_x": [-0.5, 0.5, -0.5],
                           "plate_z": [1.0, 1.0, 2.0],
                           "sz_bot": [1.5, 1.5, 1.5]})
        m = down_and_away_mask(df, "L")
        # row 0: below + away -> True; row 1: inside -> False;
        # row 2: away but not below -> False
        self.assertEqual(list(m), [True, False, False])

    def test_righty_mirrors(self):
        df = pd.DataFrame({"plate_x": [0.5], "plate_z": [1.0],
                           "sz_bot": [1.5]})
        self.assertTrue(down_and_away_mask(df, "R").iloc[0])
        self.assertFalse(down_and_away_mask(df, "L").iloc[0])


class TestSeasonDecomposition(unittest.TestCase):
    def _pitches(self):
        # 6 regular-season pitches, hand-checkable, + 1 spring pitch dropped
        cols = ["description", "zone", "type", "pitch_type", "release_speed",
                "plate_x", "plate_z", "sz_top", "sz_bot", "stand",
                "game_type", "bat_speed", "swing_length", "attack_angle"]
        rows = [
            # 95+ FB, in zone, swung and missed
            ("swinging_strike", 5, "S", "FF", 97.0, 0.0, 2.5, 3.5, 1.5, "L",
             "R", 76.0, 7.5, 6.0),
            # 95+ FB, in zone, contact (foul)
            ("foul", 5, "S", "FF", 96.0, 0.1, 2.4, 3.5, 1.5, "L",
             "R", 74.0, 7.4, 5.0),
            # slow FB out of zone, taken
            ("ball", 12, "B", "SI", 91.0, 1.2, 2.5, 3.5, 1.5, "L",
             "R", None, None, None),
            # breaking ball down-and-away, chased and missed
            ("swinging_strike", 13, "S", "SL", 84.0, -0.6, 1.0, 3.5, 1.5, "L",
             "R", 71.0, 7.8, 4.0),
            # breaking ball down-and-away, taken
            ("ball", 13, "B", "SL", 83.0, -0.7, 0.9, 3.5, 1.5, "L",
             "R", None, None, None),
            # changeup in zone, hit into play
            ("hit_into_play", 5, "X", "CH", 86.0, 0.0, 2.6, 3.5, 1.5, "L",
             "R", 73.0, 7.2, 8.0),
            # spring training pitch: must be excluded everywhere
            ("swinging_strike", 5, "S", "FF", 99.0, 0.0, 2.5, 3.5, 1.5, "L",
             "S", 80.0, 8.0, 9.0),
        ]
        return pd.DataFrame(rows, columns=cols)

    def test_hand_computed_cuts(self):
        d = season_decomposition(self._pitches(), 2026)
        # 95+ FB: 2 swings, 1 whiff
        self.assertEqual(d["whiff_fb95"]["n"], 2)
        self.assertAlmostEqual(d["whiff_fb95"]["rate"], 0.5)
        # breaking: 1 swing, 1 whiff; 2 out-of-zone, 1 chased
        self.assertAlmostEqual(d["whiff_breaking"]["rate"], 1.0)
        self.assertAlmostEqual(d["chase_breaking"]["rate"], 0.5)
        # down-and-away breaking: 2 seen, 1 swung at
        self.assertEqual(d["chase_brk_down_away"]["n"], 2)
        self.assertAlmostEqual(d["chase_brk_down_away"]["rate"], 0.5)
        # in-zone contact: 3 in-zone swings (FF miss, FF foul, CH in play) -> 2/3
        self.assertAlmostEqual(d["z_contact"]["rate"], 2 / 3)
        # bat tracking: comp swings 76/74/71/73 (spring 80 excluded)
        self.assertEqual(d["bat"]["n_swings"], 4)
        self.assertAlmostEqual(d["bat"]["avg_mph"], (76 + 74 + 71 + 73) / 4)
        self.assertAlmostEqual(d["bat"]["fast_swing_pct"], 0.25)

    def test_empty_frame(self):
        self.assertEqual(season_decomposition(pd.DataFrame(), 2024),
                         {"season": 2024})


if __name__ == "__main__":
    unittest.main()
