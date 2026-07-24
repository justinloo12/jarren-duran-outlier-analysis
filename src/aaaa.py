"""The quad-A audit: how much of Boston's surge came from fringe players
playing over their heads — and what that means at the deadline.

Cohort (programmatic, not hand-picked): 2026 Red Sox with a real role
(hitters >= 40 PA, pitchers >= 15 IP) whose MLB track record entering
2026 was thin — hitters < 1000 career PA, pitchers < 250 career IP,
age >= 24 (so genuine prospects are excluded, journeymen are not).

For each player:
  * 2026 line (FanGraphs: wRC+/WAR or ERA/FIP/WAR),
  * career-entering-2026 baseline and best prior season (MLB StatsAPI
    year-by-year; OPS for hitters, ERA for pitchers),
  * results-vs-process from pitch-level Statcast (wOBA vs xwOBA for
    hitters; wOBA-against vs xwOBA-against for pitchers),
  * career-high / career-best flags.

Writes data/aaaa.json, outputs/aaaa_audit.md, figures/17_aaaa_audit.png,
and splices a section into outputs/ARTICLE.md (before the trades menu).
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from . import config as C
from . import style as S
from .deadline import _fg_pull

S.apply()

MIN_PA, MIN_IP = 40, 15
CAREER_PA_MAX, CAREER_IP_MAX = 1000, 250
MIN_AGE = 24
_SAPI = "https://statsapi.mlb.com/api/v1"


# ---------------------------------------------------------------- careers
def _mlbam_id(name: str):
    r = requests.get(f"{_SAPI}/people/search", params={"names": name},
                     headers=C.HTTP_HEADERS, timeout=C.HTTP_TIMEOUT).json()
    people = r.get("people", [])
    return people[0]["id"] if people else None


def _year_by_year(pid: int, group: str) -> list[dict]:
    r = requests.get(f"{_SAPI}/people/{pid}/stats",
                     params={"stats": "yearByYear", "group": group,
                             "sportId": 1},
                     headers=C.HTTP_HEADERS, timeout=C.HTTP_TIMEOUT).json()
    out = []
    for blk in r.get("stats", []):
        for sp in blk.get("splits", []):
            st = sp.get("stat", {})
            st["season"] = int(sp.get("season", 0))
            out.append(st)
    return out


def _ip_float(s) -> float:
    try:
        whole, _, frac = str(s).partition(".")
        return int(whole) + {"1": 1 / 3, "2": 2 / 3}.get(frac, 0.0)
    except ValueError:
        return 0.0


def _career_bat(pid: int) -> dict:
    rows = [r for r in _year_by_year(pid, "hitting") if r["season"] < 2026]
    if not rows:
        return {"pa": 0, "ops": None, "best_ops": None, "best_season": None}
    df = pd.DataFrame(rows)
    df["pa"] = pd.to_numeric(df.get("plateAppearances"), errors="coerce")
    for c in ("obp", "slg"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    g = df.groupby("season").apply(
        lambda d: pd.Series({
            "pa": d["pa"].sum(),
            "ops": (np.average(d["obp"], weights=d["pa"])
                    + np.average(d["slg"], weights=d["pa"]))
            if d["pa"].sum() else np.nan}),
        include_groups=False).reset_index()
    pa = float(g["pa"].sum())
    ops = (float(np.average(g["ops"].dropna(),
                            weights=g.loc[g["ops"].notna(), "pa"]))
           if g["ops"].notna().any() and pa else None)
    qual = g[(g["pa"] >= 100) & g["ops"].notna()]
    best = qual.sort_values("ops").iloc[-1] if len(qual) else None
    return {"pa": int(pa), "ops": ops,
            "best_ops": (float(best["ops"]) if best is not None else None),
            "best_season": (int(best["season"]) if best is not None
                            else None)}


def _career_pit(pid: int) -> dict:
    rows = [r for r in _year_by_year(pid, "pitching") if r["season"] < 2026]
    if not rows:
        return {"ip": 0, "era": None, "best_era": None, "best_season": None}
    df = pd.DataFrame(rows)
    df["ip"] = df.get("inningsPitched").map(_ip_float)
    df["er"] = pd.to_numeric(df.get("earnedRuns"), errors="coerce")
    g = df.groupby("season").agg(ip=("ip", "sum"),
                                 er=("er", "sum")).reset_index()
    ip = float(g["ip"].sum())
    era = float(g["er"].sum() / ip * 9) if ip else None
    qual = g[g["ip"] >= 20].copy()
    if len(qual):
        qual["era"] = qual["er"] / qual["ip"] * 9
        best = qual.sort_values("era").iloc[0]
        best_era, best_season = float(best["era"]), int(best["season"])
    else:
        best_era = best_season = None
    return {"ip": round(ip, 1), "era": era, "best_era": best_era,
            "best_season": best_season}


# ------------------------------------------------------- statcast process
def _statcast_woba() -> tuple[dict, dict]:
    """{batter_id: (wOBA, xwOBA)}, {pitcher_id: (wOBA-against, x-against)}
    from the 2026 league pitch parquet."""
    df = pd.read_parquet(C.STATCAST_DIR / "league_pitches_2026.parquet")
    pa = df[df["woba_denom"].notna() & (df["woba_denom"] > 0)].copy()
    pa["x"] = pa["estimated_woba_using_speedangle"].fillna(pa["woba_value"])

    def agg(col):
        g = pa.groupby(col).agg(w=("woba_value", "mean"), x=("x", "mean"),
                                n=("woba_value", "size"))
        return {int(i): (float(r["w"]), float(r["x"]), int(r["n"]))
                for i, r in g.iterrows()}
    return agg("batter"), agg("pitcher")


def _sc_ids(names: list[str]) -> dict:
    from pybaseball import playerid_lookup
    out = {}
    for n in names:
        parts = n.split()
        first, last = parts[0], " ".join(parts[1:])
        try:
            t = playerid_lookup(last, first, fuzzy=True)
            if len(t):
                out[n] = int(t.iloc[0]["key_mlbam"])
        except Exception:
            pass
    return out


# ----------------------------------------------------------------- build
def build() -> dict:
    bat = _fg_pull("all", team=3, stats="bat", typ=8)
    for c in ("PA", "wRC+", "WAR", "Age", "wOBA", "OBP", "SLG"):
        bat[c] = pd.to_numeric(bat[c], errors="coerce")
    bat = bat[(bat["PA"] >= MIN_PA) & (bat["Age"] >= MIN_AGE)]

    pit = _fg_pull("all", team=3, stats="pit", typ=1)
    for c in ("IP", "ERA", "FIP", "WAR", "Age", "GS"):
        pit[c] = pd.to_numeric(pit[c], errors="coerce")
    pit = pit[(pit["IP"] >= MIN_IP) & (pit["Age"] >= MIN_AGE)]
    # young starters with pedigree are prospects graduating, not quad-A
    pit = pit[~((pit["GS"].fillna(0) >= 5) & (pit["Age"] <= 26))]

    b_ids, p_ids = _statcast_woba()
    names = bat["Name"].tolist() + pit["Name"].tolist()
    sc = _sc_ids(names)

    hitters, arms = [], []
    for _, r in bat.iterrows():
        pid = _mlbam_id(r["Name"]) or sc.get(r["Name"])
        if pid is None:
            continue
        car = _career_bat(pid)
        if car["pa"] >= CAREER_PA_MAX:
            continue  # established — not quad-A
        if car["pa"] >= 500 and car["ops"] and car["ops"] >= 0.750:
            continue  # proven regular on a short clock, not a journeyman
        w, x, n = b_ids.get(sc.get(r["Name"], pid), (None, None, 0))
        ops26 = float(r["OBP"] + r["SLG"])
        hitters.append({
            "name": r["Name"], "age": int(r["Age"]), "pa_2026": int(r["PA"]),
            "wrc_2026": round(float(r["wRC+"])), "war_2026":
            round(float(r["WAR"]), 1), "ops_2026": round(ops26, 3),
            "career_pa": car["pa"],
            "career_ops": round(car["ops"], 3) if car["ops"] else None,
            "best_ops": (round(car["best_ops"], 3) if car["best_ops"]
                         else None),
            "best_season": car["best_season"],
            "woba": round(w, 3) if w else None,
            "xwoba": round(x, 3) if x else None,
            "rookie": car["best_ops"] is None,
            "career_high": bool(car["best_ops"] is not None
                                and ops26 > car["best_ops"]),
            "vs_career": (round(ops26 - car["ops"], 3) if car["ops"]
                          else None)})
    for _, r in pit.iterrows():
        pid = _mlbam_id(r["Name"]) or sc.get(r["Name"])
        if pid is None:
            continue
        car = _career_pit(pid)
        if car["ip"] >= CAREER_IP_MAX:
            continue
        w, x, n = p_ids.get(sc.get(r["Name"], pid), (None, None, 0))
        era26 = float(r["ERA"])
        arms.append({
            "name": r["Name"], "age": int(r["Age"]),
            "ip_2026": round(float(r["IP"]), 1),
            "era_2026": round(era26, 2), "fip_2026":
            round(float(r["FIP"]), 2), "war_2026":
            round(float(r["WAR"]), 1),
            "career_ip": car["ip"],
            "career_era": round(car["era"], 2) if car["era"] else None,
            "best_era": (round(car["best_era"], 2) if car["best_era"]
                         else None),
            "best_season": car["best_season"],
            "woba_against": round(w, 3) if w else None,
            "xwoba_against": round(x, 3) if x else None,
            "rookie": car["best_era"] is None,
            "career_best": bool(car["best_era"] is not None
                                and era26 < car["best_era"]),
            "vs_career": (round(era26 - car["era"], 2) if car["era"]
                          else None)})

    hitters.sort(key=lambda h: -(h["vs_career"] or 0))
    arms.sort(key=lambda a: (a["vs_career"] or 0))
    tot_war = (sum(h["war_2026"] for h in hitters)
               + sum(a["war_2026"] for a in arms))
    n_high = (sum(h["career_high"] for h in hitters)
              + sum(a["career_best"] for a in arms))
    n_rookie = (sum(h["rookie"] for h in hitters)
                + sum(a["rookie"] for a in arms))
    # process check: PA/BF-weighted results-vs-expected across the cohort
    hl = [(h["woba"] - h["xwoba"], h["pa_2026"]) for h in hitters
          if h["woba"] and h["xwoba"]]
    al = [(a["xwoba_against"] - a["woba_against"], a["ip_2026"])
          for a in arms if a["woba_against"] and a["xwoba_against"]]
    luck_bat = (sum(g * w for g, w in hl) / sum(w for _, w in hl)
                if hl else 0.0)
    luck_arm = (sum(g * w for g, w in al) / sum(w for _, w in al)
                if al else 0.0)
    return {"hitters": hitters, "arms": arms,
            "total_war": round(tot_war, 1), "n": len(hitters) + len(arms),
            "n_career_high": int(n_high), "n_rookie": int(n_rookie),
            "cohort_bat_luck": round(luck_bat, 3),
            "cohort_arm_luck": round(luck_arm, 3)}


# ---------------------------------------------------------------- figure
def fig_aaaa(res: dict):
    h = [x for x in res["hitters"] if x["career_ops"]]
    a = [x for x in res["arms"] if x["career_era"]]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 5.6))
    for ax, rows, k26, kc, kb, better_hi in (
            (ax1, h, "ops_2026", "career_ops", "best_ops", True),
            (ax2, a, "era_2026", "career_era", "best_era", False)):
        ys = np.arange(len(rows))
        for y, r in zip(ys, rows):
            hot = (r[k26] > r[kc]) if better_hi else (r[k26] < r[kc])
            ax.plot([r[kc], r[k26]], [y, y], color=S.GREY, lw=2,
                    alpha=0.6, zorder=1)
            if r[kb] is not None:
                ax.scatter(r[kb], y, marker="|", s=210, color=S.AMBER,
                           lw=2.4, zorder=2)
            ax.scatter(r[kc], y, s=68, facecolors="none",
                       edgecolors=S.MUTED, zorder=3)
            ax.scatter(r[k26], y, s=105,
                       color=S.GREEN if hot else S.RED, zorder=4)
        ax.set_yticks(ys)
        ax.set_yticklabels([r["name"] for r in rows])
        ax.invert_yaxis()
        S.style(ax, grid_axis="x")
    ax1.set_xlabel("OPS — hollow: career, solid: 2026, tick: best season")
    ax2.set_xlabel("ERA — hollow: career, solid: 2026, tick: best season")
    ax1.set_title("Hitters", loc="left", fontsize=14, fontweight="bold")
    ax2.set_title("Pitchers", loc="left", fontsize=14, fontweight="bold")
    fig.suptitle("The quad-A cohort, 2026 vs their own careers — "
                 f"{res['n_career_high']} career bests among the "
                 "returners", x=0.02, y=0.99, ha="left", fontsize=16,
                 fontweight="bold")
    fig.tight_layout()
    out = C.FIG_DIR / "17_aaaa_audit.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"  [aaaa] wrote {out}")


# ------------------------------------------------------------------ memo
def memo_md(res: dict) -> str:
    L = []
    A = L.append
    A("# The Quad-A Audit — the surge's supporting cast, vs their own "
      "careers\n")
    A("*Cohort: 2026 Red Sox with a real role (40+ PA / 15+ IP) and a "
      "thin MLB track record entering the year (hitters < 1,000 career "
      "PA, pitchers < 250 career IP, age 24+). Career baselines from MLB "
      "StatsAPI year-by-year; process checks from pitch-level Statcast.*\n")
    n_vet = res["n"] - res["n_rookie"]
    A(f"**Headline:** {res['n']} players fit the profile. Together they "
      f"account for **{res['total_war']:+.1f} WAR** in 2026. Of the "
      f"{n_vet} with prior MLB seasons, **{res['n_career_high']} are "
      f"running career bests**, and the other {res['n_rookie']} are "
      "rookies with no MLB baseline at all. Depth like this is why the "
      "surge happened; counting on it to repeat is how deadline mistakes "
      "get made.\n")
    A("## Hitters\n")
    A("| Player | Age | 2026 PA | wRC+ | OPS | Career OPS | Best (yr) | "
      "wOBA−xwOBA | Career high? |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|:--|")
    for h in res["hitters"]:
        gap = ((f"{(h['woba']-h['xwoba'])*1000:+.0f}")
               if h["woba"] and h["xwoba"] else "—")
        best = (f"{h['best_ops']:.3f} ({h['best_season']})"
                if h["best_ops"] else "rookie season")
        A(f"| {h['name']} | {h['age']} | {h['pa_2026']} | {h['wrc_2026']} "
          f"| {h['ops_2026']:.3f} | "
          f"{h['career_ops'] if h['career_ops'] else '—'} | {best} | "
          f"{gap} | "
          f"{'first MLB season' if h['rookie'] else ('**YES**' if h['career_high'] else 'no')} |")
    A("\n## Pitchers\n")
    A("| Player | Age | 2026 IP | ERA | FIP | Career ERA | Best (yr) | "
      "xwOBA−wOBA against | Career best? |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|:--|")
    for a in res["arms"]:
        gap = ((f"{(a['xwoba_against']-a['woba_against'])*1000:+.0f}")
               if a["woba_against"] and a["xwoba_against"] else "—")
        best = (f"{a['best_era']:.2f} ({a['best_season']})"
                if a["best_era"] else "rookie season")
        A(f"| {a['name']} | {a['age']} | {a['ip_2026']} | "
          f"{a['era_2026']:.2f} | {a['fip_2026']:.2f} | "
          f"{a['career_era'] if a['career_era'] else '—'} | {best} | "
          f"{gap} | "
          f"{'first MLB season' if a['rookie'] else ('**YES**' if a['career_best'] else 'no')} |")
    A("\n*Positive wOBA−xwOBA = results ahead of contact quality "
      "(regression risk). For pitchers, positive xwOBA−wOBA against = "
      "allowing weaker results than the contact deserves (same risk, "
      "run-prevention side).*\n")
    A("![Quad-A audit](../figures/17_aaaa_audit.png)\n")
    return "\n".join(L)


# ------------------------------------------------------- article section
def article_section(res: dict) -> str:
    # feature career-best players who are actually producing
    top_h = ([h for h in res["hitters"] if h["career_high"]
              and h["wrc_2026"] >= 90]
             or [h for h in res["hitters"] if h["career_high"]])[:3]
    top_a = [a for a in res["arms"] if a["career_best"]][:3]
    names_h = ", ".join(f"{h['name']} ({h['wrc_2026']} wRC+ against a "
                        f".{h['career_ops']*1000:.0f} career OPS)"
                        if h["career_ops"] else h["name"]
                        for h in top_h[:2])
    names_a = ", ".join(f"{a['name']} ({a['era_2026']:.2f} ERA vs "
                        f"{a['career_era']:.2f} career)"
                        if a["career_era"] else a["name"]
                        for a in top_a[:2])
    L = []
    A = L.append
    A("\n## The quad-A engine, audited\n")
    A("The streak is over, and it is worth being honest about who built "
      f"it. {res['n']} Red Sox with almost no MLB track record (waiver "
      "claims, up-and-down arms, career minor leaguers) hold real "
      f"roles, and together they have produced **{res['total_war']:+.1f} "
      f"WAR**. Of the {res['n'] - res['n_rookie']} with prior MLB "
      f"seasons, **{res['n_career_high']} are running the best seasons "
      f"of their careers**, and the other {res['n_rookie']} are rookies "
      "with no baseline to regress to, which cuts both ways (full "
      "table in the quad-A audit memo). "
      + (f"On the position side that means {names_h}; " if names_h else "")
      + (f"in the pen, {names_a}." if names_a else "") + "\n")
    A("![Quad-A audit](figures/17_aaaa_audit.png)\n")
    big_luck = max(abs(res["cohort_arm_luck"]),
                   abs(res["cohort_bat_luck"])) >= 0.010
    if big_luck:
        proc = ("and the pitch-level check agrees: as a group the "
                "cohort's arms are allowing "
                f"**{res['cohort_arm_luck']*1000:+.0f} points** less "
                "wOBA than their contact quality deserves, while the "
                f"bats run {res['cohort_bat_luck']*1000:+.0f} points "
                "versus expected")
    else:
        proc = ("and to be fair, the pitch-level check says the group "
                "is mostly earning it (results within "
                f"{res['cohort_bat_luck']*1000:+.0f}/"
                f"{res['cohort_arm_luck']*1000:+.0f} points of expected "
                "for bats/arms). The risk is not luck, it is track "
                "record. Journeymen do not usually carry career bests "
                "through August, and the projection systems will bet on "
                "the career, not the heater")
    A("That is not a durable foundation; it is a tailwind. Career-best "
      "seasons from journeymen are exactly the production that fades "
      f"down the stretch, {proc}. "
      "This is the strongest argument for buying real reinforcements "
      "rather than standing pat: Boston does not need to add stars, it "
      "needs to replace borrowed production before it gets returned. A "
      "real reliever instead of a career-year one; a real infield bat "
      "instead of a waiver claim on a heater. The trades below are sized "
      "for exactly that.\n")
    return "\n".join(L)


MARKER = "## Three trades that fit"


def run() -> dict:
    res = build()
    (C.DATA_DIR / "aaaa.json").write_text(json.dumps(res, indent=2))
    print(f"  [aaaa] wrote {C.DATA_DIR / 'aaaa.json'} "
          f"({res['n']} players, {res['n_career_high']} at career bests)")
    fig_aaaa(res)
    out = C.OUT_DIR / "aaaa_audit.md"
    out.write_text(memo_md(res))
    print(f"  [aaaa] wrote {out}")
    art = C.OUT_DIR / "ARTICLE.md"
    if art.exists():
        s = art.read_text()
        if "## The quad-A engine" not in s and MARKER in s:
            i = s.index(MARKER)
            s = s[:i] + article_section(res).strip() + "\n\n" + s[i:]
            art.write_text(s)
            print("  [aaaa] spliced quad-A section into ARTICLE.md")
    return res
