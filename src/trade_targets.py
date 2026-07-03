"""Duran trade value + best-fit trade partners.

Fit = a contending team (2026 standings) that also has a weak outfield
(FanGraphs team OF production). Trade value converts Duran's surplus into a
prospect-tier return, discounted for his down-year risk. Returns are described
as value tiers / archetypes, not specific fabricated prospect names.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests

from . import config as C
from . import style as S

S.apply()

DOLLARS_PER_WAR = 8.0

# FanGraphs team abbrev -> MLB StatsAPI full team name.
FG_TO_NAME = {
    "ARI": "Diamondbacks", "ATH": "Athletics", "ATL": "Braves",
    "BAL": "Orioles", "BOS": "Red Sox", "CHC": "Cubs", "CHW": "White Sox",
    "CIN": "Reds", "CLE": "Guardians", "COL": "Rockies", "DET": "Tigers",
    "HOU": "Astros", "KCR": "Royals", "LAA": "Angels", "LAD": "Dodgers",
    "MIA": "Marlins", "MIL": "Brewers", "MIN": "Twins", "NYM": "Mets",
    "NYY": "Yankees", "PHI": "Phillies", "PIT": "Pirates", "SDP": "Padres",
    "SEA": "Mariners", "SFG": "Giants", "STL": "Cardinals", "TBR": "Rays",
    "TEX": "Rangers", "TOR": "Blue Jays", "WSN": "Nationals",
}

# --- Duran trade value ------------------------------------------------------
# arb-escalating salary and gently declining true-talent WAR over control years
DURAN_CONTROL = [
    dict(year=2026, war=2.6, salary=7.7),   # already partly sunk / in season
    dict(year=2027, war=2.4, salary=10.0),  # arb projection
    dict(year=2028, war=2.2, salary=12.0),  # arb projection
]
DOWN_YEAR_DISCOUNT = 0.35  # haircut for 2026 slump / volatility

# Rough surplus-$ -> prospect Future Value equivalents (industry ballpark).
FV_VALUE = {"55 FV": 40, "50 FV": 27, "45+ FV": 15, "45 FV": 9,
            "40 FV": 4, "40- FV": 2}


def duran_value() -> dict:
    # value from 2027 onward (2026 is largely in the books / depends on buyer)
    future = [y for y in DURAN_CONTROL if y["year"] >= 2027]
    gross = sum(y["war"] * DOLLARS_PER_WAR - y["salary"] for y in future)
    full = sum(y["war"] * DOLLARS_PER_WAR - y["salary"] for y in DURAN_CONTROL)
    risk_adj = gross * (1 - DOWN_YEAR_DISCOUNT)
    return {
        "surplus_full_3yr": full,
        "surplus_2027_28": gross,
        "risk_adjusted": risk_adj,
        "range_low": risk_adj,
        "range_high": gross,
    }


# --- team fit ---------------------------------------------------------------
def team_of_need() -> pd.DataFrame:
    d = pd.read_csv(C.DATA_DIR / "league_of_2026.csv")
    d = d[(d["PA"] >= 30) & (d["Team"].isin(FG_TO_NAME))]
    g = (d.groupby("Team")
         .apply(lambda x: pd.Series({
             "of_war": x["WAR"].sum(),
             "of_wrcplus": (x["wRC+"] * x["PA"]).sum() / x["PA"].sum()}),
             include_groups=False)
         .reset_index())
    g["team_name"] = g["Team"].map(FG_TO_NAME)
    return g


def standings() -> pd.DataFrame:
    url = ("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
           "&season=2026&standingsTypes=regularSeason")
    r = requests.get(url, headers=C.HTTP_HEADERS, timeout=C.HTTP_TIMEOUT).json()
    rows = []
    for rec in r.get("records", []):
        for t in rec["teamRecords"]:
            wcgb = t.get("wildCardGamesBack", "-")
            rows.append({
                "team_name": t["team"]["name"],
                "W": t["wins"], "L": t["losses"],
                "win_pct": float(t.get("winningPercentage", 0) or 0),
                "wc_gb": wcgb,
            })
    return pd.DataFrame(rows)


def _wc_num(x):
    if x in ("-", "+", None):
        return 0.0
    try:
        return float(str(x).replace("+", "-"))  # "+3.0" -> leading = in
    except ValueError:
        return 99.0


def fits() -> pd.DataFrame:
    need = team_of_need()
    st = standings()
    df = need.merge(st, on="team_name", how="inner")
    # contention: winning record OR within ~6 games of a wild card
    df["wc_gb_num"] = df["wc_gb"].map(_wc_num)
    df["contender"] = (df["win_pct"] >= 0.485) | (df["wc_gb_num"] <= 6)
    # a real fit needs BOTH contention AND a below-average outfield.
    df["needs_of"] = df["of_wrcplus"] < 102
    df["fit_candidate"] = df["contender"] & df["needs_of"]
    of_z = (df["of_war"] - df["of_war"].mean()) / df["of_war"].std()
    win_z = (df["win_pct"] - df["win_pct"].mean()) / df["win_pct"].std()
    # reward winning + OF weakness; zero out non-candidates so strong-OF
    # winners (e.g. Dodgers/Brewers) don't surface as "fits".
    df["fit_score"] = (win_z - of_z).where(df["fit_candidate"], -99)
    df = df.sort_values("fit_score", ascending=False)
    df.to_csv(C.DATA_DIR / "trade_fits.csv", index=False)
    return df


# --- figure -----------------------------------------------------------------
def fig_fits(df):
    fig, ax = plt.subplots(figsize=(9.8, 6.2))
    of_avg, win_avg = 100, 0.500
    x0, x1, y0, y1 = 72, 122, 0.38, 0.66
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    top = df[df["fit_candidate"]].head(6)["team_name"].tolist()

    # target quadrant: contender (>.500) + weak OF (<100)
    ax.axvspan(x0, of_avg, (win_avg - y0) / (y1 - y0), 1.0,
               color=S.NAVY, alpha=0.05, zorder=0)
    ax.axvline(of_avg, color=S.AMBER, lw=1.3, ls="--", zorder=1)
    ax.axhline(win_avg, color=S.GREY, lw=1.1, ls=(0, (2, 3)), zorder=1)

    for _, r in df.iterrows():
        is_bos = r["team_name"] == "Red Sox"
        is_fit = r["team_name"] in top and not is_bos
        c = S.RED if is_bos else (S.NAVY if is_fit else S.GREY)
        ax.scatter(r["of_wrcplus"], r["win_pct"], s=150 if is_fit else 66,
                   c=c, edgecolor="white", linewidth=1.0,
                   alpha=1.0 if (is_fit or is_bos) else 0.6,
                   zorder=5 if is_fit else 3)
    nudge = {"Red Sox": (8, -10, "left"), "Reds": (8, -9, "left"),
             "Astros": (9, 4, "left"), "Guardians": (-8, 6, "right"),
             "White Sox": (8, -9, "left"), "Padres": (8, 5, "left")}
    for _, r in df.iterrows():
        is_bos = r["team_name"] == "Red Sox"
        if not (r["team_name"] in top or is_bos):
            continue
        dx, dy, ha = nudge.get(r["team_name"], (8, 4, "left"))
        ax.annotate(r["team_name"], (r["of_wrcplus"], r["win_pct"]),
                    textcoords="offset points", xytext=(dx, dy), ha=ha,
                    fontsize=8.5, fontweight="bold", va="center",
                    color=S.RED if is_bos else S.NAVY)
    ax.text(x0 + 1.2, y1 - 0.012, "BEST-FIT TARGETS", fontsize=9.5,
            color=S.NAVY, fontweight="bold", va="top")
    ax.text(x0 + 1.2, y1 - 0.035, "contenders with a weak outfield",
            fontsize=8.5, color=S.MUTED, va="top")
    ax.text(x1 - 0.4, win_avg + 0.004, ".500", fontsize=8, color=S.GREY,
            ha="right", va="bottom")
    ax.text(of_avg + 0.6, y0 + 0.008, "league-avg OF", fontsize=8,
            color=S.AMBER, va="bottom")
    S.style(ax, grid_axis="both")
    ax.grid(color=S.GRID, linewidth=1.0)
    ax.set_xlabel("Team outfield production — 2026 wRC+   (left = more need)")
    ax.set_ylabel("Team winning %  (2026)")
    S.titled(ax, "Who should call Boston about Duran?",
             "Best fits are winning teams with a weak outfield (upper-left)")
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "08_trade_fit_targets.png")
    plt.close(fig)


# --- memo -------------------------------------------------------------------
def memo(df, val):
    L = []
    A = L.append
    A("# Jarren Duran — Trade Value & Best-Fit Partners\n")
    A("*Generated 2026-07-02 · OF production via FanGraphs; standings via MLB "
      "Stats API; value model uses ~$8M/WAR (the widely used market rate "
      "from FanGraphs' dollars-per-WAR research on free-agent contracts) and "
      "prospect FV-to-surplus-value conversions in the spirit of FanGraphs' "
      "prospect valuation studies (Craig Edwards, 2019, updated for salary "
      "inflation). Illustrative, not a scouting "
      "report.*\n")

    A("## What Duran is worth\n")
    A(f"- Full 3-year (2026–28) surplus at true talent (~2.6 → 2.2 WAR, "
      f"arb salary rising ~$8M→$12M): **≈ ${val['surplus_full_3yr']:.0f}M**.")
    A(f"- The two future control years a winter buyer gets (2027–28): "
      f"**≈ ${val['surplus_2027_28']:.0f}M** gross → "
      f"**≈ ${val['risk_adjusted']:.0f}M** after a "
      f"~{int(DOWN_YEAR_DISCOUNT*100)}% haircut for 2026 down-year risk.\n")
    A("**So the return splits into two scenarios — which is the whole "
      "timing argument:**")
    A(f"- **Sell now, at the nadir (~${val['risk_adjusted']:.0f}M):** about a "
      "**45-FV prospect** — a fringe/back-end top-100 arm, or a 40-FV piece "
      "plus a lottery ticket. You cash the 2026 slump.")
    A(f"- **Sell after a rebound to ~2025 form (~${val['surplus_full_3yr']:.0f}"
      "M over full control):** about a **50-FV prospect** — a genuine "
      "back-end top-100, controllable arm, potentially a 50-FV headliner if a "
      "buyer bids the ≈110-wRC+ version. That one-grade jump is worth waiting "
      "for a **winter** trade rather than a deadline dump.\n")

    A("## Best-fit trade partners (contender + weak OF)\n")
    A("| Team | 2026 W-L | Win% | Team OF wRC+ | OF WAR | Fit |")
    A("|------|:--------:|-----:|------------:|-------:|:---:|")
    show = df[df["fit_candidate"] & (df["team_name"] != "Red Sox")].head(8)
    for _, r in show.iterrows():
        flag = "★ strong" if r["fit_score"] > 1.2 else (
            "good" if r["fit_score"] > 0.6 else "marginal")
        A(f"| {r['team_name']} | {int(r['W'])}-{int(r['L'])} | "
          f"{r['win_pct']:.3f} | {r['of_wrcplus']:.0f} | {r['of_war']:.1f} | "
          f"{flag} |")
    A("\n*Fit score rewards winning % and penalizes existing OF production; a "
      "low team OF wRC+ = more need for a bat like Duran's.*\n")

    A("## Sample deal frameworks\n")
    A("These are *archetypes* — plug in the buyer's actual prospects from a "
      "current top-30 list. **Because Boston's pitching (a top-10 rotation) is "
      "a strength, target controllable *bats* and best-available young talent, "
      "not arms** — the offense is the soft spot to fix.")
    top3 = show.head(3)["team_name"].tolist()
    if len(top3) >= 1:
        A(f"1. **{top3[0]}:** Duran for a controllable, MLB-ready position "
          "player (or a 50-FV hitting prospect) at a lineup spot of need. "
          "Boston's cleanest fit if the buyer needs an everyday OF now.")
    if len(top3) >= 2:
        A(f"2. **{top3[1]}:** Duran for a 45+-FV bat with upside + a 40-FV "
          "flier — swaps a redundant OF for offensive help elsewhere in the "
          "lineup.")
    if len(top3) >= 3:
        A(f"3. **{top3[2]}:** salary-relief variant — Boston eats a little of "
          "Duran's arb money to upgrade the prospect tier by one grade.")
    A("\n> **Two-birds option:** package Duran *with* a chunk of the Yoshida "
      "money to a DH/OF-needy contender, clearing both the jam and part of the "
      "albatross in one deal — though that likely lowers the Duran return.\n")

    A("## Caveats\n")
    A("- Value math is a $/WAR surplus model, not a scouting valuation; the "
      "2026 down year makes the true number unusually uncertain (that's the "
      "point).")
    A("- **Park translation:** Duran's raw counting stats (doubles/triples "
      "off the Monster, home BABIP) carry a Fenway boost — his career home "
      "wOBA (.350) runs ~25 pts above road (.325). A buyer should value the "
      "park-adjusted line (wRC+, which this analysis uses throughout) plus "
      "the speed/defense, which travel; his xwOBA overperformance is venue-"
      "independent (+20 pts home, +22 road career), so that skill travels "
      "too. Fit matters at the margins: a spacious outfield rewards his legs "
      "more than a small one.")
    A("- Standings/OF-need are a July-2026 snapshot; deadline buyers and needs "
      "shift weekly. Re-run near the deadline / in the offseason.")
    A("- Prospect FV↔$ conversions are industry ballparks; use current "
      "org-specific top-prospect lists to name real players.\n")

    out = C.OUT_DIR / "trade_targets.md"
    out.write_text("\n".join(L))
    print(f"  [trade] wrote {out}")


def run():
    val = duran_value()
    df = fits()
    fig_fits(df)
    print("  [trade] wrote figure 08")
    memo(df, val)


if __name__ == "__main__":
    run()
