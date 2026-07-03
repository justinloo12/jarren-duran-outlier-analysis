"""How to fix the Red Sox outfield jam.

Builds a light surplus-value model over the OF/DH group and turns it, plus the
performance analysis and current roster context, into a sequenced plan.

Forward-looking WAR figures are *projections* (anchored on 2025 full seasons
with regression toward true talent; 2026 is partial and, for Anthony, injury-
shortened), and are labeled as such. Surplus value uses a market rate of
~$8M / WAR. This is a back-of-envelope framework, not a precise valuation.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import config as C
from . import style as S

S.apply()

DOLLARS_PER_WAR = 8.0  # $M per WAR, approx open-market rate

# name, position, proj true-talent WAR (full season), control seasons remaining
# incl. 2026, 2026 salary $M, verdict, one-line rationale.
PLAYERS = [
    dict(name="Roman Anthony", pos="LF/CF", proj_war=3.8, control=8,
         salary=2.6, verdict="KEEP — cornerstone",
         note="22, 8yr/$130M extension; franchise bat. Untouchable. "
              "Currently on the 60-day IL (finger)."),
    dict(name="Ceddanne Rafaela", pos="CF/SS", proj_war=3.2, control=6,
         salary=2.0, verdict="KEEP — premium glove",
         note="25, 8yr/$50M; elite CF defense + SS/utility flexibility at a "
              "cost-controlled price. Plays the hardest position."),
    dict(name="Wilyer Abreu", pos="RF", proj_war=2.8, control=4,
         salary=0.8, verdict="KEEP — cheap surplus",
         note="27, pre-arb ($0.8M) through 2029; plus RF glove and an "
              "above-average, left-handed bat. Best value on the roster."),
    dict(name="Jarren Duran", pos="LF/CF", proj_war=2.6, control=3,
         salary=7.7, verdict="TRADE — the movable piece",
         note="29, controllable through 2028; above-average at true talent "
              "(~2025) but redundant behind the core and the priciest of the "
              "young group. Highest-return asset the Sox can actually move."),
    dict(name="Masataka Yoshida", pos="DH", proj_war=0.3, control=2,
         salary=18.6, verdict="ABSORB / salary-dump",
         note="32, $18.6M through 2027, DH-only, below-average bat. Negative "
              "trade value; move only in a partial salary-dump, else let it "
              "expire as a platoon DH."),
    dict(name="Nate Eaton", pos="4th OF", proj_war=0.7, control=4,
         salary=0.76, verdict="DEPTH",
         note="Cheap, versatile 4th/5th OF; useful bench piece, not a "
              "blocker."),
]

VERDICT_COLOR = {
    "KEEP — cornerstone": "#1b5e20",
    "KEEP — premium glove": "#2e7d32",
    "KEEP — cheap surplus": "#43a047",
    "TRADE — the movable piece": "#BD3039",
    "ABSORB / salary-dump": "#616161",
    "DEPTH": "#9e9e9e",
}


def table() -> pd.DataFrame:
    df = pd.DataFrame(PLAYERS)
    df["surplus_annual"] = df["proj_war"] * DOLLARS_PER_WAR - df["salary"]
    df["surplus_total"] = df["surplus_annual"] * df["control"]
    # attach actual recent output for grounding
    rs = pd.read_csv(C.DATA_DIR / "redsox_of_comparison.csv")
    for yr in (2025, 2026):
        m = {r["Name"]: r["wRC+"] for _, r in rs[rs.Season == yr].iterrows()}
        df[f"wRCplus_{yr}"] = df["name"].map(m)
    df.to_csv(C.DATA_DIR / "outfield_plan.csv", index=False)
    return df


def fig_plan(df):
    """Horizontal bar: estimated annual surplus value, colored by verdict."""
    d = df.sort_values("surplus_annual")
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    colors = [VERDICT_COLOR[v] for v in d["verdict"]]
    ax.barh(d["name"], d["surplus_annual"], color=colors, height=0.66,
            zorder=3)
    ax.axvline(0, color=S.SPINE, lw=1.2, zorder=2)
    for y, (_, r) in enumerate(d.iterrows()):
        x = r["surplus_annual"]
        stat = (f"{r['proj_war']:.1f} WAR · ${r['salary']:.1f}M · "
                f"{int(r['control'])}yr")
        if x >= 0:
            ax.text(x + 0.7, y, stat + " control", va="center", ha="left",
                    fontsize=8.5, color=S.MUTED)
        else:  # inside the dark bar, white for contrast
            ax.text(x + 0.5, y, stat, va="center", ha="left",
                    fontsize=8.5, color="white")
        vx = -0.7 if x >= 0 else 0.7
        ax.text(vx, y, r["verdict"].split(" — ")[0],
                va="center", ha="right" if x >= 0 else "left",
                fontsize=8.5, fontweight="bold", color=VERDICT_COLOR[r["verdict"]])
    S.style(ax, grid_axis="x")
    ax.tick_params(axis="y", labelcolor=S.TEXT)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["name"], fontsize=10)
    ax.set_xlabel("Estimated annual surplus value  ($M = proj. WAR × $8M − 2026 salary)")
    ax.set_xlim(-20, 37)
    S.titled(ax, "Keep the cheap core, move Duran, absorb Yoshida",
             "Value each player returns over cost — labels show projected WAR · "
             "salary · years of control")
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "07_outfield_plan.png")
    plt.close(fig)


def memo(df):
    L = []
    A = L.append
    A("# How to Fix the Red Sox Outfield Jam\n")
    A("*Generated 2026-07-02 · output via FanGraphs; salary via Spotrac; "
      "roster/injury context via reporting (July 2026). "
      "Forward WAR are labeled projections; surplus uses ~$8M/WAR.*\n")

    A("## The situation\n")
    A("Five bats for four spots (three OF + DH): **Roman Anthony, Ceddanne "
      "Rafaela, Wilyer Abreu, Jarren Duran, Masataka Yoshida**. The consensus "
      "alignment is Anthony LF / Rafaela CF / Abreu RF, which leaves Duran (a "
      "natural LF/CF) and the DH-only Yoshida fighting for at-bats — Duran "
      "opened 2026 at DH. Boston was criticized for not clearing this two "
      "winters running.\n")
    A("> **Timing wrinkle that changes everything:** the jam is *masked right "
      "now* because Anthony is on the 60-day IL (finger). Duran, Abreu and "
      "Rafaela are the current starters and the Sox actually need Duran's "
      "innings today. The crunch is a **2027 problem**, not a July-2026 "
      "emergency — which argues against a fire-sale at this deadline.\n")

    A("## Who's what (surplus-value view)\n")
    A("| Player | Pos | Proj WAR | Ctrl yrs | 2026 $ | Annual surplus | 2025→2026 wRC+ | Verdict |")
    A("|--------|-----|--------:|--------:|------:|---------------:|:-------------:|---------|")
    for _, r in df.sort_values("surplus_annual", ascending=False).iterrows():
        A(f"| {r['name']} | {r['pos']} | {r['proj_war']:.1f} | "
          f"{int(r['control'])} | ${r['salary']:.1f}M | "
          f"${r['surplus_annual']:+.1f}M | "
          f"{_i(r.get('wRCplus_2025'))}→{_i(r.get('wRCplus_2026'))} | "
          f"{r['verdict']} |")
    A("\n*Surplus = proj. true-talent WAR × $8M − 2026 salary (annual; multiply "
      "by control years for total). Illustrative, not a precise valuation.*\n")

    A("## The plan\n")
    A("### 1. Keep the young, cheap, controllable core (the actual OF)\n")
    A("- **Roman Anthony (LF)** — franchise cornerstone on an 8yr/$130M deal; "
      "untouchable. Health is the only question.")
    A("- **Ceddanne Rafaela (CF)** — elite center-field glove + SS/utility "
      "flexibility at $2M; he anchors the premium position and gives roster "
      "elasticity.")
    A("- **Wilyer Abreu (RF)** — the best surplus on the team ($0.8M, plus "
      "glove, above-average LH bat, controlled through 2029).")
    A("These three are the 2027 outfield. Everything else flexes around them.\n")

    A("### 2. Trade Jarren Duran — but sequence it right\n")
    A("- He is **the movable piece**: redundant behind the core, above-average "
      "at true talent (~110 wRC+, his 2025 line), and controllable through "
      "2028 — exactly the profile a contender pays for. With Boston's "
      "top-10 rotation already a strength, the return should target **bats / "
      "young controllable position talent**, not pitching.")
    A("- **Don't dump him at the 2026 deadline.** Two reasons: (a) his value is "
      "artificially low right now — the analysis shows 2026 is partly *unlucky* "
      "(wOBA below xwOBA; BABIP .244 vs .311 xBABIP), so positive regression is "
      "likely; and (b) with Anthony hurt, the Sox need Duran's at-bats through "
      "2026.")
    A("- **Trade him in the offseason**, once Anthony is healthy (jam returns, "
      "depth need gone) and Duran has ideally rebuilt value with a second-half "
      "bounce. Sell the 2025 version — cheap, fast, defensively flexible, "
      "controllable — and **target young controllable pitching**, the org's "
      "real need.")
    A("- *Contingency:* if a contender meets Breslow's (historically high) ask "
      "at the deadline, take it — but only at a price reflecting the 2025 "
      "player, not the 2026 slump.\n")

    A("### 3. Manage the Yoshida problem separately\n")
    A("- $18.6M through 2027 for a DH-only, below-average bat is a **sunk "
      "cost with negative trade value**. Do **not** attach a prospect or eat "
      "Duran's value to move him.")
    A("- Best case: a **partial salary-dump** if a DH-needy team bites. "
      "Otherwise **absorb** him as a strong-side platoon DH and let the deal "
      "expire after 2027 — which then opens the DH slot cleanly.\n")

    A("### 4. Resulting 2027 alignment\n")
    A("| Spot | 2027 | Notes |")
    A("|------|------|-------|")
    A("| LF | Roman Anthony | cornerstone |")
    A("| CF | Ceddanne Rafaela | premium glove; SS/util flex |")
    A("| RF | Wilyer Abreu | cheap surplus |")
    A("| DH | Yoshida (final year) → open in 2028 | platoon/absorb |")
    A("| 4th OF | Nate Eaton / depth | |")
    A("| — | **Duran traded** for pitching | value cashed near his 2025 level |")
    A("")

    A("## Risks & honest caveats\n")
    A("- **Sell-low risk on Duran:** part of his 2026 slide is real — chase%, "
      "whiff% and hard-hit% all worsened significantly vs 2025 — so the "
      "rebound may be partial, and waiting costs you if the erosion continues. "
      "Monitor those skill metrics, not the batting average.")
    A("- **Anthony's health:** the whole plan assumes he returns as the ~5-WAR "
      "talent. Recurring hand/finger issues would reopen a need for Duran and "
      "change the math.")
    A("- **Yoshida may be immovable at any reasonable cost** — plan to absorb, "
      "not to escape.")
    A("- Projections and $8M/WAR are directional; use them to rank decisions, "
      "not to set exact asking prices.\n")

    A("## Bottom line\n")
    A("Keep the cheap, young, controllable core (Anthony, Rafaela, Abreu); "
      "**trade Duran in the offseason from a position of surplus and rebuilt "
      "value, for pitching**; and quarantine the Yoshida contract rather than "
      "pay to escape it. The jam is a 2027 problem — solve it with a winter "
      "trade, not a deadline dump at the bottom of Duran's value.\n")

    out = C.OUT_DIR / "outfield_plan.md"
    out.write_text("\n".join(L))
    print(f"  [plan] wrote {out}")


def _i(x):
    return "n/a" if x is None or pd.isna(x) else f"{x:.0f}"


def run():
    df = table()
    fig_plan(df)
    print("  [plan] wrote figure 07")
    memo(df)


if __name__ == "__main__":
    run()
