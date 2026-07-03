"""Minor-league + MLB year-by-year track record via the MLB Stats API.

Provides pre-MLB baseline context (Duran's contact/speed profile before 2024)
and a clean traditional MLB line to sit alongside the FanGraphs advanced table.
"""
from __future__ import annotations

import pandas as pd
import requests

from . import config as C

_BASE = "https://statsapi.mlb.com/api/v1/people/{pid}/stats"
# sportId -> level label (11 AAA, 12 AA, 13 A+, 14 A, 16 Rookie), 1 = MLB
_LEVELS = {1: "MLB", 11: "AAA", 12: "AA", 13: "A+", 14: "A", 16: "Rk"}


def _pull(sport_id: int) -> list[dict]:
    url = _BASE.format(pid=C.PLAYER["mlbam"])
    params = {"stats": "yearByYear", "group": "hitting", "sportId": sport_id}
    r = requests.get(url, params=params, headers=C.HTTP_HEADERS,
                     timeout=C.HTTP_TIMEOUT)
    r.raise_for_status()
    stats = r.json().get("stats", [])
    if not stats:
        return []
    out = []
    for sp in stats[0].get("splits", []):
        st = sp.get("stat", {})
        out.append({
            "season": int(sp.get("season")),
            "level": _LEVELS[sport_id],
            "team": sp.get("team", {}).get("name"),
            "league": sp.get("league", {}).get("name"),
            "G": st.get("gamesPlayed"),
            "PA": st.get("plateAppearances"),
            "AB": st.get("atBats"),
            "H": st.get("hits"),
            "HR": st.get("homeRuns"),
            "BB": st.get("baseOnBalls"),
            "SO": st.get("strikeOuts"),
            "SB": st.get("stolenBases"),
            "AVG": _f(st.get("avg")),
            "OBP": _f(st.get("obp")),
            "SLG": _f(st.get("slg")),
            "OPS": _f(st.get("ops")),
            "BABIP": _f(st.get("babip")),
        })
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch_all(save: bool = True) -> pd.DataFrame:
    rows = []
    for sid in _LEVELS:
        try:
            rows.extend(_pull(sid))
        except Exception as e:
            print(f"  [MiLB] sportId {sid} failed: {e}")
    df = pd.DataFrame(rows).sort_values(["season", "level"]).reset_index(drop=True)
    if save and not df.empty:
        mlb = df[df["level"] == "MLB"]
        milb = df[df["level"] != "MLB"]
        mlb.to_csv(C.DATA_DIR / "duran_mlb_yearbyyear.csv", index=False)
        milb.to_csv(C.DATA_DIR / "duran_milb.csv", index=False)
    print(f"  [MiLB] pulled {len(df)} level-seasons "
          f"({(df['level'] != 'MLB').sum()} MiLB)")
    return df


if __name__ == "__main__":
    print(fetch_all().to_string())
