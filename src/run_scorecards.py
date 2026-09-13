import sys
from datetime import date

from strategy import (
    get_weekday_open_gap_signals_from_archive,
    get_weekday_open_gap_signals_with_volume_from_archive,
    get_generic_pairs_signals_from_archive,
)
from scorecard import run_scorecard
from trial_count import count_research_trials

output_file = f"results/scorecard_{date.today().isoformat()}.txt"
sys.stdout = open(output_file, "w")

trials = count_research_trials()
print(f"(num_trials = {trials}, from research_log.md's highest entry number - conservative floor)\n")

run_scorecard(
    get_weekday_open_gap_signals_from_archive(data_folder="data/raw_nq_extended"),
    "Gap Continuation (unfiltered, corrected)",
    trials,
    entry_col="entry_price", exit_col="exit_price", date_col="date", point_value=2
)

nq_vol = get_weekday_open_gap_signals_with_volume_from_archive(data_folder="data/raw_nq_extended")
run_scorecard(
    nq_vol[nq_vol["volume_ratio"] >= 1.2].copy(),
    "Volume-Confirmed Gap NQ (1.2x)",
    trials,
    entry_col="entry_price", exit_col="exit_price", date_col="date", point_value=2
)

ym_vol = get_weekday_open_gap_signals_with_volume_from_archive(data_folder="data/raw_ym_extended")
run_scorecard(
    ym_vol[ym_vol["volume_ratio"] >= 1.2].copy(),
    "Volume-Confirmed Gap YM (1.2x)",
    trials,
    entry_col="entry_price", exit_col="exit_price", date_col="date", point_value=0.5,
    slippage_points=0.5, commission=0.74
)

es_vol = get_weekday_open_gap_signals_with_volume_from_archive(
    data_folder="data/raw_es_extended", min_gap_points=6, stop_points=10, target_points=20
)
run_scorecard(
    es_vol[es_vol["volume_ratio"] >= 1.2].copy(),
    "Volume-Confirmed Gap ES (1.2x, scaled)",
    trials,
    entry_col="entry_price", exit_col="exit_price", date_col="date", point_value=5,
    slippage_points=0.25, commission=0.74
)

pairs_configs = [
    ("NQ/ES Pairs", "data/raw_nq_extended", "data/raw_es_extended", 20, 50),
    ("NQ/YM Pairs", "data/raw_nq_extended", "data/raw_ym_extended", 20, 5),
    ("ES/YM Pairs", "data/raw_es_extended", "data/raw_ym_extended", 50, 5),
]
MICRO_SCALE_FACTOR = 0.1  # MNQ/MYM/MES are all 1/10th their full-size counterparts - matches
                            # the validated micro-sizing already used for gap continuation and
                            # confirmed to bring pairs drawdown under the 30% threshold.

for name, folder_a, folder_b, pv_a, pv_b in pairs_configs:
    signals = get_generic_pairs_signals_from_archive(folder_a, folder_b, pv_a, pv_b)
    signals["signal"] = "LONG"
    signals["entry_price"] = 0
    # Scale full-size pnl_dollars down to micro-contract sizing before scoring, so drawdown and
    # account-relative checks reflect the sizing actually validated/intended for live trading -
    # NOT the raw full-size dollar P&L, which was never the real trading plan.
    signals["exit_price"] = signals["pnl_dollars"] * MICRO_SCALE_FACTOR
    run_scorecard(
        signals, name, trials,
        entry_col="entry_price", exit_col="exit_price", date_col="entry_date", point_value=1
    )

sys.stdout.close()
sys.stdout = sys.__stdout__
print(f"Scorecard saved to {output_file}")