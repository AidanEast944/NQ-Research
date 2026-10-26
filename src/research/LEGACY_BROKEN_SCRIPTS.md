# Legacy research scripts that no longer run (known, intentionally left unchanged)

These 15 scripts call `run_scorecard()` without the now-required `num_trials` argument, so running them raises a
`TypeError`. They are historical records of experiments already written up in `research_log.md`.

They are deliberately NOT edited:
* `trial_count.py` counts research trials by scanning these files' `run_scorecard` calls, so editing them could change the
  trial count that feeds every Deflated Sharpe Ratio.
* Re-running one is a new trial. If you ever want to, register it through `src/research_runner.py` instead of running it by hand.

Scripts: breakout_micro_sizing, crude_oil_gap_3pct_check, crude_oil_gap_test, full_analysis_extended, gap_vol_regime_test,
gold_gap_stop_target_test, overnight_drift_all_days_outlier_check, overnight_drift_stop_test, overnight_drift_test,
pairs_scorecard_v2, regime_filter_test, relative_momentum_rotation_test, volume_confirmed_gap_test, vwap_scorecard,
weekday_gap_correction_check.

Guard: `src/tests/test_scorecard_calls.py` fails if any OTHER script calls `run_scorecard()` without `num_trials`,
so this list cannot quietly grow.
