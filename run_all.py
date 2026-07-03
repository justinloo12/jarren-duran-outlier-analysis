#!/usr/bin/env python3
"""End-to-end pipeline: fetch -> metrics -> analyze -> age curve -> viz -> memo.

Usage:
    python run_all.py                # full run (pulls data if missing)
    python run_all.py --no-fetch     # reuse saved CSVs, just re-analyze
    python run_all.py --fetch-only   # only pull + cache raw data
"""
from __future__ import annotations

import argparse
import sys

from src import config as C
from src import fetch_fangraphs, fetch_statcast, fetch_milb
from src import fetch_cohort
from src import (statcast_metrics, analysis, age_curve, viz, memo, comps,
                 outfield_plan, trade_targets)


def fetch():
    print("== Fetch: FanGraphs season tables ==")
    fetch_fangraphs.fetch_all()
    print("== Fetch: Statcast pitch-level + expected stats ==")
    fetch_statcast.fetch_all()
    print("== Fetch: MLB + MiLB track record ==")
    fetch_milb.fetch_all()
    print("== Fetch: Red Sox + league OF cohorts ==")
    fetch_cohort.fetch()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true",
                    help="reuse cached CSVs, skip network pulls")
    ap.add_argument("--fetch-only", action="store_true")
    args = ap.parse_args()

    if not args.no_fetch:
        fetch()
    if args.fetch_only:
        return

    print("== Compute Statcast season metrics ==")
    statcast_metrics.build()
    print("== Run analysis (outlier tests, baselines, consistency) ==")
    analysis.run()
    print("== Aging-curve context ==")
    age_curve.run()
    print("== Visualizations ==")
    viz.run()
    print("== Decision memo ==")
    memo.run()
    print("== Peer & salary comparison ==")
    comps.run()
    print("== Outfield-jam plan ==")
    outfield_plan.run()
    print("== Trade value & best-fit partners ==")
    trade_targets.run()

    print(f"\nDone. Data -> {C.DATA_DIR}\nFigures -> {C.FIG_DIR}\n"
          f"Memo -> {C.OUT_DIR / 'decision_memo.md'}")


if __name__ == "__main__":
    sys.exit(main())
