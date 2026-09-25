import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy import get_weekday_open_gap_signals_with_volume_from_archive
from scorecard import run_scorecard
from trial_count import count_research_trials

# Same three legs/configs as check_volume_gap_realistic_costs.py and check_volume_gap_dsr.py
# (the scripts that produced the currently-live 1.2x numbers in results/scorecard_2026-09-20.txt),
# but at the LOOSEST threshold from Entry 25's original 3-way sweep (1.0x) instead of the middle
# cut (1.2x) that was actually picked for live tracking. Entry 25 only ever printed basic
# full_stats() for 1.0x/1.5x (gross PF, trade count) - this is the first time the FULL
# standardized scorecard (walk-forward, realistic per-instrument costs, honest DSR) has been run
# at 1.0x, to see whether the extra trade frequency survives the same rigor the 1.2x definition
# already cleared.
configs = [
    ("Volume-Confirmed Gap NQ (1.0x, realistic MNQ costs)", "data/raw_nq_extended", 30, 40, 80, 2, 0.5, 0.74),
    ("Volume-Confirmed Gap YM (1.0x, realistic MYM costs)", "data/raw_ym_extended", 30, 40, 80, 0.5, 0.5, 0.74),
    ("Volume-Confirmed Gap ES (1.0x, realistic MES costs)", "data/raw_es_extended", 6, 10, 20, 5, 0.25, 0.74),
]

for name, folder, min_gap, stop, target, point_value, slippage_pts, commission in configs:
    signals = get_weekday_open_gap_signals_with_volume_from_archive(
        data_folder=folder, min_gap_points=min_gap, stop_points=stop, target_points=target
    )
    filtered = signals[signals["volume_ratio"] >= 1.0].copy()

    run_scorecard(
        filtered,
        name,
        entry_col="entry_price",
        date_col="date",
        point_value=point_value,
        slippage_points=slippage_pts,
        commission=commission,
        num_trials=count_research_trials()
    )
