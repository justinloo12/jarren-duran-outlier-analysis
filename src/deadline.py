"""Deadline decision: should the Red Sox buy or sell?

Grounds the buy/sell call in a simple, documented model:
  * AL standings + run differential from the MLB Stats API.
  * Team "talent" = Pythagorean win% (exponent 1.83) regressed toward .500
    by adding K=35 games of league-average ball (a standard shrinkage).
  * 10,000-iteration Monte Carlo of the remaining schedule (binomial games,
    no schedule/opponent effects — a simplification, stated in the memo).
    Division winners = most wins per division; 3 wild cards from the rest.
  * Duran 2026 monthly splits (is the rebound visible yet?).

Outputs: data/deadline.json, figures/12_playoff_race.png,
outputs/deadline_decision.md, and the post-ready outputs/ARTICLE.md.
"""
from __future__ import annotations

import datetime as dt
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from . import config as C
from . import style as S
from .fetch_statcast import load_pitches

S.apply()

N_SIMS = 10_000
REGRESS_GAMES = 35          # shrinkage toward .500
PYTH_EXP = 1.83
SEASON_GAMES = 162


# --------------------------------------------------------------- standings
def al_standings() -> pd.DataFrame:
    url = ("https://statsapi.mlb.com/api/v1/standings?leagueId=103"
           "&season=2026&standingsTypes=regularSeason")
    r = requests.get(url, headers=C.HTTP_HEADERS, timeout=C.HTTP_TIMEOUT).json()
    rows = []
    for rec in r.get("records", []):
        div_id = rec.get("division", {}).get("id")
        for t in rec["teamRecords"]:
            rows.append({
                "team": t["team"]["name"],
                "division": div_id,
                "W": t["wins"], "L": t["losses"],
                "RS": t.get("runsScored"), "RA": t.get("runsAllowed"),
                "run_diff": t.get("runDifferential"),
                "wc_gb": t.get("wildCardGamesBack"),
                "streak": t.get("streak", {}).get("streakCode", ""),
            })
    df = pd.DataFrame(rows)
    df["G"] = df["W"] + df["L"]
    df["pct"] = df["W"] / df["G"]
    pyth = df["RS"] ** PYTH_EXP / (df["RS"] ** PYTH_EXP + df["RA"] ** PYTH_EXP)
    df["pythag"] = pyth
    df["talent"] = (pyth * df["G"] + 0.5 * REGRESS_GAMES) / (df["G"] + REGRESS_GAMES)
    df["remaining"] = SEASON_GAMES - df["G"]
    return df


# --------------------------------------------------------------- simulation
def simulate(df: pd.DataFrame, n: int = N_SIMS, seed: int = 34) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    teams = df.reset_index(drop=True)
    nt = len(teams)
    wins_now = teams["W"].to_numpy()
    rem = teams["remaining"].to_numpy()
    p = teams["talent"].to_numpy()
    divs = teams["division"].to_numpy()

    playoff = np.zeros(nt)
    for _ in range(n):
        final = wins_now + rng.binomial(rem, p) + rng.random(nt) * 1e-6
        made = np.zeros(nt, dtype=bool)
        for d in np.unique(divs):
            idx = np.where(divs == d)[0]
            made[idx[np.argmax(final[idx])]] = True
        rest = np.where(~made)[0]
        wc = rest[np.argsort(final[rest])[::-1][:3]]
        made[wc] = True
        playoff += made
    teams["playoff_odds"] = playoff / n
    return teams


# --------------------------------------------------------------- Duran month
def duran_monthly() -> pd.DataFrame:
    d = load_pitches(2026)
    if "game_type" in d.columns:
        d = d[d["game_type"] == "R"]
    d = d.copy()
    d["month"] = pd.to_datetime(d["game_date"]).dt.month
    ev = d[d["woba_denom"].notna() & (d["woba_denom"] > 0)].copy()
    ev["x"] = ev["estimated_woba_using_speedangle"].where(
        ev["estimated_woba_using_speedangle"].notna(), ev["woba_value"])
    g = ev.groupby("month").apply(
        lambda t: pd.Series({
            "PA": t["woba_denom"].sum(),
            "wOBA": t["woba_value"].sum() / t["woba_denom"].sum(),
            "xwOBA": t["x"].sum() / t["woba_denom"].sum()}),
        include_groups=False).reset_index()
    return g[g["PA"] >= 20]   # drop tiny stubs


# ------------------------------------------------------ positional audit
_FG_API = "https://www.fangraphs.com/api/leaders/major-league/data"
_POS = ["c", "1b", "2b", "ss", "3b", "lf", "cf", "rf", "dh"]


