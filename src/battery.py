"""Catcher-battery analysis: how the staff performs with each catcher.

Computes, from pitch-level Statcast (BOS fielding, 2026):
  * per-catcher staff RA9 and xwOBA-against,
  * per-pitcher battery splits (RA9 with each catcher, min 30 outs),
and writes data/battery.json plus figures/14_battery_map.png.

Caveat carried into every consumer: battery splits are small samples
(30-95 IP) confounded by usage choices (day games, personal catchers,
opponent quality). They are evidence of a working assignment system,
not a causal framing/game-calling measurement.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import pandas as pd

from . import config as C
from . import style as S

S.apply()

PITCH_CSV = C.DATA_DIR / "statcast" / "bos_team_pitches_2026.csv"
PITCH_CSV_2025 = C.DATA_DIR / "statcast" / "bos_team_pitches_2025.csv"
MIN_OUTS = 30  # ~10 innings before a battery split is shown

# outs credited per event (post_outs_when_up not present in this feed)
OUT_EV = {
    "field_out": 1, "strikeout": 1, "force_out": 1, "sac_fly": 1,
    "sac_bunt": 1, "grounded_into_double_play": 2, "double_play": 2,
    "strikeout_double_play": 2, "fielders_choice_out": 1,
    "caught_stealing_2b": 1, "caught_stealing_3b": 1,
    "caught_stealing_home": 1, "other_out": 1, "triple_play": 3,
    "sac_fly_double_play": 2, "pickoff_1b": 1, "pickoff_2b": 1,
    "pickoff_3b": 1,
}


def _fetch() -> pd.DataFrame:
    import datetime as dt
    from pybaseball import statcast
    end = min(dt.date.today(), dt.date(2026, 9, 27)).isoformat()
    df = statcast(start_dt="2026-03-25", end_dt=end, team="BOS",
                  verbose=False)
    PITCH_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(PITCH_CSV, index=False)
    return df


def _fetch_2025() -> pd.DataFrame:
    from pybaseball import statcast
    df = statcast(start_dt="2025-03-25", end_dt="2025-09-28", team="BOS",
                  verbose=False)
    PITCH_CSV_2025.parent.mkdir(exist_ok=True)
    df.to_csv(PITCH_CSV_2025, index=False)
    return df


def load(csv=None) -> pd.DataFrame:
    csv = csv or PITCH_CSV
    if csv.exists():
        df = pd.read_csv(csv, low_memory=False)
    elif csv is PITCH_CSV_2025:
        df = _fetch_2025()
    else:
        df = _fetch()
    from pybaseball import playerid_reverse_lookup
    for col, out in (("fielder_2", "catcher"), ("pitcher", "pitcher_name")):
        ids = df[col].dropna().astype(int).unique().tolist()
        lk = playerid_reverse_lookup(ids, key_type="mlbam")
        nm = {r["key_mlbam"]: (r["name_first"] + " " + r["name_last"]).title()
              for _, r in lk.iterrows()}
        df[out] = df[col].astype(int).map(nm)
    df["runs"] = (df["post_bat_score"] - df["bat_score"]).clip(lower=0)
    df["outs_rec"] = df["events"].map(OUT_EV).fillna(0)
    return df


def starters(df: pd.DataFrame) -> set:
    """True starters: took the first fielding pitch in 2+ games AND
    average 3+ innings per appearance (drops relievers used as
    openers, who face an inning or two and hand it off)."""
    first = (df.sort_values(["game_pk", "at_bat_number", "pitch_number"])
             if "at_bat_number" in df.columns else df)
    gs = first.groupby("game_pk")["pitcher_name"].first().value_counts()
    per_app = (df.groupby("pitcher_name")
               .agg(outs=("outs_rec", "sum"), games=("game_pk", "nunique")))
    bulk = per_app[per_app["outs"] / per_app["games"] >= 9].index
    return set(gs[gs >= 2].index) & set(bulk)


def compute(df: pd.DataFrame) -> dict:
    per_c = {}
    for c, d in df.groupby("catcher"):
        ip = d["outs_rec"].sum() / 3
        pa = d[d["woba_denom"].notna() & (d["woba_denom"] > 0)]
        xw = (pa["estimated_woba_using_speedangle"].fillna(pa["woba_value"])
              * pa["woba_denom"]).sum() / pa["woba_denom"].sum()
        per_c[c] = {"IP": round(ip, 1),
                    "RA9": round(d["runs"].sum() / ip * 9, 2),
                    "xwOBA_against": round(float(xw), 3)}

    sp = starters(df)
    top = (df[df["pitcher_name"].isin(sp)]
           .groupby("pitcher_name")["outs_rec"].sum()
           .sort_values(ascending=False).head(8))
    batteries = {}
    for p in top.index:
        sub = df[df["pitcher_name"] == p]
        bat = sub.groupby("catcher").agg(outs=("outs_rec", "sum"),
                                         runs=("runs", "sum"))
        bat = bat[bat["outs"] >= MIN_OUTS]
        batteries[p] = {c: {"IP": round(r["outs"] / 3, 1),
                            "RA9": round(r["runs"] / (r["outs"] / 3) * 9, 2)}
                        for c, r in bat.iterrows()}
    return {"per_catcher": per_c, "batteries": batteries,
            "min_outs": MIN_OUTS,
            "league_ra9": round(float(df["runs"].sum()
                                      / (df["outs_rec"].sum() / 3) * 9), 2)}


def fig_battery(res: dict):
    cats = ["Carlos Narváez", "Connor Wong"]
    colors = {"Carlos Narváez": S.RED, "Connor Wong": S.NAVY}
    skip = {"Connelly Early", "Garrett Crochet", "Garrett Crochet (2025)"}
    rows = [(p, b) for p, b in res["batteries"].items()
            if any(c in b for c in cats) and p not in skip]
    lg_ra9 = res.get("league_ra9")
    n = len(rows)
    fig, ax = plt.subplots(figsize=(10.2, 1.35 + 0.82 * n))
    for y in range(n):
        if y % 2 == 0:
            ax.axhspan(y - 0.5, y + 0.5, color=S.FAINT, zorder=0)
    for y, (p, b) in zip(range(n), rows):
        pts = [(c, b[c]["RA9"]) for c in cats if c in b]
        if len(pts) == 2:
            ax.plot([pts[0][1], pts[1][1]], [y, y], color=S.GREY,
                    lw=2.4, zorder=2, alpha=0.7)
        close = len(pts) == 2 and abs(pts[0][1] - pts[1][1]) < 1.1
        for k, (c, ra9) in enumerate(pts):
            ax.scatter(ra9, y, s=150, color=colors[c], zorder=4,
                       edgecolors="white", linewidths=1.2)
            dy = 14 if (not close or k == 0) else -22
            ax.annotate(f"{ra9:.2f}  ({b[c]['IP']:.0f} IP)", (ra9, y),
                        textcoords="offset points", xytext=(0, dy),
                        ha="center", fontsize=9.5, color=S.MUTED)
    if lg_ra9:
        ax.axvline(lg_ra9, color=S.SPINE, lw=1.4, ls=":", zorder=1)
        ax.annotate(f"staff avg {lg_ra9:.2f}", (lg_ra9, n - 0.52),
                    textcoords="offset points", xytext=(7, 2),
                    fontsize=9.5, color=S.MUTED)
    handles = [plt.Line2D([], [], marker="o", ls="", color=colors[c],
                          markersize=11, markeredgecolor="white")
               for c in cats]
    leg = ax.legend(handles, [c.split()[-1] for c in cats],
                    loc="lower right", title="RA9 with", ncol=1,
                    borderaxespad=0.6)
    leg.get_title().set_color(S.MUTED)
    for t in leg.get_texts():
        t.set_color(S.TEXT)
    ax.set_yticks(range(n))
    ax.set_yticklabels([p for p, _ in rows], fontsize=12.5)
    ax.set_ylim(n - 0.5, -0.75)
    S.style(ax, grid_axis="x")
    ax.set_xlabel("Runs allowed per 9 innings with each catcher "
                  f"(min {res['min_outs']} outs)")
    ax.set_title("The battery map: each Red Sox starter has a clear "
                 "preferred catcher", loc="left", fontsize=15,
                 fontweight="bold", pad=14)
    ax.text(0, -0.16, "Starters with 30+ outs caught by both catchers, "
            "2026. Small, usage-shaped samples: evidence of an "
            "assignment system, not a causal measure.",
            transform=ax.transAxes, fontsize=10, color=S.MUTED)
    fig.tight_layout()
    out = C.FIG_DIR / "14_battery_map.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [battery] wrote {out}")


def _battery_for(df: pd.DataFrame, pitcher: str) -> dict:
    sub_df = df[df["pitcher_name"] == pitcher]
    bat = sub_df.groupby("catcher").agg(outs=("outs_rec", "sum"),
                                        runs=("runs", "sum"))
    bat = bat[bat["outs"] >= MIN_OUTS]
    return {c: {"IP": round(r["outs"] / 3, 1),
                "RA9": round(r["runs"] / (r["outs"] / 3) * 9, 2)}
            for c, r in bat.iterrows()}


def run() -> dict:
    df = load()
    res = compute(df)
    # Crochet's 2026 is a 13-17 IP rehab sample: not chartable
    res["batteries"].pop("Garrett Crochet", None)
    (C.DATA_DIR / "battery.json").write_text(json.dumps(res, indent=2))
    print(f"  [battery] wrote {C.DATA_DIR / 'battery.json'}")
    fig_battery(res)
    return res
