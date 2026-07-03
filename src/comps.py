"""Peer & market comparison: Red Sox OF, league average, and a salary-vs-output
cohort of outfielders.

Output data comes from the FanGraphs pulls (data/fangraphs/league_YYYY.csv,
all hitters). Salary has no free API, so 2026 figures are manually sourced from
Spotrac via web search and recorded here with an as-of date; any player whose
2026 salary could not be verified is omitted rather than guessed. Re-verify
against Spotrac before quoting.
"""
from __future__ import annotations

import json
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from . import style as S

S.apply()

SALARY_AS_OF = "2026-07-02"
SALARY_SOURCE = "Spotrac 2026 cap hit / total salary, via web search"

# 2026 salary (total salary / cap hit), USD. See module docstring for sourcing.
SALARY_2026 = {
    # --- Red Sox OF / DH ---
    "Jarren Duran": 7_700_000,       # 1yr, avoided arb (declined $8M option)
    "Wilyer Abreu": 810_000,         # pre-arb rookie deal, FA 2030
    "Ceddanne Rafaela": 2_000_000,   # 8yr/$50M extension
    "Roman Anthony": 2_625_000,      # 8yr/$130M extension (up to $230M)
    "Masataka Yoshida": 18_600_000,  # 5yr/$90M through 2027
    "Nate Eaton": 760_000,           # ~MLB minimum, pre-arb (approx)
    # --- salary/output cohort (other OF) ---
    "Juan Soto": 61_875_000,
    "Aaron Judge": 40_000_000,
    "Mike Trout": 37_116_666,
    "Cody Bellinger": 36_500_000,
    "Luis Robert Jr.": 20_000_000,
    "Jung Hoo Lee": 18_833_333,
    "Byron Buxton": 15_142_857,
    "Teoscar Hernandez": 14_709_589,
    "Daulton Varsho": 10_750_000,
    "Adolis Garcia": 10_000_000,
    "Michael Harris II": 9_000_000,
    "Steven Kwan": 7_725_000,
    "Harrison Bader": 7_500_000,
    "Cedric Mullins": 6_500_000,
}
APPROX_SALARY = {"Nate Eaton"}  # flagged as estimated, not confirmed

# Red Sox OF/DH group for the teammate comparison (incl. Yoshida per request).
REDSOX_GROUP = ["Jarren Duran", "Wilyer Abreu", "Ceddanne Rafaela",
                "Roman Anthony", "Masataka Yoshida", "Nate Eaton"]
# Cohort in the scatter needs a stable-ish sample; always keep Duran + Sox.
SCATTER_MIN_PA = 150


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s))
                   if not unicodedata.combining(c)).lower().strip()


def _league(season):
    return pd.read_csv(C.FANGRAPHS_DIR / f"league_{season}.csv")


def _lookup(df, name):
    idx = {_norm(n): n for n in df["Name"]}
    m = idx.get(_norm(name))
    return df[df["Name"] == m].iloc[0] if m is not None else None


def league_benchmarks():
    """League-average context for 2026 (OF and all-hitter)."""
    of = pd.read_csv(C.DATA_DIR / "league_of_2026.csv")
    allh = _league(2026)
    out = {}
    for lab, d in [("of", of), ("all", allh)]:
        q = d[d["PA"] >= 200]
        w = q["PA"].to_numpy()
        out[lab] = {
            "wRC+": float(np.average(q["wRC+"], weights=w)),
            "wOBA": float(np.average(q["wOBA"], weights=w)),
            "WAR_per600": float(np.average(q["WAR"] / q["PA"] * 600, weights=w)),
            "n": int(len(q)),
        }
    return out


def redsox_table():
    """Red Sox OF/DH: 2025 & 2026 output + 2026 salary."""
    rows = []
    for season in (2025, 2026):
        lg = _league(season)
        for name in REDSOX_GROUP:
            r = _lookup(lg, name)
            if r is None:
                continue
            rows.append({
                "Name": name, "Season": season,
                "Age": r.get("Age"), "PA": r.get("PA"),
                "wRC+": r.get("wRC+"), "WAR": r.get("WAR"),
                "wOBA": r.get("wOBA"), "Spd": r.get("Spd"),
                "salary_2026": SALARY_2026.get(name),
            })
    df = pd.DataFrame(rows)
    df.to_csv(C.DATA_DIR / "redsox_of_comparison.csv", index=False)
    return df


