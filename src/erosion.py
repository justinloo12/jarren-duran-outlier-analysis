"""Pitch-level erosion decomposition: is 2026's decline PHYSICAL or APPROACH?

The decision memo documents real 2026 process erosion (chase 31.1->35.8,
whiff 26.2->32.8, hard-hit down). This module asks the next question — the one
that decides how to weight the two rebound scenarios: is the erosion the body
(bat slowing = physical decline, hard to reverse at 29) or the plan at the
plate (approach/intent, fixable)?

Three cuts, all from the cached pitch-level Statcast (bat tracking 2024+):

1. BAT TRACKING (the tiebreaker). Statcast measures bat speed directly on
   every competitive swing since 2024. A hitter in physical decline swings
   slower; a hitter pressing swings *harder*. We report average bat speed on
   competitive swings (>= 50 mph, Savant's convention for excluding checked
   swings/bunts), fast-swing rate (>= 75 mph, the Savant "fast swing"
   threshold), swing length and attack angle, 2024 -> 2025 -> 2026.

2. WHIFF / CHASE BY PITCH TYPE AND VELOCITY. Whiff rate vs >= 95 mph
   fastballs is the classic bat-slowing tell (you can't cheat velocity with
   a slow bat); chase rate on breaking balls down-and-away is the classic
   approach tell (getting fooled / expanding). Plus in-zone contact and
   swing rate in the Savant-style "chase" attack zone.

3. VERDICT. A small, unit-tested classifier turns the deltas into a label
   (physical / approach / mixed) and the memo says plainly how it re-weights
   the healthy-prior vs erosion rebound scenarios.

Attack zones are derived from plate_x/plate_z normalized to the batter's own
strike zone (Savant convention, approximated): heart = inner 2/3 of the zone,
shadow = zone edge band out to 1/3 beyond, chase = out to 2x the zone
half-extent, waste = beyond. Horizontal half-width 0.83 ft = plate half-width
plus one ball radius.

Standalone: python3 -m src.erosion   (uses cached CSVs only, no network)
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from . import style as S
from .fetch_statcast import load_pitches
from .statcast_metrics import SWING, CONTACT

S.apply()

# --- constants ----------------------------------------------------------------
BAT_TRACK_SEASONS = [2024, 2025, 2026]      # Statcast bat tracking era
COMPETITIVE_MPH = 50.0                      # Savant floor: excludes checked swings
FAST_SWING_MPH = 75.0                       # Savant "fast swing" threshold
HARD_FB_MPH = 95.0                          # "can he still catch up?" cut
HALF_WIDTH_FT = 0.83                        # plate half-width + ball radius

FASTBALLS = {"FF", "SI", "FC"}
BREAKING = {"SL", "ST", "SV", "CU", "KC", "CS", "SC"}
OFFSPEED = {"CH", "FS", "FO", "EP", "KN"}

# verdict thresholds (documented in classify_verdict docstring)
PHYS_DROP_MPH = -1.0
INTACT_MPH = -0.3
CHASE_UP = 0.02

# scenario re-weighting: agnostic 50/50 -> this weight on the scenario the
# decomposition favors (a nudge, not a certainty claim)
REWEIGHT_FAVORED = 0.60


# --- pure helpers (unit-tested) -------------------------------------------------
def pitch_group(pitch_type) -> str:
    """Map a Statcast pitch_type code to fastball/breaking/offspeed/other."""
    if pitch_type in FASTBALLS:
        return "fastball"
    if pitch_type in BREAKING:
        return "breaking"
    if pitch_type in OFFSPEED:
        return "offspeed"
    return "other"


def attack_zone(plate_x, plate_z, sz_top, sz_bot) -> np.ndarray:
    """Savant-style attack zone (heart/shadow/chase/waste), vectorized.

    Coordinates are normalized to the batter's own zone: horizontally by
    HALF_WIDTH_FT, vertically by the half-height around the zone midpoint.
    With u = max(|x_norm|, |z_norm|):  heart u <= 2/3, shadow <= 4/3,
    chase <= 2, waste beyond. Missing coordinates -> 'unknown'.
    """
    px = np.asarray(plate_x, float)
    pz = np.asarray(plate_z, float)
    top = np.asarray(sz_top, float)
    bot = np.asarray(sz_bot, float)
    mid = (top + bot) / 2.0
    half = (top - bot) / 2.0
    with np.errstate(invalid="ignore", divide="ignore"):
        u = np.maximum(np.abs(px) / HALF_WIDTH_FT, np.abs(pz - mid) / half)
    out = np.select([u <= 2 / 3, u <= 4 / 3, u <= 2.0],
                    ["heart", "shadow", "chase"], default="waste")
    out = out.astype(object)
    out[~np.isfinite(u)] = "unknown"
    return out


def bat_speed_summary(bat_speed, competitive_mph: float = COMPETITIVE_MPH,
                      fast_mph: float = FAST_SWING_MPH) -> dict:
    """Aggregate tracked swings: mean / p90 bat speed + fast-swing share.

    Only competitive swings (>= competitive_mph) count, per Savant convention;
    checked swings and bunt attempts register absurdly low speeds.
    """
    s = pd.Series(bat_speed, dtype=float).dropna()
    comp = s[s >= competitive_mph]
    n = int(len(comp))
    if n == 0:
        return {"n_swings": 0, "avg_mph": None, "p90_mph": None,
                "fast_swing_pct": None}
    return {
        "n_swings": n,
        "avg_mph": float(comp.mean()),
        "p90_mph": float(comp.quantile(0.90)),
        "fast_swing_pct": float((comp >= fast_mph).mean()),
    }


def rate(num: int, den: int):
    return num / den if den else None


def down_and_away_mask(df: pd.DataFrame, stand: str) -> pd.Series:
    """Below the zone AND on the outer edge or beyond for the batter's side.

    'Away' for a LHB (stands on the catcher's right, +x side) is negative
    plate_x; for a RHB it is positive plate_x. 0.2 ft off center keeps the
    cut to the outer third and beyond.
    """
    below = df["plate_z"] < df["sz_bot"]
    away = (df["plate_x"] <= -0.2) if stand == "L" else (df["plate_x"] >= 0.2)
    return below & away


def classify_verdict(bat_speed_delta_mph: float, chase_delta: float,
                     whiff_hard_fb_delta: float,
                     zcontact_delta: float) -> dict:
    """Turn the four deltas (2026 minus the 2024-25 baseline, except
    chase/whiff which are 2026 minus 2025) into a physical-vs-approach label.

    Rules (documented, deliberately simple):
      * bat speed down >= 1.0 mph -> 'physical' (league-normal aging is only
        ~0.2-0.3 mph/yr; a full-mph drop is a real bat-slowing signal).
      * bat speed within noise or UP (>= -0.3 mph) AND chase up >= 2 pts ->
        'approach' (the body is fine; the swing decisions moved).
      * anything else -> 'mixed'.
    Whiff-vs-95+ and zone-contact deltas are attached as context flags: if
    bat speed is up but hard-velocity whiffs are also up, the approach story
    is "selling out for speed" (more intent, less control), not bat death.
    """
    if bat_speed_delta_mph <= PHYS_DROP_MPH:
        label = "physical"
    elif bat_speed_delta_mph >= INTACT_MPH and chase_delta >= CHASE_UP:
        label = "approach"
    elif bat_speed_delta_mph >= INTACT_MPH:
        label = "ambiguous"
    else:
        label = "mixed"
    return {
        "label": label,
        "bat_speed_delta_mph": bat_speed_delta_mph,
        "chase_delta": chase_delta,
        "whiff_hard_fb_delta": whiff_hard_fb_delta,
        "zcontact_delta": zcontact_delta,
        "selling_out": bool(bat_speed_delta_mph > 0
                            and whiff_hard_fb_delta > 0),
    }


def reweighted_p(p_healthy: float, p_erosion: float,
                 w_healthy: float) -> float:
    """Scenario-weighted rebound probability."""
    return w_healthy * p_healthy + (1 - w_healthy) * p_erosion


# --- per-season decomposition ----------------------------------------------------
def season_decomposition(df: pd.DataFrame, season: int) -> dict:
    """All the cuts for one season of pitch data (regular season only)."""
    if df.empty:
        return {"season": season}
    d = df[df["game_type"] == "R"].copy() if "game_type" in df.columns \
        else df.copy()
    desc = d["description"].fillna("")
    d["swing"] = desc.isin(SWING)
    d["contact"] = desc.isin(CONTACT)
    d["whiff"] = d["swing"] & ~d["contact"]
    d["grp"] = d["pitch_type"].map(pitch_group)
    d["az"] = attack_zone(d["plate_x"], d["plate_z"], d["sz_top"], d["sz_bot"])
    in_zone = d["zone"].between(1, 9)
    out_zone = d["zone"].between(11, 14)

    out = {"season": season}

    # 1) bat tracking
    if "bat_speed" in d.columns:
        out["bat"] = bat_speed_summary(d.loc[d["swing"], "bat_speed"])
        sw = d[d["swing"]]
        out["bat"]["swing_length_ft"] = (
            float(sw["swing_length"].dropna().mean())
            if "swing_length" in d.columns and sw["swing_length"].notna().any()
            else None)
        out["bat"]["attack_angle_deg"] = (
            float(sw["attack_angle"].dropna().mean())
            if "attack_angle" in d.columns and sw["attack_angle"].notna().any()
            else None)
    else:
        out["bat"] = {"n_swings": 0, "avg_mph": None, "p90_mph": None,
                      "fast_swing_pct": None, "swing_length_ft": None,
                      "attack_angle_deg": None}

    # 2) whiff + chase by pitch group
    for g in ("fastball", "breaking", "offspeed"):
        gd = d[d["grp"] == g]
        n_sw = int(gd["swing"].sum())
        n_oz = int((gd["zone"].between(11, 14)).sum())
        out[f"whiff_{g}"] = {"rate": rate(int(gd["whiff"].sum()), n_sw),
                             "n": n_sw}
        out[f"chase_{g}"] = {
            "rate": rate(int((gd["zone"].between(11, 14)
                              & gd["swing"]).sum()), n_oz),
            "n": n_oz}

    # hard-velocity fastballs: the bat-slowing tell
    hard = d[(d["grp"] == "fastball") & (d["release_speed"] >= HARD_FB_MPH)]
    n_hsw = int(hard["swing"].sum())
    out["whiff_fb95"] = {"rate": rate(int(hard["whiff"].sum()), n_hsw),
                         "n": n_hsw}

    # in-zone contact
    izsw = d[in_zone & d["swing"]]
    out["z_contact"] = {"rate": rate(int(izsw["contact"].sum()), len(izsw)),
                        "n": int(len(izsw))}

    # approach tells: breaking down-and-away + chase-zone swing rate
    stand = (d["stand"].mode().iat[0] if "stand" in d.columns
             and d["stand"].notna().any() else "L")
    brk = d[d["grp"] == "breaking"]
    dna = brk[down_and_away_mask(brk, stand)]
    out["chase_brk_down_away"] = {"rate": rate(int(dna["swing"].sum()),
                                               len(dna)),
                                  "n": int(len(dna))}
    cz = d[d["az"] == "chase"]
    out["swing_chase_zone"] = {"rate": rate(int(cz["swing"].sum()), len(cz)),
                               "n": int(len(cz))}
    # overall chase/whiff (matches statcast_metrics definitions)
    n_oz_all, n_sw_all = int(out_zone.sum()), int(d["swing"].sum())
    out["chase_all"] = {"rate": rate(int((out_zone & d["swing"]).sum()),
                                     n_oz_all), "n": n_oz_all}
    out["whiff_all"] = {"rate": rate(int(d["whiff"].sum()), n_sw_all),
                        "n": n_sw_all}
    return out


# --- assembly ---------------------------------------------------------------------
def compute() -> dict:
    rows = {s: season_decomposition(load_pitches(s), s)
            for s in BAT_TRACK_SEASONS}
    r24, r25, r26 = rows[2024], rows[2025], rows[2026]

    base_bs = np.mean([r24["bat"]["avg_mph"], r25["bat"]["avg_mph"]])
    verdict = classify_verdict(
        bat_speed_delta_mph=r26["bat"]["avg_mph"] - base_bs,
        chase_delta=r26["chase_all"]["rate"] - r25["chase_all"]["rate"],
        whiff_hard_fb_delta=(r26["whiff_fb95"]["rate"]
                             - r25["whiff_fb95"]["rate"]),
        zcontact_delta=r26["z_contact"]["rate"] - r25["z_contact"]["rate"],
    )

    # re-weight the rebound scenarios given the verdict
    reweight = None
    reb_p = C.DATA_DIR / "rebound_sim.json"
    if reb_p.exists():
        reb = json.load(open(reb_p))
        ph = reb["scenarios"]["healthy"]["p_ros_wrcplus_100"]
        pe = reb["scenarios"]["erosion"]["p_ros_wrcplus_100"]
        w = (REWEIGHT_FAVORED if verdict["label"] == "approach"
             else (1 - REWEIGHT_FAVORED) if verdict["label"] == "physical"
             else 0.5)
        reweight = {"p_healthy": ph, "p_erosion": pe,
                    "w_healthy": w,
                    "p_agnostic_5050": reweighted_p(ph, pe, 0.5),
                    "p_reweighted": reweighted_p(ph, pe, w)}

    return {"seasons": rows, "bat_speed_baseline_2024_25": float(base_bs),
            "verdict": verdict, "reweight": reweight}


# --- figure ------------------------------------------------------------------------
SEASON_COLORS = {2024: S.GREY, 2025: S.TEAL, 2026: S.RED}


def fig(res: dict):
    rows = res["seasons"]
    fig_, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))

    # panel 1 — bat speed (the tiebreaker)
    ax = axes[0]
    yrs = BAT_TRACK_SEASONS
    bs = [rows[s]["bat"]["avg_mph"] for s in yrs]
    fast = [rows[s]["bat"]["fast_swing_pct"] for s in yrs]
    bars = ax.bar([str(s) for s in yrs], bs, width=0.62,
                  color=[S.NAVY, S.NAVY, S.RED], zorder=3)
    for b, v in zip(bars, bs):
        ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 4), textcoords="offset points", ha="center",
                    fontsize=10.5, fontweight="bold", color=S.TEXT)
    ax.set_ylim(68, 77)
    ax2 = ax.twinx()
    ax2.plot([str(s) for s in yrs], [f * 100 for f in fast], color=S.AMBER,
             lw=2.2, marker="o", ms=5, zorder=4)
    for x, f in zip([str(s) for s in yrs], fast):
        ax2.annotate(f"{f:.0%}", (x, f * 100), xytext=(0, 7),
                     textcoords="offset points", ha="center", fontsize=9,
                     color=S.AMBER, fontweight="bold")
    ax2.set_ylim(0, 80)
    ax2.set_yticks([])
    for sp in ("top", "right"):
        ax2.spines[sp].set_visible(False)
    S.style(ax)
    ax.set_ylabel("Avg bat speed, competitive swings (mph)")
    S.titled(ax, "Bat speed is UP, not down",
             "bars: avg bat speed · line: fast-swing rate (≥75 mph)")

    # panels 2 & 3 — whiff and chase by pitch type
    cats_w = [("whiff_fb95", "FB ≥95"), ("whiff_fastball", "FB all"),
              ("whiff_breaking", "Breaking"), ("whiff_offspeed", "Offspeed")]
    cats_c = [("chase_fastball", "Fastball"), ("chase_breaking", "Breaking"),
              ("chase_offspeed", "Offspeed")]
    for ax, cats, title, sub in (
            (axes[1], cats_w, "…but whiffs are up everywhere",
             "whiff rate by pitch type — incl. the ≥95 mph 'bat speed' test"),
            (axes[2], cats_c, "…and the zone is expanding",
             "chase rate (swings at pitches out of the zone) by pitch type")):
        x = np.arange(len(cats))
        wdt = 0.26
        for i, s in enumerate(BAT_TRACK_SEASONS):
            vals = [rows[s][k]["rate"] * 100 for k, _ in cats]
            ax.bar(x + (i - 1) * wdt, vals, wdt, label=str(s),
                   color=SEASON_COLORS[s], zorder=3)
            if s == 2026:
                for xi, v in zip(x + (i - 1) * wdt, vals):
                    ax.annotate(f"{v:.0f}", (xi, v), xytext=(0, 3),
                                textcoords="offset points", ha="center",
                                fontsize=9, fontweight="bold", color=S.RED)
        ax.set_xticks(x)
        ax.set_xticklabels([lab for _, lab in cats], fontsize=9.5)
        S.style(ax)
        ax.set_ylabel("%")
        S.titled(ax, title, sub)
        ax.legend(loc="upper left")

    fig_.tight_layout(w_pad=2.2)
    fig_.savefig(C.FIG_DIR / "10_erosion_decomposition.png")
    plt.close(fig_)


# --- memo --------------------------------------------------------------------------
def _p(x, d=1):
    return "n/a" if x is None else f"{x*100:.{d}f}%"


def memo(res: dict):
    rows = res["seasons"]
    r24, r25, r26 = rows[2024], rows[2025], rows[2026]
    v = res["verdict"]
    rw = res["reweight"]
    import datetime as _dt
    L = []
    A = L.append
    A("# Erosion Decomposition — Physical or Approach?\n")
    A(f"*Generated {_dt.date.today().isoformat()} · pitch-level Statcast, "
      "regular season only, bat tracking 2024+ · methodology in "
      "`src/erosion.py`.*\n")

    A("## The tiebreaker: bat speed is UP\n")
    A("| Season | Avg bat speed (mph) | Fast-swing % (≥75) | P90 (mph) | "
      "Swing length (ft) | Attack angle (°) | Tracked swings |")
    A("|--------|--------------------:|-------------------:|----------:|"
      "------------------:|-----------------:|---------------:|")
    for s in BAT_TRACK_SEASONS:
        b = rows[s]["bat"]
        A(f"| {s} | {b['avg_mph']:.2f} | {_p(b['fast_swing_pct'])} | "
          f"{b['p90_mph']:.1f} | {b['swing_length_ft']:.2f} | "
          f"{b['attack_angle_deg']:.1f} | {b['n_swings']} |")
    A(f"\n**Duran's 2026 bat speed ({r26['bat']['avg_mph']:.2f} mph) is "
      f"{v['bat_speed_delta_mph']:+.2f} mph versus his 2024–25 average** "
      f"({res['bat_speed_baseline_2024_25']:.2f}), and his fast-swing rate "
      f"has climbed {_p(r24['bat']['fast_swing_pct'],0)} → "
      f"{_p(r25['bat']['fast_swing_pct'],0)} → "
      f"{_p(r26['bat']['fast_swing_pct'],0)}. A physically declining hitter "
      "swings *slower*; Duran is swinging harder, longer "
      f"({r24['bat']['swing_length_ft']:.2f} → "
      f"{r26['bat']['swing_length_ft']:.2f} ft) and steeper "
      f"({r24['bat']['attack_angle_deg']:.1f}° → "
      f"{r26['bat']['attack_angle_deg']:.1f}°). Whatever 2026 is, it is not "
      "a slowing bat.\n")

    A("## Where the whiffs and chases actually live\n")
    A("| Cut | 2024 | 2025 | 2026 |")
    A("|-----|-----:|-----:|-----:|")
    cuts = [("Whiff% overall", "whiff_all"),
            ("Whiff% vs fastballs ≥95", "whiff_fb95"),
            ("Whiff% vs fastballs", "whiff_fastball"),
            ("Whiff% vs breaking", "whiff_breaking"),
            ("Whiff% vs offspeed", "whiff_offspeed"),
            ("Chase% overall", "chase_all"),
            ("Chase% vs fastballs", "chase_fastball"),
            ("Chase% vs breaking", "chase_breaking"),
            ("Chase% vs offspeed", "chase_offspeed"),
            ("Chase% breaking, down-and-away", "chase_brk_down_away"),
            ("Swing% in the 'chase' attack zone", "swing_chase_zone"),
            ("In-zone contact%", "z_contact")]
    for lab, k in cuts:
        A(f"| {lab} | {_p(r24[k]['rate'])} | {_p(r25[k]['rate'])} | "
          f"{_p(r26[k]['rate'])} |")
    A("\nThree honest observations:\n")
    A(f"1. **The whiff spike is everywhere, including premium velocity** "
      f"(≥95 FB: {_p(r24['whiff_fb95']['rate'])} → "
      f"{_p(r25['whiff_fb95']['rate'])} → {_p(r26['whiff_fb95']['rate'])}, "
      f"n={r26['whiff_fb95']['n']} swings in 2026). On its own that reads "
      "like a slowing bat — but the bat is *measured* and it is not slowing. "
      "Rising whiffs on a rising bat speed + a longer, steeper swing is the "
      "signature of **selling out**: more intent, less bat control.")
    A(f"2. **The chase leak is velocity and offspeed, not the classic "
      f"breaking-ball-in-the-dirt.** Chase on fastballs jumped "
      f"{_p(r24['chase_fastball']['rate'])} → "
      f"{_p(r26['chase_fastball']['rate'])} and on offspeed "
      f"{_p(r24['chase_offspeed']['rate'])} → "
      f"{_p(r26['chase_offspeed']['rate'])}, while chase on breaking balls "
      f"down-and-away has actually *improved* "
      f"({_p(r24['chase_brk_down_away']['rate'])} → "
      f"{_p(r26['chase_brk_down_away']['rate'])}, small n). He is not "
      "getting fooled by spin; he is starting the A-swing early and "
      "expanding off velocity — an approach/timing problem.")
    A(f"3. **In-zone contact is down** ({_p(r24['z_contact']['rate'])} → "
      f"{_p(r26['z_contact']['rate'])}) — the cost of the max-intent swing "
      "showing up even on hittable pitches.\n")

    A("## Verdict\n")
    if v["label"] == "approach":
        A(f"**This is an approach problem, not a physical one — and the bat "
          f"speed is the receipt.** The one direct physical measurement got "
          f"*better* ({v['bat_speed_delta_mph']:+.1f} mph vs 2024–25) while "
          f"every decision metric got worse (chase "
          f"{v['chase_delta']*100:+.1f} pts vs 2025, in-zone contact "
          f"{v['zcontact_delta']*100:+.1f} pts). Duran at 29 is not losing "
          "bat speed; he appears to be pressing — swinging harder, longer "
          "and steeper, expanding against velocity and offspeed. Approach "
          "problems are fixable (his own 2022→2023 chase overhaul is the "
          "in-house proof); bat-death is not. **This re-weights the rebound "
          "scenarios toward the healthy prior.**")
    elif v["label"] == "physical":
        A(f"**The bat is slowing ({v['bat_speed_delta_mph']:+.1f} mph) — "
          "this is physical decline, and the erosion scenario deserves the "
          "weight.** The buy-low thesis takes a real hit here.")
    else:
        A(f"**The signals are mixed** (bat speed "
          f"{v['bat_speed_delta_mph']:+.1f} mph, chase "
          f"{v['chase_delta']*100:+.1f} pts) — neither story wins cleanly, "
          "so the two rebound scenarios keep equal weight.")
    if rw:
        A(f"\nQuantified: weighting the scenarios "
          f"{int(rw['w_healthy']*100)}/{int((1-rw['w_healthy'])*100)} "
          f"(vs an agnostic 50/50) puts the blended P(rest-of-season wRC+ ≥ "
          f"100) at **{rw['p_reweighted']:.0%}** (vs "
          f"{rw['p_agnostic_5050']:.0%} agnostic; the pure scenarios are "
          f"{rw['p_healthy']:.0%} healthy / {rw['p_erosion']:.0%} eroded).")
    A("\nOne caveat, stated plainly: 'approach' does not mean 'automatically "
      "fixed.' The fix requires him (or the hitting group) to actually dial "
      "the intent back, and half a season of habit is real. But the asset a "
      "trade partner is pricing — bat speed, foot speed, defense — is "
      "intact, which strengthens the case that today's $10M nadir price "
      "sells the slump, not the player.\n")
    A("![Erosion decomposition](../figures/10_erosion_decomposition.png)\n")
    A("---\n*Definitions: competitive swings ≥50 mph bat speed; fast swing "
      "≥75 mph (Savant thresholds). Pitch groups: FB=FF/SI/FC, "
      "BRK=SL/ST/SV/CU/KC/CS/SC, OFF=CH/FS/FO/EP/KN. Attack zones "
      "normalized to the batter's own strike zone (heart ≤2/3, shadow ≤4/3, "
      "chase ≤2, waste beyond). 2026 is a half season — the by-pitch-type "
      "cells run n≈100–350, so read cell-level moves as directional; the "
      "bat-speed trend itself is measured on 600+ swings per season.*")

    out = C.OUT_DIR / "erosion_decomposition.md"
    out.write_text("\n".join(L))
    print(f"  [erosion] wrote {out}")


def run():
    res = compute()
    fig(res)
    print("  [erosion] wrote figure 10")
    memo(res)
    with open(C.DATA_DIR / "erosion_decomposition.json", "w") as f:
        json.dump(res, f, indent=2,
                  default=lambda o: (float(o) if isinstance(o, np.floating)
                                     else int(o) if isinstance(o, np.integer)
                                     else bool(o) if isinstance(o, np.bool_)
                                     else str(o)))
    return res


if __name__ == "__main__":
    run()
