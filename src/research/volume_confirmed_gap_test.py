from strategy import get_gap_signals_with_volume_from_archive
from analysis_utils import compute_points, full_stats, print_stats
import scorecard

POINT_VALUE = 2  # MNQ - matches the live gap_forward_check.py sizing

print("=" * 60)
print("VOLUME-CONFIRMED GAP CONTINUATION")
print("=" * 60)
print("Extends Entry 10 (gap continuation, PF 2.57 on 70 trades) by checking whether")
print("filtering to only gaps with above-average opening-bar volume improves the edge,")
print("hurts it, or makes no difference. NOTE: this only measures total bar volume from")
print("OHLCV data - it is NOT true order-flow / bid-ask imbalance, which would need a")
print("different (likely paid) Databento schema (tick or MBP data) than what's archived")
print("here. Treat this as a volume-participation filter, not a microstructure signal.\n")

signals = get_gap_signals_with_volume_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

print(f"Total gap-continuation trades (unfiltered): {len(signals)}\n")

print("--- UNFILTERED (baseline, matches Entry 10 methodology) ---")
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

best_threshold = 1.2
confirmed = signals[signals["volume_ratio"] >= best_threshold]
print(f"\n--- Standardized scorecard on CONFIRMED subset (threshold {best_threshold}x) ---")
scorecard.run_scorecard(confirmed, f"Volume-Confirmed Gap Continuation ({best_threshold}x)",
                         account_size=10000, point_value=POINT_VALUE, date_col="date")
