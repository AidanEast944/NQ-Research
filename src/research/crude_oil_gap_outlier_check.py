from strategy import get_crude_oil_gap_signals_from_history
from analysis_utils import compute_points

signals = get_crude_oil_gap_signals_from_history(min_gap_pct=3.0, direction="continuation")
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

POINT_VALUE = 100

print("=" * 70)
print(f"OUTLIER CONCENTRATION CHECK: Crude Oil Gap Continuation (3%+), n={len(signals)}")
print("=" * 70)
print("This strategy has no fixed stop/target (daily-only resolution, enter-open/exit-close) -")
print("structurally similar to the overnight-drift case that turned out to hinge on one trade.")
print("Checking whether the same problem exists here before trusting the 6/6 scorecard.\n")

total_pnl = signals["points"].sum() * POINT_VALUE
signals_sorted = signals.reindex(signals["points"].sort_values(ascending=False).index)
for n in [1, 3, 5, 10, 20]:
    top_n_pnl = signals_sorted.head(n)["points"].sum() * POINT_VALUE
    pct = (top_n_pnl / total_pnl) * 100 if total_pnl != 0 else float("nan")
    print(f"  Top {n:>2} winning trade(s): ${top_n_pnl:,.2f} of ${total_pnl:,.2f} total ({pct:.1f}%)")

print(f"\n  Median trade: {signals['points'].median():.2f} pts (${signals['points'].median()*POINT_VALUE:,.2f})")
print(f"  Largest single trade: {signals_sorted.iloc[0]['points']:.2f} pts "
      f"(${signals_sorted.iloc[0]['points']*POINT_VALUE:,.2f}) on {signals_sorted.iloc[0]['date']}, "
      f"gap was {signals_sorted.iloc[0]['gap_pct']:.2f}%")
print(f"  2nd largest: {signals_sorted.iloc[1]['points']:.2f} pts on {signals_sorted.iloc[1]['date']}")
print(f"  3rd largest: {signals_sorted.iloc[2]['points']:.2f} pts on {signals_sorted.iloc[2]['date']}")

print(f"\n--- Same stats with the single largest trade excluded (n={len(signals)-1}) ---")
from analysis_utils import full_stats, print_stats
ex1 = signals[signals["date"] != signals_sorted.iloc[0]["date"]]
print_stats(full_stats(ex1, point_value=POINT_VALUE))

print(f"\n--- Same stats with the top 3 largest trades excluded (n={len(signals)-3}) ---")
top3_dates = set(signals_sorted.head(3)["date"])
ex3 = signals[~signals["date"].isin(top3_dates)]
print_stats(full_stats(ex3, point_value=POINT_VALUE))
