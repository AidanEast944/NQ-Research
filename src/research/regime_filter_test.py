from strategy import get_trend_following_signals_from_archive, get_regime_filtered_trend_signals_from_archive
from walk_forward import walk_forward_test
from scorecard import run_scorecard

print("BASELINE (no regime filter):")
baseline = get_trend_following_signals_from_archive(ma_period=5, stop_points=200)
run_scorecard(baseline, "Trend, no filter", date_col="entry_date")

print("\n\nWITH REGIME FILTER:")
filtered = get_regime_filtered_trend_signals_from_archive(ma_period=5, regime_ma_period=20, regime_lookback=10, stop_points=200)
run_scorecard(filtered, "Trend, regime-filtered", date_col="entry_date")

print("\n\nWALK-FORWARD, WITH REGIME FILTER:")
walk_forward_test(filtered, "Trend, regime-filtered", date_col="entry_date", num_windows=3)