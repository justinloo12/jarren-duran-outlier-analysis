"""Adjusted catcher-battery model: from raw splits to a defensible estimate.

battery.py reports raw RA9 splits by battery — suggestive but confounded
(who catches whom, against which lineup, in which park, is a choice).
This module handles the confounds three ways, all at the plate-appearance
level with wOBA-against as the outcome (cleaner than RA9: no sequencing
or baserunning noise):

1. WOWY (with-or-without-you): for each pitcher caught >= MIN_PA by both
   Narváez and Wong, the within-pitcher wOBA-against difference, pooled
   across pitchers with harmonic-mean-PA weights. Within-pitcher deltas
   kill the "good catchers catch good pitchers" confound by construction.

2. Fixed-effects OLS: wOBA_value ~ catcher + pitcher FE + opponent FE +
   home, so the catcher coefficient is identified only from variation
   within pitcher and within opponent. 95% CI from a cluster bootstrap
   by game (outcomes within a game are not independent).

3. Empirical-Bayes shrinkage of the per-pitcher pairing gaps: each raw
   battery delta is shrunk toward the pooled effect by its reliability
   n_eff/(n_eff + K), where K is the pitcher-to-pitcher variance ratio
   estimated from the data. Small-sample screamers (a 1.12 RA9 on 12
   innings) get pulled in; well-sampled gaps survive.

Writes data/battery_model.json and figures/15_battery_adjusted.png.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import battery
from . import config as C
from . import style as S

S.apply()

MIN_PA = 25          # min PA with EACH catcher for the WOWY pitcher pool
N_BOOT = 2000
SEED = 34
CATS = ("Carlos Narváez", "Connor Wong")


def _pa_table() -> pd.DataFrame:
    """PA-level rows: one per PA-ending pitch with a wOBA denominator."""
    df = battery.load()
    pa = df[df["woba_denom"].notna() & (df["woba_denom"] > 0)].copy()
    pa = pa[pa["catcher"].isin(CATS)]
    # opponent = the batting team (BOS is fielding on every row)
    pa["opponent"] = np.where(pa["home_team"] == "BOS",
                              pa["away_team"], pa["home_team"])
    pa["home"] = (pa["home_team"] == "BOS").astype(int)
    pa["y"] = pa["woba_value"].astype(float)
    pa["wong"] = (pa["catcher"] == "Connor Wong").astype(int)
    return pa[["game_pk", "pitcher_name", "catcher", "opponent", "home",
               "wong", "y"]]


# ------------------------------------------------------------------ WOWY
def wowy(pa: pd.DataFrame) -> dict:
    rows = []
    for p, d in pa.groupby("pitcher_name"):
        n = {c: (d["catcher"] == c).sum() for c in CATS}
        if min(n.values()) < MIN_PA:
            continue
        m = {c: d.loc[d["catcher"] == c, "y"].mean() for c in CATS}
        w = 2 / (1 / n[CATS[0]] + 1 / n[CATS[1]])  # harmonic mean PA
        rows.append({"pitcher": p, "delta_wong_minus_narvaez":
                     m["Connor Wong"] - m["Carlos Narváez"],
                     "pa_narvaez": int(n[CATS[0]]), "pa_wong": int(n[CATS[1]]),
                     "weight": w})
    t = pd.DataFrame(rows)
    pooled = float(np.average(t["delta_wong_minus_narvaez"],
                              weights=t["weight"])) if len(t) else np.nan
    return {"pitchers": t.to_dict("records"), "pooled_delta": pooled,
            "n_pitchers": len(t)}


# ------------------------------------------------- fixed-effects OLS
def _fe_fit(pa: pd.DataFrame) -> float:
    """Catcher coefficient from OLS with pitcher + opponent FE + home."""
    X = pd.get_dummies(pa[["pitcher_name", "opponent"]], drop_first=True,
                       dtype=float)
    X["home"] = pa["home"].values
    X["wong"] = pa["wong"].values
    X["const"] = 1.0
    beta, *_ = np.linalg.lstsq(X.values, pa["y"].values, rcond=None)
    return float(beta[list(X.columns).index("wong")])


def fe_model(pa: pd.DataFrame) -> dict:
    est = _fe_fit(pa)
    rng = np.random.default_rng(SEED)
    games = pa["game_pk"].unique()
    boots = []
    for _ in range(N_BOOT):
        gs = rng.choice(games, size=len(games), replace=True)
        bs = pd.concat([pa[pa["game_pk"] == g] for g in gs],
                       ignore_index=True)
        # a resample can drop a catcher entirely; skip those draws
        if bs["wong"].nunique() < 2:
            continue
        try:
            boots.append(_fe_fit(bs))
        except np.linalg.LinAlgError:
            continue
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"catcher_effect_wong_minus_narvaez": est,
            "ci95": [float(lo), float(hi)],
            "n_boot": len(boots),
            "n_pa": int(len(pa)),
            "significant": bool(lo > 0 or hi < 0)}


# ---------------------------------------------- empirical-Bayes shrinkage
def shrink(pa: pd.DataFrame, pooled: float) -> list[dict]:
    """Shrink per-pitcher battery deltas toward the pooled effect."""
    sigma2 = pa["y"].var()  # within-PA outcome variance
    rows = []
    for p, d in pa.groupby("pitcher_name"):
        n = {c: (d["catcher"] == c).sum() for c in CATS}
        if min(n.values()) < 10:
            continue
        delta = (d.loc[d["catcher"] == CATS[1], "y"].mean()
                 - d.loc[d["catcher"] == CATS[0], "y"].mean())
        var_delta = sigma2 * (1 / n[CATS[0]] + 1 / n[CATS[1]])
        rows.append({"pitcher": p, "raw_delta": float(delta),
                     "var": float(var_delta),
                     "n_eff": 2 / (1 / n[CATS[0]] + 1 / n[CATS[1]])})
    if not rows:
        return rows
    raw = np.array([r["raw_delta"] for r in rows])
    var = np.array([r["var"] for r in rows])
    # method-of-moments between-pitcher variance
    tau2 = max(0.0, float(np.var(raw) - var.mean()))
    for r in rows:
        rel = tau2 / (tau2 + r["var"]) if tau2 > 0 else 0.0
        r["reliability"] = float(rel)
        r["shrunk_delta"] = float(pooled + rel * (r["raw_delta"] - pooled))
    return sorted(rows, key=lambda r: r["shrunk_delta"])


# ----------------------------------------------------------------- figure
def fig_adjusted(res: dict):
    fig, ax = plt.subplots(figsize=(9, 5.4))
    rows = [r for r in res["shrunk"] if r["pitcher"] != "Connelly Early"]
    ys = np.arange(len(rows))
    for y, r in zip(ys, rows):
        ax.plot([r["raw_delta"] * 1000, r["shrunk_delta"] * 1000], [y, y],
                color=S.GREY, lw=1.5, alpha=0.6, zorder=1)
        ax.scatter(r["raw_delta"] * 1000, y, s=55, facecolors="none",
                   edgecolors=S.MUTED, zorder=2)
        ax.scatter(r["shrunk_delta"] * 1000, y, s=95, color=S.NAVY, zorder=3)
    fe = res["fe"]
    lo, hi = [v * 1000 for v in fe["ci95"]]
    est = fe["catcher_effect_wong_minus_narvaez"] * 1000
    ax.axvspan(lo, hi, color=S.TEAL, alpha=0.12, zorder=0)
    ax.axvline(est, color=S.TEAL, lw=2, ls="--",
               label=f"adjusted team effect {est:+.0f} "
                     f"[{lo:+.0f}, {hi:+.0f}]")
    ax.axvline(0, color=S.SPINE, lw=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([r["pitcher"] for r in rows])
    S.style(ax, grid_axis="x")
    ax.set_xlabel("wOBA-against with Wong minus with Narváez "
                  "(points; negative = better with Wong)")
    ax.set_title("Adjusted battery effects: raw splits (hollow) shrink "
                 "toward the truth (solid)", loc="left", fontsize=15,
                 fontweight="bold")
    leg = ax.legend(loc="lower right")
    for t in leg.get_texts():
        t.set_color(S.TEXT)
    ax.text(0, -0.14, "Empirical-Bayes shrinkage by sample size; team "
            "effect from pitcher+opponent+park fixed-effects OLS, "
            "cluster-bootstrap 95% CI.",
            transform=ax.transAxes, fontsize=10, color=S.MUTED)
    fig.tight_layout()
    out = C.FIG_DIR / "15_battery_adjusted.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [battery_model] wrote {out}")


def run() -> dict:
    pa = _pa_table()
    w = wowy(pa)
    fe = fe_model(pa)
    sh = shrink(pa, w["pooled_delta"] if np.isfinite(w["pooled_delta"])
                else 0.0)
    res = {"wowy": w, "fe": fe, "shrunk": sh,
           "min_pa_wowy": MIN_PA, "outcome": "wOBA-against per PA"}
    (C.DATA_DIR / "battery_model.json").write_text(json.dumps(res, indent=2))
    print(f"  [battery_model] wrote {C.DATA_DIR / 'battery_model.json'}")
    print(f"  [battery_model] WOWY pooled (Wong-Narváez): "
          f"{w['pooled_delta']*1000:+.1f} pts over {w['n_pitchers']} "
          "shared pitchers")
    print(f"  [battery_model] FE effect: "
          f"{fe['catcher_effect_wong_minus_narvaez']*1000:+.1f} pts, "
          f"95% CI [{fe['ci95'][0]*1000:+.1f}, {fe['ci95'][1]*1000:+.1f}]")
    fig_adjusted(res)
    return res
