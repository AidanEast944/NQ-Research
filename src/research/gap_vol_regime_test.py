from strategy import get_weekday_open_gap_signals_with_vol_regime_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 2  # MNQ - matches the live gap_forward_check.py sizing

print("=" * 70)
print("GAP CONTINUATION, VOLATILITY-REGIME FILTERED")
print("=" * 70)
print("Hypothesis: Entry 16's corrected gap-continuation backtest (468 trades, PF 1.22,")
print("just under the 1.3 bar) is a momentum/persistence effect. Persistence should be")
print("stronger in higher-volatility regimes and weaker/noisier in low-vol chop. Testing")
print("that by splitting the SAME trades (same stop/target, same entries - no re-fit) by")
print("entry-day ATR percentile rank against the trailing 60 sessions.")
print()
print("This is a filter on an existing signal, not a new parameter search - if the edge")
print("doesn't concentrate cleanly in one regime, that's a real result to report, not")
print("something to keep re-cutting until it looks good.\n")

signals = get_weekday_open_gap_signals_with_vol_regime_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

usable = signals.dropna(subset=["vol_regime_pct"])
dropped = len(signals) - len(usable)
print(f"Total trades: {len(signals)} | usable (has enough ATR history): {len(usable)} | dropped (insufficient warmup): {dropped}\n")

print("--- BASELINE: unfiltered (sanity check - should match Entry 16's PF 1.22) ---")
print_stats(full_stats(usable, point_value=POINT_VALUE))

print("\n--- Split at median vol_regime_pct ---")
low = usable[usable["vol_regime_pct"] < 0.5]
high = usable[usable["vol_regime_pct"] >= 0.5]
print(f"\nLOW-VOL regime (below median), n={len(low)}:")
print_stats(full_stats(low, point_value=POINT_VALUE))
print(f"\nHIGH-VOL regime (at/above median), n={len(high)}:")
print_stats(full_stats(high, point_value=POINT_VALUE))

print("\n--- Split into terciles (bottom/middle/top third by vol_regime_pct) ---")
t1 = usable[usable["vol_regime_pct"] < 1/3]
t2 = usable[(usable["vol_regime_pct"] >= 1/3) & (usable["vol_regime_pct"] < 2/3)]
t3 = usable[usable["vol_regime_pct"] >= 2/3]
for label, subset in [("BOTTOM third (lowest vol)", t1), ("MIDDLE third", t2), ("TOP third (highest vol)", t3)]:
    print(f"\n{label}, n={len(subset)}:")
    print_stats(full_stats(subset, point_value=POINT_VALUE))

print("\n" + "=" * 70)
print("If the top-vol subset (high or top-third) shows a materially higher PF on a")
print("still-reasonable sample, that's the candidate worth taking further:")
print("=" * 70)

best_subset = high if len(high) >= 100 else usable  # only promote a filtered subset if it still clears 100 trades
label = "HIGH-VOL regime (>= median)" if len(high) >= 100 else "UNFILTERED (high-vol subset too small to trust)"
print(f"\n--- Walk-forward on: {label}, n={len(best_subset)} ---")
walk_forward_test(best_subset, f"Gap Continuation ({label})", num_windows=4, date_col="date")

print(f"\n--- Standardized scorecard on: {label} ---")
scorecard.run_scorecard(best_subset, f"Gap Continuation - {label}",
                         account_size=10000, point_value=POINT_VALUE, date_col="date")
