"""Pull pitch-level Statcast and the Savant expected-stats leaderboard.

Pitch-level data is the authoritative source for the *process* metrics the
thesis hinges on (chase/whiff/zone-contact, barrel%, hard-hit%, xBABIP), and
lets us compute them independently of FanGraphs.
"""
from __future__ import annotations

import pandas as pd

from pybaseball import statcast_batter, statcast_batter_expected_stats
from pybaseball import cache as _pb_cache

from . import config as C

_pb_cache.enable()  # cache raw pulls so reruns are fast


def fetch_pitches(season: int, save: bool = True) -> pd.DataFrame:
    """All pitches Duran saw in a season (Mar 1 - Nov 15 covers reg + post)."""
    start, end = f"{season}-03-01", f"{season}-11-15"
    df = statcast_batter(start, end, C.PLAYER["mlbam"])
    if df is None:
        df = pd.DataFrame()
    if save and not df.empty:
        df.to_csv(C.STATCAST_DIR / f"duran_pitches_{season}.csv", index=False)
    print(f"  [SC] {season}: pitches={len(df)}")
    return df


def fetch_expected(season: int, save: bool = True) -> pd.DataFrame:
    """Savant expected-stats leaderboard row for Duran (est_woba etc.)."""
    try:
        lb = statcast_batter_expected_stats(season, minPA=1)
    except Exception as e:  # partial/early seasons can 500
        print(f"  [SC] expected {season}: unavailable ({e})")
        return pd.DataFrame()
    d = lb[lb["player_id"] == C.PLAYER["mlbam"]].copy()
    if not d.empty:
        d["season"] = season
    if save and not d.empty:
        d.to_csv(C.STATCAST_DIR / f"duran_expected_{season}.csv", index=False)
    return d


def fetch_all(seasons=C.SEASONS):
    exp = []
    for s in seasons:
        fetch_pitches(s)
        e = fetch_expected(s)
        if not e.empty:
            exp.append(e)
    if exp:
        allexp = pd.concat(exp, ignore_index=True).sort_values("season")
        allexp.to_csv(C.DATA_DIR / "duran_expected_stats.csv", index=False)


def load_pitches(season: int) -> pd.DataFrame:
    p = C.STATCAST_DIR / f"duran_pitches_{season}.csv"
    return pd.read_csv(p, low_memory=False) if p.exists() else pd.DataFrame()


if __name__ == "__main__":
    fetch_all()
