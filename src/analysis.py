"""Core analysis: is 2024 the outlier, on results AND on process?

Design note on statistics
--------------------------
We have six season-points (one partial), so we do NOT pretend those six numbers
form a distribution and run an outlier test on n=6. Instead we treat each
season's *rate stats* as estimates with sampling error (binomial SE on the
correct denominator: balls-in-play for BABIP/barrel/hard-hit, out-of-zone
pitches for chase, swings for whiff, in-zone swings for zone-contact) and ask:

  1. Does 2024 differ from the pooled "rest-of-career-minus-2024" baseline by
     more than sampling noise?  (two-proportion z-test)
  2. Is the 2024 gap on *results* (wOBA, BABIP) bigger than the gap on
     *process* (xwOBA, barrel%, hard-hit%, xBABIP, swing decisions)?
  3. Do 2025 and 2026 agree with each other, or is 2026 a further decline?

That keeps the claims honest given the tiny sample.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from . import config as C
from . import fetch_fangraphs as fg
from .statcast_metrics import season_metrics
from .fetch_statcast import load_pitches

NORM_P = None  # lazily use math.erf for two-sided p-values


# --- small stats helpers ---------------------------------------------------
def two_sided_p(z: float) -> float:
    if z is None or math.isnan(z):
        return float("nan")
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def two_prop_test(p1, n1, p2, n2) -> dict:
    """Compare proportion 1 (e.g. 2024) to proportion 2 (baseline)."""
    if not n1 or not n2 or any(map(_nan, (p1, p2))):
        return {"diff": np.nan, "z": np.nan, "p": np.nan,
                "ci_lo": np.nan, "ci_hi": np.nan}
    pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
    se_pool = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se_pool if se_pool else np.nan
    se_diff = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p1 - p2
    return {"diff": diff, "z": z, "p": two_sided_p(z),
            "ci_lo": diff - 1.96 * se_diff, "ci_hi": diff + 1.96 * se_diff}


def _nan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


# --- assemble the season table --------------------------------------------
def load_season_table() -> pd.DataFrame:
    """Merge FanGraphs + Statcast-derived metrics + Savant expected stats."""
    fgs = pd.read_csv(C.DATA_DIR / "duran_fangraphs_seasons.csv")
    fgs = fgs.rename(columns={"Season": "season"})
    sc = pd.read_csv(C.DATA_DIR / "duran_statcast_metrics.csv")
    df = fgs.merge(sc, on="season", how="outer")
    exp_p = C.DATA_DIR / "duran_expected_stats.csv"
    if exp_p.exists():
        exp = pd.read_csv(exp_p)[["season", "woba", "est_woba", "ba",
                                  "est_ba", "slg", "est_slg"]]
        df = df.merge(exp, on="season", how="left")
    df["age"] = df["season"].map(C.season_age)
    df["partial"] = df["season"].isin(C.PARTIAL_SEASONS)
    return df.sort_values("season").reset_index(drop=True)


def pa_weighted_baseline(df: pd.DataFrame, cols, seasons) -> dict:
    """PA-weighted mean of a metric across a set of seasons."""
    sub = df[df["season"].isin(seasons)]
    w = sub["PA"].fillna(0).to_numpy()
    out = {}
    for c in cols:
        if c not in sub:
            out[c] = np.nan
            continue
        v = sub[c].to_numpy(dtype=float)
        m = ~np.isnan(v) & (w > 0)
        out[c] = float(np.average(v[m], weights=w[m])) if m.any() else np.nan
    return out


def pooled_statcast(seasons) -> dict:
    """Recompute process metrics on the concatenated pitches of `seasons`.

    Gives a properly pooled baseline proportion + denominator for tests.
    """
    frames = [load_pitches(s) for s in seasons]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return {}
    return season_metrics(pd.concat(frames, ignore_index=True),
                          season=-1)


def league_babip(season: int) -> float:
    lg = fg.load_league(season)
    if lg.empty or "BABIP" not in lg:
        return np.nan
    q = lg[lg["PA"] >= C.BABIP_LEAGUE_MIN_PA]
    return float(q["BABIP"].mean()) if len(q) else np.nan


# --- the tests -------------------------------------------------------------
PROC_PROPS = {   # metric -> (per-season p col, per-season den col)
    "chase":    ("sc_chase_pct", "sc_chase_den"),
    "whiff":    ("sc_whiff_pct", "sc_whiff_den"),
    "zcontact": ("sc_zcontact_pct", "sc_zcontact_den"),
    "barrel":   ("sc_barrel_pct", "sc_barrel_den"),
    "hardhit":  ("sc_hardhit_pct", "sc_hardhit_den"),
    "babip":    ("sc_babip", "sc_babip_den"),
}


def run(save: bool = True) -> dict:
    df = load_season_table()
    y = C.OUTLIER_SEASON
    row24 = df[df["season"] == y].iloc[0]

    res = {"player": C.PLAYER["name"], "outlier_season": y, "seasons": {}}

    # -- Per-season snapshot for the memo/plots ----------------------------
    for _, r in df.iterrows():
        res["seasons"][int(r["season"])] = {
            k: (None if pd.isna(r.get(k)) else float(r.get(k)))
            for k in ["age", "PA", "AVG", "OBP", "SLG", "wOBA", "xwOBA",
                      "wRC+", "WAR", "BABIP", "ISO", "Barrel%", "HardHit%",
                      "O-Swing%", "Z-Contact%", "Contact%", "SwStr%", "Spd",
                      "BaseRunning", "Defense", "Fielding", "Offense",
                      "sc_babip", "sc_xbabip", "sc_barrel_pct",
                      "sc_hardhit_pct", "sc_chase_pct", "sc_whiff_pct",
                      "sc_zcontact_pct", "sc_EV", "est_woba", "woba"]
            if k in df.columns
        }
        res["seasons"][int(r["season"])]["partial"] = bool(r["partial"])

    # -- (1) 2024 vs pooled rest-of-career-minus-2024 baseline -------------
    m24 = season_metrics(load_pitches(y), y)
    base_pool = pooled_statcast(C.BASELINE_SEASONS)
    base_pool_est = pooled_statcast(C.BASELINE_ESTABLISHED)

    res["baseline_seasons"] = C.BASELINE_SEASONS
    res["baseline_established"] = C.BASELINE_ESTABLISHED
    res["tests_2024_vs_baseline"] = {}
    for name, key in PROC_PROPS.items():
        p1, n1 = m24.get(key[0]), m24.get(key[1])
        p2, n2 = base_pool.get(key[0]), base_pool.get(key[1])
        t = two_prop_test(p1, n1, p2, n2)
        t.update({"val_2024": p1, "n_2024": n1,
                  "val_baseline": p2, "n_baseline": n2})
        res["tests_2024_vs_baseline"][name] = t

    # -- (2) results vs process gap in 2024 --------------------------------
    res["results_vs_process"] = {
        "woba": _num(row24.get("wOBA")),
        "xwoba_fg": _num(row24.get("xwOBA")),
        "woba_minus_xwoba": _diff(row24.get("wOBA"), row24.get("xwOBA")),
        "woba_savant": _num(row24.get("woba")),
        "est_woba_savant": _num(row24.get("est_woba")),
        "woba_minus_est_savant": _diff(row24.get("woba"),
                                       row24.get("est_woba")),
        "babip": m24.get("sc_babip"),
        "xbabip": m24.get("sc_xbabip"),
        "babip_minus_xbabip": _diff(m24.get("sc_babip"), m24.get("sc_xbabip")),
    }

    # -- (2b) speed-adjusted luck: Statcast xstats ignore sprint speed, so a
    # burner like Duran *should* chronically out-hit his xwOBA (infield hits,
    # stretched doubles). The honest luck estimate for any season is its
    # wOBA−xwOBA gap measured against his OWN typical gap, not against zero.
    base_rows = df[df["season"].isin(C.BASELINE_SEASONS)]
    gaps, weights = [], []
    for _, r in base_rows.iterrows():
        g = _diff(r.get("wOBA"), r.get("xwOBA"))
        if g is not None and not pd.isna(r.get("PA")):
            gaps.append(g)
            weights.append(float(r["PA"]))
    personal_gap = (float(np.average(gaps, weights=weights))
                    if gaps else np.nan)
    gap24 = res["results_vs_process"]["woba_minus_xwoba"]
    row26 = df[df["season"] == 2026]
    gap26 = (_diff(row26["wOBA"].iloc[0], row26["xwOBA"].iloc[0])
             if len(row26) else None)
    res["speed_adjusted"] = {
        "personal_gap_baseline": _num(personal_gap),
        "gap_by_season": {int(r["season"]): _diff(r.get("wOBA"), r.get("xwOBA"))
                          for _, r in df.iterrows()},
        "gap_2024": gap24,
        "gap_2024_excess": (None if gap24 is None or pd.isna(personal_gap)
                            else gap24 - personal_gap),
        "gap_2026": gap26,
        "gap_2026_deficit": (None if gap26 is None or pd.isna(personal_gap)
                             else gap26 - personal_gap),
    }

    # -- (2c) park robustness: is the xwOBA overperformance a Fenway artifact?
    # Compute home/road wOBA-xwOBA gaps from pitch data. wRC+ is already
    # park-adjusted; this checks the *luck* analysis specifically.
    res["park_check"] = _home_road_gaps()

    # -- (3) BABIP: 2024 vs career-ex-2024, vs league, vs profile ----------
    res["babip"] = {
        "2024": m24.get("sc_babip"),
        "2024_xbabip": m24.get("sc_xbabip"),
        "baseline_all": base_pool.get("sc_babip"),
        "baseline_established": base_pool_est.get("sc_babip"),
        "league_2024": league_babip(y),
        "by_season": {int(r["season"]): _num(r.get("sc_babip"))
                      for _, r in df.iterrows()},
        "league_by_season": {s: league_babip(s) for s in C.SEASONS},
        "xbabip_by_season": {int(r["season"]): _num(r.get("sc_xbabip"))
                             for _, r in df.iterrows()},
    }
    res["babip"]["test_vs_baseline"] = two_prop_test(
        m24.get("sc_babip"), m24.get("sc_babip_den"),
        base_pool.get("sc_babip"), base_pool.get("sc_babip_den"))
    res["babip"]["test_vs_league"] = _one_sample_prop(
        m24.get("sc_babip"), m24.get("sc_babip_den"), league_babip(y))

    # -- (4) plate-discipline persistence (approach change?) ---------------
    disc = {}
    for _, r in df.iterrows():
        disc[int(r["season"])] = {
            "chase": _num(r.get("sc_chase_pct")),
            "whiff": _num(r.get("sc_whiff_pct")),
            "zcontact": _num(r.get("sc_zcontact_pct")),
            "swstr": _num(r.get("sc_swstr_pct")),
        }
    res["plate_discipline"] = disc

    # -- (5) 2025 vs 2026 consistency --------------------------------------
    res["y25_vs_y26"] = {}
    if 2025 in df["season"].values and 2026 in df["season"].values:
        m25 = season_metrics(load_pitches(2025), 2025)
        m26 = season_metrics(load_pitches(2026), 2026)
        for name, key in PROC_PROPS.items():
            res["y25_vs_y26"][name] = two_prop_test(
                m26.get(key[0]), m26.get(key[1]),
                m25.get(key[0]), m25.get(key[1]))
        res["y25_vs_y26"]["woba_2025"] = _num(
            df[df.season == 2025]["wOBA"].iloc[0])
        res["y25_vs_y26"]["woba_2026"] = _num(
            df[df.season == 2026]["wOBA"].iloc[0])
        res["y25_vs_y26"]["wrcplus_2025"] = _num(
            df[df.season == 2025]["wRC+"].iloc[0])
        res["y25_vs_y26"]["wrcplus_2026"] = _num(
            df[df.season == 2026]["wRC+"].iloc[0])

    if save:
        with open(C.DATA_DIR / "analysis_results.json", "w") as f:
            json.dump(res, f, indent=2, default=_json_default)
        df.to_csv(C.DATA_DIR / "season_metrics.csv", index=False)
    return res


def _home_road_gaps() -> dict:
    """wOBA, xwOBA and the gap, split home (Fenway) vs road, career + 2024/26.

    xwOBA per PA uses estimated_woba_using_speedangle on batted balls and the
    actual woba_value on non-contact events (K/BB/HBP), per the standard
    construction. Regular season only.
    """
    frames = []
    for s in C.SEASONS:
        d = load_pitches(s)
        if not d.empty:
            d = d.copy()
            d["season"] = s
            frames.append(d)
    if not frames:
        return {}
    df = pd.concat(frames, ignore_index=True)
    if "game_type" in df.columns:
        df = df[df["game_type"] == "R"]
    df["home"] = df["home_team"] == "BOS"
    ev = df[df["woba_denom"].notna() & (df["woba_denom"] > 0)].copy()
    ev["x_contrib"] = ev["estimated_woba_using_speedangle"].where(
        ev["estimated_woba_using_speedangle"].notna(), ev["woba_value"])

    def _agg(g):
        den = g["woba_denom"].sum()
        return {"PA": int(den),
                "woba": float(g["woba_value"].sum() / den),
                "xwoba": float(g["x_contrib"].sum() / den),
                "gap": float((g["woba_value"].sum()
                              - g["x_contrib"].sum()) / den)}

    out = {"career": {}, "by_season": {}}
    for home, label in [(True, "home"), (False, "road")]:
        out["career"][label] = _agg(ev[ev["home"] == home])
    for s in (C.OUTLIER_SEASON, 2026):
        sub = ev[ev["season"] == s]
        if len(sub):
            out["by_season"][s] = {
                label: _agg(sub[sub["home"] == home])
                for home, label in [(True, "home"), (False, "road")]}
    return out


def _one_sample_prop(p, n, target) -> dict:
    if _nan(p) or _nan(target) or not n:
        return {"diff": np.nan, "z": np.nan, "p": np.nan}
    se = math.sqrt(target * (1 - target) / n)
    z = (p - target) / se if se else np.nan
    return {"diff": p - target, "z": z, "p": two_sided_p(z),
            "target": target}


def _num(x):
    return None if pd.isna(x) else float(x)


def _diff(a, b):
    if pd.isna(a) or pd.isna(b):
        return None
    return float(a) - float(b)


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float) and math.isnan(o):
        return None
    return str(o)


if __name__ == "__main__":
    import pprint
    pprint.pprint(run())
