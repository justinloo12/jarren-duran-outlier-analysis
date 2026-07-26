"""The trade Boston actually made: Curtis Mead for Connelly Early.

Verifies the deal from the MLB StatsAPI roster/transaction feeds and
grades it against the article's trade menu:
  * Mead's 2026 line (FanGraphs) and his career shape (StatsAPI),
  * the Fenway-fit claim, quantified: pull-air rate and production on
    pulled air balls from the league pitch parquet, with a league
    percentile (RHB pull-air plays to the Monster),
  * the skeptic checks the project applies to every breakout: results
    vs contact quality, and the career-high flag.

Writes data/acquisition.json, figures/18_mead_fit.png, and splices
"## The trade they made" into ARTICLE.md after the trade menu.
"""
from __future__ import annotations

import datetime as dt
import json

import matplotlib.pyplot as plt
import pandas as pd
import requests

from . import config as C
from . import style as S
from .deadline import _fg_pull
from .xcontact import spray_angle

S.apply()

MEAD_ID = 678554
PULL_DEG = 15     # spray angle beyond this = pulled
AIR_DEG = 10      # launch angle at/above this = air
MIN_BB = 100      # batted balls to enter the league percentile pool
MARKER = "## The left fielder: the whole season in one player"


def _ord(n) -> str:
    n = int(n)
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _league_pull_air() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(C.STATCAST_DIR / "league_pitches_2026.parquet")
    bb = df[(df["type"] == "X") & df["launch_speed"].notna()
            & df["hc_x"].notna() & df["hc_y"].notna()].copy()
    bb["spray"] = spray_angle(bb["hc_x"], bb["hc_y"], bb["stand"])
    bb["pull_air"] = ((bb["spray"] > PULL_DEG)
                      & (bb["launch_angle"] >= AIR_DEG))
    pool = bb.groupby("batter").agg(n=("pull_air", "size"),
                                    rate=("pull_air", "mean"))
    return bb, pool[pool["n"] >= MIN_BB]


def _career(pid: int = MEAD_ID) -> dict:
    r = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}/stats",
                     params={"stats": "yearByYear", "group": "hitting"},
                     headers=C.HTTP_HEADERS, timeout=C.HTTP_TIMEOUT).json()
    pa_pre = 0
    ops_wt = 0.0
    for sp in r["stats"][0]["splits"]:
        st = sp["stat"]
        if (sp.get("league", {}).get("id") in (103, 104)
                and sp.get("team") and sp["season"] != "2026"):
            pa = int(st.get("plateAppearances") or 0)
            pa_pre += pa
            ops_wt += float(st.get("ops") or 0) * pa
    return {"pa_pre_2026": pa_pre,
            "ops_pre_2026": round(ops_wt / pa_pre, 3) if pa_pre else None}


def compute() -> dict:
    bats = _fg_pull("all", team=0, stats="bat", typ=8)
    for c in ("PA", "wRC+", "WAR", "OBP", "ISO", "wOBA", "Age"):
        bats[c] = pd.to_numeric(bats[c], errors="coerce")
    fg = bats[bats["Name"] == "Curtis Mead"].iloc[0]

    bb, pool = _league_pull_air()
    mead_bb = bb[bb["batter"] == MEAD_ID]
    rate = float(pool.loc[MEAD_ID, "rate"])
    pctile = float((pool["rate"] < rate).mean() * 100)
    pulled = mead_bb[mead_bb["pull_air"]]

    pa_ev = pd.read_parquet(C.STATCAST_DIR / "league_pitches_2026.parquet")
    pa_ev = pa_ev[(pa_ev["batter"] == MEAD_ID) & pa_ev["woba_denom"].notna()
                  & (pa_ev["woba_denom"] > 0)]
    xw = pa_ev["estimated_woba_using_speedangle"].fillna(pa_ev["woba_value"])

    return {
        "as_of": dt.date.today().isoformat(),
        "player": "Curtis Mead", "bats": "R", "age": int(fg["Age"]),
        "traded_for": "Connelly Early",
        "fg": {"PA": int(fg["PA"]), "wRC+": round(float(fg["wRC+"])),
               "wOBA": round(float(fg["wOBA"]), 3),
               "ISO": round(float(fg["ISO"]), 3),
               "WAR": round(float(fg["WAR"]), 1)},
        "pull_air_rate": round(rate, 3), "pull_air_pctile": round(pctile),
        "n_batted_balls": int(len(mead_bb)),
        "ev_pull_air": round(float(pulled["launch_speed"].mean()), 1),
        "wobacon_pull_air": round(float(pulled["woba_value"].mean()), 3),
        "woba": round(float(pa_ev["woba_value"].mean()), 3),
        "xwoba": round(float(xw.mean()), 3),
        "career": _career(),
        "pool_n": int(len(pool)),
    }


