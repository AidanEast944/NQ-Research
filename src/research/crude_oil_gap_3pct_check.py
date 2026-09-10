from strategy import get_crude_oil_gap_signals_from_history
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

POINT_VALUE = 100  # MCL

# Realistic MCL cost assumptions - MCL ticks in $0.01/barrel increments ($1 per tick on the
# 100-barrel micro contract). trading_costs.py's SLIPPAGE_POINTS=1.0 default means "1.0 points
# of slippage" = a full $1.00/barrel move = 100 ticks - correct order of magnitude for NQ/MNQ's
# price granularity, wildly wrong for crude oil. Using 2 ticks (0.02 points) of slippage instead -
# a reasonable assumption for a liquid market crossing the spread at the open, NOT verified
# against your actual broker's fill data. Commission estimated at $3.00 round-trip for a micro
# contract (~$1.50/side) - also an estimate, not your actual statement. Both are flagged here so
# they're easy to correct once you know your real numbers.
CRUDE_SLIPPAGE_POINTS = 0.02
CRUDE_COMMISSION = 3.00

print("=" * 70)
print("CRUDE OIL GAP CONTINUATION, 3% THRESHOLD - re-run with a realistic cost model")
print("=" * 70)

signals = get_crude_oil_gap_signals_from_history(min_gap_pct=3.0, direction="continuation")
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

label = "Crude Oil Gap Continuation (3.0%+)"
print(f"\n--- Walk-forward: {label}, n={len(signals)} ---")
walk_forward_test(signals, label, num_windows=4, date_col="date")

print(f"\n--- Standardized scorecard (corrected crude-oil cost model): {label} ---")
scorecard.run_scorecard(signals, label, account_size=10000, point_value=POINT_VALUE, date_col="date",
                         slippage_points=CRUDE_SLIPPAGE_POINTS, commission=CRUDE_COMMISSION)

print("\n" + "=" * 70)
print("REGIME CHECK: the 2% cut's walk-forward showed a big swing (window 3, 2009-2020, PF 2.58")
print("vs window 4, 2020-2026, PF 0.57) - checking whether the SAME pattern (strong-then-weak)")
print("shows up here, or whether 3% behaves differently across the same eras:")
print("=" * 70)
signals["year"] = signals["date"].apply(lambda d: d.year)
for start, end, era_label in [(2000, 2008, "2000-2008"), (2009, 2019, "2009-2019"),
                                 (2020, 2026, "2020-2026")]:
    era = signals[(signals["year"] >= start) & (signals["year"] <= end)]
    print(f"\n--- {era_label}, n={len(era)} ---")
    print_stats(full_stats(era, point_value=POINT_VALUE))
