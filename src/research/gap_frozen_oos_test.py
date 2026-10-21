"""
PRE-REGISTERED frozen-rules out-of-sample test of the gap strategies on history BEFORE 2024-01-01.
Written and committed BEFORE the older data exists on disk - nothing here may be tuned afterward.

FROZEN RULES (identical to the live scripts; no parameter is allowed to change):
  NQ (MNQ $2/pt):  min gap 30, stop 40, target 80   YM (MYM $0.5/pt): 30 / 40 / 80
  ES (MES $5/pt):  min gap 6,  stop 10, target 20
  Entry 08:30 ET bar open vs prior day close, continuation direction, exit by 16:00.
  Volume filter: 08:30 bar volume >= 1.2x trailing-20-day average (the live threshold).

TRIALS DECLARED UP FRONT: 6 scorecards = {NQ, ES, YM} x {unfiltered, volume >= 1.2x}.
The 1.5x threshold is printed DESCRIPTIVELY only (no scorecard, not counted as a trial).
num_trials passed to the DSR = max(trial_count, 68) + 6.

PASS CRITERIA (set in advance): a market "holds up" if the older-history profit factor after
costs is >= 1.10 on >= 100 trades. Volume-confirmation "adds value" only if its PF beats the
unfiltered PF on at least 2 of 3 markets. Anything else is reported as not confirmed - including
a sub-1.0 result, which would be evidence the 2024-26 edge is regime-specific.

Run (after the backfill has landed):
    cd ~/nq-research && source venv/bin/activate && python3 src/research/gap_frozen_oos_test.py
"""
import sys
import os
import pandas as pd

sys.path.insert(0, "src")
import strategy
import scorecard
import trial_count

CUTOFF = pd.Timestamp("2024-01-01")
MARKETS = {
    "NQ": dict(folder="data/raw_nq_extended", min_gap=30, stop=40, target=80, pv=2),
    "ES": dict(folder="data/raw_es_extended", min_gap=6, stop=10, target=20, pv=5),
    "YM": dict(folder="data/raw_ym_extended", min_gap=30, stop=40, target=80, pv=0.5),
}
N_NEW_TRIALS = 6


def pf(points_dollars):
    w = points_dollars[points_dollars > 0].sum()
    l = -points_dollars[points_dollars < 0].sum()
    return w / l if l > 0 else float("nan")


if __name__ == "__main__":
    num_trials = max(trial_count.count_research_trials(), 68) + N_NEW_TRIALS
    print(f"num_trials (DSR) = {num_trials}\n")
    summary = []
    for mkt, p in MARKETS.items():
        sigs = strategy.get_weekday_open_gap_signals_with_volume_from_archive(
            min_gap_points=p["min_gap"], stop_points=p["stop"], target_points=p["target"],
            data_folder=p["folder"], volume_lookback=20)
        sigs["entry_date"] = pd.to_datetime(sigs["date"])
        old = sigs[sigs["entry_date"] < CUTOFF].copy()
        if old.empty:
            print(f"{mkt}: no pre-2024 trades found - run the backfill first.")
            continue
        print(f"{mkt}: {len(old)} unfiltered trades, {old['entry_date'].min().date()} -> {old['entry_date'].max().date()}")
        for thr in (1.5,):
            sub = old[old["volume_ratio"] >= thr]
            sgn = (sub["exit_price"] - sub["entry_price"]).where(sub["signal"] == "LONG",
                                                                  sub["entry_price"] - sub["exit_price"])
            print(f"   (descriptive only) volume >= {thr}x: {len(sub)} trades, gross PF {pf(sgn):.2f}")
        for label, df in (("unfiltered", old), ("vol>=1.2x", old[old["volume_ratio"] >= 1.2])):
            name = f"{mkt} gap {label} (pre-2024, frozen)"
            if len(df) == 0:
                continue
            res = scorecard.run_scorecard(df.reset_index(drop=True), name, num_trials=num_trials,
                                          account_size=10000, point_value=p["pv"],
                                          date_col="entry_date")
            summary.append((mkt, label, len(df)))
    print("\nReminder: judge ONLY against the pass criteria in this file's docstring.")