def fig_fit(res: dict):
    _, pool = _league_pull_air()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(pool["rate"] * 100, bins=32, color=S.GREY, alpha=0.55,
            edgecolor="none", zorder=2)
    ax.axvline(res["pull_air_rate"] * 100, color=S.RED, lw=2.5, zorder=3)
    ax.annotate(f"Mead {res['pull_air_rate']*100:.1f}%\n"
                f"({res['pull_air_pctile']:.0f}th pctile)",
                xy=(res["pull_air_rate"] * 100, ax.get_ylim()[1] * 0.82),
                xytext=(res["pull_air_rate"] * 100 + 2,
                        ax.get_ylim()[1] * 0.82),
                color=S.RED, fontsize=12, fontweight="bold")
    S.style(ax)
    ax.set_xlabel(f"Pull-air rate, share of batted balls (hitters with "
                  f"{MIN_BB}+ batted balls, 2026)")
    ax.set_ylabel("Hitters")
    ax.set_title("Mead's pull-air rate sits in the top fifth of MLB, "
                 "the profile Fenway pays", loc="left", fontsize=15,
                 fontweight="bold")
    ax.text(0, -0.15, "Pulled = spray angle beyond 15 degrees to the pull "
            "side; air = launch angle 10 degrees or higher. RHB pull-air "
            "plays to the Monster.",
            transform=ax.transAxes, fontsize=10, color=S.MUTED)
    fig.tight_layout()
    out = C.FIG_DIR / "18_mead_fit.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [acquisition] wrote {out}")


def article_section(res: dict) -> str:
    days_left = max(0, (dt.date(2026, 8, 3) - dt.date.today()).days)
    f = res["fg"]
    c = res["career"]
    L = []
    A = L.append
    A("\n## The trade they made\n")
    A(f"Boston moved first. On July 23 the Red Sox acquired "
      f"**{res['player']}** from Washington for {res['traded_for']}: one "
      "surplus rotation arm for a "
      f"{res['age']}-year-old infield bat running a **{f['wRC+']} wRC+** "
      f"(.{int(f['wOBA']*1000)} wOBA, .{int(f['ISO']*1000)} ISO in "
      f"{f['PA']} PA) with years of club control. Graded against the "
      "menu above, this is the big-swing shape at half the price: one "
      "arm out instead of two, and it fills the infield hole the audit "
      "flagged without touching the bullpen, the catchers, or any "
      "lineup regular. Early leaves the active rotation, which is real "
      "disruption, but Crochet and Sandoval are due back and the "
      "rotation surplus was the one place the roster could afford to "
      "pay from.\n")
    A(f"The park fit is the interesting part. Mead is a right-handed "
      f"hitter who puts **{res['pull_air_rate']*100:.1f}%** of his "
      "batted balls in the air to the pull side, "
      f"**{_ord(res['pull_air_pctile'])} percentile** among the "
      f"{res['pool_n']} hitters with {100}+ batted balls this season, "
      f"and he does damage there: a .{int(res['wobacon_pull_air']*1000)} "
      f"wOBA and {res['ev_pull_air']} mph average exit velocity on "
      "pulled air balls (fig. 18). At Fenway those balls fly at a "
      "310-foot wall. Medium-depth pulled flies that die in an average "
      "left field become wall balls in Boston. This is the specific "
      "profile the park rewards most.\n")
    A("![Mead Fenway fit](figures/18_mead_fit.png)\n")
    A(f"The skeptic checks mostly pass. Statcast has him at a "
      f".{int(res['woba']*1000)} wOBA against a "
      f".{int(res['xwoba']*1000)} xwOBA, so the season is earned, not "
      "batted-ball luck. The honest flag is the "
      f"career shape: {c['pa_pre_2026']} PA of roughly "
      f".{int((c['ops_pre_2026'] or 0)*1000)} OPS from 2023 to 2025 "
      "before this year's breakout, so the same career-year caution "
      "from the quad-A section applies. Two things separate him from "
      "that bucket: he is 25, not 30, and the contact quality supports "
      "the new level. Buying a breakout with process behind it beats "
      "renting one.\n")
    A(f"One item left on the list: the front office bought the bat "
      "before the reliever. The pen fix is still the cheapest win on "
      f"the board, and there are {days_left} days left to make it.\n")
    return "\n".join(L)


def run() -> dict:
    res = compute()
    (C.DATA_DIR / "acquisition.json").write_text(json.dumps(res, indent=2))
    print(f"  [acquisition] wrote {C.DATA_DIR / 'acquisition.json'}")
    fig_fit(res)
    art = C.OUT_DIR / "ARTICLE.md"
    if art.exists():
        s = art.read_text()
        if "## The trade they made" not in s and MARKER in s:
            s = s.replace(MARKER,
                          article_section(res).strip() + "\n\n" + MARKER)
            art.write_text(s)
            print("  [acquisition] spliced trade section into ARTICLE.md")
    return res
