"""Pull season batting tables from the FanGraphs JSON leaders API.

pybaseball's batting_stats() targets FanGraphs' deprecated leaders-legacy
endpoint (now HTTP 403), so we hit the current JSON API directly. One request
per season returns the full league (qual=0), which gives us both Duran's line
and the league-wide frame used for league averages and the aging curve.
"""
from __future__ import annotations

import re
import time

import pandas as pd
import requests

from . import config as C

_API = "https://www.fangraphs.com/api/leaders/major-league/data"
_TAG = re.compile(r"<[^>]+>")

# Columns we care about (FanGraphs stores rates as decimals, e.g. 0.217 = 21.7%).
KEEP = [
    "Name", "Team", "Season", "Age", "G", "PA", "AB", "H", "HR",
    "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP",
    "wOBA", "xwOBA", "wRC+", "WAR",
    "K%", "BB%", "Barrel%", "HardHit%", "EV", "maxEV", "LA",
    "O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%",
    "Contact%", "SwStr%", "GB%", "FB%", "LD%", "Pull%", "Cent%", "Oppo%",
    # speed / baserunning / defense (FG API key names)
    "Spd", "BaseRunning", "UBR", "wBsR", "Defense", "Fielding", "Offense",
]


def _clean(txt) -> str:
    return _TAG.sub("", str(txt)).strip()


def fetch_fg_season(season: int, qual: int = 0) -> pd.DataFrame:
    """Full-league batting table for one season."""
    params = {
        "pos": "all", "stats": "bat", "lg": "all", "qual": qual,
        "season": season, "season1": season, "month": 0, "team": 0,
        "pageitems": 2000000000, "pagenum": 1, "ind": 0, "type": 8,
    }
    r = requests.get(_API, params=params, headers=C.HTTP_HEADERS,
                     timeout=C.HTTP_TIMEOUT)
    r.raise_for_status()
    rows = r.json().get("data", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Name"] = df["Name"].map(_clean)
    if "Team" in df:
        df["Team"] = df["Team"].map(_clean)
    keep = [c for c in KEEP if c in df.columns]
    df = df[keep].copy()
    for c in df.columns:
        if c not in ("Name", "Team"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def fetch_all(seasons=C.SEASONS, save: bool = True) -> pd.DataFrame:
    """Fetch every season, cache each league table, return Duran's rows."""
    duran_rows = []
    for s in seasons:
        df = fetch_fg_season(s)
        if save and not df.empty:
            df.to_csv(C.FANGRAPHS_DIR / f"league_{s}.csv", index=False)
        d = df[df["Name"] == C.PLAYER["name"]]
        if not d.empty:
            duran_rows.append(d)
        print(f"  [FG] {s}: league rows={len(df):>4}  duran rows={len(d)}")
        time.sleep(0.8)  # be polite to the API
    out = (pd.concat(duran_rows, ignore_index=True)
           if duran_rows else pd.DataFrame())
    if save and not out.empty:
        out = out.sort_values("Season")
        out.to_csv(C.DATA_DIR / "duran_fangraphs_seasons.csv", index=False)
    return out


def load_league(season: int) -> pd.DataFrame:
    p = C.FANGRAPHS_DIR / f"league_{season}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


if __name__ == "__main__":
    print(fetch_all().to_string())
