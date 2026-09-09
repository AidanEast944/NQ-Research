from strategy import get_overnight_drift_signals_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test
from trading_costs import apply_costs
import scorecard

POINT_VALUE = 20  # full NQ - matches the account_size=10000/point_value=20 convention used
                   # elsewhere in research_log.md's scorecards, for direct comparability

print("=" * 60)
print("OVERNIGHT SESSION DRIFT - unconditional long, prior RTH close -> today's RTH open")
print("=" * 60)
print("Distinct from Entry 10 (gap continuation, trades AFTER the open) and Entry 15")
print("(overnight reversion, only fires on unusually large overnight moves). This tests")
print("the pure calendar hypothesis: is NQ's overnight session structurally positive,")
print("with no size filter or condition at all?\n")

signals = get_overnight_drift_signals_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("entry_date").reset_index(drop=True)

print(f"Total overnight sessions tested: {len(signals)}\n")

print("--- Overall stats (no costs) ---")
print_stats(full_stats(signals, point_value=POINT_VALUE))

print("\n--- Walk-forward consistency ---")
walk_forward_test(signals, "Overnight Drift", num_windows=4, date_col="entry_date")

print("\n--- Cost sensitivity (single instrument, one round-trip per session) ---")
for commission in [0, 2.50, 4.50]:
    for slippage_points in [0, 0.5, 1]:
        net_dollars = sum(
            apply_costs(p, point_value=POINT_VALUE, slippage_points=slippage_points, commission=commission)
            for p in signals["points"]
        )
        print(f"  Commission ${commission}, slippage {slippage_points}pt: "
              f"Net P&L ${net_dollars:,.2f} (${net_dollars/len(signals):.2f}/session)")

print("\n--- Standardized scorecard ---")
scorecard.run_scorecard(signals, "Overnight Drift (unconditional long)", point_value=POINT_VALUE, date_col="entry_date")
