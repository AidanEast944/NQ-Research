from strategy import get_weekday_open_gap_signals_with_volume_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 2  # MNQ - matches the live gap_forward_check.py sizing

print("=" * 60)
print("VOLUME-CONFIRMED GAP CONTINUATION (corrected weekday gap definition)")
print("=" * 60)
print("Extends Entry 16 (corrected gap continuation, PF 1.22 on 468 trades) by checking whether")
print("filtering to only gaps with above-average opening-bar volume improves the edge, hurts it,")
print("or makes no difference. FIXES A BUG: this script previously called")
print("get_gap_signals_with_volume_from_archive(), which defines its gap off the Sunday Globex")
print("reopen bar for ~68 of its trades (the same bug Entry 16 corrected for the unfiltered")
print("strategy) - it never actually tested the live weekday gap strategy with a volume filter.")
print("Now uses get_weekday_open_gap_signals_with_volume_from_archive(), the volume-aware version")
print("of Entry 16's corrected definition.\n")
print("NOTE: this only measures total bar volume from OHLCV data - it is NOT true order-flow /")
print("bid-ask imbalance, which would need a different (likely paid) Databento schema (tick or")
print("MBP data) than what's archived here. Treat this as a volume-participation filter, not a")
print("microstructure signal.\n")

signals = get_weekday_open_gap_signals_with_volume_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

print(f"Total gap-continuation trades (unfiltered): {len(signals)}\n")

print("--- UNFILTERED (baseline, matches Entry 16 methodology) ---")
print_stats(full_stats(signals, point_value=POINT_VALUE))

for threshold in [1.0, 1.2, 1.5]:
    confirmed = signals[signals["volume_ratio"] >= threshold]
    unconfirmed = signals[signals["volume_ratio"] < threshold]
    print(f"\n--- CONFIRMED (opening volume >= {threshold}x trailing 20-day avg) ---")
    print(f"Trades: {len(confirmed)}")
    print_stats(full_stats(confirmed, point_value=POINT_VALUE))
    print(f"\n--- UNCONFIRMED (opening volume < {threshold}x trailing 20-day avg) ---")
    print(f"Trades: {len(unconfirmed)}")
    print_stats(full_stats(unconfirmed, point_value=POINT_VALUE))

print("\n" + "=" * 60)
print("Picking whichever threshold looks most coherent (real sample size, not just the best")
print("headline number) for a full walk-forward + scorecard, reported honestly rather than the")
print("best-looking cut, since 3 thresholds were just swept above:")
print("=" * 60)

BEST_THRESHOLD = 1.2
confirmed = signals[signals["volume_ratio"] >= BEST_THRESHOLD]
label = f"Volume-Confirmed Gap Continuation ({BEST_THRESHOLD}x, corrected weekday definition)"

print(f"\n--- Walk-forward: {label}, n={len(confirmed)} ---")
walk_forward_test(confirmed, label, num_windows=4, date_col="date", point_value=POINT_VALUE)

print(f"\n--- Standardized scorecard: {label} ---")
scorecard.run_scorecard(confirmed, label, account_size=10000, point_value=POINT_VALUE, date_col="date")
