# The Quad-A Audit — the surge's supporting cast, vs their own careers

*Cohort: 2026 Red Sox with a real role (40+ PA / 15+ IP) and a thin MLB track record entering the year (hitters < 1,000 career PA, pitchers < 250 career IP, age 24+). Career baselines from MLB StatsAPI year-by-year; process checks from pitch-level Statcast.*

**Headline:** 5 players currently on the roster fit the profile. Together they account for **+1.3 WAR** in 2026. Of the 3 with prior MLB seasons, **1 is running a career best**, and the other 2 are rookies with no MLB baseline at all. Depth like this is why the surge happened; counting on it to repeat is how deadline mistakes get made.

**The base rate (2016-2025):** 100 hitters and 198 relievers matched this profile with a career-best first half. The median kept 39% of the surge; 34% of hitters and 37% of relievers fell back to career level in the second half. Full design in `src/aaaa_backtest.py`, figure 20.

## Regulars running hot (same 40-point screen)

| Player | Age | 2026 PA | wRC+ | 2026 OPS | Career OPS | Delta | Career high? |
|---|---:|---:|---:|---:|---:|---:|:--|
| Willson Contreras | 34 | 396 | 158 | 0.941 | 0.811 | +0.130 | yes |
| Ceddanne Rafaela | 25 | 406 | 108 | 0.761 | 0.685 | +0.076 | yes |

## Hitters

| Player | Age | 2026 PA | wRC+ | OPS | Career OPS | Best (yr) | wOBA−xwOBA | Career high? |
|---|---:|---:|---:|---:|---:|---:|---:|:--|
| Anthony Seigler | 27 | 115 | 112 | 0.775 | 0.502 | rookie season | -7 | first MLB season |
| Andruw Monasterio | 29 | 187 | 101 | 0.743 | 0.671 | 0.756 (2025) | +17 | no |
| Tsung-Che Cheng | 24 | 44 | 68 | 0.600 | — | rookie season | -27 | first MLB season |

## Pitchers

| Player | Age | 2026 IP | ERA | FIP | Career ERA | Best (yr) | xwOBA−wOBA against | Career best? |
|---|---:|---:|---:|---:|---:|---:|---:|:--|
| Tayron Guerrero | 35 | 23.0 | 2.35 | 2.32 | 5.77 | 5.43 (2018) | -35 | **YES** |
| Jovani Moran | 29 | 42.1 | 2.76 | 3.84 | 4.26 | 2.21 (2022) | +5 | no |

*Positive wOBA−xwOBA = results ahead of contact quality (regression risk). For pitchers, positive xwOBA−wOBA against = allowing weaker results than the contact deserves (same risk, run-prevention side).*

![Quad-A audit](../figures/17_aaaa_audit.png)
