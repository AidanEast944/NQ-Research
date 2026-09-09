from strategy import (
    get_prior_day_break_signals_from_archive,
    get_prior_day_fade_signals_from_archive,
    get_trend_following_signals_from_archive,
    get_trend_following_atr_signals_from_archive,
)
from walk_forward import walk_forward_test

walk_forward_test(
    get_prior_day_break_signals_from_archive(stop_points=30, target_points=60),
    "Prior Day Breakout (30/60)", entry_col="Close", date_col="date"
)

walk_forward_test(
    get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60),
    "Prior Day Fade (30/60)", entry_col="Close", date_col="date"
)

walk_forward_test(
    get_trend_following_signals_from_archive(ma_period=5, stop_points=200),
    "Trend Following (5-day MA, 200pt)", date_col="entry_date", num_windows=3
)

walk_forward_test(
    get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0),
    "Trend Following ATR (5-day MA, 1.0x)", date_col="entry_date", num_windows=3
)