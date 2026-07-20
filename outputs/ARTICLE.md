# The Red Sox Won 13 Straight. Now Comes the Hard Part

### A trade-deadline case study: the run differential saw the streak coming — and says buy

*Deadline runway, 2026 · data through 2026-07-19 · full methods, code and figures at the end*

---

The Red Sox are the hottest team in baseball — winners of **13 straight**, the longest run in the majors this season. Three weeks ago they were well under .500 and the easy take wrote itself: sell. Today they are 50-48, and **Boston currently holds the final wild-card spot**.

Here is the part the streak did not change: the math saw it coming. Boston has outscored its opponents by **+45** runs — a Pythagorean .553 team that spent three months wearing a .510 record. Hot streaks are usually where analysis goes to die. This one is different, because it isn't a lucky team getting hot — it's an unlucky team's record catching up to its run differential. In 10,000 simulations of the rest of the season, Boston makes the playoffs **75%** of the time.

![AL playoff race](figures/12_playoff_race.png)

That's a bona fide playoff team — one the standings have only just begun to reflect. So the deadline question is no longer whether to sell — it's what a team like this should buy. And the roster's biggest open question — what to do with Jarren Duran — turns out to be the whole season in miniature: **the team is its left fielder — the process is better than the results.** We'll get to him. First, the money question.

## So: buy or sell?

**BUY.** At ~75% odds, a marginal win is worth real assets — the fire-sale case is dead, and even the sell-the-vets hedge should wait. But buy like the math, not like a panic: targeted, controllable additions at the actual holes, not rental splurges. And one constraint sits over every deal: **don't disturb the room.** A 13-game streak is the sound of a clubhouse that works, and chemistry is a real asset that never shows up in a WAR column — so additions should cost prospects before they cost big-leaguers, and fill empty spots before occupied ones. Which is why the right version of this deadline is deliberately **small**: the roster's biggest upgrades — Anthony, Mayer, Story, Casas, Duran's own regression — are already in-house and free. The decision tree by asset:

