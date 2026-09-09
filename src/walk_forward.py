from analysis_utils import compute_points, full_stats, print_stats

def walk_forward_test(signals, strategy_name, num_windows=4, entry_col="entry_price", exit_col="exit_price", date_col="entry_date"):
    print("=" * 60)
    print(f"WALK-FORWARD TEST: {strategy_name}")
    print("=" * 60)

    signals = compute_points(signals, entry_col=entry_col, exit_col=exit_col)
    signals = signals.sort_values(date_col).reset_index(drop=True)
    n = len(signals)

    if n < num_windows * 5:
        print(f"\nOnly {n} trades total - too few to split into {num_windows} meaningful windows.")
        print("Reporting overall stats instead:\n")
        print_stats(full_stats(signals))
        return

    window_size = n // num_windows
    window_results = []

    print(f"\nSplitting {n} trades into {num_windows} sequential windows (~{window_size} trades each).")
    print("Each window is genuinely unseen relative to prior windows - no re-optimization happens here")
    print("since these strategies use fixed rules, but this checks whether performance is CONSISTENT")
    print("across sequential time periods, not just a single lucky/unlucky split.\n")

    for w in range(num_windows):
        start = w * window_size
        end = start + window_size if w < num_windows - 1 else n
        window = signals.iloc[start:end]
        stats = full_stats(window, label=f"Window {w+1}")
        window_results.append(stats)

        print(f"--- Window {w+1} ({window[date_col].min()} to {window[date_col].max()}) ---")
        print_stats(stats)
        print()

    expectancies = [w["expectancy_dollars"] for w in window_results if w is not None]
    profitable_windows = sum(1 for e in expectancies if e > 0)

    print("=" * 60)
    print(f"CONSISTENCY SUMMARY: {profitable_windows}/{num_windows} windows were profitable")
    if profitable_windows == num_windows:
        print("Consistent across ALL windows - meaningful positive signal.")
    elif profitable_windows <= num_windows // 2:
        print("Profitable in half or fewer windows - likely NOT a durable edge, "
              "probably relies on one favorable stretch.")
    else:
        print("Mixed results - inconclusive, worth re-testing as more data accumulates.")
    print("=" * 60)