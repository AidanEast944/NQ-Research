from strategy import get_crude_oil_gap_signals_from_history
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 100  # MCL (Micro WTI Crude Oil) - $100 per $1.00/barrel move, same "start with the
                    # micro contract" convention used everywhere else in this codebase.

print("=" * 70)
print("CRUDE OIL GAP: CONTINUATION vs. REVERSION (first independent-instrument candidate)")
print("=" * 70)
print("26 years of daily history (2000-2026, 6539 bars) - far more regime coverage than anything")
print("else in this project. No intrabar stop yet (daily-only resolution) - enter at open, exit")
print("at close. Testing BOTH continuation and reversion as genuinely open questions across a few")
print("gap-size thresholds, rather than assuming the equity mechanism transfers.\n")

for direction in ["continuation", "reversion"]:
    print(f"\n{'='*70}\nDIRECTION: {direction.upper()}\n{'='*70}")
    for min_gap in [1.0, 2.0, 3.0]:
        signals = get_crude_oil_gap_signals_from_history(min_gap_pct=min_gap, direction=direction)
        signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
        signals = signals.sort_values("date").reset_index(drop=True)
        print(f"\n--- min_gap_pct={min_gap}%, n={len(signals)} ---")
        print_stats(full_stats(signals, point_value=POINT_VALUE))

print("\n" + "=" * 70)
print("Picking whichever (direction, threshold) combination looks most coherent - real sample")
print("size, not just the single best number - for a full walk-forward + scorecard. Report this")
print("choice honestly: it's chosen for coherence, not for having the highest headline PF, since")
print("6 combinations were just swept above and cherry-picking the best would be hollow.")
print("=" * 70)

# NOTE: fill in after seeing the sweep above - this default (continuation, 2%) is a reasonable
# starting guess (mirrors the equity strategy's mechanism at a threshold with a real sample size)
# but should be reconsidered based on what the sweep actually shows.
DIRECTION, MIN_GAP = "continuation", 2.0
final_signals = get_crude_oil_gap_signals_from_history(min_gap_pct=MIN_GAP, direction=DIRECTION)
final_signals = compute_points(final_signals, entry_col="entry_price", exit_col="exit_price")
final_signals = final_signals.sort_values("date").reset_index(drop=True)

label = f"Crude Oil Gap {DIRECTION} ({MIN_GAP}%+)"
print(f"\n--- Walk-forward: {label}, n={len(final_signals)} ---")
walk_forward_test(final_signals, label, num_windows=4, date_col="date")

print(f"\n--- Standardized scorecard: {label} ---")
scorecard.run_scorecard(final_signals, label, account_size=10000, point_value=POINT_VALUE, date_col="date")
