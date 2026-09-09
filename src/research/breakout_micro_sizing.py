from strategy import get_prior_day_break_signals_from_archive
from scorecard import run_scorecard
from analysis_utils import compute_points, full_stats, print_stats

FOLDER = "data/raw_nq_extended"
MICRO_POINT_VALUE = 2  # MNQ = 1/10th of NQ's $20/point

signals = get_prior_day_break_signals_from_archive(stop_points=30, target_points=60, data_folder=FOLDER)

print("=" * 60)
print("BREAKOUT (30/60) - MNQ MICRO CONTRACT SIZING")
print("=" * 60)

run_scorecard(
    signals.copy(),
    "Breakout, MNQ sizing",
    entry_col="Close",
    date_col="date",
    point_value=MICRO_POINT_VALUE
)

print("\n" + "=" * 60)
print("SAME STRATEGY, DIFFERENT ACCOUNT SIZES (MNQ sizing)")
print("=" * 60)

for account_size in [5000, 10000, 25000, 50000]:
    signals_copy = compute_points(signals.copy(), entry_col="Close")
    stats = full_stats(signals_copy, point_value=MICRO_POINT_VALUE)
    dd_pct = (stats["max_drawdown_dollars"] / account_size) * 100
    print(f"\nAccount size ${account_size:,}:")
    print(f"  Max drawdown: ${stats['max_drawdown_dollars']:,.2f} ({dd_pct:.1f}% of account)")
    print(f"  Total P&L: ${stats['total_pnl_dollars']:,.2f}")
    print(f"  Profit factor: {stats['profit_factor']:.2f}")