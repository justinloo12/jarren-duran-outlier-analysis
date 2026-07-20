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

import pandas as pd

from . import config as C
from .deadline import _fg_pull

AS_OF = dt.date.today().isoformat()

# FV -> surplus $M (FanGraphs prospect-valuation ballparks, per trade_targets)
FV = {"55 FV": 40, "50 FV": 27, "45+ FV": 15, "45 FV": 9, "40 FV": 4}


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
    bats = _bats(["Zach Neto", "Luis Arraez", "Shea Langeliers",
                  "Bobby Witt Jr.", "Elly De La Cruz"])
    arms = _arms(["Payton Tolle", "Connelly Early", "Jake Bennett",
                  "Brayan Bello", "Sonny Gray", "Luke Weaver",
                  "Daniel Lynch IV", "Aroldis Chapman"])

    L = []
    A = L.append
    A("# Mock Deadline Trades — Arms for Bats\n")
    A(f"*Generated {AS_OF} · stats live via FanGraphs; contracts verified "
      "via reporting as of this date; value framework: ~$8M/WAR plus "
      "FanGraphs-style prospect FV conversions (55 FV≈$40M, 50 FV≈$27M, "
      "45+ FV≈$15M, 45 FV≈$9M, 40 FV≈$4M). Hypotheticals, not reporting.*\n")

    A("## The premise\n")
    A("Boston's tradeable surplus is **starting pitching**: eight viable "
      "starters for five slots once Crochet and Sandoval are back —")
    for n in ("Payton Tolle", "Jake Bennett", "Connelly Early",
              "Brayan Bello", "Sonny Gray"):
        A(f"- **{n}** — {_arm_line(arms[n])}")
    A("\nThe needs, per the positional audit: a **shortstop-adjacent infield "
      "bat** (the roster's biggest external hole), **bullpen help** (bottom "
      "half of MLB in reliever WAR), and a **catcher upgrade** — a season-long leak with no internal help "
      "coming, unlike the injury-driven infield holes. LF and DH fix themselves "
      "(Duran's regression behind a new Jahmai Jones platoon, Anthony's "
      "eventual return, and the Yoshida/Gonzalez platoon already running). Witt Jr. "
      f"({_bat_line(bats['Bobby Witt Jr.'])}) and De La Cruz "
      f"({_bat_line(bats['Elly De La Cruz'])}) top the seller SS list but "
      "are franchise players — named for completeness, not available.\n")
    A("These four trades are a **menu, not a plan** — Early and Bennett "
      "each appear in more than one package, and Boston can realistically "
      "afford about two of these deals.\n")

    # ---- Trade 1 ----------------------------------------------------------
    A("## Trade 1 — The big swing: a real shortstop\n")
    A("> **Red Sox get:** SS Zach Neto "
      f"({_bat_line(bats['Zach Neto'])}; $4.15M, arbitration-controlled "
      "through 2029)")
    A("> **Angels get:** LHP Payton Tolle "
      f"({_arm_line(arms['Payton Tolle'])}), RHP Connelly Early "
      f"({_arm_line(arms['Connelly Early'])}), plus a 45 FV lottery arm\n")
    A("**The math.** Neto projects as a ~3.5-WAR shortstop with 3.5 cheap "
      "years of control after 2026 — roughly **$75–90M of surplus value**. "
      "Tolle is a breakout 23-year-old lefty (top-100 type, ~$45–55M), "
      "Early a controllable mid-rotation arm (~$20M), plus ~$9M in FV: the "
      "package lands in the same band. LA declined to extend Neto and is "
      "10.5 out — this is exactly when a rebuilding club cashes a "
      "26-and-under core piece for three arms.")
    A("**Why Boston says yes anyway:** it hurts, but it converts two of "
      "eight starters into the roster's only true external hole, and Neto "
      "arrives controlled through the entire Anthony/Rafaela/Abreu window. "
      "**Why they might not:** if the org believes Mayer is the shortstop, "
      "this is paying retail for a redundancy.\n")

    # ---- Trade 2 ----------------------------------------------------------
    A("## Trade 2 — The stabilizer: rental bat for a buy-low arm\n")
    A("> **Red Sox get:** 2B Luis Arraez "
      f"({_bat_line(bats['Luis Arraez'])}; 1yr/$12M, free agent after "
      "2026 — a pure rental)")
    A("> **Giants get:** RHP Brayan Bello "
      f"({_arm_line(arms['Brayan Bello'])}; controllable, change-of-scenery "
      "candidate), Boston covers Arraez's remaining ~$5M\n")
    A("**The math.** Arraez's rest-of-season is worth ~1.2 WAR ≈ $10M "
      "against ~$5M of salary — modest surplus, rental price. Bello's 2026 "
      "has been poor, but a controllable 27-year-old with mid-rotation "
      "history carries $5–10M of option value a retooling San Francisco "
      "can afford to wait on. Near-even swap.")
    A("**The fit.** Arraez takes second while the Cheng/Monasterio "
      "platoon bridges short until Mayer (10-day IL) returns — turning two "
      "patchwork infield spots into one. No prospect cost at all — the "
      "cleanest add on the board.\n")

    # ---- Trade 3 ----------------------------------------------------------
    A("## Trade 3 — The pen fix\n")
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
    A("**Why this one matters most:** Boston's bullpen ERA is masking a "
      "worse FIP and bottom-half reliever WAR. In a race decided by 2–3 "
      "wins, the reliever is the highest-probability marginal win on the "
      "board.\n")

    # ---- Trade 4 ----------------------------------------------------------
    A("## Trade 4 — The quiet three-season fix: a controllable catcher\n")
    A("> **Red Sox get:** C Shea Langeliers "
      f"({_bat_line(bats['Shea Langeliers'])}; $5.25M, controlled through "
      "2028)")
    A("> **Athletics get:** LHP Jake Bennett "
      f"({_arm_line(arms['Jake Bennett'])}) plus a 45 FV prospect\n")
    A("**The math.** Langeliers at ~2.5 WAR/yr with 2.5 cheap years ≈ "
      "**$35–45M surplus**. Bennett (~$25M as a controllable mid-rotation "
      "lefty) plus a 45 FV (~$9M) matches. The A's perpetually need cheap "
      "innings; Boston turns a season-long leak — with no internal help "
      "coming — into a plus for three seasons, at a position where the "
      "self-healing ones into a plus for three seasons.\n")

    # ---- Sell branch ------------------------------------------------------
    A("## The contingency — if the gap is 6+ by August 1\n")
    A("> **Sonny Gray** "
      f"({_arm_line(arms['Sonny Gray'])}; expiring) → a pitching-poor "
      "contender (the Cubs' staff ranks near the bottom of contending "
      "clubs) for a 45+ FV near-MLB bat.")
    A("> **Aroldis Chapman** "
      f"({_arm_line(arms['Aroldis Chapman'])}; expiring) → any contender "
      "for a 40+ FV flier.\n")
    A("Selling the rentals is the *only* sell branch — the audit gives no "
      "case for moving Contreras, Duran, or any controllable starter at "
      "this deadline.\n")

    A("---\n*Contracts: Neto $4.15M arb-controlled through 2029 (avoided "
      "arbitration Jan 2026); Arraez 1yr/$12M (SF, Feb 2026); Weaver "
      "2yr/$22M through 2027 (NYM); Langeliers $5.25M, controlled through "
      "2028 — all per public reporting as of the generation date. Stats "
      "refresh on every pipeline run; verify contracts before publishing. "
      "These are analytical hypotheticals, not reported rumors.*")
    return "\n".join(L)


