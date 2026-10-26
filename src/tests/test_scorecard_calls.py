import ast, glob, os, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEGACY = {  # see src/research/LEGACY_BROKEN_SCRIPTS.md
    "breakout_micro_sizing", "crude_oil_gap_3pct_check", "crude_oil_gap_test", "full_analysis_extended",
    "gap_vol_regime_test", "gold_gap_stop_target_test", "overnight_drift_all_days_outlier_check",
    "overnight_drift_stop_test", "overnight_drift_test", "pairs_scorecard_v2", "regime_filter_test",
    "relative_momentum_rotation_test", "volume_confirmed_gap_test", "vwap_scorecard", "weekday_gap_correction_check",
}


class TestScorecardCalls(unittest.TestCase):
    def test_no_new_script_omits_num_trials(self):
        offenders = set()
        for f in glob.glob(os.path.join(ROOT, "src", "**", "*.py"), recursive=True):
            if os.sep + "tests" + os.sep in f:
                continue
            tree = ast.parse(open(f).read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", None)) == "run_scorecard":
                    if "num_trials" not in {k.arg for k in n.keywords} and len(n.args) < 3:
                        offenders.add(os.path.splitext(os.path.basename(f))[0])
        self.assertEqual(offenders - LEGACY, set(), "new script calls run_scorecard() without num_trials")


if __name__ == "__main__":
    unittest.main()
