"""
Re-run the Tier 1 pairs strategies (Entry 9: NQ/ES, Entry 13: NQ/YM, ES/YM) through the
standardized, cost-aware scorecard.

Why this is needed: Entry 9/13's original "PASS" verdicts came from pairs_scorecard.py, a
hand-rolled, one-off scorecard that reimplements 5 of the 6 standard checks by hand directly on
the "pnl_dollars" column - it never used scorecard.py at all, so it predates AND bypasses the
Check 6 cost-adjustment fix (Entry 21/research_log.md, commit 4154f03). These pairs strategies
have never actually been judged against realistic trading costs.

Sizing: pairs signals come out of get_pairs_trading_signals_from_archive() /
get_generic_pairs_signals_from_archive() as full-size-contract dollar P&L (NQ=$20/pt, ES=$50/pt,
YM=$5/pt - see strategy.py). Rescaling to MICRO contracts (MNQ/MES/MYM, exactly 1/10th of
full-size) matches this project's "start with the micro contract" convention used everywhere else
(pairs_micro_sizing.py already did this for NQ/ES's drawdown check; extending it here to ALL
three pairs and to the profit-factor/cost checks too, not just drawdown). Profit factor, win rate,
and expectancy RATIOS are scale-invariant, so this rescaling only matters for the dollar-figures
(drawdown, expectancy, cost check) - it does not change whether checks 1-5 pass or fail relative
to the original full-size run, but it does put the cost check on a realistic footing.

Cost model: these are 2-leg trades (entry + exit on BOTH legs), so realistic slippage/commission
is the SUM of both legs' costs, not a single instrument's. Using this project's existing
convention (1.0 points of slippage + $4.50 commission per leg, same numbers used everywhere else,
just applied per-leg at each leg's own micro point value - NOT a new arbitrary calibration):
  MNQ leg: 1.0pt x $2/pt slippage = $2.00, + $4.50 commission = $6.50
  MES leg: 1.0pt x $5/pt slippage = $5.00, + $4.50 commission = $9.50
  MYM leg: 1.0pt x $0.50/pt slippage = $0.50, + $4.50 commission = $5.00
  Pair round-trip cost = sum of both legs' slippage + both legs' commission.
These are still estimates (not verified against your actual broker's per-contract fees for a
2-leg spread order) - flagged the same way the crude-oil cost overrides were.
"""
from strategy import get_pairs_trading_signals_from_archive, get_generic_pairs_signals_from_archive
from analysis_utils import full_stats, print_stats
from walk_forward import walk_forward_test
import scorecard

SCALE_FACTOR = 0.1  # full-size -> micro (MNQ/MES/MYM), exact 1/10th per strategy.py's own point values

# Per-leg costs at MICRO point values, using this project's existing 1.0pt-slippage + $4.50-commission
# convention (unmodified default from trading_costs.py, just applied per-instrument).
LEG_COSTS = {
    "MNQ": {"point_value": 2.0, "slippage_dollars": 1.0 * 2.0, "commission": 4.50},
    "MES": {"point_value": 5.0, "slippage_dollars": 1.0 * 5.0, "commission": 4.50},
    "MYM": {"point_value": 0.5, "slippage_dollars": 1.0 * 0.5, "commission": 4.50},
}

def to_scorecard_format(signals, scale=SCALE_FACTOR):
    """Same entry_price=0/exit_price=<dollar P&L>/signal='LONG' trick used for Relative Momentum
    Rotation - lets compute_points()/full_stats()/walk_forward_test()/scorecard.run_scorecard()
    all reproduce correct dollar figures automatically with point_value=1."""
    signals = signals.copy()
    signals["entry_price"] = 0.0
    signals["exit_price"] = signals["pnl_dollars"] * scale
    signals["signal"] = "LONG"
    return signals

def pair_cost(leg_a, leg_b):
    a, b = LEG_COSTS[leg_a], LEG_COSTS[leg_b]
    slippage = a["slippage_dollars"] + b["slippage_dollars"]
    commission = a["commission"] + b["commission"]
    return slippage, commission

PAIRS = [
    ("NQ/ES Pairs Trading (Entry 9)", "MNQ", "MES",
     lambda: get_pairs_trading_signals_from_archive()),
    ("NQ/YM Pairs Trading (Entry 13)", "MNQ", "MYM",
     lambda: get_generic_pairs_signals_from_archive("data/raw_nq_extended", "data/raw_ym_extended",
                                                      point_value_a=20, point_value_b=5)),
    ("ES/YM Pairs Trading (Entry 13)", "MES", "MYM",
     lambda: get_generic_pairs_signals_from_archive("data/raw_es_extended", "data/raw_ym_extended",
                                                      point_value_a=50, point_value_b=5)),
]

if __name__ == "__main__":
    for label, leg_a, leg_b, loader in PAIRS:
        print("\n" + "#" * 70)
        print(f"# {label} - re-run at micro sizing with cost-aware scorecard")
        print("#" * 70)

        raw = loader()
        raw = raw.sort_values("entry_date").reset_index(drop=True)
        signals = to_scorecard_format(raw)

        slippage, commission = pair_cost(leg_a, leg_b)
        print(f"\nSample: {len(signals)} trades. Sizing: 1x {leg_a} + hedge-ratio-weighted {leg_b}.")
        print(f"Cost model: ${slippage:.2f} combined slippage + ${commission:.2f} combined commission "
              f"per round-trip pair trade (both legs, entry+exit).")

        print(f"\n--- Walk-forward: {label} ---")
        walk_forward_test(signals, label, num_windows=4, date_col="entry_date", point_value=1)

        print(f"\n--- Standardized scorecard (cost-aware, micro sizing): {label} ---")
        scorecard.run_scorecard(signals, label, account_size=10000, point_value=1, date_col="entry_date",
                                 slippage_points=slippage, commission=commission)
