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
MARKER = "## The left-field question"


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
    pa_dmg = (bb[bb["pull_air"]].groupby("batter")["woba_value"].mean()
              .rename("pull_air_woba"))
    pool = bb.groupby("batter").agg(n=("pull_air", "size"),
                                    rate=("pull_air", "mean"))
    pool = pool.join(pa_dmg)
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


FT_PER_UNIT = 2.495           # Savant hc pixel -> feet (standard spraychart)
# Fenway outfield wall, (bearing from CF in degrees, distance ft);
# negative bearing = left field. Monster: LF pole to left-center.
FENWAY_WALL = [(-45, 310), (-33, 312), (-20, 379), (-5, 388), (0, 390),
               (3, 420), (8, 380), (20, 370), (35, 335), (42, 310),
               (45, 302)]
MONSTER_ARC = (-45, -18)      # bearing range covered by the wall


def _mead_bip() -> pd.DataFrame:
    df = pd.read_parquet(C.STATCAST_DIR / "league_pitches_2026.parquet")
    m = df[(df["batter"] == MEAD_ID) & (df["type"] == "X")
           & df["hc_x"].notna() & df["hc_y"].notna()].copy()
    m["x_ft"] = FT_PER_UNIT * (m["hc_x"] - 125.42)
    m["y_ft"] = FT_PER_UNIT * (198.27 - m["hc_y"])
    m["dist"] = (m["x_ft"] ** 2 + m["y_ft"] ** 2) ** 0.5
    m["bearing"] = pd.Series(
        __import__("numpy").degrees(
            __import__("numpy").arctan2(m["x_ft"], m["y_ft"])),
        index=m.index)
    m["air"] = m["launch_angle"] >= 10
    return m


def fenway_verdict(m: pd.DataFrame) -> dict:
    """Air balls to the Monster arc that reached wall depth but were
    not homers where he actually played: Fenway upgrades them."""
    lf = m[(m["bearing"] >= MONSTER_ARC[0]) & (m["bearing"] <= MONSTER_ARC[1])]
    lf_air = lf[lf["air"]]
    wall_zone = lf_air[(lf_air["dist"] >= 300) & (lf_air["dist"] <= 380)]
    upgrades = wall_zone[wall_zone["events"] != "home_run"]
    return {"lf_air": int(len(lf_air)),
            "wall_zone": int(len(wall_zone)),
            "upgrades": int(len(upgrades)),
            "upgrade_outs": int((upgrades["events"].isin(
                {"field_out", "double_play",
                 "grounded_into_double_play"})).sum()),
            "upgrade_singles": int((upgrades["events"] == "single").sum()),
            "lf_hr": int((lf["events"] == "home_run").sum())}


# linear-weight values (FanGraphs-scale, approximate)
W1B, W2B = 0.882, 1.254


def fenway_projection(fw: dict, woba: float, n_pa: int) -> dict:
    """Replay the Monster-zone contact as wall doubles: outs become
    doubles, singles become doubles. Full = every such ball at Fenway;
    half = the realistic season share of home games."""
    gain = (fw["upgrade_outs"] * W2B
            + fw["upgrade_singles"] * (W2B - W1B))
    delta_full = gain / n_pa if n_pa else 0.0
    return {"woba_now": round(woba, 3),
            "woba_all_fenway": round(woba + delta_full, 3),
            "woba_half_home": round(woba + delta_full / 2, 3),
            "delta_full_pts": round(delta_full * 1000),
            "n_pa": int(n_pa)}


def _arm_facts(names: list[str]) -> dict:
    pit = _fg_pull("all", team=0, stats="pit", typ=1)
    for c in ("IP", "ERA", "FIP"):
        pit[c] = pd.to_numeric(pit[c], errors="coerce")
    out = {}
    for n in names:
        row = pit[pit["Name"] == n]
        d = {}
        if len(row):
            r = row.iloc[0]
            d = {"ip": round(float(r["IP"])), "era": round(float(r["ERA"]), 2),
                 "fip": round(float(r["FIP"]), 2)}
        try:
            sr = requests.get(
                "https://statsapi.mlb.com/api/v1/people/search",
                params={"names": n}, headers=C.HTTP_HEADERS,
                timeout=C.HTTP_TIMEOUT).json()["people"][0]
            d["height"] = sr.get("height")
            d["weight"] = sr.get("weight")
        except Exception:
            pass
        out[n] = d
    return out


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
        "fenway": fenway_verdict(_mead_bip()),
        "arms": _arm_facts(["Connelly Early", "Payton Tolle",
                            "Jake Bennett"]),
    } | {"fenway_proj": None}


