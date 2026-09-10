from strategy import get_gold_gap_signals_with_stop_from_history
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 10  # MGC (Micro Gold) - $10 per $1.00/oz move, matching this project's
                   # "start with the micro contract" convention.

# Realistic MGC cost assumptions, applying Entry 21/22's lesson UP FRONT this time instead of
# discovering it via a bug: trading_costs.py's SLIPPAGE_POINTS=1.0 default (1 full $1.00/oz of
# slippage = 10 ticks on MGC's $0.10 tick size) is too large for a liquid market crossing the
# spread at the open - using 2 ticks (0.2 points) instead, same reasoning as the crude oil fix.
# Still an estimate, not verified against real broker fills.
GOLD_SLIPPAGE_POINTS = 0.2
GOLD_COMMISSION = 3.00

print("=" * 70)
print("GOLD GAP, FIXED STOP/TARGET (second independent-instrument candidate)")
print("=" * 70)
print("Built with a FIXED stop/target from the start (unlike Entry 22's crude oil test, which had")
print("none and turned out to be outlier-dependent) - Entry 21's lesson (a fixed stop/target")
print("structurally caps single-trade domination) applied up front this time, not discovered after")
print("the fact. Daily OHLC only (no intraday archive yet) - if both stop and target were touched")
print("the same day, this conservatively assumes the stop hit first (see strategy.py docstring).\n")

for direction in ["continuation", "reversion"]:
    print(f"\n{'='*70}\nDIRECTION: {direction.upper()}\n{'='*70}")
    for min_gap in [0.5, 1.0, 1.5]:
        for stop_pct, target_pct in [(0.5, 1.0), (0.5, 0.75), (1.0, 2.0)]:
            signals = get_gold_gap_signals_with_stop_from_history(
                min_gap_pct=min_gap, stop_pct=stop_pct, target_pct=target_pct, direction=direction
            )
            signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
            signals = signals.sort_values("date").reset_index(drop=True)
            print(f"\n--- min_gap={min_gap}%, stop={stop_pct}%/target={target_pct}%, n={len(signals)} ---")
            print_stats(full_stats(signals, point_value=POINT_VALUE))
            if len(signals):
                reasons = signals["exit_reason"].value_counts().to_dict() if "exit_reason" in signals.columns else {}

print("\n" + "=" * 70)
print("Picking whichever (direction, threshold, stop/target) combination looks most coherent -")
print("real sample size and a sane exit-reason mix, not just the best headline PF - for a full")
print("walk-forward + cost-aware scorecard + outlier check, reported honestly rather than")
print("cherry-picked, since many combinations were just swept above:")
print("=" * 70)

# NOTE: fill in after seeing the sweep above.
DIRECTION, MIN_GAP, STOP_PCT, TARGET_PCT = "continuation", 1.0, 0.5, 1.0
final_signals = get_gold_gap_signals_with_stop_from_history(
    min_gap_pct=MIN_GAP, stop_pct=STOP_PCT, target_pct=TARGET_PCT, direction=DIRECTION
)
final_signals = compute_points(final_signals, entry_col="entry_price", exit_col="exit_price")
final_signals = final_signals.sort_values("date").reset_index(drop=True)

label = f"Gold Gap {DIRECTION} ({MIN_GAP}%+, {STOP_PCT}%/{TARGET_PCT}% stop/target)"
print(f"\nExit reason breakdown: {final_signals['exit_reason'].value_counts().to_dict()}")

print(f"\n--- Walk-forward: {label}, n={len(final_signals)} ---")
walk_forward_test(final_signals, label, num_windows=4, date_col="date", point_value=POINT_VALUE)

print(f"\n--- Standardized scorecard (gold-calibrated costs): {label} ---")
scorecard.run_scorecard(final_signals, label, account_size=10000, point_value=POINT_VALUE, date_col="date",
                         slippage_points=GOLD_SLIPPAGE_POINTS, commission=GOLD_COMMISSION)

print("\n" + "=" * 70)
print("OUTLIER CONCENTRATION CHECK (checked up front this time, not after the fact):")
print("=" * 70)
total_pnl = final_signals["points"].sum() * POINT_VALUE
sorted_signals = final_signals.reindex(final_signals["points"].sort_values(ascending=False).index)
for n in [1, 3, 5]:
    n = min(n, len(final_signals))
    top_pnl = sorted_signals.head(n)["points"].sum() * POINT_VALUE
    pct = (top_pnl / total_pnl) * 100 if total_pnl != 0 else float("nan")
    print(f"  Top {n} winning trade(s): ${top_pnl:,.2f} of ${total_pnl:,.2f} total ({pct:.1f}%)")

print(f"\n--- Same stats with the top 3 largest trades excluded (n={len(final_signals)-3}) ---")
top3_dates = set(sorted_signals.head(3)["date"])
ex3 = final_signals[~final_signals["date"].isin(top3_dates)]
print_stats(full_stats(ex3, point_value=POINT_VALUE))
