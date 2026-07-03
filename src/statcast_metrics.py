"""Compute season process metrics directly from pitch-level Statcast.

This is the independent, authoritative view of *contact quality and swing
decisions* — the heart of the "did he actually hit it better, or did it just
fall in?" question. Every rate comes with a binomial standard error so we can
test differences between seasons instead of eyeballing point estimates.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config as C
from .fetch_statcast import load_pitches

# Pitch `description` classification.
SWING = {"swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
         "hit_into_play", "foul_bunt", "missed_bunt"}
CONTACT = {"foul", "foul_tip", "hit_into_play", "foul_bunt"}
HIT_EVENTS = {"single", "double", "triple", "home_run"}


def _se(p: float, n: int) -> float:
    """Binomial standard error of a proportion."""
    if not n or p is None or (isinstance(p, float) and math.isnan(p)):
        return float("nan")
    return math.sqrt(max(p * (1 - p), 0) / n)


def season_metrics(df: pd.DataFrame, season: int) -> dict:
    """Reduce a season of pitches to a dict of metrics + denominators + SEs.

    Regular-season only: the Savant search behind statcast_batter returns
    game types R|PO|S (regular, postseason, spring). We filter to 'R' so the
    process metrics match the regular-season FanGraphs stats they are
    compared against.
    """
    if df.empty:
        return {"season": season}
    d = df.copy()
    if "game_type" in d.columns:
        d = d[d["game_type"] == "R"]
    if d.empty:
        return {"season": season}
    desc = d["description"].fillna("")
    in_zone = d["zone"].between(1, 9)            # 1-9 in zone, 11-14 out
    out_zone = d["zone"].between(11, 14)
    swing = desc.isin(SWING)
    contact = desc.isin(CONTACT)

    n_pitches = len(d)
    n_oz = int(out_zone.sum())
    n_iz = int(in_zone.sum())
    n_swings = int(swing.sum())
    iz_swings = int((in_zone & swing).sum())

    chase = (out_zone & swing).sum() / n_oz if n_oz else np.nan      # O-Swing
    z_swing = (in_zone & swing).sum() / n_iz if n_iz else np.nan
    whiff = (swing & ~contact).sum() / n_swings if n_swings else np.nan
    z_contact = ((in_zone & contact).sum() / iz_swings
                 if iz_swings else np.nan)
    swstr = (swing & ~contact).sum() / n_pitches if n_pitches else np.nan

    # Batted balls (type == 'X').
    bip = d[d["type"] == "X"].copy()
    n_bip = len(bip)
    ev = bip["launch_speed"]
    hard = (ev >= 95).sum() / ev.notna().sum() if ev.notna().sum() else np.nan
    # Statcast barrels: launch_speed_angle == 6.
    barrel = ((bip["launch_speed_angle"] == 6).sum() / n_bip
              if n_bip else np.nan)

    events = bip["events"].fillna("")
    hr = int((events == "home_run").sum())
    hits_ip = int(events.isin(HIT_EVENTS).sum())
    # BABIP = (H - HR) / (BIP - HR); BIP already includes HR and SF outs.
    babip_den = n_bip - hr
    babip = (hits_ip - hr) / babip_den if babip_den else np.nan
    # Expected BABIP from contact quality: mean estimated_ba on non-HR BIP.
    non_hr = bip[events != "home_run"]
    xbabip = (non_hr["estimated_ba_using_speedangle"].mean()
              if len(non_hr) else np.nan)

    return {
        "season": season,
        "sc_pitches": n_pitches,
        "sc_bip": n_bip,
        # denominators for two-proportion tests
        "sc_chase_den": n_oz, "sc_whiff_den": n_swings,
        "sc_zcontact_den": iz_swings, "sc_barrel_den": n_bip,
        "sc_hardhit_den": int(ev.notna().sum()),
        "sc_EV": float(ev.mean()) if ev.notna().any() else np.nan,
        "sc_LA": float(bip["launch_angle"].mean())
        if bip["launch_angle"].notna().any() else np.nan,
        "sc_barrel_pct": barrel, "sc_barrel_se": _se(barrel, n_bip),
        "sc_hardhit_pct": hard,
        "sc_hardhit_se": _se(hard, int(ev.notna().sum())),
        "sc_chase_pct": chase, "sc_chase_se": _se(chase, n_oz),
        "sc_zswing_pct": z_swing, "sc_zswing_se": _se(z_swing, n_iz),
        "sc_whiff_pct": whiff, "sc_whiff_se": _se(whiff, n_swings),
        "sc_zcontact_pct": z_contact, "sc_zcontact_se": _se(z_contact, iz_swings),
        "sc_swstr_pct": swstr,
        "sc_babip": babip, "sc_babip_den": babip_den,
        "sc_babip_se": _se(babip, babip_den),
        "sc_xbabip": xbabip,
    }


def build(seasons=C.SEASONS, save: bool = True) -> pd.DataFrame:
    rows = [season_metrics(load_pitches(s), s) for s in seasons]
    df = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    if save:
        df.to_csv(C.DATA_DIR / "duran_statcast_metrics.csv", index=False)
    return df


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 220)
    print(build().to_string())
