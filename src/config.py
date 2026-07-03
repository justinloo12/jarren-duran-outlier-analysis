"""Central config: player identity, seasons, paths, HTTP.

Everything downstream imports from here so the project is reusable for a
different player by swapping the PLAYER block and re-running run_all.py.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

# --- Player identity -------------------------------------------------------
PLAYER = {
    "name": "Jarren Duran",
    "mlbam": 680776,        # Baseball Savant / Statcast id
    "fangraphs": 24617,     # FanGraphs id
    "bbref": "duranja01",
    "birthdate": _dt.date(1996, 9, 5),  # -> 2024 season age 27, 2026 age 29
}

# --- Seasons ---------------------------------------------------------------
SEASONS = [2021, 2022, 2023, 2024, 2025, 2026]
OUTLIER_SEASON = 2024                       # the season under scrutiny
CURRENT_SEASON = 2026                       # partial as of analysis date
PARTIAL_SEASONS = {2026}                    # flag incomplete seasons in output

# "Rest of career minus 2024" — the baseline the thesis wants to compare against.
BASELINE_SEASONS = [s for s in SEASONS if s != OUTLIER_SEASON]
# Established-role variant (drops the tiny 2021/2022 cups of coffee) so the
# baseline is not dominated by rookie small-sample noise.
BASELINE_ESTABLISHED = [2023, 2025, 2026]

# --- Statcast era + batted-ball reference ----------------------------------
# Statcast fields available 2015+. estimated_ba/woba_using_speedangle drive the
# "expected" (process) metrics.
LEAGUE_QUAL_PA = 300          # PA floor when computing league-average context
BABIP_LEAGUE_MIN_PA = 300

def season_age(season: int) -> int:
    """FanGraphs-style season age: age on June 30 of that season."""
    ref = _dt.date(season, 6, 30)
    b = PLAYER["birthdate"]
    return ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))

# --- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATCAST_DIR = DATA_DIR / "statcast"
FANGRAPHS_DIR = DATA_DIR / "fangraphs"
FIG_DIR = ROOT / "figures"
OUT_DIR = ROOT / "outputs"

for _d in (DATA_DIR, STATCAST_DIR, FANGRAPHS_DIR, FIG_DIR, OUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- HTTP ------------------------------------------------------------------
# macOS python.org builds fail urllib SSL verification; use requests (certifi).
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
HTTP_TIMEOUT = 30
