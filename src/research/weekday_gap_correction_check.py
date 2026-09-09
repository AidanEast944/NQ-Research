from strategy import get_weekday_open_gap_signals_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 2  # MNQ - matches the live gap_forward_check.py sizing

print("=" * 60)
print("CORRECTED GAP CONTINUATION - matches what gap_forward_check.py actually trades")
print("=" * 60)
print("Entry 10's original backtest (get_gap_signals_from_archive) defines 'open' as the")
print("FIRST bar of the calendar date. For Sunday, that's the 6PM Globex reopen - so its")
print("gap is really the Friday-close-to-Sunday-reopen weekend gap, not an intraday open-")
print("bell gap. Every one of Entry 10's 70 trades turned out to be exactly this (68 of 70")
print("are Sundays, and all 70 exit via 'eod' - the stop/target were never actually used,")
print("since a Sunday date has no 08:30-16:00 RTH bars to check them against).")
print()
print("This script instead uses the entry_time bar's Open vs. the prior day's close - the")
print("way the LIVE script actually defines the gap - restricted to days that actually have")
print("an entry_time bar (which excludes Sunday by construction). This is the strategy that")
print("is really running live, and it has never been backtested until now.\n")

signals = get_weekday_open_gap_signals_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

print(f"Total trades: {len(signals)}")
print(f"Exit reasons:\n{signals['exit_reason'].value_counts().to_string()}\n")

print("--- Overall stats (MNQ sizing) ---")
print_stats(full_stats(signals, point_value=POINT_VALUE))

print("\n--- Walk-forward consistency ---")
walk_forward_test(signals, "Weekday-Open Gap Continuation", num_windows=4, date_col="date")

print("\n--- Standardized scorecard ---")
scorecard.run_scorecard(signals, "Weekday-Open Gap Continuation (corrected)",
                         account_size=10000, point_value=POINT_VALUE, date_col="date")
