"""Speed-aware expected-contact model: fixing xwOBA's blind spot, formally.

The project's luck analysis rests on a critique of Statcast xstats: they
are built from exit velocity + launch angle only, so a burner chronically
out-hits his xwOBA *as a skill*, not luck. Elsewhere we handle that with
an offset (Duran's own career wOBA-xwOBA gap). This module trains the
corrected model instead and lets the data decide:

  * Data: every 2026 MLB batted ball (league parquet, ~110k in-play
    events), joined to Savant sprint speed by batter.
  * Two GBMs per target, identical but for one feature:
      base  = f(exit velo, launch angle, spray angle)
      speed = f(exit velo, launch angle, spray angle, sprint speed)
    Targets: P(hit) on balls in play ex-HR (xBABIP) and wOBA value on
    all contact (xwOBAcon).
  * Validation: 5-fold GroupKFold BY BATTER — a player's own batted
    balls never inform his prediction, so player-level residuals are
    honest out-of-sample quantities.
  * The exhibit: the base model's hit-probability residual by sprint-
    speed decile. If xstats were speed-neutral this curve would be flat
    at zero; its slope IS the blind spot, and Duran's decile locates
    him on it.

Writes data/xcontact.json and figures/16_speed_model.png.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier as HGBC
from sklearn.ensemble import HistGradientBoostingRegressor as HGBR
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

from . import config as C
from . import style as S

S.apply()

PARQUET = C.STATCAST_DIR / "league_pitches_2026.parquet"
DURAN_ID = 680776
SEED = 34
HIT_EVENTS = {"single", "double", "triple"}
OUT_BIP = {"field_out", "grounded_into_double_play", "double_play",
           "force_out", "fielders_choice_out", "fielders_choice",
           "sac_fly", "sac_fly_double_play", "field_error", "sac_bunt",
           "triple_play"}


def spray_angle(hc_x, hc_y, stand):
    """Spray angle in degrees from Savant hit coordinates, mirrored by
    batter handedness so positive is always the pull side. Pure/vectorized
    (unit-tested offline)."""
    phi = np.degrees(np.arctan2(np.asarray(hc_x, dtype=float) - 125.42,
                                198.27 - np.asarray(hc_y, dtype=float)))
    return np.where(np.asarray(stand) == "L", phi, -phi)


def _sprint_speeds() -> pd.DataFrame:
    from pybaseball import statcast_sprint_speed
    ss = statcast_sprint_speed(2026, min_opp=5)
    id_col = [c for c in ss.columns if "player_id" in c][0]
    return ss[[id_col, "sprint_speed"]].rename(columns={id_col: "batter"})


def _fetch_league() -> pd.DataFrame:
    import datetime as dt
    from pybaseball import statcast
    end = min(dt.date.today(), dt.date(2026, 9, 27)).isoformat()
    df = statcast(start_dt="2026-03-25", end_dt=end, verbose=False)
    keep = ["game_pk", "game_date", "batter", "pitcher", "stand",
            "p_throws", "events", "description", "type", "launch_speed",
            "launch_angle", "hc_x", "hc_y", "bb_type",
            "estimated_woba_using_speedangle",
            "estimated_ba_using_speedangle", "woba_value", "woba_denom",
            "babip_value", "home_team", "away_team", "inning_topbot",
            "balls", "strikes"]
    df = df[[c for c in keep if c in df.columns]]
    PARQUET.parent.mkdir(exist_ok=True)
    df.to_parquet(PARQUET, index=False)
    return df


def load() -> pd.DataFrame:
    df = (pd.read_parquet(PARQUET) if PARQUET.exists() else _fetch_league())
    bb = df[(df["type"] == "X") & df["launch_speed"].notna()
            & df["launch_angle"].notna() & df["hc_x"].notna()
            & df["hc_y"].notna()].copy()
    bb = bb[bb["bb_type"] != "bunt"]
    bb["spray"] = spray_angle(bb["hc_x"], bb["hc_y"], bb["stand"])
    ss = _sprint_speeds()
    bb = bb.merge(ss, on="batter", how="left")
    bb = bb[bb["sprint_speed"].notna()]
    bb["is_hr"] = bb["events"] == "home_run"
    bb["hit"] = bb["events"].isin(HIT_EVENTS).astype(int)
    bb["wobacon"] = bb["woba_value"].astype(float)
    return bb


FEATS_BASE = ["launch_speed", "launch_angle", "spray"]
FEATS_SPEED = FEATS_BASE + ["sprint_speed"]


def _oof(df, feats, target, kind) -> np.ndarray:
    """Out-of-fold predictions, folds grouped by batter."""
    oof = np.full(len(df), np.nan)
    gkf = GroupKFold(n_splits=5)
    X, y, g = df[feats].values, df[target].values, df["batter"].values
    for tr, te in gkf.split(X, y, g):
        if kind == "clf":
            m = HGBC(random_state=SEED)
            m.fit(X[tr], y[tr])
            oof[te] = m.predict_proba(X[te])[:, 1]
        else:
            m = HGBR(random_state=SEED)
            m.fit(X[tr], y[tr])
            oof[te] = m.predict(X[te])
    return oof


def run() -> dict:
    bb = load()
    bip = bb[~bb["is_hr"]].copy()  # BABIP universe
    print(f"  [xcontact] {len(bb):,} batted balls "
          f"({bip['batter'].nunique()} hitters with sprint speed)")

    # ---- xBABIP: P(hit) on balls in play --------------------------------
    for feats, tag in ((FEATS_BASE, "base"), (FEATS_SPEED, "speed")):
        bip[f"p_{tag}"] = _oof(bip, feats, "hit", "clf")
    m_babip = {t: {"auc": float(roc_auc_score(bip["hit"], bip[f"p_{t}"])),
                   "logloss": float(log_loss(bip["hit"], bip[f"p_{t}"]))}
               for t in ("base", "speed")}

    # ---- xwOBAcon: wOBA value on all contact ----------------------------
    for feats, tag in ((FEATS_BASE, "base"), (FEATS_SPEED, "speed")):
        bb[f"w_{tag}"] = _oof(bb, feats, "wobacon", "reg")
    m_woba = {t: {"rmse": float(np.sqrt(np.mean(
        (bb["wobacon"] - bb[f"w_{t}"]) ** 2)))} for t in ("base", "speed")}

    # ---- the blind-spot curve: base-model residual by speed decile ------
    bip["decile"] = pd.qcut(bip["sprint_speed"], 10, labels=False) + 1
    dec = bip.groupby("decile").apply(
        lambda d: pd.Series({
            "sprint_speed": d["sprint_speed"].mean(),
            "resid_base": (d["hit"] - d["p_base"]).mean(),
            "resid_speed": (d["hit"] - d["p_speed"]).mean(),
            "n": len(d)})).reset_index()

    # ---- Duran ----------------------------------------------------------
    du_bip = bip[bip["batter"] == DURAN_ID]
    du_bb = bb[bb["batter"] == DURAN_ID]
    duran = {
        "n_bip": int(len(du_bip)),
        "sprint_speed": float(du_bb["sprint_speed"].iloc[0]),
        "decile": int(du_bip["decile"].iloc[0]) if len(du_bip) else None,
        "babip": float(du_bip["hit"].mean()),
        "xbabip_base": float(du_bip["p_base"].mean()),
        "xbabip_speed": float(du_bip["p_speed"].mean()),
        "xwobacon_base": float(du_bb["w_base"].mean()),
        "xwobacon_speed": float(du_bb["w_speed"].mean()),
    }
    # contact share -> full-wOBA scale: the premium only acts on batted
    # balls, so scale by (batted balls / season PA) from FanGraphs
    duran["speed_premium_wobacon"] = (duran["xwobacon_speed"]
                                      - duran["xwobacon_base"])
    try:
        fg = pd.read_csv(C.DATA_DIR / "duran_fangraphs_seasons.csv")
        pa26 = float(fg.loc[fg["Season"] == 2026, "PA"].iloc[0])
        share = len(du_bb) / pa26
        duran["contact_share"] = round(share, 3)
        duran["speed_premium_full_woba"] = (duran["speed_premium_wobacon"]
                                            * share)
    except (FileNotFoundError, IndexError, KeyError):
        duran["contact_share"] = None
        duran["speed_premium_full_woba"] = None

    res = {"n_batted_balls": int(len(bb)), "n_hitters":
           int(bb["batter"].nunique()), "metrics_babip": m_babip,
           "metrics_wobacon": m_woba,
           "deciles": dec.to_dict("records"), "duran": duran}
    (C.DATA_DIR / "xcontact.json").write_text(json.dumps(res, indent=2))
    print(f"  [xcontact] wrote {C.DATA_DIR / 'xcontact.json'}")
    print(f"  [xcontact] xBABIP AUC {m_babip['base']['auc']:.4f} -> "
          f"{m_babip['speed']['auc']:.4f} with sprint speed")
    print(f"  [xcontact] top-decile base-model bias "
          f"{dec['resid_base'].iloc[-1]*1000:+.1f} pts of BABIP")
    print(f"  [xcontact] Duran speed premium on contact: "
          f"{duran['speed_premium_wobacon']*1000:+.1f} pts of wOBAcon")
    fig_speed(res)
    return res


def fig_speed(res: dict):
    dec = pd.DataFrame(res["deciles"])
    du = res["duran"]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.axhline(0, color=S.SPINE, lw=1)
    se = (1000 * (dec["resid_base"].abs() * 0 + 1)
          * (0.25 / dec["n"]) ** 0.5)  # binomial upper-bound SE, points
    ax.errorbar(dec["decile"], dec["resid_base"] * 1000, yerr=se,
                fmt="-o", color=S.RED, lw=2.2, ms=7, capsize=3,
                label="EV + LA + spray only (xstats' view)")
    ax.errorbar(dec["decile"], dec["resid_speed"] * 1000, yerr=se,
                fmt="-o", color=S.NAVY, lw=2.2, ms=7, capsize=3,
                label="+ sprint speed")
    if du.get("decile"):
        ax.axvline(du["decile"], color=S.AMBER, lw=2, ls=":",
                   label=f"Duran ({du['sprint_speed']:.1f} ft/s)")
    ax.set_xticks(dec["decile"])
    S.style(ax)
    ax.set_xlabel("Sprint-speed decile (league hitters, 2026)")
    ax.set_ylabel("Actual minus expected BABIP (points)")
    ax.set_title("The blind spot, measured: EV/LA models under-predict "
                 "fast runners", loc="left", fontsize=15, fontweight="bold")
    leg = ax.legend(loc="upper left")
    for t in leg.get_texts():
        t.set_color(S.TEXT)
    ax.text(0, -0.15, "Out-of-fold residuals with binomial standard "
            "errors, 5-fold CV grouped by batter; "
            f"{res['n_batted_balls']:,} batted balls, 2026 league-wide.",
            transform=ax.transAxes, fontsize=10, color=S.MUTED)
    fig.tight_layout()
    out = C.FIG_DIR / "16_speed_model.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [xcontact] wrote {out}")
