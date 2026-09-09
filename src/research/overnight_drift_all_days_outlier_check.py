from strategy import get_overnight_drift_signals_with_stop_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard, trading_costs

STOP = 100
POINT_VALUE = 2  # MNQ

signals = get_overnight_drift_signals_with_stop_from_archive(stop_points=STOP)
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)

print("=" * 70)
print(f"OUTLIER CHECK: Overnight Drift + {STOP}pt stop, ALL WEEKDAYS COMBINED (n={len(signals)})")
print("=" * 70)
print("The Wednesday-only cut's 5/5 scorecard turned out to hinge almost entirely on ONE real")
print("trade: the 2026-04-08 overnight session, driven by the US-Iran ceasefire/Hormuz reopening")
print("news (confirmed - a genuine, huge, one-off geopolitical event, not a data error). That event")
print("could have landed on any weekday - it happening to fall on a Tuesday-close-to-Wednesday-open")
print("window looks like it's mostly coincidence, not a real Wednesday-specific structural effect.")
print("Checking whether the UNCONDITIONAL (all-weekday) version - which doesn't depend on that one")
print("trade landing in the 'right' bucket - has a more genuine, diversified edge underneath it.\n")

total_pnl = signals["points"].sum() * POINT_VALUE
signals_sorted = signals.reindex(signals["points"].sort_values(ascending=False).index)
print(f"Total P&L: ${total_pnl:,.2f}")
for n in [1, 3, 5, 10, 20]:
    top_n_pnl = signals_sorted.head(n)["points"].sum() * POINT_VALUE
    pct = (top_n_pnl / total_pnl) * 100 if total_pnl != 0 else float("nan")
    print(f"  Top {n:>2} winning trade(s): ${top_n_pnl:,.2f} ({pct:.1f}% of total)")
print(f"  Median trade: {signals['points'].median():.1f} pts (${signals['points'].median()*POINT_VALUE:,.2f})")

print(f"\n--- Same check with the 2026-04-08 outlier trade EXCLUDED ---")
ex_outlier = signals[signals["date"].astype(str) != "2026-04-08"]
print(f"n={len(ex_outlier)} (excluded {len(signals)-len(ex_outlier)} trade(s))")
print_stats(full_stats(ex_outlier, point_value=POINT_VALUE))

wed = signals[signals["exit_weekday"] == "Wednesday"]
wed_ex = wed[wed["date"].astype(str) != "2026-04-08"]
print(f"\n--- Wednesday-only, WITH the 2026-04-08 outlier excluded (n={len(wed_ex)}) ---")
print("This is the honest answer to 'is there anything left of the Wednesday story once you")
print("remove the one trade that was really just a geopolitical news event':")
print_stats(full_stats(wed_ex, point_value=POINT_VALUE))

print("\n" + "=" * 70)
print("Full walk-forward + scorecard on ALL-WEEKDAYS COMBINED (the un-cherry-picked version):")
print("=" * 70)
walk_forward_test(signals, f"Overnight Drift + {STOP}pt stop (all weekdays)", num_windows=4, date_col="date")
scorecard.run_scorecard(signals, f"Overnight Drift + {STOP}pt stop (all weekdays)",
                         account_size=10000, point_value=POINT_VALUE, date_col="date")

net_expectancy = sum(trading_costs.apply_costs(p, point_value=POINT_VALUE) for p in signals["points"]) / len(signals)
print(f"\nNet-of-cost expectancy, all weekdays combined: ${net_expectancy:.2f}/trade")