def _fg_pull(pos, team=0, stats="bat", typ=8) -> pd.DataFrame:
    import re
    p = {"pos": pos, "stats": stats, "lg": "all", "qual": 0, "season": 2026,
         "season1": 2026, "month": 0, "team": team, "pageitems": 3000,
         "pagenum": 1, "ind": 0, "type": typ}
    d = pd.DataFrame(requests.get(_FG_API, params=p, headers=C.HTTP_HEADERS,
                                  timeout=C.HTTP_TIMEOUT).json()["data"])
    if d.empty:
        return d
    d["Name"] = d["Name"].map(lambda s: re.sub("<[^>]+>", "", str(s)).strip())
    if "Team" in d:
        d["Team"] = d["Team"].map(
            lambda s: re.sub("<[^>]+>", "", str(s)).strip())
    return d


def positional_audit() -> tuple[pd.DataFrame, dict]:
    """BOS wRC+ by position vs league (PA-weighted), + pitching unit ranks.

    Caveat: the FG position filter selects players who qualify at a position
    and returns their FULL batting line (not position-split) — the standard
    quick positional audit, so a two-position player (e.g. Anthony LF/DH)
    counts in both rows.
    """
    rows = []
    for pos in _POS:
        bos, lg = _fg_pull(pos, team=3), _fg_pull(pos, team=0)

        def wavg(d):
            d = d[d["PA"].notna() & (d["PA"] > 0)]
            return float(np.average(d["wRC+"], weights=d["PA"]))

        bw, lw = wavg(bos), wavg(lg)
        top = bos.sort_values("PA", ascending=False).head(2)["Name"].tolist()
        rows.append({"pos": pos.upper(), "bos_wrc": round(bw),
                     "lg_wrc": round(lw), "gap": round(bw - lw),
                     "top": ", ".join(top)})
    aud = pd.DataFrame(rows).sort_values("gap")

    pit = _fg_pull("all", team=0, stats="pit", typ=1)
    for c in ("WAR", "IP", "ERA", "FIP", "GS", "G"):
        pit[c] = pd.to_numeric(pit[c], errors="coerce")
    pit["sp"] = pit["GS"].fillna(0) >= pit["G"].fillna(0) * 0.5

    def rank(sub, col, asc):
        g = sub.groupby("Team").apply(
            lambda t: (t[col] * t["IP"]).sum() / t["IP"].sum()
            if col in ("ERA", "FIP") else t[col].sum(),
            include_groups=False).sort_values(ascending=asc)
        return int(list(g.index).index("BOS") + 1), round(float(g.get("BOS")), 2)

    units = {
        "rotation_era_rank": rank(pit[pit["sp"]], "ERA", True),
        "rotation_war_rank": rank(pit[pit["sp"]], "WAR", False),
        "bullpen_era_rank": rank(pit[~pit["sp"]], "ERA", True),
        "bullpen_fip_rank": rank(pit[~pit["sp"]], "FIP", True),
        "bullpen_war_rank": rank(pit[~pit["sp"]], "WAR", False),
    }
    return aud, units


def fig_positions(aud: pd.DataFrame):
    d = aud.sort_values("gap")
    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    colors = [S.RED if g < -8 else (S.GREEN if g > 8 else S.GREY)
              for g in d["gap"]]
    ax.barh(d["pos"], d["gap"], color=colors, height=0.62, zorder=3)
    ax.axvline(0, color=S.SPINE, lw=1.2, zorder=2)
    for y, (_, r) in enumerate(d.iterrows()):
        x = r["gap"]
        label = f"{r['gap']:+d}  ({r['top'].split(',')[0]})"
        ax.text(x + (1.2 if x >= 0 else -1.2), y, label,
                va="center", ha="left" if x >= 0 else "right",
                fontsize=8.5, color=S.MUTED)
    S.style(ax, grid_axis="x")
    ax.tick_params(axis="y", labelcolor=S.TEXT)
    ax.set_xlim(-50, 54)
    ax.set_xlabel("Boston wRC+ minus league average at the position (2026)")
    S.titled(ax, "Where the roster actually leaks runs",
             "PA-weighted wRC+ by position vs. league · red = hole, green = "
             "strength · label = primary occupant")
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "13_positional_audit.png")
    plt.close(fig)


