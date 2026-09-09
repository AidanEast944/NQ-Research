from strategy import get_overnight_drift_signals_with_stop_from_archive
from analysis_utils import compute_points, full_stats, print_stats
import trading_costs

STOP = 100
POINT_VALUE = 2  # MNQ

signals = get_overnight_drift_signals_with_stop_from_archive(stop_points=STOP)
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
wed = signals[signals["exit_weekday"] == "Wednesday"].copy().sort_values("date").reset_index(drop=True)

print("=" * 70)
print(f"COST-ADJUSTED CHECK: Overnight Drift + {STOP}pt stop, Wednesday only (n={len(wed)})")
print("=" * 70)
print(f"Cost model: {trading_costs.SLIPPAGE_POINTS}pt slippage + ${trading_costs.COMMISSION_PER_TRADE} "
      f"commission per trade (src/trading_costs.py)\n")

wed["net_dollars"] = wed["points"].apply(lambda p: trading_costs.apply_costs(p, point_value=POINT_VALUE))
gross_dollars = (wed["points"] * POINT_VALUE).sum()
net_dollars = wed["net_dollars"].sum()
gross_expectancy = gross_dollars / len(wed)
net_expectancy = net_dollars / len(wed)

print(f"Gross expectancy: ${gross_expectancy:.2f}/trade")
print(f"Net (after slippage+commission) expectancy: ${net_expectancy:.2f}/trade")
print(f"Total gross P&L: ${gross_dollars:,.2f}  |  Total net P&L: ${net_dollars:,.2f}")
print(f"Cost as % of gross edge: {(1 - net_dollars/gross_dollars)*100:.1f}%\n")

print("=" * 70)
print("OUTLIER CONCENTRATION CHECK: how much of the total P&L comes from just a few trades?")
print("(Windows 3 and 4 of the walk-forward showed unusually large avg wins - 214pts in window 4")
print("vs 59-120pts elsewhere - worth checking this isn't a couple of huge trades doing all the work.)")
print("=" * 70)

wed_sorted = wed.reindex(wed["points"].sort_values(ascending=False).index)
total_pnl = wed["points"].sum() * POINT_VALUE
for n in [1, 3, 5, 10]:
    top_n_pnl = wed_sorted.head(n)["points"].sum() * POINT_VALUE
    pct = (top_n_pnl / total_pnl) * 100 if total_pnl != 0 else float("nan")
    print(f"  Top {n:>2} winning trade(s): ${top_n_pnl:,.2f} of ${total_pnl:,.2f} total ({pct:.1f}%)")

print(f"\n  Largest single trade: {wed_sorted.iloc[0]['points']:.1f} pts "
      f"(${wed_sorted.iloc[0]['points']*POINT_VALUE:,.2f}) on {wed_sorted.iloc[0]['date']}")
print(f"  Median trade: {wed['points'].median():.1f} pts (${wed['points'].median()*POINT_VALUE:,.2f})")
print("\nIf the top 3-5 trades account for a large share of total P&L, that's a real fragility")
print("flag - the edge would depend on catching a small number of rare big moves, not a broad,")
print("repeatable pattern.")
