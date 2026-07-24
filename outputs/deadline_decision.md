# Deadline Decision — Should the Red Sox Buy or Sell?

*Generated 2026-07-23 · standings via MLB Stats API · simulation details in the method note.*

## The verdict: **BUY** — clear buyer

- Record **52-49** (.515) but run differential **+45** — a Pythagorean **.551** team underperforming its runs by ~4 wins.
- Boston currently holds the final wild-card spot in a congested, weak race — riding a L1 streak.
- Simulated playoff odds: **77%** (10,000 sims; talent = run-diff-based, regressed).

> **The team is its left fielder.** The same results-vs-process gap that defines Duran's 2026 defines the roster: a top-10 rotation and a positive run differential producing a losing record. Process says this team is better than its line. That is precisely the profile you do not fire-sale at the bottom.

## What that means by asset

| Asset class | Action | Why |
|---|---|---|
| Duran | **Hold through deadline** | value at its nadir; xstats and venue splits say the market is under-pricing him; revisit in winter |
| Young OF core (Anthony/Rafaela/Abreu) | **Keep** | the 2027 outfield |
| Expiring vets (reported: Gray, Chapman, Contreras) | **Sell only if out of it by Aug 1** | rentals with real deadline markets; the one true sell-now inventory |
| Yoshida | **Keep/absorb** | bat above average in 2026; contract still immovable |
| Rotation | **Do not trade from it** | it is the reason the odds are alive |

## If they buy: where the roster actually leaks runs

PA-weighted wRC+ by position vs. league average (see figure 10; position filter counts a player's full line at each position he qualifies for — a standard approximation):

| Pos | BOS | Lg | Gap | Primary occupants |
|-----|----:|---:|----:|---|
| LF | 68 | 100 | -32 | Jarren Duran, Roman Anthony |
| SS | 74 | 94 | -20 | Marcelo Mayer, Andruw Monasterio |
| DH | 89 | 108 | -19 | Masataka Yoshida, Roman Anthony |
| C | 74 | 89 | -15 | Carlos Narvaez, Connor Wong |
| 2B | 86 | 94 | -9 | Marcelo Mayer, Andruw Monasterio |
| 3B | 91 | 99 | -8 | Caleb Durbin, Nick Sogard |
| RF | 112 | 99 | +13 | Wilyer Abreu |
| CF | 108 | 93 | +14 | Ceddanne Rafaela |
| 1B | 146 | 113 | +32 | Willson Contreras, Romy Gonzalez |

Pitching units: rotation ERA ranks **5th** (3.61) and WAR 6th — a real strength. The bullpen's ERA ranks 5th but its FIP ranks 11th and WAR 14th — **the ERA is flattering it**; this is the quiet weakness.

> **Reading the audit:**
> - **The biggest hole is LF (-32) — which is the Duran slump itself.** The best 'deadline additions' are internal and cheap: Duran's positive regression — now sheltered by a platoon with new RHB pickup Jahmai Jones (Detroit, 7/14 — a reclamation bet: .426 wOBA vs LHP in 2025 but .272 in 2026, albeit with a .327 xwOBA) — and Roman Anthony's eventual return (still rehabbing, no firm date).
> - **DH (-19) is a positional-bar problem, not a Yoshida problem.** Yoshida himself has been above league average with one of the lowest strikeout rates in baseball; the gap comes from the high league DH bar and the non-Yoshida PAs at the spot. Gonzalez covers the tough lefties. No move needed.
> - **SS (-20) is the one true external target — with a caveat: half the infield is on the IL** (Mayer 10-day, Story 60-day, Kiner-Falefa 10-day; Casas 60-day at 1B). A Tsung-Che Cheng / Andruw Monasterio platoon is bridging short. A stabilizing infield bat is still the highest-leverage add, but internal returns shrink the urgency.
> - **Catcher (-15) is the sneaky third add** — below league average at the position all season, with no internal help coming (unlike the infield). A controllable upgrade is a three-season fix, not a rental.
> - **A bullpen arm is the classic fringe-buyer move**: relievers are the cheapest marginal wins at the deadline, and the FIP-ERA gap says this pen will regress without help.
> - **The Contreras tension:** the reported sell candidate is Boston's *best hitter* (146 wRC+ at 1B). Selling him only makes sense in the full-sell branch — moving him from a live playoff race would be self-defeating.

## Is Duran's rebound visible yet? (2026 by month)

| Month | PA | wOBA | xwOBA |
|-------|---:|-----:|------:|
| Apr | 90 | 0.205 | 0.266 |
| May | 130 | 0.375 | 0.345 |
| Jun | 100 | 0.176 | 0.222 |
| Jul | 63 | 0.252 | 0.347 |

> Getting warmer. May was a full month of the 2024–25 player (.375 wOBA), April and June were bad on both results and contact quality — and July's contact quality (a .347 xwOBA over 63 PA, vs .252 results) has surged with the team's streak while the results *still* lag it. The pattern holds: the skills flicker, the luck stays bad. This volatility is exactly why the deadline is the wrong time to price him.

## AL race snapshot

| Team | W-L | RD | WC GB | Odds |
|------|-----|---:|------:|-----:|
| Yankees | 57-45 | +88 | +4.5 | 99% |
| Rays | 59-43 | +30 | - | 98% |
| White Sox | 54-47 | +44 | - | 88% |
| Red Sox | 52-49 | +45 | - | 77% |
| Mariners | 51-52 | +17 | 2.0 | 60% |
| Guardians | 54-50 | -6 | +0.5 | 57% |
| Rangers | 51-51 | -30 | - | 38% |
| Tigers | 49-54 | +29 | 4.0 | 27% |
| Orioles | 50-53 | -13 | 3.0 | 19% |
| Twins | 51-53 | -30 | 2.5 | 18% |
| Astros | 50-54 | -45 | 3.5 | 17% |
| Blue Jays | 47-56 | -61 | 6.0 | 1% |

---
*Method:* team talent = Pythagorean win% (exponent 1.83) regressed toward .500 with 35 games of shrinkage; 10,000 Monte Carlo seasons; remaining games simulated as independent binomials (no schedule, injuries, or deadline moves — a simplification that slightly compresses odds toward the pack). Reported trade candidates per Boston media (NBC Sports Boston, July 2026). Re-run `python run_all.py` before publishing to refresh.