import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
import pandas as pd
from strategy import get_prior_day_break_signals_from_archive

class TestPriorDayBreak(unittest.TestCase):

    def test_returns_dataframe_with_expected_columns(self):
        """The function should always return a DataFrame with these exact columns,
        even if there are zero signals - this is the exact bug we hit months ago
        when an empty result crashed instead of returning gracefully."""
        result = get_prior_day_break_signals_from_archive(stop_points=30, target_points=60)
        expected_columns = ["date", "signal", "Close", "exit_price", "exit_reason"]
        for col in expected_columns:
            self.assertIn(col, result.columns)

    def test_signals_are_only_long_or_short(self):
        """Every row's signal should be exactly LONG or SHORT - never NONE,
        since NONE rows should have been filtered out already."""
        result = get_prior_day_break_signals_from_archive(stop_points=30, target_points=60)
        unique_signals = result["signal"].unique()
        for signal in unique_signals:
            self.assertIn(signal, ["LONG", "SHORT"])

    def test_exit_reason_is_valid(self):
        """Every closed trade should have exited for one of these three reasons -
        anything else would indicate a logic bug in the simulation."""
        result = get_prior_day_break_signals_from_archive(stop_points=30, target_points=60)
        valid_reasons = ["stop", "target", "eod"]
        unique_reasons = result["exit_reason"].dropna().unique()
        for reason in unique_reasons:
            self.assertIn(reason, valid_reasons)

if __name__ == "__main__":
    unittest.main()