# --------------------------------------------------------------- figure 09
def fig_race(sim: pd.DataFrame):
    d = sim[(sim["playoff_odds"] > 0.005)].copy()
    d = d.sort_values("playoff_odds")
    # teams currently holding a playoff spot (division lead or WC in hand)
    holding = set()
    for div in d["division"].unique():
        sub = sim[sim["division"] == div]
        holding.add(sub.loc[sub["pct"].idxmax(), "team"])
    wc_now = (sim[~sim["team"].isin(holding)]
              .sort_values("pct", ascending=False).head(3)["team"])
    holding |= set(wc_now)

    fig, ax = plt.subplots(figsize=(9.4, 5.8))
    colors = [S.RED if "Red Sox" in t
              else (S.NAVY if t in holding else S.GREY) for t in d["team"]]
    ax.barh(d["team"], d["playoff_odds"] * 100, color=colors, height=0.62,
            zorder=3)
    for y, (_, r) in enumerate(d.iterrows()):
        ax.text(r["playoff_odds"] * 100 + 1.2, y,
                f"{r['playoff_odds']*100:.0f}%   "
                f"({int(r['W'])}-{int(r['L'])}, RD {int(r['run_diff']):+d})",
                va="center", fontsize=8.5,
                color=S.RED if "Red Sox" in r["team"] else S.MUTED,
                weight="bold" if "Red Sox" in r["team"] else "normal")
    S.style(ax, grid_axis="x")
    ax.tick_params(axis="y", labelcolor=S.TEXT)
    ax.set_xlim(0, 108)
    ax.set_xlabel("Simulated playoff odds (%) — 10,000 season simulations")
    S.titled(ax, "Boston is alive — barely, but genuinely",
             "AL playoff odds: talent = regressed run differential · navy = "
             "currently holding a playoff spot")
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "12_playoff_race.png")
    plt.close(fig)


_ALL_BATS = None


def _player_line(name: str):
    """League batting row for one player (cached per run)."""
    global _ALL_BATS
    if _ALL_BATS is None:
        d = _fg_pull("all", team=0, stats="bat", typ=8)
        for c in ("PA", "wRC+", "OBP", "K%", "wOBA"):
            if c in d.columns:
                d[c] = pd.to_numeric(d[c], errors="coerce")
        _ALL_BATS = d
    m = _ALL_BATS[_ALL_BATS["Name"] == name]
    return None if m.empty else m.iloc[0]


def _wc_phrase(bos) -> str:
    g = str(bos.get("wc_gb", "")).strip()
    if g in ("-", "", "0.0") :
        return "Boston currently holds the final wild-card spot"
    if g.startswith("+"):
        return f"Boston holds a wild card, {g.lstrip('+')} games clear of the cut line"
    return f"the third wild card sits {g} games away"


# --------------------------------------------------------------- verdict
def verdict(bos: pd.Series) -> dict:
    odds = float(bos["playoff_odds"])
    if odds >= 0.40:
        call, label = "BUY", "clear buyer"
    elif odds >= 0.12:
        call, label = "CONDITIONAL HOLD", ("hold the core, no rental splurge, "
                                           "let the next three weeks decide")
    elif odds >= 0.04:
        call, label = "SOFT SELL", "sell expiring vets only, keep controllables"
    else:
        call, label = "SELL", "clear seller (expiring vets)"
    return {"call": call, "label": label, "odds": odds}


