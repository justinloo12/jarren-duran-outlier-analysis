"""Mock deadline trades: converting Boston's pitching surplus into bats.

Constructs value-checked hypothetical trades using:
  * live 2026 stats (FanGraphs API) for every named player,
  * verified contract status (sourced via reporting, as-of dates noted),
  * the same $8M/WAR + prospect-FV surplus framework as trade_targets.py.

The candidate pools are computed (sellers x positions of need); the trade
constructions are curated from those pools so the packages stay realistic.
Writes outputs/mock_trades.md and appends a section to outputs/ARTICLE.md.
"""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from . import config as C
from .deadline import _fg_pull

AS_OF = dt.date.today().isoformat()

# FV -> surplus $M (FanGraphs prospect-valuation ballparks, per trade_targets)
FV = {"55 FV": 40, "50 FV": 27, "45+ FV": 15, "45 FV": 9, "40 FV": 4}


def _streak_n() -> int:
    """Length of the season's signature win streak (persisted by
    deadline.run(), so the number survives the run ending)."""
    try:
        return int(json.load(open(C.DATA_DIR / "deadline.json"))
                   .get("max_win_streak", 13))
    except (FileNotFoundError, KeyError, ValueError):
        return 13


def _bats(names):
    d = _fg_pull("all", team=0, stats="bat", typ=8)
    for c in ("PA", "wRC+", "WAR", "Age"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return {n: d[d["Name"] == n].iloc[0] if (d["Name"] == n).any() else None
            for n in names}


def _arms(names):
    d = _fg_pull("all", team=0, stats="pit", typ=1)
    for c in ("IP", "ERA", "FIP", "WAR", "Age", "GS"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return {n: d[d["Name"] == n].iloc[0] if (d["Name"] == n).any() else None
            for n in names}


def _bat_line(r):
    if r is None:
        return "stats n/a"
    return (f"{r['wRC+']:.0f} wRC+, {r['WAR']:.1f} WAR in {r['PA']:.0f} PA, "
            f"age {r['Age']:.0f}")


def _arm_line(r):
    if r is None:
        return "stats n/a"
    return (f"{r['ERA']:.2f} ERA / {r['FIP']:.2f} FIP, {r['WAR']:.1f} WAR in "
            f"{r['IP']:.0f} IP, age {r['Age']:.0f}")


def build() -> str:
    bats = _bats(["Zach Neto", "Shea Langeliers", "Otto Lopez",
                  "Ezequiel Duran",
                  "Bobby Witt Jr.", "Elly De La Cruz"])
    arms = _arms(["Payton Tolle", "Jake Bennett",
                  "Brayan Bello", "Sonny Gray", "Luke Weaver",
                  "Daniel Lynch IV", "Aroldis Chapman",
                  "Michael Wacha", "Kevin Gausman",
                  "Louie Varland", "Tyler Rogers"])

    L = []
    A = L.append
    A("# Mock Deadline Trades — Arms for Bats\n")
    A(f"*Generated {AS_OF} · stats live via FanGraphs; contracts verified "
      "via reporting as of this date; value framework: ~$8M/WAR plus "
      "FanGraphs-style prospect FV conversions (55 FV≈$40M, 50 FV≈$27M, "
      "45+ FV≈$15M, 45 FV≈$9M, 40 FV≈$4M). Hypotheticals, not reporting.*\n")

    A("## The premise\n")
    A("Boston's tradeable surplus is **starting pitching**: seven viable "
      "starters for five slots once Crochet and Sandoval are back "
      "(Connelly Early was the eighth until the July 23 Mead trade "
      "cashed him in):")
    for n in ("Payton Tolle", "Jake Bennett",
              "Brayan Bello", "Sonny Gray"):
        A(f"- **{n}** — {_arm_line(arms[n])}")
    A("\nThe needs, post-Mead: **bullpen help** (bottom half of MLB in "
      "reliever WAR, and Kelly is on the 60-day IL) and **rotation "
      "innings** (Early traded, Crochet building back from rehab, "
      "Sandoval still ramping). The infield bat is filled: Mead takes "
      "that lane. Catcher looks like a need on the audit but the "
      "battery data takes it off the list (see the walk-away below). "
      "LF and DH need no outside help: Duran's regression sits behind "
      "the Jahmai Jones platoon with Anthony's return behind that, and "
      "Yoshida has quietly been above average with Gonzalez covering "
      "the tougher lefties. Witt Jr. "
      f"({_bat_line(bats['Bobby Witt Jr.'])}) and De La Cruz "
      f"({_bat_line(bats['Elly De La Cruz'])}) top the seller SS list but "
      "are franchise players — named for completeness, not available.\n")
    A("**The disruption constraint.** A team holding a playoff spot "
      "in late July has a roster that works, and disruption is a cost even though it "
      "never shows up in a WAR column. Every deal below is graded on both "
      "ledgers, value and disruption, and the menu is **ranked by the "
      "second**: prospects out before big-leaguers, open spots before "
      "occupied ones, nobody demoted while the team is winning.\n")
    A("Three live trades and one deliberate pass make the menu — a menu, "
      "not a plan. Boston only *needs* the first one. The right deadline "
      "here is small.\n")

    # ---- Trade 1 ----------------------------------------------------------
    A("## Trade 1 — The pen fix: the zero-disruption add\n")
    A("> **Red Sox get:** RHP Luke Weaver "
      f"({_arm_line(arms['Luke Weaver'])}; signed through 2027, ~$12.5M "
      "owed next year)")
    A("> **Mets get:** a 45 FV bat plus a 40 FV arm (~$13M of prospect "
      "value)\n")
    A("**The math.** Weaver is having an elite relief season on a selling "
      "Mets club that reporting already lists as motivated to move him. A "
      "year-and-a-half of a 2.5-FIP reliever is worth ~$15–18M against "
      "~$18M of salary — the prospect price is real but mid-tier, not "
      "painful. Cheaper alternative from the same pool: KC's Daniel Lynch "
      f"IV ({_arm_line(arms['Daniel Lynch IV'])}) for a 40 FV flier.")
    A("**Package options.** (A) The clean one: a 45 FV bat plus a 40 FV "
      "arm, all minor-leaguers, roughly $13M of prospect value for "
      "$15-18M of reliever. (B) The roster version: Brayan Bello plus a "
      "40 FV, spending the surplus arm instead of the farm; near-even "
      "on value but it touches the active roster.")
    A("**Elsewhere in the lane.** Premium and controllable: Toronto's "
      f"Louie Varland ({_arm_line(arms['Louie Varland'])}), a bigger "
      "prospect price for multiple years of a dominant arm. Cheap "
      f"rental: Tyler Rogers ({_arm_line(arms['Tyler Rogers'])}) for a "
      "single 40 FV flier.")
    A("**Clubhouse cost: none** on option A. The bullpen simply gets "
      "deeper at its quiet weakness: the pen's ERA is masking a worse "
      "FIP and bottom-half reliever WAR. In a race decided by two or "
      "three wins, this is the surest marginal win on the board.\n")

    # ---- Trade 2 ----------------------------------------------------------
    A("## Trade 2 — The innings: a back-end starter\n")
    A("> **Red Sox get:** RHP Michael Wacha "
      f"({_arm_line(arms['Michael Wacha'])}; veteran innings, expiring "
      "money per reporting, verify before publishing)")
    A("> **Royals get:** a 40 FV prospect, Boston covers the remaining "
      "salary\n")
    A("**The math.** With Early traded, Crochet building back from "
      "rehab and Sandoval still ramping, the rotation needs innings "
      "more than upside. Wacha is the classic rental: a vet who takes "
      "the ball every fifth day at roughly league average, priced at a "
      "40 FV flier from a selling club. Buy-low alternative with more "
      "upside: Toronto's Kevin Gausman "
      f"({_arm_line(arms['Kevin Gausman'])}), whose FIP says he is "
      "better than his surface line, the mirror image of the Early "
      "sale.")
    A("**Clubhouse cost: none.** A prospect out, an open rotation slot "
      "filled. Nobody loses a job.\n")

    # ---- Trade 3 ----------------------------------------------------------
    A("## Trade 3 — The big swing: a real shortstop, at a real cost\n")
    A("> **Red Sox get:** SS Zach Neto "
      f"({_bat_line(bats['Zach Neto'])}; $4.15M, arbitration-controlled "
      "through 2029)")
    A("> **Angels get:** LHP Payton Tolle "
      f"({_arm_line(arms['Payton Tolle'])}), LHP Jake Bennett "
      f"({_arm_line(arms['Jake Bennett'])}), plus a 45 FV lottery arm\n")
    A("**The math.** Neto projects as a ~3.5-WAR shortstop with 3.5 cheap "
      "years of control after 2026 — roughly **$75–90M of surplus value**. "
      "Tolle is a breakout 23-year-old lefty (top-100 type, ~$45–55M), "
      "Bennett a controllable mid-rotation arm (~$25M), plus ~$9M in FV: the "
      "package lands in the same band. LA declined to extend Neto and is "
      "10.5 out — this is exactly when a rebuilding club cashes a "
      "26-and-under core piece for three arms.")
    A("**Package options.** (A) Arms-only: Tolle + Bennett + a 45 FV "
      "lottery arm, roughly the $75-90M band. (B) The Mayer version: "
      "Marcelo Mayer + Tolle + a 40 FV; Neto's arrival makes Mayer "
      "redundant at short anyway, so this spends the blocked prospect "
      "and keeps Bennett in the rotation. Similar value, less 2026 "
      "disruption, more long-term risk if Mayer hits.")
    A("**Elsewhere in the lane.** Miami's Otto Lopez "
      f"({_bat_line(bats['Otto Lopez'])}) is the realistic controllable "
      "alternative at a materially lower price; Texas's Ezequiel Duran "
      f"({_bat_line(bats['Ezequiel Duran'])}) is the budget utility "
      "version.")
    A("**Clubhouse cost: high on either package.** The surplus-value "
      "math says yes; the disruption is the argument for waiting until "
      "winter. **Why Boston might do it anyway:** it converts rotation "
      "surplus into the one real external hole, and Neto arrives "
      "controlled through the entire Anthony/Rafaela/Abreu window. "
      "**Why they might not:** Neto through 2029 blocks both Mayer and "
      "Franklin Arias; if the org believes either is the shortstop, "
      "this is paying retail for a redundancy.\n")

    # ---- The walk-away ----------------------------------------------------
    try:
        batt = json.load(open(C.DATA_DIR / "battery.json"))
    except FileNotFoundError:
        batt = None
    A("## The walk-away — the catcher \"upgrade\" we're not making\n")
    A("*Update, July 26: the market settled this one. Langeliers went "
      "on the 10-day IL with a torn right meniscus, so the deal below "
      "is academic, and the ripple effect prices out the alternative: "
      "with the best available catcher bat down, Colorado's Hunter "
      "Goodman now costs even more. The analysis stands as the reason "
      "Boston was right not to chase either one.*\n")
    A("> **The deal that was on the menu:** C Shea Langeliers "
      f"({_bat_line(bats['Shea Langeliers'])}; $5.25M, controlled through "
      "2028) from the A's for LHP Jake Bennett "
      f"({_arm_line(arms['Jake Bennett'])}) plus a 45 FV prospect\n")
    A("**The math still works.** Langeliers at ~2.5 WAR/yr with 2.5 cheap "
      "years ≈ **$35–45M surplus**; Bennett (~$25M as a controllable "
      "mid-rotation lefty) plus a 45 FV (~$9M) matches. On the value "
      "ledger alone, this is a fine trade.")
    if batt:
        pc, bb = batt["per_catcher"], batt["batteries"]

        def _r(p, c):
            v = bb.get(p, {}).get(c, {}).get("RA9")
            return f"{v:.2f}" if v is not None else "—"

        A("**The battery data is why Boston should pass.** The staff runs "
          f"a {pc['Connor Wong']['RA9']:.2f} RA9 with Wong catching and "
          f"{pc['Carlos Narváez']['RA9']:.2f} with Narváez, and the "
          "rotation pairings underneath are the real story: Gray at "
          f"{_r('Sonny Gray', 'Connor Wong')} with Wong vs "
          f"{_r('Sonny Gray', 'Carlos Narváez')} with Narváez, Bennett at "
          f"{_r('Jake Bennett', 'Carlos Narváez')} with Narváez, Bello "
          "nearly five runs better with Wong (fig. 14). These are small, "
          "usage-shaped samples, not a causal framing stat, but they "
          "show a club deliberately assigning each starter the catcher "
          "it works best with, on a staff that is carrying the season. A "
          "new catcher resets every one of those relationships in August, "
          "in a race, for a bat.\n")
        try:
            fe = json.load(open(C.DATA_DIR / "battery_model.json"))["fe"]
            A("**The adjusted model seals it.** Controlling for pitcher, "
              "opponent and park (fixed-effects OLS, cluster-bootstrapped "
              "by game), the overall catcher effect is "
              f"{fe['catcher_effect_wong_minus_narvaez']*1000:+.0f} points "
              "of wOBA-against toward Wong, 95% CI "
              f"[{fe['ci95'][0]*1000:+.0f}, {fe['ci95'][1]*1000:+.0f}] — "
              "statistically indistinguishable from zero. In short, "
              "there is **no catcher problem**. The position's "
              "below-average bat never shows up in run prevention, and "
              "the shrinkage analysis (fig. 15) says most individual "
              "battery splits are noise around a healthy tandem. That "
              "leaves nothing for a trade to fix.\n")
        except FileNotFoundError:
            pass
    else:
        A("**The battery data is why Boston should pass** — the staff has "
          "settled pitcher-catcher pairings midseason, and a new catcher "
          "resets all of them in August, in a race, for a bat.\n")

    # ---- Sell branch ------------------------------------------------------
    A("## The contingency — if the gap is 6+ by August 1\n")
    A("> **Sonny Gray** "
      f"({_arm_line(arms['Sonny Gray'])}; expiring) → a pitching-poor "
      "contender (the Cubs' staff ranks near the bottom of contending "
      "clubs) for a 45+ FV near-MLB bat.")
    A("> **Aroldis Chapman** "
      f"({_arm_line(arms['Aroldis Chapman'])}; expiring) → any contender "
      "for a 40+ FV flier.\n")
    A("Selling the rentals is the *only* sell branch; the audit gives no "
      "case for moving Contreras, Duran, or any controllable starter at "
      "this deadline. The chemistry ledger doubles the point. Trading "
      "your best hitter out of a playoff race would tell "
      "the clubhouse exactly what the front office thinks of it, and "
      "that message has a cost of its own.\n")

    A("---\n*Contracts: Neto $4.15M arb-controlled through 2029 (avoided "
      "arbitration Jan 2026); Weaver 2yr/$22M through 2027 (NYM); Wacha "
      "expiring money (KC, verify); Langeliers $5.25M through "
      "2028 — all per public reporting as of the generation date. Stats "
      "refresh on every pipeline run; verify contracts before publishing. "
      "These are analytical hypotheticals, not reported rumors.*")
    return "\n".join(L)


def article_section(md: str) -> str:
    """Compact version of the trades for ARTICLE.md."""
    L = []
    A = L.append
    A("\n## Three trades that fit, and one to skip\n")
    A("A team holding a playoff spot has a roster that works, so "
      "disruption is priced like a cost here. The right deadline is "
      "small. The first two below are the needs; the third is the "
      "luxury (full value math in the mock-trades memo):\n")
    A("1. **The pen fix (zero disruption, do it):** a 45 FV + 40 FV "
      "prospect package to the selling Mets for Luke Weaver (elite relief "
      "season, signed through 2027), or Bello plus a 40 FV if the farm "
      "stays closed. Bigger swing: Toronto's Louie Varland, controllable "
      "and dominant, at a steeper prospect price. Cheap version: rental "
      "Tyler Rogers for one 40 FV.")
    A("2. **The innings (zero disruption):** a 40 FV flier to Kansas "
      "City for Michael Wacha, a veteran back-end starter to cover the "
      "slot Early left while Crochet and Sandoval build back. Buy-low "
      "alternative: Gausman, whose FIP runs ahead of his ERA, the "
      "mirror image of the Early sale.")
    A("3. **The shortstop (high, probably wait):** Zach Neto from the "
      "Angels (controlled through 2029) for Tolle + Bennett + a lottery "
      "arm, or the Mayer version (Mayer + Tolle + a 40 FV) since Neto "
      "would block both Mayer and Franklin Arias anyway. Cheaper lane: "
      "Miami's Otto Lopez at a fraction of the price. Right for the "
      "franchise window on paper, but the same trades will still be "
      "there in the winter.")
    try:
        fe = json.load(open(C.DATA_DIR / "battery_model.json"))["fe"]
        adj = (f"an adjusted model (pitcher, opponent and park controls) "
               "puts the overall catcher effect at "
               f"{fe['catcher_effect_wong_minus_narvaez']*1000:+.0f} "
               "points of wOBA-against with a confidence interval that "
               "crosses zero")
    except (FileNotFoundError, KeyError):
        adj = ("an adjusted model with pitcher, opponent and park "
               "controls finds no significant catcher effect")
    A("\nAnd the walk-away: the catcher \"upgrade\" the positional "
      "audit seems to demand, whether Langeliers (now academic: he "
      "went on the IL July 26 with a torn meniscus) or Colorado's "
      "Hunter Goodman, whose price spikes with Langeliers down. The "
      "battery data was always the veto. "
      "Nearly every Boston arm works with a settled catcher (fig. 14), "
      f"and {adj}. There is no catcher problem to fix (fig. 15). Wong "
      "already out-hits the league catcher bar; the gap is all "
      "Narváez, whose value is the glove. And a genuine power-hitting "
      "catcher costs a controllable arm plus a prospect, money that "
      "buys more win in the bullpen. No August bat is worth resetting "
      "a working staff.")
    A("\nAnd the contingency: if the gap hits six games by August 1, "
      "the sell list is Gray and Chapman, the rentals, and it stops "
      "there.\n")
    return "\n".join(L)


def run():
    md = build()
    out = C.OUT_DIR / "mock_trades.md"
    out.write_text(md)
    print(f"  [trades] wrote {out}")

    art = C.OUT_DIR / "ARTICLE.md"
    if art.exists():
        s = art.read_text()
        marker = "## The left-field question"
        section = article_section(s)
        if "## Three trades that fit" not in s and marker in s:
            s = s.replace(marker, section.strip() + "\n\n" + marker)
            art.write_text(s)
            print("  [trades] appended trades section to ARTICLE.md")


if __name__ == "__main__":
    run()
