from strategy import get_vwap_reversion_signals_from_archive
from scorecard import run_scorecard

signals = get_vwap_reversion_signals_from_archive(stretch_points=50, stop_points=30, target_points=40)
run_scorecard(signals, "VWAP Mean-Reversion (50pt stretch, 30/40)", date_col="date")