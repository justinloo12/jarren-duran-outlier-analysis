"""Figures 01-04 — sleek, de-cluttered, cohesive style (see src/style.py)."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from . import style as S

S.apply()


def _load():
    tbl = pd.read_csv(C.DATA_DIR / "season_metrics.csv").sort_values("season")
    res = json.load(open(C.DATA_DIR / "analysis_results.json"))
    age = json.load(open(C.DATA_DIR / "age_curve.json"))
    return tbl, res, age


def fig_babip(tbl, res):
    seasons = tbl["season"].to_numpy()
    babip = tbl["sc_babip"].to_numpy(dtype=float)
    xbabip = tbl["sc_xbabip"].to_numpy(dtype=float)
    lg = res["babip"]["league_by_season"]
    lg_vals = [lg.get(str(int(s)), lg.get(int(s))) for s in seasons]

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    colors = [S.RED if s == C.OUTLIER_SEASON else S.NAVY for s in seasons]
    bars = ax.bar(seasons, babip, color=colors, width=0.62, zorder=3)
    for s, b in zip(seasons, babip):
        ax.text(s, b + 0.006, f"{b:.3f}", ha="center", fontsize=9,
                color=S.RED if s == C.OUTLIER_SEASON else S.NAVY, weight="bold")
    ax.plot(seasons, lg_vals, "--", color=S.GREY, lw=2, zorder=4,
            marker="o", ms=5, mfc="white", mec=S.GREY, label="League avg (300+ PA)")
    ax.plot(seasons, xbabip, ":", color=S.GREEN, lw=2, zorder=4,
            marker="D", ms=5, mfc="white", mec=S.GREEN,
            label="Duran xBABIP (contact quality)")
    S.style(ax)
    ax.set_ylim(0.22, 0.40)
    ax.set_ylabel("BABIP")
    ax.set_xticks(seasons)
    ax.margins(x=0.04)
    S.titled(ax, "2024 was earned; 2026 is unlucky",
             "BABIP by season vs. league average and his own expected BABIP")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "01_babip_vs_league.png")
    plt.close(fig)


def fig_woba(tbl):
    seasons = tbl["season"].to_numpy()
    woba = tbl["wOBA"].to_numpy(dtype=float)
    xwoba = tbl["xwOBA"].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.fill_between(seasons, woba, xwoba, where=~np.isnan(woba),
                    color=S.RED, alpha=0.08, zorder=1)
    ax.plot(seasons, xwoba, "--", color=S.NAVY, lw=2.4, marker="s", ms=6,
            mfc="white", mec=S.NAVY, label="xwOBA (contact quality)", zorder=3)
    ax.plot(seasons, woba, "-", color=S.RED, lw=2.6, marker="o", ms=7,
            mfc="white", mec=S.RED, label="wOBA (results)", zorder=4)
    # annotate only the two informative gaps, clear of the lines
    for s, col, dy in [(2024, S.RED, 13), (2026, S.NAVY, -17)]:
        i = list(seasons).index(s)
        g = woba[i] - xwoba[i]
        note = (f"{g*1000:+.0f} pts  " + ("lucky" if g > 0 else "unlucky"))
        ax.annotate(note, (s, woba[i]), textcoords="offset points",
                    xytext=(0, dy), ha="center", fontsize=9, color=col,
                    weight="bold")
    S.style(ax, grid_axis="y")
    ax.set_ylabel("wOBA"); ax.set_xticks(seasons); ax.margins(x=0.06)
    ax.set_ylim(0.238, 0.372)
    S.titled(ax, "Results vs. contact quality",
             "When the red line sits above the navy, output ran ahead of the "
             "batted-ball quality")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0))
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "02_woba_vs_xwoba.png")
    plt.close(fig)


def fig_discipline(tbl):
    seasons = tbl["season"].to_numpy()
    chase = tbl["sc_chase_pct"].to_numpy(dtype=float) * 100
    contact = tbl["sc_zcontact_pct"].to_numpy(dtype=float) * 100
    whiff = tbl["sc_whiff_pct"].to_numpy(dtype=float) * 100
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for y, col, lab, mk in [(contact, S.NAVY, "Zone-Contact%", "s"),
                            (whiff, S.AMBER, "Whiff%", "^"),
                            (chase, S.RED, "Chase%", "o")]:
        ax.plot(seasons, y, "-", color=col, lw=2.4, marker=mk, ms=6,
                mfc="white", mec=col, label=lab, zorder=3)
    S.style(ax)
    ax.set_ylabel("Percent"); ax.set_xticks(seasons); ax.margins(x=0.04)
    ax.set_ylim(15, 95)
    S.titled(ax, "Swing decisions peaked, then slipped in 2026",
             "A durable breakout shows a lasting approach change; his eroded in "
             "2026")
    ax.legend(loc="center left", bbox_to_anchor=(0.02, 0.5))
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "03_plate_discipline_trend.png")
    plt.close(fig)


def fig_agecurve(age):
    def pts(d):
        d = {int(k): v for k, v in d.items()}
        xs = sorted(d)
        return xs, [d[x] for x in xs]

    actual = {int(k): v for k, v in age["actual_by_age"].items()}
    xs = sorted(actual)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))

    x1, y1 = pts(age["expected_from_2024_league"])
    x2, y2 = pts(age["expected_from_2024_cohort"])
    x3, y3 = pts(age["expected_from_baseline_league"])
    ax.plot(x2, y2, ":", color=S.TEAL, lw=2, label="If 2024 real · speed cohort")
    ax.plot(x1, y1, "--", color=S.NAVY, lw=2, label="If 2024 real · league aging")
    ax.plot(x3, y3, "--", color=S.GREEN, lw=2, label="From true-talent baseline")
    ax.plot(xs, [actual[x] for x in xs], "-", color=S.RED, lw=2.8, marker="o",
            ms=8, mfc="white", mec=S.RED, label="Duran actual wRC+", zorder=6)

    ax.axhline(100, color=S.GREY, lw=1, ls=(0, (2, 3)))
    ax.text(xs[-1] + 0.02, 100, " league avg", fontsize=8, color=S.GREY,
            va="center")
    # place each year label clear of the red line
    year_off = {27: (0, 13, "center"),   # 2024 peak -> above
                28: (13, 12, "left"),    # 2025 -> up and right, off the descent
                29: (0, -17, "center")}  # 2026 -> below (open)
    for a in (27, 28, 29):
        if a in actual:
            tag = {27: "2024", 28: "2025", 29: "2026"}[a]
            dx, dy, ha = year_off[a]
            ax.annotate(f"{tag}: {actual[a]:.0f}", (a, actual[a]),
                        textcoords="offset points", xytext=(dx, dy),
                        ha=ha, fontsize=8.5, color=S.RED, weight="bold")
    S.style(ax)
    ax.set_xlabel("Season age"); ax.set_ylabel("wRC+")
    ax.set_xticks(sorted(set(xs) | set(x1)))
    ax.set_ylim(35, 150)
    S.titled(ax, "Aging can't explain the drop",
             "2024→2026 fell ~70 wRC+; a normal age 27→29 curve "
             "predicts ~7")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0))
    fig.tight_layout()
    fig.savefig(C.FIG_DIR / "04_age_curve_overlay.png")
    plt.close(fig)


def run():
    tbl, res, age = _load()
    fig_babip(tbl, res)
    fig_woba(tbl)
    fig_discipline(tbl)
    fig_agecurve(age)
    print(f"  [viz] wrote 4 figures to {C.FIG_DIR}")


if __name__ == "__main__":
    run()
