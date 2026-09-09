from strategy import get_weekday_open_gap_signals_with_vol_regime_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import trading_costs

POINT_VALUE = 2  # MNQ

signals = get_weekday_open_gap_signals_with_vol_regime_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
usable = signals.dropna(subset=["vol_regime_pct"]).sort_values("date").reset_index(drop=True)

low = usable[usable["vol_regime_pct"] < 0.5]
high = usable[usable["vol_regime_pct"] >= 0.5]

print("=" * 70)
print("CHECK 1: OUTLIER CONCENTRATION on the HIGH-VOL subset")
print("=" * 70)
print("This strategy has a fixed 40pt stop / 80pt target, so unlike the overnight-drift")
print("case, no single trade CAN dominate the way a naked, unbounded hold can. Confirming")
print("that's actually true here rather than assuming it:\n")
total_pnl = high["points"].sum() * POINT_VALUE
high_sorted = high.reindex(high["points"].sort_values(ascending=False).index)
for n in [1, 3, 5, 10]:
    top_n = high_sorted.head(n)["points"].sum() * POINT_VALUE
    pct = (top_n / total_pnl) * 100 if total_pnl != 0 else float("nan")
    print(f"  Top {n:>2} winning trade(s): ${top_n:,.2f} of ${total_pnl:,.2f} total ({pct:.1f}%)")
print(f"  Median trade: {high['points'].median():.1f} pts (${high['points'].median()*POINT_VALUE:,.2f})")

print("\n" + "=" * 70)
print("CHECK 2: DOES THE LOW-VOL SUBSET *ALSO* IMPROVE OVER TIME?")
print("=" * 70)
print("Entry 16's unfiltered walk-forward already improved over time (0.96->1.19->1.27->1.54),")
print("and the high-vol subset's walk-forward improves too (0.92->1.14->1.47->1.88, same shape).")
print("If the LOW-vol subset shows the SAME improving trend, that's evidence the vol-regime")
print("filter isn't adding real information beyond 'this strategy generally got better over")
print("time for some other reason' - the two would be confounded, not genuinely separable.")
print("If low-vol does NOT show the same improvement while high-vol does, that's real support")
print("for volatility regime specifically mattering.\n")

walk_forward_test(low, "Gap Continuation (LOW-VOL regime, for comparison)", num_windows=4, date_col="date")

print("\n" + "=" * 70)
print("CHECK 3: COST-ADJUSTED PROFIT FACTOR on the HIGH-VOL subset")
print("=" * 70)
high = high.copy()
high["net_dollars"] = high["points"].apply(lambda p: trading_costs.apply_costs(p, point_value=POINT_VALUE))
net_wins = high[high["net_dollars"] > 0]["net_dollars"].sum()
net_losses = abs(high[high["net_dollars"] <= 0]["net_dollars"].sum())
net_pf = net_wins / net_losses if net_losses > 0 else float("inf")
net_expectancy = high["net_dollars"].mean()
print(f"Gross expectancy: ${high['points'].mean()*POINT_VALUE:.2f}/trade")
print(f"Net (after {trading_costs.SLIPPAGE_POINTS}pt slippage + ${trading_costs.COMMISSION_PER_TRADE} "
      f"commission) expectancy: ${net_expectancy:.2f}/trade")
print(f"Net profit factor: {net_pf:.2f} (gross was 1.32)")
