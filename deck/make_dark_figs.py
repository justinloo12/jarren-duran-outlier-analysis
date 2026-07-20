#!/usr/bin/env python3
"""Re-render every figure the deck embeds in dark mode -> figures/dark/.

Canonical light figures (used by the article, HTML pack and memos) are left
untouched; the deck's image() helper prefers figures/dark/ when present.
Run after `run_all.py` so the saved data artifacts are fresh.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config as C
from src import style as S

DARK_DIR = C.FIG_DIR / "dark"
DARK_DIR.mkdir(exist_ok=True)

# All fig functions save to C.FIG_DIR — repoint it, then switch the palette.
# NOTE: modules call S.apply() at import time, so import FIRST, then go dark.
C.FIG_DIR = DARK_DIR
from src import viz, deadline, trade_targets, rebound_sim, erosion  # noqa: E402

S.apply_dark()

# 01-04 (deck uses 01 and 04)
viz.run()

# 08 trade fits
fits = pd.read_csv(C.DATA_DIR / "trade_fits.csv")
trade_targets.fig_fits(fits)
print("  [dark] 08_trade_fit_targets")

# 12 race + 13 positional audit
sim = pd.read_csv(C.DATA_DIR / "al_race_sim.csv")
deadline.fig_race(sim)
aud = pd.read_csv(C.DATA_DIR / "positional_audit.csv")
deadline.fig_positions(aud)
print("  [dark] 12_playoff_race, 13_positional_audit")

# 09 rebound + 10 erosion — their fig() needs in-memory draws, so re-run
# the (local, cached-data) computations with the dark palette active.
rebound_sim.run()
erosion.run()
print("  [dark] 09_rebound_probability, 10_erosion_decomposition")

print(f"dark figures -> {DARK_DIR}")