- **Hold Duran through the deadline.** His trade value sits at its nadir while his underlying profile says the market is under-pricing him (the full case is a chapter below). Sophisticated buyers read xstats too — you will not get 2024 prices in August 2026. Revisit in the winter, after the rebound has (or hasn't) shown up on the field.
- **Keep the young outfield** (Anthony, Rafaela, Abreu) and the rotation — they are the 2027 team.
- **Keep the expiring veterans** (Gray, Chapman, Contreras were the winter's reported trade names) — they are playoff innings and playoff at-bats now, and the veteran spine of the room that just won 13 straight. The sell branch reopens only if the gap blows out before August 1.
- **Absorb Yoshida.** Negative trade value; paying to escape it burns real prospects to save sunk money.

## And if they buy — where? Not where you'd think

![Positional audit](figures/13_positional_audit.png)

Auditing every position against league average (PA-weighted wRC+) reorders the shopping list:

- **The biggest hole on the roster is left field (-31 wRC+ vs league) — which is the Duran slump itself.** Boston's best deadline additions are internal and nearly free: Duran's batted-ball luck regressing to normal — the club is already sheltering him in a platoon with new right-handed pickup Jahmai Jones — a zero-cost reclamation bet whose elite 2025 line against lefties (.426 wOBA, backed by a .405 xwOBA) collapsed to .272 this year, though even that came with a .327 xwOBA. Boston, fittingly, acquired another hitter running under his contact quality — and Roman Anthony's eventual return, though he is still rehabbing without a firm date. A team that trades for an outfielder here would be buying what it already owns.
- **Shortstop (-18) is the one true external target — with an asterisk: half the infield is hurt** (Mayer, Story, Kiner-Falefa; Casas at first). A Cheng/Monasterio platoon is bridging short, and Boston's DH fix is already running (Yoshida platooning with Romy Gonzalez). A cheap, controllable infield stabilizer is still the highest-leverage add; the internal returns are the fallback, not the plan.
- **Catcher (-11) looks like a hole — and is the trap.** The Narváez/Wong bats are below the position's league average, but the battery data says leave the tandem alone: the staff runs a 3.47 RA9 with Wong and 4.17 with Narváez, and the club is quietly running an assignment system — Gray at 1.86 with Wong (4.40 with Narváez), Bennett at 1.12 with Narváez, Bello five runs better with Wong, and the leverage relievers sharper with Narváez (fig. 14). Small, usage-confounded samples — but that is working pitcher-catcher chemistry, and a mid-race catcher trade would rip up every one of those pairings for a bat.
- **The bullpen is the quiet weakness.** Its ERA ranks 6th, but its FIP ranks 12th and its WAR 14th — the ERA is flattering it. One reliever is the cheapest marginal win at any deadline.
- **And the awkward one: the reported sell candidate is their best hitter.** Willson Contreras carries a 142 wRC+ at first base. Moving him while holding a playoff spot isn't a retool — it's surrender priced as prudence.

![Battery map](figures/14_battery_map.png)

## Three trades that fit — and the one to walk away from

A team that just won 13 straight has a clubhouse that is working, so disruption gets priced like a cost — and the honest conclusion is that **the right deadline here is small**. The menu, ordered from least to most disturbance (full value math in the mock-trades memo):

1. **The pen fix (zero disruption — do it):** a 45 FV + 40 FV prospect package to the selling Mets for Luke Weaver (elite relief season, signed through 2027). Nobody in the room loses a job or an inning — and it's the highest-probability marginal win available.
2. **The stabilizer (moderate — if the price holds):** Brayan Bello to the Giants for rental Luis Arraez — zero prospect cost, and Arraez fills a patchwork platoon spot rather than displacing a hot regular. The first deal that subtracts from the active roster.
3. **The big swing (high — probably wait):** Payton Tolle + Connelly Early + a lottery arm to the Angels for SS Zach Neto (controlled through 2029). Franchise-window correct on paper — but it pulls two arms out of a winning rotation mid-streak, and the same trade will still be there in the winter.

And the walk-away: the Langeliers catcher "upgrade" that the positional audit seems to demand. The battery map (fig. 14) is the veto — Gray runs a 1.86 RA9 with Wong, Bennett a 1.12 with Narváez, and nearly every Boston arm has a clear preferred catcher. That's a working assignment system in the middle of a streak built on run prevention, and no August bat is worth resetting it.

And the contingency: if the gap hits six games by August 1, the sell list is Gray and Chapman — the rentals — and stops there.

## The left fielder: the whole season in one player

The biggest hole on the roster is the Duran slump — which makes the biggest deadline call a diagnosis, not a trade. The full workup, in four findings:

**1. His 2024 breakout was real — a peak in every phase.** The All-Star year (wRC+ 131) came with career-best swing decisions, career-best baserunning (+8.3 runs) and a defensive spike (+7.6). His xwOBA (.340) was legitimate. Results outran contact quality by just 17 points of wOBA — and once you credit the points his speed adds over Statcast expectations in his other seasons (xstats ignore sprint speed), the true luck component lands between 5 and 14 points. 2024 was his peak, mildly gilded — not a mirage.

**2. His 2026 collapse is part erosion, mostly bad luck.** The wRC+ (60) looks like a career ending. But his wOBA (.263) sits *below* his xwOBA (.293) — and for a burner who normally beats his xstats, running negative is a 34-to-43-point anomaly against his own baseline. His BABIP (.244) is 67 points under what his contact quality supports. Real erosion exists — chase, whiff and hard-hit rate all moved the wrong way — but no injury has been reported, and his speed, baserunning and defense remain plus. The legs a buyer would pay for are intact.

**3. It isn't Fenway.** His career wOBA−xwOBA gap is +19 points at home and +19 on the road — essentially identical. The skill travels. 2024's overperformance was actually *road*-concentrated (+50 vs +14), the opposite of a Monster-driven fluke.

**4. His true level is the 2023–25 plateau (~110–120 wRC+).** Aging explains ~7 points of the 70-point fall from 2024; regression from a lucky peak plus a 2026 bad-luck tail explains the rest.

![BABIP by season](figures/01_babip_vs_league.png)

Which is the same shape as the team's season: results below process, market ready to misprice it. The biggest hole on the roster is the one no trade can fix — and none needs to.

## What would change my mind

- A 2026 second-half BABIP rebound with flat chase/whiff → the luck thesis confirmed; extend-or-hold gets stronger.
- Chase% and whiff% still elevated through September → the erosion is real; sell next winter at whatever the market bears.
- The wild-card gap at 6+ by August 1 → flip the expiring vets and call it a retool, not a teardown.

---

*Methods: park-adjusted wRC+ for all talent comparisons; luck measured against Duran's own career wOBA−xwOBA gap (Statcast xstats ignore sprint speed); venue splits from pitch-level Statcast; playoff odds from a 10,000-run Monte Carlo (Pythagorean talent, regressed, no schedule effects); ~a dozen significance tests reported without family-wise correction — isolated p≈.03–.05 findings are directional. Data: Baseball Savant (pybaseball), FanGraphs, MLB Stats API; salaries via Spotrac. Full reproducible pipeline: `python run_all.py`.*