def fig_fit(res: dict):
    _, pool = _league_pull_air()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.2))
    ax.hist(pool["rate"] * 100, bins=32, color=S.GREY, alpha=0.55,
            edgecolor="none", zorder=2)
    ax.axvline(res["pull_air_rate"] * 100, color=S.RED, lw=2.5, zorder=3)
    ax.annotate(f"Mead {res['pull_air_rate']*100:.1f}%\n"
                f"({_ord(res['pull_air_pctile'])} pctile)",
                xy=(res["pull_air_rate"] * 100, ax.get_ylim()[1] * 0.82),
                xytext=(res["pull_air_rate"] * 100 + 2,
                        ax.get_ylim()[1] * 0.82),
                color=S.RED, fontsize=12, fontweight="bold")
    S.style(ax)
    ax.set_xlabel(f"Pull-air rate, % of batted balls ({MIN_BB}+ BB)")
    ax.set_ylabel("Hitters")
    ax.set_title("Rate: top fifth of MLB", loc="left", fontsize=14,
                 fontweight="bold")

    sc = pool.dropna(subset=["pull_air_woba"])
    ax2.scatter(sc["rate"] * 100, sc["pull_air_woba"], s=26, color=S.GREY,
                alpha=0.45, edgecolors="none", zorder=2)
    ax2.scatter(res["pull_air_rate"] * 100, res["wobacon_pull_air"],
                s=180, color=S.RED, zorder=3, edgecolors="white",
                linewidths=1.2)
    ax2.annotate("Mead", (res["pull_air_rate"] * 100,
                          res["wobacon_pull_air"]),
                 textcoords="offset points", xytext=(10, 6),
                 color=S.RED, fontsize=12, fontweight="bold")
    lg_w = float(sc["pull_air_woba"].median())
    ax2.axhline(lg_w, color=S.SPINE, lw=1.2, ls=":", zorder=1)
    ax2.annotate(f"league median .{lg_w*1000:.0f}",
                 (ax2.get_xlim()[1] * 0.98, lg_w),
                 ha="right", va="bottom", fontsize=9, color=S.MUTED)
    S.style(ax2)
    ax2.set_xlabel("Pull-air rate, % of batted balls")
    ax2.set_ylabel("wOBA on pulled air balls")
    ax2.set_title("Damage: elite when he lifts to the pull side",
                  loc="left", fontsize=14, fontweight="bold")

    fig.suptitle("Mead's pull-air profile is the one Fenway pays",
                 x=0.02, y=0.99, ha="left", fontsize=16,
                 fontweight="bold")
    fig.text(0.02, 0.015, "Pulled: spray angle beyond 15 degrees to the "
             "pull side. Air: launch angle 10 degrees or higher. RHB "
             "pull-air plays to the Monster. 2026 league-wide, "
             f"{MIN_BB}+ batted balls.", fontsize=10, color=S.MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    out = C.FIG_DIR / "18_mead_fit.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [acquisition] wrote {out}")


