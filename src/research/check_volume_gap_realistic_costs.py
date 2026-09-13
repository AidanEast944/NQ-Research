import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy import get_weekday_open_gap_signals_with_volume_from_archive
from scorecard import run_scorecard

configs = [
    ("Volume-Confirmed Gap NQ (1.2x, realistic MNQ costs)", "data/raw_nq_extended", 30, 40, 80, 2, 0.5, 0.74),
    ("Volume-Confirmed Gap YM (1.2x, realistic MYM costs)", "data/raw_ym_extended", 30, 40, 80, 0.5, 0.5, 0.74),
    ("Volume-Confirmed Gap ES (1.2x, realistic MES costs)", "data/raw_es_extended", 6, 10, 20, 5, 0.25, 0.74),
]

for name, folder, min_gap, stop, target, point_value, slippage_pts, commission in configs:
    signals = get_weekday_open_gap_signals_with_volume_from_archive(
        data_folder=folder, min_gap_points=min_gap, stop_points=stop, target_points=target
    )
    filtered = signals[signals["volume_ratio"] >= 1.2].copy()

    run_scorecard(
        filtered,
        name,
        entry_col="entry_price",
        date_col="date",
        point_value=point_value,
        slippage_points=slippage_pts,
        commission=commission,
        num_trials=41
    )