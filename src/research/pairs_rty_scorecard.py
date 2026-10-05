"""
Entry 62: three new RTY pairs (NQ/RTY, ES/RTY, YM/RTY) as ONE bounded, pre-declared test.

Same signal logic, parameters and cost-aware scorecard as pairs_scorecard_v2.py (lookback 20,
entry z 2.0, exit z 0.5, stop z 3.5, max hold 15 trading days; micro sizing at 1/10th of full
size; per-leg 1pt slippage + $4.50 commission). Nothing was tuned: no parameter sweep, exactly
three pairs, run once. The three run_scorecard() calls below count as 3 new trials in
trial_count.count_research_trials(), so num_trials rises honestly and the DSR bar rises with it.
Not wired into live_gate.py; a pass here does NOT promote anything to live.
"""
import sys
sys.path.insert(0, "src")
from strategy import get_generic_pairs_signals_from_archive
from walk_forward import walk_forward_test
import scorecard
import trial_count

SCALE_FACTOR = 0.1
LEG_COSTS = {
    "MNQ": {"slippage_dollars": 1.0 * 2.0, "commission": 4.50},
    "MES": {"slippage_dollars": 1.0 * 5.0, "commission": 4.50},
    "MYM": {"slippage_dollars": 1.0 * 0.5, "commission": 4.50},
    "M2K": {"slippage_dollars": 1.0 * 5.0, "commission": 4.50},
}

PAIRS = [
    ("NQ/RTY Pairs", "MNQ", "M2K", "data/raw_nq_extended", "data/raw_rty_extended", 20, 50),
    ("ES/RTY Pairs", "MES", "M2K", "data/raw_es_extended", "data/raw_rty_extended", 50, 50),
    ("YM/RTY Pairs", "MYM", "M2K", "data/raw_ym_extended", "data/raw_rty_extended", 5, 50),
]


def to_scorecard_format(signals):
    signals = signals.copy()
    signals["entry_price"] = 0.0
    signals["exit_price"] = signals["pnl_dollars"] * SCALE_FACTOR
    signals["signal"] = "LONG"
    return signals


if __name__ == "__main__":
    num_trials = trial_count.count_research_trials()
    print(f"num_trials (DSR) = {num_trials}")
    for label, leg_a, leg_b, folder_a, folder_b, pv_a, pv_b in PAIRS:
        print("\n" + "#" * 70 + f"\n# {label}\n" + "#" * 70)
        raw = get_generic_pairs_signals_from_archive(folder_a, folder_b, point_value_a=pv_a, point_value_b=pv_b)
        raw = raw.sort_values("entry_date").reset_index(drop=True)
        signals = to_scorecard_format(raw)
        slippage = LEG_COSTS[leg_a]["slippage_dollars"] + LEG_COSTS[leg_b]["slippage_dollars"]
        commission = LEG_COSTS[leg_a]["commission"] + LEG_COSTS[leg_b]["commission"]
        print(f"Sample: {len(signals)} trades, {raw['entry_date'].min()} to {raw['entry_date'].max()}. "
              f"Cost: ${slippage:.2f} slippage + ${commission:.2f} commission per round trip.")
        walk_forward_test(signals, label, num_windows=4, date_col="entry_date", point_value=1)
        scorecard.run_scorecard(signals, label, num_trials=num_trials, account_size=10000, point_value=1,
                                 date_col="entry_date", slippage_points=slippage, commission=commission)