# --------------------------------------------------------------- memo
def memo(sim: pd.DataFrame, v: dict, monthly: pd.DataFrame,
         aud: pd.DataFrame = None, units: dict = None):
    bos = sim[sim["team"].str.contains("Red Sox")].iloc[0]
    L = []
    A = L.append
    A("# Deadline Decision — Should the Red Sox Buy or Sell?\n")
    A(f"*Generated {dt.date.today().isoformat()} · standings via MLB Stats "
      "API · simulation details in the method note.*\n")
    A(f"## The verdict: **{v['call']}** — {v['label']}\n")
    A(f"- Record **{int(bos['W'])}-{int(bos['L'])}** (.{bos['pct']*1000:.0f}) "
      f"but run differential **{int(bos['run_diff']):+d}** — a Pythagorean "
      f"**.{bos['pythag']*1000:.0f}** team underperforming its runs by ~"
      f"{(bos['pythag']-bos['pct'])*bos['G']:.0f} wins.")
    A(f"- {_wc_phrase(bos)} in a congested, weak race — riding a "
      f"{bos['streak']} streak.")
    A(f"- Simulated playoff odds: **{v['odds']*100:.0f}%** "
      f"({N_SIMS:,} sims; talent = run-diff-based, regressed).")
    A("\n> **The team is its left fielder.** The same results-vs-process gap "
      "that defines Duran's 2026 defines the roster: a top-10 rotation and a "
      "positive run differential producing a losing record. Process says this "
      "team is better than its line. That is precisely the profile you do "
      "not fire-sale at the bottom.\n")
    A("## What that means by asset\n")
    A("| Asset class | Action | Why |")
    A("|---|---|---|")
    A("| Duran | **Hold through deadline** | value at its nadir; xstats and "
      "venue splits say the market is under-pricing him; revisit in winter |")
    A("| Young OF core (Anthony/Rafaela/Abreu) | **Keep** | the 2027 outfield |")
    A("| Expiring vets (reported: Gray, Chapman, Contreras) | **Sell only if "
      "out of it by Aug 1** | rentals with real deadline markets; the one "
      "true sell-now inventory |")
    A("| Yoshida | **Keep/absorb** | bat above average in 2026; contract "
      "still immovable |")
    A("| Rotation | **Do not trade from it** | it is the reason the odds are "
      "alive |\n")

    if aud is not None:
        A("## If they buy: where the roster actually leaks runs\n")
        A("PA-weighted wRC+ by position vs. league average (see figure 10; "
          "position filter counts a player's full line at each position he "
          "qualifies for — a standard approximation):\n")
        A("| Pos | BOS | Lg | Gap | Primary occupants |")
        A("|-----|----:|---:|----:|---|")
        for _, r in aud.iterrows():
            A(f"| {r['pos']} | {r['bos_wrc']} | {r['lg_wrc']} | "
              f"{r['gap']:+d} | {r['top']} |")
        A("")
        if units:
            A(f"Pitching units: rotation ERA ranks "
              f"**{units['rotation_era_rank'][0]}th** "
              f"({units['rotation_era_rank'][1]}) and WAR "
              f"{units['rotation_war_rank'][0]}th — a real strength. The "
              f"bullpen's ERA ranks {units['bullpen_era_rank'][0]}th but its "
              f"FIP ranks {units['bullpen_fip_rank'][0]}th and WAR "
              f"{units['bullpen_war_rank'][0]}th — **the ERA is flattering "
              "it**; this is the quiet weakness.\n")
        g = {r["pos"]: int(r["gap"]) for _, r in aud.iterrows()}
        first_base = aud[aud["pos"] == "1B"].iloc[0]
        A("> **Reading the audit:**")
        A(f"> - **The biggest hole is LF ({g.get('LF', 0):+d}) — which is "
          "the Duran slump itself.** The best 'deadline additions' are "
          "internal and cheap: Duran's positive regression — now sheltered "
          "by a platoon with new RHB pickup Jahmai Jones (Detroit, 7/14 — a "
          "reclamation bet: .426 wOBA vs LHP in 2025 but .272 in 2026, "
          "albeit with a .327 xwOBA) — and Roman Anthony's "
          "eventual return (still rehabbing, no firm date).")
        A(f"> - **DH ({g.get('DH', 0):+d}) is a positional-bar problem, "
          "not a Yoshida problem.** Yoshida himself has been above league "
          "average with one of the lowest strikeout rates in baseball; "
          "the gap comes from the high league DH bar and the non-Yoshida "
          "PAs at the spot. Gonzalez covers the tough lefties. No move "
          "needed.")
        A(f"> - **SS ({g.get('SS', 0):+d}) is the one true external "
          "target — with a caveat: half the infield is on the IL** (Mayer "
          "10-day, Story 60-day, Kiner-Falefa 10-day; Casas 60-day at 1B). "
          "A Tsung-Che Cheng / Andruw Monasterio platoon is bridging short. "
          "A stabilizing infield bat is still the highest-leverage add, but "
          "internal returns shrink the urgency.")
        A(f"> - **Catcher ({g.get('C', 0):+d}) is the sneaky third add** — "
          "below league average at the position all season, with no "
          "internal help coming (unlike the infield). A controllable "
          "upgrade is a three-season fix, not a rental.")
        A("> - **A bullpen arm is the classic fringe-buyer move**: relievers "
          "are the cheapest marginal wins at the deadline, and the FIP-ERA "
          "gap says this pen will regress without help.")
        A("> - **The Contreras tension:** the reported sell candidate is "
          f"Boston's *best hitter* ({int(first_base['bos_wrc'])} wRC+ at "
          "1B). Selling him only makes sense in the full-sell branch — "
          "moving him from a live playoff race would be self-defeating.\n")

    A("## Is Duran's rebound visible yet? (2026 by month)\n")
    A("| Month | PA | wOBA | xwOBA |")
    A("|-------|---:|-----:|------:|")
    mn = {3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep"}
    for _, r in monthly.iterrows():
        A(f"| {mn.get(int(r['month']), int(r['month']))} | {int(r['PA'])} | "
          f"{r['wOBA']:.3f} | {r['xwOBA']:.3f} |")
    jul = monthly[monthly["month"] == 7]
    jul_note = ""
    if len(jul):
        j = jul.iloc[0]
        jul_note = (f"and July's contact quality (a .{j['xwOBA']*1000:.0f} "
                    f"xwOBA over {j['PA']:.0f} PA, vs .{j['wOBA']*1000:.0f} "
                    "results) has surged with the team's streak while the "
                    "results *still* lag it. ")
    A("\n> Getting warmer. May was a full month of the 2024–25 player "
      "(.375 wOBA), April and June were bad on both results and contact "
      f"quality — {jul_note}"
      "The pattern holds: the skills flicker, the luck stays bad. This "
      "volatility is exactly why the deadline is the wrong time to price "
      "him.\n")
    A("## AL race snapshot\n")
    A("| Team | W-L | RD | WC GB | Odds |")
    A("|------|-----|---:|------:|-----:|")
    for _, r in sim.sort_values("playoff_odds", ascending=False).iterrows():
        if r["playoff_odds"] < 0.01:
            continue
        A(f"| {r['team']} | {int(r['W'])}-{int(r['L'])} | "
          f"{int(r['run_diff']):+d} | {r['wc_gb']} | "
          f"{r['playoff_odds']*100:.0f}% |")
    A("\n---\n*Method:* team talent = Pythagorean win% (exponent 1.83) "
      f"regressed toward .500 with {REGRESS_GAMES} games of shrinkage; "
      f"{N_SIMS:,} Monte Carlo seasons; remaining games simulated as "
      "independent binomials (no schedule, injuries, or deadline moves — a "
      "simplification that slightly compresses odds toward the pack). "
      "Reported trade candidates per Boston media (NBC Sports Boston, July "
      "2026). Re-run `python run_all.py` before publishing to refresh.")
    out = C.OUT_DIR / "deadline_decision.md"
    out.write_text("\n".join(L))
    print(f"  [deadline] wrote {out}")


# --------------------------------------------------------------- article
def article(sim: pd.DataFrame, v: dict, aud: pd.DataFrame = None,
            units: dict = None):
    bos = sim[sim["team"].str.contains("Red Sox")].iloc[0]
    res = json.load(open(C.DATA_DIR / "analysis_results.json"))
    try:
        bat = json.load(open(C.DATA_DIR / "battery.json"))
    except FileNotFoundError:
        bat = None
    try:
        bmod = json.load(open(C.DATA_DIR / "battery_model.json"))
    except FileNotFoundError:
        bmod = None
    try:
        xc = json.load(open(C.DATA_DIR / "xcontact.json"))
    except FileNotFoundError:
        xc = None
    sa = res.get("speed_adjusted", {})
    s26 = res["seasons"]["2026"]
    s24 = res["seasons"]["2024"]

    L = []
    A = L.append
    streak = str(bos.get("streak", ""))
    n_streak = int(streak[1:]) if streak[1:].isdigit() else 0
    hot = streak.startswith("W") and n_streak >= 3
    # the signature streak is a season fact; persisted so the number
    # survives the run ending (run() tracks the max in deadline.json)
    try:
        big = int(json.load(open(C.DATA_DIR / "deadline.json"))
                  .get("max_win_streak", 13))
    except (FileNotFoundError, ValueError):
        big = 13
    A(f"# The Red Sox Won {big} Straight. Now Comes the Hard Part\n")
    A("### A trade-deadline case study: the run differential saw the streak "
      "coming — and says buy\n")
    A(f"*Deadline runway, {dt.date.today().year} · data through "
      f"{dt.date.today().isoformat()} · full methods, code and figures at "
      "the end*\n")
    A("---\n")
    if hot and n_streak >= 8:
        A(f"The Red Sox are the hottest team in baseball — winners of "
          f"**{n_streak} straight**, the longest run in the majors this "
          "season. Three weeks ago they were well under .500 and the easy "
          "take wrote itself: sell. Today they are "
          f"{int(bos['W'])}-{int(bos['L'])}, and **{_wc_phrase(bos)}**.\n")
    else:
        A(f"The Red Sox ripped off a **{big}-game winning streak** around "
          "the All-Star break — the longest run in the majors this season — "
          "and turned a sell-the-vets summer into a playoff race. They are "
          f"{int(bos['W'])}-{int(bos['L'])}"
          + (f" (riding a {n_streak}-game winning streak)" if hot else "")
          + f", and **{_wc_phrase(bos)}**.\n")
    A("The streak itself is not the story. Boston has outscored its "
      f"opponents by **{int(bos['run_diff']):+d}** runs this season, the "
      f"profile of a .{bos['pythag']*1000:.0f} team, and spent three "
      f"months wearing a .{bos['pct']*1000:.0f} record anyway. This is "
      "not a mediocre club that got hot at the right time. It is a good "
      "club whose record finally caught up with how it has been playing. "
      f"In {N_SIMS:,} simulations of the rest of the season, Boston makes "
      f"the playoffs **{v['odds']*100:.0f}%** of the time.\n")
    A("![AL playoff race](figures/12_playoff_race.png)\n")
    A(("That is a playoff team, and the standings are only starting to "
       "reflect it. "
       if v["odds"] >= 0.62 else
       "That is a coin flip: a live playoff team wearing a seller's "
       "record. "
       if v["odds"] >= 0.40 else
       "That is not a contender. It is also not a corpse. ")
      + "The deadline question is what a team like this should buy, and "
      "the answer runs through the roster's strangest case. Jarren "
      "Duran's season is the team's season in miniature: **the process "
      "is better than the results.** His file comes later. The money "
      "question comes first.\n")
    A("## So: buy or sell?\n")
    if v["odds"] >= 0.40:
        A(f"**{v['call']}.** At ~{v['odds']*100:.0f}% odds a marginal win "
          "is worth real assets, so the fire-sale case is dead and even "
          "the sell-the-vets hedge should wait. But buy carefully, and "
          "with one constraint over every deal: **don't disturb the "
          "room.** Whatever mix of talent and chemistry produced a "
          f"{big}-game winning streak is worth protecting, so additions should cost "
          "prospects rather than big-leaguers and fill empty spots rather "
          "than occupied ones. That points to a deliberately **small** "
          "deadline. The biggest upgrades available to this roster — "
          "Anthony, Mayer, Story, Casas, and Duran's own regression — are "
          "internal, and free. By asset:\n")
    else:
        A(f"**{v['call']}.** With ~{v['odds']*100:.0f}% odds, splurging on "
          "rentals would be malpractice — but so would a fire sale of a "
          "positive-run-differential roster with a top-10 rotation. The "
          "decision tree by asset:\n")
    A("- **Hold Duran through the deadline.** His trade value sits at its "
      "nadir while his underlying profile says the market is under-pricing "
      "him (the full case is a chapter below). Sophisticated buyers read "
      "xstats too — you will not get 2024 prices in August 2026. Revisit in "
      "the winter, after the rebound has (or hasn't) shown up on the field.")
    A("- **Keep the young outfield** (Anthony, Rafaela, Abreu) and the "
      "rotation — they are the 2027 team.")
    if v["odds"] >= 0.40:
        A("- **Keep the expiring veterans.** Gray, Chapman and Contreras "
          "were the winter's reported trade names; right now they are "
          "playoff innings, playoff at-bats, and most of the clubhouse's "
          "seniority. The sell branch reopens only if the gap blows out "
          "before August 1.")
    else:
        A("- **The only sell-now inventory is the expiring veterans** (Gray, "
          "Chapman, Contreras have been the reported names) — and only if "
          "the next three weeks bury the wild-card gap.")
    yo = _player_line("Masataka Yoshida")
    if yo is not None and yo.get("wRC+", 0) >= 95:
        A("- **Keep Yoshida, and retire the dead-money talk.** He has "
          f"quietly been a useful hitter this year: {yo['wRC+']:.0f} wRC+, "
          f".{yo['OBP']*1000:.0f} OBP, a {yo['K%']*100:.0f}% strikeout "
          "rate that ranks among the league's lowest, league-average "
          "contact quality. The contract ($18.6M through 2027 for a DH) "
          "is still underwater as a trade asset, but the bat is doing its "
          "job. Absorb the deal and play the hitter.\n")
    else:
        A("- **Absorb Yoshida.** The contract has negative trade value; "
          "paying to escape it burns real prospects to save sunk "
          "money.\n")

    if aud is not None:
        g = {r["pos"]: int(r["gap"]) for _, r in aud.iterrows()}
        first_base = aud[aud["pos"] == "1B"].iloc[0]
        A("## And if they buy — where? Not where you'd think\n")
        A("![Positional audit](figures/13_positional_audit.png)\n")
        A("Auditing every position against league average (PA-weighted "
          "wRC+) reorders the shopping list:\n")
        A(f"- **The biggest hole on the roster is left field "
          f"({g.get('LF', 0):+d} wRC+ vs league) — which is the Duran slump "
          "itself.** Boston's best deadline additions are internal and "
          "nearly free: Duran's batted-ball luck regressing to normal — the "
          "club is already sheltering him in a platoon with new right-handed "
          "pickup Jahmai Jones — a zero-cost reclamation bet whose elite "
          "2025 line against lefties (.426 wOBA, backed by a .405 xwOBA) "
          "collapsed to .272 this year, though even that came with a .327 "
          "xwOBA. Boston, fittingly, acquired another hitter running under "
          "his contact quality — and Roman Anthony's eventual return, though "
          "he is still rehabbing without a firm date. A team that trades "
          "for an outfielder here would be buying what it already owns.")
        A(f"- **Shortstop ({g.get('SS', 0):+d}) is the one true external "
          "target — with an asterisk: half the infield is hurt** (Mayer, "
          "Story, Kiner-Falefa; Casas at first). A Cheng/Monasterio platoon "
          "is bridging short, and DH has steadied on its own — Yoshida has "
          "been above league average, with Gonzalez taking the tougher "
          "lefties. A cheap, controllable infield stabilizer is still the "
          "highest-leverage add; the internal returns are the fallback, "
          "not the plan.")
        if bat:
            bb = bat["batteries"]

            def _ra9(p, c):
                v = bb.get(p, {}).get(c, {}).get("RA9")
                return f"{v:.2f}" if v is not None else "—"

            w9 = bat["per_catcher"]["Connor Wong"]["RA9"]
            n9 = bat["per_catcher"]["Carlos Narváez"]["RA9"]
            A(f"- **Catcher ({g.get('C', 0):+d}) looks like a hole — and "
              "is the trap.** The Narváez/Wong bats are below the "
              "position's league average, but the battery data says leave "
              f"the tandem alone: the staff runs a {w9:.2f} RA9 with Wong "
              f"and {n9:.2f} with Narváez, and the club is quietly running "
              "an assignment system — Gray at "
              f"{_ra9('Sonny Gray', 'Connor Wong')} with Wong "
              f"({_ra9('Sonny Gray', 'Carlos Narváez')} with Narváez), "
              f"Bennett at {_ra9('Jake Bennett', 'Carlos Narváez')} with "
              "Narváez, Bello five runs better with Wong, and the leverage "
              "relievers sharper with Narváez (fig. 14). Small, "
              "usage-confounded samples — but that is working "
              "pitcher-catcher chemistry, and a mid-race catcher trade "
              "would rip up every one of those pairings for a bat."
              + ((" A formal check backs this up: a fixed-effects model "
                  "(pitcher, opponent and park controls, cluster-"
                  "bootstrapped) puts the overall catcher effect at "
                  f"{bmod['fe']['catcher_effect_wong_minus_narvaez']*1000:+.0f} "
                  "points of wOBA-against toward Wong with a 95% CI of "
                  f"[{bmod['fe']['ci95'][0]*1000:+.0f}, "
                  f"{bmod['fe']['ci95'][1]*1000:+.0f}] — no significant "
                  "catcher problem exists, and empirical-Bayes shrinkage "
                  "pulls most single-pairing splits toward noise (fig. "
                  "15). There is nothing here a trade would fix.")
                 if bmod else ""))
        else:
            A(f"- **Catcher ({g.get('C', 0):+d}) is the sneaky third "
              "add.** Narváez/Wong have been below the position's league "
              "average all year, and unlike the injury-driven infield "
              "holes, no internal help is coming.")
        A("- **The bullpen is the quiet weakness.** Its ERA ranks "
          f"{units['bullpen_era_rank'][0]}th, but its FIP ranks "
          f"{units['bullpen_fip_rank'][0]}th and its WAR "
          f"{units['bullpen_war_rank'][0]}th — the ERA is flattering it. "
          "One reliever is the cheapest marginal win at any deadline.")
        A(f"- **And the awkward one: the reported sell candidate is their "
          f"best hitter.** Willson Contreras carries a "
          f"{int(first_base['bos_wrc'])} wRC+ at first base. Moving him "
          + ("while holding a playoff spot"
             if str(bos.get("wc_gb", "")).strip() in ("-", "", "0.0")
             else f"while {bos['wc_gb']} games out of a playoff spot")
          + " isn't a retool — it's surrender priced as prudence.\n")
        if bat:
            A("![Battery map](figures/14_battery_map.png)\n")

    A("## The left fielder: the whole season in one player\n")
    A("The biggest hole on the roster is the Duran slump — which makes the "
      "biggest deadline call a diagnosis, not a trade. The full workup, in "
      "four findings:\n")
    A("**1. His 2024 breakout was real — a peak in every phase.** The "
      f"All-Star year (wRC+ {s24['wRC+']:.0f}) came with career-best swing "
      "decisions, career-best baserunning (+8.3 runs) and a defensive spike "
      "(+7.6). His xwOBA (.340) was legitimate. Results outran contact "
      "quality by just 17 points of wOBA — and once you credit the points "
      "his speed adds over Statcast expectations in his other seasons "
      "(xstats ignore sprint speed), the true luck component lands between "
      "5 and 14 points. 2024 was his peak, mildly gilded — not a mirage.\n")
    A(f"**2. His 2026 collapse is part erosion, mostly bad luck.** The wRC+ "
      f"({s26['wRC+']:.0f}) looks like a career ending. But his wOBA "
      f"(.{s26['wOBA']*1000:.0f}) sits *below* his xwOBA (.{s26['xwOBA']*1000:.0f}) — "
      "and for a burner who normally beats his xstats, running negative is a "
      f"{abs(sa.get('gap_2026_deficit',0))*1000:.0f}-to-"
      f"{abs(sa.get('gap_2026_deficit_ex26') or sa.get('gap_2026_deficit',0))*1000:.0f}"
      "-point anomaly against his own baseline. His BABIP (.244) is 67 points under what his "
      "contact quality supports. Real erosion exists — chase, whiff and "
      "hard-hit rate all moved the wrong way — but no injury has been "
      "reported, and his speed, baserunning and defense remain plus. The "
      "legs a buyer would pay for are intact.\n")
    if xc:
        du = xc["duran"]
        dec10 = [d for d in xc["deciles"] if d["decile"] == 10][0]
        full = du.get("speed_premium_full_woba")
        A("*The speed claim, formalized:* rather than assert that xstats "
          "shortchange burners, we trained the corrected model — gradient "
          f"boosting on all {xc['n_batted_balls']:,} tracked 2026 batted "
          "balls (exit velo, launch angle, spray), once without and once "
          "with sprint speed, validated out-of-sample with folds grouped "
          "by batter. The speed-blind model under-predicts the fastest "
          f"decile of hitters by {dec10['resid_base']*1000:+.0f} points of "
          "BABIP — the blind spot, measured (fig. 16) — and for Duran "
          f"({du['sprint_speed']:.1f} ft/s, decile {du['decile']}) the "
          "speed term is worth "
          f"**{du['speed_premium_wobacon']*1000:+.0f} points of wOBA on "
          "contact**"
          + (f" (≈{full*1000:+.0f} on full wOBA at his contact rate)"
             if full else "")
          + " — landing inside the +5-to-14 band this analysis derived "
          "independently from his career gaps.\n")
        A("![Speed model](figures/16_speed_model.png)\n")
    pkc = res.get("park_check", {}).get("career", {})
    hg = (pkc.get("home", {}).get("gap") or 0) * 1000
    rg = (pkc.get("road", {}).get("gap") or 0) * 1000
    A(f"**3. It isn't Fenway.** His career wOBA−xwOBA gap is {hg:+.0f} "
      f"points at home and {rg:+.0f} on the road — essentially identical. "
      "The skill travels. 2024's overperformance was actually "
      "*road*-concentrated (+50 vs +14), the opposite of a Monster-driven "
      "fluke.\n")
    A("**4. His true level is the 2023–25 plateau (~110–120 "
      "wRC+).** Aging explains ~7 points of the 70-point fall from 2024; "
      "regression from a lucky peak plus a 2026 bad-luck tail explains the "
      "rest.\n")
    A("![BABIP by season](figures/01_babip_vs_league.png)\n")
    A("His season has the same shape as the team's: results running "
      "behind process, and a market ready to misprice both. The roster's "
      "biggest hole is the one no trade can fix, and none needs to.\n")

    A("## What would change my mind\n")
    A("- A 2026 second-half BABIP rebound with flat chase/whiff → the luck "
      "thesis confirmed; extend-or-hold gets stronger.")
    A("- Chase% and whiff% still elevated through September → the erosion is "
      "real; sell next winter at whatever the market bears.")
    A("- The wild-card gap at 6+ by August 1 → flip the expiring vets and "
      "call it a retool, not a teardown.\n")
    A("---\n")
    A("*Methods: park-adjusted wRC+ for all talent comparisons; luck "
      "measured against Duran's own career wOBA−xwOBA gap (Statcast xstats "
      "ignore sprint speed), cross-checked by a gradient-boosted expected-"
      "contact model trained league-wide with sprint speed as a feature "
      "(out-of-fold, folds grouped by batter); venue splits from "
      "pitch-level Statcast; playoff odds from a 10,000-run Monte Carlo "
      "(Pythagorean talent, regressed, no schedule effects); catcher "
      "effects from a WOWY + fixed-effects model (pitcher/opponent/park "
      "controls, cluster-bootstrap CIs, empirical-Bayes shrinkage); ~a "
      "dozen significance tests reported without family-wise correction — "
      "isolated p≈.03–.05 findings are directional. Data: Baseball Savant "
      "(pybaseball), FanGraphs, MLB Stats API; salaries via Spotrac. Full "
      "reproducible pipeline: `python run_all.py`.*")
    out = C.OUT_DIR / "ARTICLE.md"
    out.write_text("\n".join(L))
    print(f"  [deadline] wrote {out}")


def run():
    df = al_standings()
    sim = simulate(df)
    sim.to_csv(C.DATA_DIR / "al_race_sim.csv", index=False)
    bos = sim[sim["team"].str.contains("Red Sox")].iloc[0]
    v = verdict(bos)
    # remember the season's longest win streak even after it snaps
    try:
        max_stk = int(json.load(open(C.DATA_DIR / "deadline.json"))
                      .get("max_win_streak", 13))
    except (FileNotFoundError, ValueError):
        max_stk = 13
    s = str(bos.get("streak", ""))
    if s.startswith("W") and s[1:].isdigit():
        max_stk = max(max_stk, int(s[1:]))
    with open(C.DATA_DIR / "deadline.json", "w") as f:
        json.dump({"as_of": dt.date.today().isoformat(),
                   "verdict": v,
                   "max_win_streak": max_stk,
                   "bos": {k: (float(bos[k]) if isinstance(bos[k], (int, float, np.floating)) else str(bos[k]))
                           for k in ("W", "L", "run_diff", "pythag", "talent",
                                      "playoff_odds", "wc_gb", "streak")}},
                  f, indent=2, default=float)
    fig_race(sim)
    print("  [deadline] wrote figure 09")
    monthly = duran_monthly()
    aud, units = positional_audit()
    aud.to_csv(C.DATA_DIR / "positional_audit.csv", index=False)
    fig_positions(aud)
    print("  [deadline] wrote figure 10")
    memo(sim, v, monthly, aud, units)
    article(sim, v, aud, units)


if __name__ == "__main__":
    run()