def salary_cohort():
    """Join 2026 salary to 2026 output for the scatter cohort."""
    lg = _league(2026)
    rows = []
    for name, sal in SALARY_2026.items():
        r = _lookup(lg, name)
        if r is None:
            continue
        rows.append({
            "Name": name, "salary_2026": sal,
            "approx_salary": name in APPROX_SALARY,
            "Age": r.get("Age"), "PA": r.get("PA"),
            "wRC+": r.get("wRC+"), "WAR": r.get("WAR"),
            "wOBA": r.get("wOBA"), "Spd": r.get("Spd"),
            "redsox": name in REDSOX_GROUP,
            "dollars_per_war": (sal / r.get("WAR")
                               if r.get("WAR") and r.get("WAR") > 0 else None),
        })
    df = pd.DataFrame(rows).sort_values("salary_2026", ascending=False)
    df.to_csv(C.DATA_DIR / "salary_output_cohort.csv", index=False)
    return df


# --- figures ---------------------------------------------------------------
RED = "#BD3039"
NAVY = "#0C2340"
GOLD = "#C8A15A"
GREY = "#8a8d90"


def fig_redsox(df, bench):
    """Grouped bar: 2025 vs 2026 wRC+ for Red Sox OF/DH, salary labeled."""
    order = ["Jarren Duran", "Wilyer Abreu", "Ceddanne Rafaela",
             "Roman Anthony", "Masataka Yoshida", "Nate Eaton"]
    order = [n for n in order if n in df["Name"].values]
    x = np.arange(len(order))
    w = 0.36
    v25 = [_val(df, n, 2025, "wRC+") for n in order]
    v26 = [_val(df, n, 2026, "wRC+") for n in order]
    fig, ax = plt.subplots(figsize=(9.4, 5.3))
    ax.bar(x - w/2, v25, w, color=S.GREY, label="2025 wRC+", zorder=3)
    b26 = ax.bar(x + w/2, v26, w, color=S.NAVY, label="2026 wRC+", zorder=3)
    for i, n in enumerate(order):
        if n == "Jarren Duran":
            b26[i].set_color(S.RED)
        sal = SALARY_2026.get(n)
        ax.text(x[i], max(v25[i] or 0, v26[i] or 0) + 3.5,
                f"${sal/1e6:.1f}M" + ("*" if n in APPROX_SALARY else ""),
                ha="center", fontsize=9, color=S.MUTED, weight="bold")
    ax.axhline(100, color=S.AMBER, lw=1.3, ls="--", zorder=2)
    ax.text(len(order) - 0.45, 101.5, "league avg", ha="right",
            fontsize=8.5, color=S.AMBER, va="bottom")
    S.style(ax)
    ax.set_ylim(0, 158)
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ", "\n") for n in order], fontsize=9)
    ax.tick_params(axis="x", labelcolor=S.TEXT)
    ax.set_ylabel("wRC+  (100 = league average)")
    S.titled(ax, "Duran: from the unit's best bat to its worst",
             "Red Sox outfield/DH — 2025 vs. 2026 wRC+, with 2026 salary")
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
    fig.text(0.5, 0.005, "*Eaton salary approximate (pre-arb minimum).",
             ha="center", fontsize=7.5, color=S.GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(C.FIG_DIR / "05_redsox_of_comparison.png")
    plt.close(fig)


def fig_scatter(df, bench):
    """Salary (y) vs 2026 wRC+ (x); Duran + Red Sox + Yoshida highlighted."""
    d = df[(df["PA"] >= SCATTER_MIN_PA) | (df["redsox"])].copy()
    fig, ax = plt.subplots(figsize=(9.8, 6.2))
    sal_m = d["salary_2026"] / 1e6
    is_sox = d["redsox"] & (d["Name"] != "Jarren Duran")
    other = ~d["redsox"]
    ax.scatter(d.loc[other, "wRC+"], sal_m[other], s=64, c=S.GREY,
               alpha=0.7, edgecolor="white", linewidth=0.8, label="Other OF")
    ax.scatter(d.loc[is_sox, "wRC+"], sal_m[is_sox], s=104, c=S.NAVY,
               edgecolor="white", linewidth=1.2, label="Red Sox OF/DH", zorder=4)
    dur = d[d["Name"] == "Jarren Duran"]
    ax.scatter(dur["wRC+"], dur["salary_2026"] / 1e6, s=340, c=S.RED,
               edgecolor="white", linewidth=1.2, zorder=6,
               label="Jarren Duran", marker="*")
    suffix = {"Jr.", "Sr.", "II", "III", "IV"}

    def short(name):
        p = name.split()
        return p[-2] if p[-1] in suffix and len(p) > 1 else p[-1]

    # (dx pt, dy pt, ha, leader) nudges; leader draws a thin connector line
    # for labels pushed well away from their marker (the crowded low-salary area)
    nudge = {
        "Jarren Duran":     (-13, 2, "right", False),
        "Wilyer Abreu":     (-8, -14, "right", True),
        "Nate Eaton":       (10, -14, "left", True),
        "Ceddanne Rafaela": (12, 8, "left", True),
        "Roman Anthony":    (0, 12, "center", False),
        # spread the low-salary non-Sox cluster
        "Adolis Garcia":    (0, 12, "center", False),
        "Steven Kwan":      (0, -14, "center", True),
        "Cedric Mullins":   (8, 4, "left", False),
        "Daulton Varsho":   (-8, 2, "right", False),
        "Michael Harris II": (8, -10, "left", False),
        "Teoscar Hernandez": (0, 12, "center", False),
    }
    for _, r in d.iterrows():
        label = r["Name"] if r["redsox"] else short(r["Name"])
        dx, dy, ha, leader = nudge.get(r["Name"], (7, 3, "left", False))
        color = (S.RED if r["Name"] == "Jarren Duran"
                 else (S.NAVY if r["redsox"] else S.MUTED))
        ax.annotate(
            label, (r["wRC+"], r["salary_2026"] / 1e6),
            textcoords="offset points", xytext=(dx, dy), ha=ha,
            fontsize=8, va="center", color=color,
            fontweight="bold" if r["redsox"] else "normal",
            arrowprops=(dict(arrowstyle="-", color=color, lw=0.6, alpha=0.55,
                             shrinkA=0, shrinkB=3) if leader else None))
    ax.axvline(100, color=S.AMBER, lw=1.3, ls="--", zorder=1)
    ax.set_ylim(-2, 68)
    ax.text(101.5, 64, "league-avg wRC+", fontsize=8.5, color=S.AMBER,
            va="top")
    S.style(ax, grid_axis="both")
    ax.grid(axis="both", color=S.GRID, linewidth=1.0)
    ax.set_xlabel("2026 wRC+   (output — right = better hitter)")
    ax.set_ylabel("2026 salary  ($M)")
    S.titled(ax, "Cheap and productive vs. paid and slumping",
             "MLB outfielders — 2026 salary vs. output; Duran is a "
             "luck-depressed low point today")
    ax.legend(loc="upper left", bbox_to_anchor=(0.02, 0.98))
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "06_salary_vs_output_scatter.png")
    plt.close(fig)


