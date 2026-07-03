"""Pull outfielder cohorts from the FanGraphs API for peer comparison.

Two things:
  * Red Sox outfielders (team=3) for 2025 and 2026 -> teammate comparison.
  * League-wide outfielders (team=0) for 2026 -> the broad salary-vs-output
    scatter cohort and league-average OF benchmarks.
"""
from __future__ import annotations

import re
import time

import pandas as pd
import requests

from . import config as C

_API = "https://www.fangraphs.com/api/leaders/major-league/data"
_TAG = re.compile(r"<[^>]+>")
BOSTON_TEAM_ID = 3

KEEP = ["Name", "Team", "Season", "Age", "G", "PA", "AB", "HR",
        "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP", "wOBA", "xwOBA",
        "wRC+", "WAR", "K%", "BB%", "Barrel%", "HardHit%", "EV",
        "O-Swing%", "Z-Contact%", "Contact%", "SwStr%", "Spd", "BsR",
        "Def", "Off"]


def _clean(t):
    return _TAG.sub("", str(t)).strip()


def _pull(season: int, team: int, pos: str = "of") -> pd.DataFrame:
    params = {"pos": pos, "stats": "bat", "lg": "all", "qual": 0,
              "season": season, "season1": season, "month": 0, "team": team,
              "pageitems": 5000, "pagenum": 1, "ind": 0, "type": 8}
    r = requests.get(_API, params=params, headers=C.HTTP_HEADERS,
                     timeout=C.HTTP_TIMEOUT)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("data", []))
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


def fetch(save: bool = True):
    redsox = []
    for s in (2025, 2026):
        d = _pull(s, BOSTON_TEAM_ID, "of")
        d = d[d["PA"] >= 20]
        redsox.append(d)
        print(f"  [OF] Red Sox {s}: {len(d)} OF")
        time.sleep(0.7)
    redsox = pd.concat(redsox, ignore_index=True)

    league_of = _pull(2026, 0, "of")
    print(f"  [OF] league OF 2026: {len(league_of)}")

    if save:
        redsox.to_csv(C.DATA_DIR / "redsox_of.csv", index=False)
        league_of.to_csv(C.DATA_DIR / "league_of_2026.csv", index=False)
    return redsox, league_of


if __name__ == "__main__":
    fetch()
