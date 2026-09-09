from strategy import (
    get_prior_day_break_signals_from_archive,
    get_prior_day_fade_signals_from_archive,
    get_trend_following_signals_from_archive,
    get_trend_following_atr_signals_from_archive,
)
from scorecard import run_scorecard
from walk_forward import walk_forward_test

FOLDER = "data/raw_nq_extended"

print("\n\n" + "#" * 60)
print("# TESTING ON EXTENDED ARCHIVE (833 days, 2024-2026)")
print("#" * 60)

strategies = [
    ("Prior Day Breakout (30/60)",
     lambda: get_prior_day_break_signals_from_archive(stop_points=30, target_points=60, data_folder=FOLDER),
     "Close", "date"),
    ("Prior Day Fade (30/60)",
     lambda: get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60, data_folder=FOLDER),
     "Close", "date"),
    ("Trend Following (5-day MA, 200pt)",
     lambda: get_trend_following_signals_from_archive(ma_period=5, stop_points=200, data_folder=FOLDER),
     "entry_price", "entry_date"),
    ("Trend Following ATR (5-day MA, 1.0x)",
     lambda: get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0, data_folder=FOLDER),
     "entry_price", "entry_date"),
]

for name, get_signals, entry_col, date_col in strategies:
    signals = get_signals()
    run_scorecard(signals, name, entry_col=entry_col, date_col=date_col)
    walk_forward_test(get_signals(), name, entry_col=entry_col, date_col=date_col, num_windows=6)