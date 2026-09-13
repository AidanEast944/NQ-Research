"""
Runs the edge-decay check against every currently-live strategy, using their real backtested
trade history combined with live forward-testing results where available. Meant to be run
monthly, alongside run_scorecards.py, as part of the regular check-in routine.
"""
import sys
import json
sys.path.insert(0, "src")

from strategy import get_weekday_open_gap_signals_with_volume_from_archive, get_generic_pairs_signals_from_archive
from edge_decay_check import check_edge_decay, print_decay_report

print("=" * 60)
print("EDGE DECAY CHECK - run monthly, watch the trend across checks")
print("=" * 60)

configs = [
    ("Volume-Confirmed Gap NQ (1.2x)", "data/raw_nq_extended", 30, 40, 80, 2),
    ("Volume-Confirmed Gap YM (1.2x)", "data/raw_ym_extended", 30, 40, 80, 0.5),
    ("Volume-Confirmed Gap ES (1.2x, scaled)", "data/raw_es_extended", 6, 10, 20, 5),
]

for name, folder, min_gap, stop, target, point_value in configs:
    signals = get_weekday_open_gap_signals_with_volume_from_archive(
        data_folder=folder, min_gap_points=min_gap, stop_points=stop, target_points=target
    )
    filtered = signals[signals["volume_ratio"] >= 1.2].copy()
    result = check_edge_decay(filtered, entry_col="entry_price", date_col="date", point_value=point_value)
    print_decay_report(result, name)

pairs_configs = [
    ("NQ/ES Pairs", "data/raw_nq_extended", "data/raw_es_extended", 20, 50),
    ("NQ/YM Pairs", "data/raw_nq_extended", "data/raw_ym_extended", 20, 5),
    ("ES/YM Pairs", "data/raw_es_extended", "data/raw_ym_extended", 50, 5),
]

for name, folder_a, folder_b, pv_a, pv_b in pairs_configs:
    signals = get_generic_pairs_signals_from_archive(folder_a, folder_b, pv_a, pv_b)
    signals["signal"] = "LONG"
    signals["entry_price"] = 0
    signals["exit_price"] = signals["pnl_dollars"] * 0.1  # micro-sized, same as scorecard
    result = check_edge_decay(signals, entry_col="entry_price", exit_col="exit_price",
                                date_col="entry_date", point_value=1)
    print_decay_report(result, name)