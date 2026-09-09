from strategy import get_relative_momentum_rotation_signals_from_archive
from analysis_utils import full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

print("=" * 70)
print("RELATIVE MOMENTUM ROTATION (NQ / ES / YM / RTY)")
print("=" * 70)
print("New mechanism, not a variant of the existing pairs book: instead of betting two series")
print("mean-revert back together (the pairs thesis - Entry 18 found weak cointegration support")
print("for that), this bets whichever index has been leading keeps leading. Each day, ranks all")
print("four by trailing return (known only as of yesterday's close - no lookahead) and goes long")
print("the leader for that RTH session.\n")
print("CAVEAT UP FRONT: this is long-only, so it carries real index beta. A positive result here")
print("is evidence rotation adds something on top of just being long the market - not proof by")
print("itself, since 'being long the strongest of 4 correlated indices' will look decent in any")
print("broad rally regardless of whether the rotation logic is doing real work. Treat this as a")
print("screening test for whether the idea deserves a proper long/short market-neutral build next.\n")

for lookback in [3, 5, 10, 20]:
    signals = get_relative_momentum_rotation_signals_from_archive(lookback_days=lookback)
    stats = full_stats(signals, point_value=1)  # points column is already in dollars - see docstring
    print(f"--- lookback_days={lookback}, n={len(signals)} ---")
    print_stats(stats)
    if stats:
        leader_counts = signals["leader"].value_counts().to_dict()
        print(f"  Leader selected: {leader_counts}")
    print()

print("=" * 70)
print("Same test, requiring the leader to be ahead of the runner-up by a real margin (min_lead),")
print("to see if filtering out close/noisy rankings improves things:")
print("=" * 70)

BEST_LOOKBACK = 5
for min_lead in [0.0, 0.25, 0.5, 1.0]:
    signals = get_relative_momentum_rotation_signals_from_archive(lookback_days=BEST_LOOKBACK, min_lead=min_lead)
    stats = full_stats(signals, point_value=1)
    print(f"--- lookback_days={BEST_LOOKBACK}, min_lead={min_lead}pp, n={len(signals)} ---")
    print_stats(stats)
    print()

print("=" * 70)
print("Walk-forward + scorecard on the unfiltered base case (lookback=5, min_lead=0) - report this")
print("one honestly rather than the best-looking min_lead cut, since min_lead was swept above and")
print("picking whichever cut looks best now would just be curve-fitting one more parameter:")
print("=" * 70)

base_signals = get_relative_momentum_rotation_signals_from_archive(lookback_days=BEST_LOOKBACK)
print(f"\n--- Walk-forward, n={len(base_signals)} ---")
walk_forward_test(base_signals, "Relative Momentum Rotation (5-day, unfiltered)", num_windows=4, date_col="date")

print("\n--- Standardized scorecard ---")
scorecard.run_scorecard(base_signals, "Relative Momentum Rotation (5-day, unfiltered)",
                         account_size=10000, point_value=1, date_col="date")