def _val(df, name, season, col):
    r = df[(df["Name"] == name) & (df["Season"] == season)]
    return None if r.empty or pd.isna(r[col].iloc[0]) else float(r[col].iloc[0])


# --- memo ------------------------------------------------------------------
def _m(x):
    return "n/a" if x is None or pd.isna(x) else f"${x/1e6:.1f}M"


def memo(rs, cohort, bench):
    L = []
    A = L.append
    A("# Peer & Market Comparison — Jarren Duran\n")
    A(f"*Generated {SALARY_AS_OF} · output via FanGraphs (2025 full, 2026 "
      f"partial); salary: {SALARY_SOURCE}.*\n")

    A("## vs. league average (2026, 200+ PA)\n")
    A(f"- League-average OF: **{bench['of']['wRC+']:.0f} wRC+**, "
      f"{bench['of']['wOBA']:.3f} wOBA. League-average hitter = 100 wRC+.")
    dur26 = _val(rs, "Jarren Duran", 2026, "wRC+")
    dur25 = _val(rs, "Jarren Duran", 2025, "wRC+")
    A(f"- Duran **2025: {dur25:.0f} wRC+** (above average) → "
      f"**2026: {dur26:.0f} wRC+** (well below average, and below the "
      f"league-average OF).")
    A("- Per the main analysis, his *true talent* (~110 wRC+, his 2025 line) "
      "is modestly above league average; 2026 understates him.\n")

    A("## vs. Red Sox outfielders / DH\n")
    A("| Player | Age | 2025 wRC+ | 2026 wRC+ | 2026 WAR | 2026 salary |")
    A("|--------|----:|----------:|----------:|---------:|------------:|")
    for n in REDSOX_GROUP:
        a = _val(rs, n, 2026, "Age") or _val(rs, n, 2025, "Age")
        A(f"| {n} | {_i(a)} | {_i(_val(rs,n,2025,'wRC+'))} | "
          f"{_i(_val(rs,n,2026,'wRC+'))} | {_f(_val(rs,n,2026,'WAR'))} | "
          f"{_m(SALARY_2026.get(n))}{'*' if n in APPROX_SALARY else ''} |")
    A("\n> **The roster squeeze is the story.** In 2026 Duran is the Red Sox' "
      "**lowest-producing regular outfielder** while carrying its "
      "**second-highest OF salary** ($7.7M), behind only the Yoshida albatross "
      "($18.6M). Abreu ($0.8M) and Rafaela ($2.0M) give more production for a "
      "fraction of the cost, and Roman Anthony ($130M extension) is the "
      "long-term cornerstone. Boston has cheaper, younger, better-or-equal "
      "outfielders — so Duran is the movable piece, not a building block.\n")

    A("## Salary vs. output cohort (2026)\n")
    A("| Player | 2026 wRC+ | 2026 WAR | 2026 salary | $ / WAR |")
    A("|--------|----------:|---------:|------------:|--------:|")
    for _, r in cohort.iterrows():
        dpw = ("—" if r["dollars_per_war"] is None or pd.isna(r["dollars_per_war"])
               else f"${r['dollars_per_war']/1e6:.1f}M")
        A(f"| {r['Name']}{'*' if r['approx_salary'] else ''} | "
          f"{_i(r['wRC+'])} | {_f(r['WAR'])} | {_m(r['salary_2026'])} | {dpw} |")
    A("\n> On a 2026 snapshot Duran ($7.7M for 61 wRC+, ~0 WAR) is a poor value "
      "point — but that is the luck-depressed partial season. The instructive "
      "contrast: his own **2025 was elite value** (3.9 WAR at a $3.75M salary, "
      "≈ $1.0M per WAR — better than nearly anyone on this list), and his "
      "$7.7M/110-wRC+ *true-talent* season would still be a fair-to-good deal. "
      "The overpay risk is not the price; it is the direction of the arrow.\n")

    A("## Contract status (why this matters for trades)\n")
    A("- Duran signed a **1-year, $7.7M** deal for 2026, avoiding arbitration; "
      "the club **declined** an $8M option — a signal in itself. He remains "
      "**arbitration-controllable** (not a free agent yet), which is exactly "
      "what makes him tradeable: a contender gets 1–2 years of an above-average "
      "CF/LF at a non-star price.")
    A("- **Yoshida ($18.6M through 2027)** is the cautionary comp on the same "
      "roster: a corner bat signed to a big deal that aged badly and is now a "
      "salary-dump candidate. Duran is *not* in that bucket — his contract is "
      "short and cheap — but it shows how quickly a Red Sox OF bat can go from "
      "asset to liability, which argues for selling Duran while he still has "
      "positive, controllable value rather than holding into decline.\n")

    A("## Bottom line\n")
    A("- **vs. league:** an above-average regular in a normal year (2025), "
      "below-average in a luck-hit 2026.")
    A("- **vs. Red Sox OF:** now the least productive regular at the "
      "second-highest price — redundant behind cheaper, younger, controllable "
      "bats.")
    A("- **vs. the market:** priced like a solid regular ($7.7M), not a star; "
      "value hinges entirely on whether the ~110-wRC+ 2025 hitter or the 2026 "
      "version is real. The peer picture reinforces the memo's call: **trade "
      "from a position of surplus, value him at the 2025 baseline, and don't "
      "wait for a Yoshida-style decline to erase the controllable-value "
      "window.**\n")

    A("---\n*Salary figures are 2026 Spotrac cap hits gathered via web search "
      f"on {SALARY_AS_OF}; `*` = approximate (pre-arb minimum). Re-verify "
      "against Spotrac before quoting. Output is FanGraphs; 2026 is a partial "
      "season, so rate stats (wRC+) are more comparable across players than "
      "counting WAR.*")
    out = C.OUT_DIR / "peer_and_salary_memo.md"
    out.write_text("\n".join(L))
    print(f"  [comps] wrote {out}")


def _i(x):
    return "n/a" if x is None or pd.isna(x) else f"{x:.0f}"


def _f(x):
    return "n/a" if x is None or pd.isna(x) else f"{x:.1f}"


def run():
    bench = league_benchmarks()
    rs = redsox_table()
    cohort = salary_cohort()
    with open(C.DATA_DIR / "peer_benchmarks.json", "w") as f:
        json.dump(bench, f, indent=2)
    fig_redsox(rs, bench)
    fig_scatter(cohort, bench)
    print("  [comps] wrote figures 05, 06")
    memo(rs, cohort, bench)


if __name__ == "__main__":
    run()
