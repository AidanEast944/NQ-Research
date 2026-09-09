from strategy import get_overnight_drift_signals_with_stop_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 2  # MNQ

print("=" * 70)
print("OVERNIGHT DRIFT + STOP-LOSS, WITH WEEKDAY BREAKDOWN")
print("=" * 70)
print("Entry 17 (unconditional overnight drift) had a real, walk-forward-consistent edge but a")
print("645%-of-account max drawdown because it had NO stop at all. This adds a stop, and checks")
print("whether the edge concentrates on specific weekdays (a natural question given the Wednesday")
print("RTH effect already found independently in Entry 14).\n")

for stop in [50, 75, 100, 150]:
    signals = get_overnight_drift_signals_with_stop_from_archive(stop_points=stop)
    signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
    stats = full_stats(signals, point_value=POINT_VALUE)
    stopped = (signals["exit_reason"] == "stop").sum()
    print(f"--- stop_points={stop} ({stopped}/{len(signals)} trades stopped out) ---")
    print_stats(stats)
    print()

print("=" * 70)
print("Now picking ONE stop width (100 pts - closest to the 100pt default used elsewhere in this")
print("codebase, e.g. get_day_of_week_stop_signals_from_archive) and breaking out by exit weekday:")
print("=" * 70)

STOP = 100
all_signals = get_overnight_drift_signals_with_stop_from_archive(stop_points=STOP)
all_signals = compute_points(all_signals, entry_col="entry_price", exit_col="exit_price")

print(f"\n--- ALL WEEKDAYS COMBINED (stop={STOP}) ---")
print_stats(full_stats(all_signals, point_value=POINT_VALUE))

by_day_results = {}
for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
    subset = all_signals[all_signals["exit_weekday"] == day]
    print(f"\n--- Overnight session ending in {day}'s open, n={len(subset)} ---")
    stats = full_stats(subset, point_value=POINT_VALUE)
    print_stats(stats)
    by_day_results[day] = (subset, stats)

best_day = max(
    (d for d in by_day_results if by_day_results[d][1] is not None and by_day_results[d][1]["trades"] >= 50),
    key=lambda d: by_day_results[d][1]["profit_factor"],
    default=None,
)

print("\n" + "=" * 70)
if best_day is None:
    print("No single weekday has both 50+ trades and a standout profit factor. Reporting the")
    print("ALL-WEEKDAYS COMBINED result as the honest candidate instead of cherry-picking a thin day.")
    print("=" * 70)
    best_subset, best_stats = all_signals, full_stats(all_signals, point_value=POINT_VALUE)
    label = f"Overnight Drift + {STOP}pt stop (all weekdays)"
else:
    print(f"Best-performing weekday by profit factor with a usable sample: {best_day}")
    print("Remember this involved checking 5 weekdays - treat it as a hypothesis, not a conclusion,")
    print("until the walk-forward and scorecard below actually hold up.")
    print("=" * 70)
    best_subset, best_stats = by_day_results[best_day]
    label = f"Overnight Drift + {STOP}pt stop ({best_day} only)"

print(f"\n--- Walk-forward on: {label} ---")
walk_forward_test(best_subset, label, num_windows=4, date_col="date")

print(f"\n--- Standardized scorecard on: {label} ---")
scorecard.run_scorecard(best_subset, label, account_size=10000, point_value=POINT_VALUE, date_col="date")