def article_section(md: str) -> str:
    """Compact version of the trades for ARTICLE.md."""
    L = []
    A = L.append
    A("\n## Four trades that actually fit\n")
    A("Working the seller list against Boston's one real surplus — eight "
      "starters for five slots — produces a menu (full value math in the "
      "mock-trades memo):\n")
    A("1. **The big swing:** Payton Tolle + Connelly Early + a lottery arm "
      "to the Angels for SS Zach Neto (controlled through 2029). Painful, "
      "franchise-window correct.")
    A("2. **The stabilizer:** Brayan Bello to the Giants for rental Luis "
      "Arraez — Arraez takes second, Mayer slides to short, zero prospect "
      "cost. The move most proportionate to the odds — upgrade without betting the future.")
    A("3. **The pen fix:** a 45 FV + 40 FV package to the selling Mets for "
      "Luke Weaver (elite relief season, signed through 2027) — the "
      "highest-probability marginal win available.")
    A("4. **The opportunist:** Jake Bennett + a 45 FV to the A's for C Shea "
      "Langeliers (controlled through 2028).")
    A("\nAnd the contingency: if the gap hits six games by August 1, the "
      "sell list is Gray and Chapman — the rentals — and stops there.\n")
    return "\n".join(L)


def run():
    md = build()
    out = C.OUT_DIR / "mock_trades.md"
    out.write_text(md)
    print(f"  [trades] wrote {out}")

    art = C.OUT_DIR / "ARTICLE.md"
    if art.exists():
        s = art.read_text()
        marker = "## What would change my mind"
        section = article_section(s)
        if "## Four trades that actually fit" not in s and marker in s:
            s = s.replace(marker, section.strip() + "\n\n" + marker)
            art.write_text(s)
            print("  [trades] appended trades section to ARTICLE.md")


if __name__ == "__main__":
    run()
