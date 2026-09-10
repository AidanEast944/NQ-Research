"""
Outlier-concentration check on all three Tier 1 pairs strategies.

Triggered specifically by NQ/YM's walk-forward window 3 in pairs_scorecard_v2.py's output:
profit factor 107.53, driven by an average LOSS of just -$23.79 against an average WIN of
$730.96 in that 9-trade window - the same lopsided shape (a few trades doing almost all the work)
that turned out to be the whole story for the Wednesday overnight-drift result and the crude oil
gap continuation result. Running the same check on all three pairs for a consistent, comparable
picture, not just the one that looked suspicious - it would be easy to miss a similar problem in
NQ/ES or ES/YM by only looking where the walk-forward printout already looked odd.
"""
from analysis_utils import full_stats, print_stats
from pairs_scorecard_v2 import PAIRS, to_scorecard_format

for label, leg_a, leg_b, loader in PAIRS:
    raw = loader()
    raw = raw.sort_values("entry_date").reset_index(drop=True)
    signals = to_scorecard_format(raw)
    signals["points"] = signals["exit_price"] - signals["entry_price"]  # dollars, point_value=1

    total_pnl = signals["points"].sum()
    n = len(signals)
    sorted_signals = signals.reindex(signals["points"].sort_values(ascending=False).index)

    print("=" * 70)
    print(f"OUTLIER CONCENTRATION CHECK: {label}, n={n}")
    print("=" * 70)

    for top_n in [1, 3, 5]:
        top_n = min(top_n, n)
        top_pnl = sorted_signals.head(top_n)["points"].sum()
        pct = (top_pnl / total_pnl) * 100 if total_pnl != 0 else float("nan")
        print(f"  Top {top_n} winning trade(s): ${top_pnl:,.2f} of ${total_pnl:,.2f} total ({pct:.1f}%)")

    print(f"\n  Largest single trade: ${sorted_signals.iloc[0]['points']:,.2f} on "
          f"{sorted_signals.iloc[0]['entry_date']} (entry z-score "
          f"{sorted_signals.iloc[0]['entry_zscore']:.2f}, exit reason "
          f"{sorted_signals.iloc[0]['exit_reason']})")
    print(f"  2nd largest: ${sorted_signals.iloc[1]['points']:,.2f} on {sorted_signals.iloc[1]['entry_date']}")
    print(f"  3rd largest: ${sorted_signals.iloc[2]['points']:,.2f} on {sorted_signals.iloc[2]['entry_date']}")

    print(f"\n  --- Same stats with the single largest trade excluded (n={n-1}) ---")
    ex1 = signals[signals["entry_date"] != sorted_signals.iloc[0]["entry_date"]]
    print_stats(full_stats(ex1, point_value=1))

    print(f"\n  --- Same stats with the top 3 largest trades excluded (n={n-3}) ---")
    top3_dates = set(sorted_signals.head(3)["entry_date"])
    ex3 = signals[~signals["entry_date"].isin(top3_dates)]
    print_stats(full_stats(ex3, point_value=1))
    print()