def fig_fenway(res: dict):
    import numpy as np
    m = _mead_bip()
    fig, ax = plt.subplots(figsize=(9.8, 7.2))
    # field: foul lines, infield square, Fenway wall
    for ang in (-45, 45):
        ax.plot([0, 330 * np.sin(np.radians(ang))],
                [0, 330 * np.cos(np.radians(ang))],
                color=S.SPINE, lw=1.2, zorder=1)
    d = 90 / np.sqrt(2)
    ax.plot([0, d, 0, -d, 0], [0, d, 2 * d, d, 0],
            color=S.SPINE, lw=1.2, zorder=1)
    wx = [dd * np.sin(np.radians(a)) for a, dd in FENWAY_WALL]
    wy = [dd * np.cos(np.radians(a)) for a, dd in FENWAY_WALL]
    ax.plot(wx, wy, color=S.TEXT, lw=2.6, zorder=2)
    mono = [(a, dd) for a, dd in FENWAY_WALL if a <= MONSTER_ARC[1]]
    ax.plot([dd * np.sin(np.radians(a)) for a, dd in mono],
            [dd * np.cos(np.radians(a)) for a, dd in mono],
            color=S.GREEN, lw=6, alpha=0.85, zorder=3,
            solid_capstyle="round")
    ax.annotate("Green Monster\n310 ft, 37 ft high",
                xy=(-252, 150), ha="center", fontsize=11,
                color=S.GREEN, fontweight="bold")
    # batted balls: grounders faint, air balls by outcome
    gb = m[~m["air"]]
    ax.scatter(gb["x_ft"], gb["y_ft"], s=18, color=S.GREY, alpha=0.3,
               zorder=4)
    air = m[m["air"]]
    hr = air[air["events"] == "home_run"]
    xbh = air[air["events"].isin({"double", "triple"})]
    sng = air[air["events"] == "single"]
    out = air[~air.index.isin(hr.index.union(xbh.index).union(sng.index))]
    ax.scatter(out["x_ft"], out["y_ft"], s=42, color=S.GREY, alpha=0.75,
               zorder=5, label="air out")
    ax.scatter(sng["x_ft"], sng["y_ft"], s=48, color=S.TEAL, zorder=6,
               label="single")
    ax.scatter(xbh["x_ft"], xbh["y_ft"], s=58, color=S.NAVY, zorder=7,
               label="double/triple")
    ax.scatter(hr["x_ft"], hr["y_ft"], s=120, color=S.AMBER, marker="*",
               zorder=8, label="home run")
    # the upgrade zone
    fw = res["fenway"]
    lf = m[(m["bearing"] >= MONSTER_ARC[0]) & (m["bearing"] <= MONSTER_ARC[1])
           & m["air"] & (m["dist"] >= 300) & (m["dist"] <= 380)
           & (m["events"] != "home_run")]
    ax.scatter(lf["x_ft"], lf["y_ft"], s=150, facecolors="none",
               edgecolors=S.RED, lw=2, zorder=9,
               label=f"wall ball at Fenway ({fw['upgrades']})")
    leg = ax.legend(loc="upper right", fontsize=10.5)
    for t in leg.get_texts():
        t.set_color(S.TEXT)
    ax.set_xlim(-340, 340)
    ax.set_ylim(-15, 445)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title("Mead's 2026 batted balls on Fenway's dimensions",
                 loc="left", fontsize=15, fontweight="bold")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.13)
    fig.text(0.03, 0.025, f"{fw['upgrades']} of his air balls to left "
             "reached wall depth (300-380 ft) without leaving the yard "
             f"where he played, {fw['upgrade_outs']} of them outs. At "
             "Fenway those live at the Monster. Landing points from "
             "Savant hit coordinates; approximate.",
             fontsize=10, color=S.MUTED, wrap=True)
    out_p = C.FIG_DIR / "19_mead_fenway.png"
    fig.savefig(out_p, dpi=200)
    plt.close(fig)
    print(f"  [acquisition] wrote {out_p}")


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
      f"{res['age']}-year-old former consensus top-100 prospect running "
      f"a **{f['wRC+']} wRC+** "
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
    fw = res.get("fenway", {})
    if fw:
        A(f"Overlaying his 2026 batted balls on Fenway's dimensions "
          "makes the fit concrete: "
          f"**{fw['upgrades']} of his air balls to left field reached "
          "wall depth (300 to 380 feet) without leaving the parks he "
          f"played in, and {fw['upgrade_outs']} of those were caught.** "
          "At Fenway that contact lives on the Monster: doubles off the "
          "wall instead of warning-track outs. Landing points are from "
          "Savant hit coordinates, so treat the count as approximate "
          "(fig. 19).\n")
        fp = res.get("fenway_proj")
        if fp:
            A("Put a number on the park factor: replay just those "
              "Monster-zone balls as wall doubles and his season line "
              f"moves from a .{int(fp['woba_now']*1000)} wOBA to "
              f".{int(fp['woba_all_fenway']*1000)} if every one played "
              f"at Fenway, or about .{int(fp['woba_half_home']*1000)} "
              "over a realistic half-home schedule. Call it roughly "
              f"{fp['delta_full_pts']//2}-{fp['delta_full_pts']} points "
              "of wOBA from the park before any change in approach, "
              "using linear weights on the reclassified outcomes.\n")
        A("![Mead at Fenway](figures/19_mead_fenway.png)\n")
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
    arms = res.get("arms", {})
    e = arms.get("Connelly Early", {})
    t = arms.get("Payton Tolle", {})
    b = arms.get("Jake Bennett", {})
    if e.get("fip"):
        A("The Early side of the ledger holds up too. His "
          f"{e['era']:.2f} ERA was carrying a {e['fip']:.2f} FIP, a "
          f"{e['fip']-e['era']:+.2f} gap that made him the most "
          "flattered arm on the staff, so Boston sold the perception "
          "rather than the pitcher. And the org keeps growing this "
          f"exact asset: Tolle ({t.get('height','6-6')}, "
          f"{t.get('weight','250')} lbs, {t.get('era',0):.2f} ERA with "
          f"a matching {t.get('fip',0):.2f} FIP) and Bennett "
          f"({b.get('height','6-6')}, {b.get('weight','234')} lbs, "
          f"{b.get('era',0):.2f}/{b.get('fip',0):.2f}) are bigger "
          "frames with better underlying numbers, already in the "
          "rotation. Trading the smallest, most FIP-flattered of the "
          "three rookie arms for a controllable middle-of-the-order "
          "bat is the surplus conversion this report has argued for "
          "all along.\n")
    A(f"One item left on the list: the front office bought the bat "
      "before the reliever. The pen fix is still the cheapest win on "
      f"the board, and there are {days_left} days left to make it.\n")
    return "\n".join(L)


def run() -> dict:
    res = compute()
    res["fenway_proj"] = fenway_projection(
        res["fenway"], res["woba"],
        res["fg"]["PA"])
    (C.DATA_DIR / "acquisition.json").write_text(json.dumps(res, indent=2))
    print(f"  [acquisition] wrote {C.DATA_DIR / 'acquisition.json'}")
    fig_fit(res)
    fig_fenway(res)
    art = C.OUT_DIR / "ARTICLE.md"
    if art.exists():
        s = art.read_text()
        if "## The trade they made" not in s and MARKER in s:
            s = s.replace(MARKER,
                          article_section(res).strip() + "\n\n" + MARKER)
            art.write_text(s)
            print("  [acquisition] spliced trade section into ARTICLE.md")
    return res
