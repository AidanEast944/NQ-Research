from strategy import (
    get_prior_day_break_signals_from_archive,
    get_prior_day_fade_signals_from_archive,
    get_trend_following_signals_from_archive,
    get_trend_following_atr_signals_from_archive,
)
from scorecard import run_scorecard

import sys
from datetime import date

output_file = f"results/scorecard_{date.today().isoformat()}.txt"
sys.stdout = open(output_file, "w")

run_scorecard(
    get_prior_day_break_signals_from_archive(stop_points=30, target_points=60),
    "Prior Day Breakout (30/60)",
    entry_col="Close", exit_col="exit_price", date_col="date"
)

run_scorecard(
    get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60),
    "Prior Day Fade (30/60)",
    entry_col="Close", exit_col="exit_price", date_col="date"
)

run_scorecard(
    get_trend_following_signals_from_archive(ma_period=5, stop_points=200),
    "Trend Following (5-day MA, 200pt stop)",
    entry_col="entry_price", exit_col="exit_price", date_col="entry_date"
)

run_scorecard(
    get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0),
    "Trend Following ATR (5-day MA, 1.0x ATR)",
    entry_col="entry_price", exit_col="exit_price", date_col="entry_date"
)


sys.stdout.close()
sys.stdout = sys.__stdout__
print(f"Scorecard saved to {output_file}")