import sys, os, io, unittest, contextlib
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scorecard


def signals(n, edge_pts, seed=0):
    rng = np.random.default_rng(seed)
    move = rng.normal(edge_pts, 10, n)
    return pd.DataFrame({
        "signal": ["LONG"] * n,
        "entry_price": np.full(n, 1000.0),
        "exit_price": 1000.0 + move,
        "entry_date": pd.date_range("2020-01-01", periods=n, freq="B"),
    })


def run(df, trials=5, pv=2):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        scorecard.run_scorecard(df, "test", num_trials=trials, point_value=pv, date_col="entry_date")
    return buf.getvalue()


class TestScorecard(unittest.TestCase):
    def test_small_sample_fails_check_1(self):
        out = run(signals(30, 5))
        self.assertIn("[1] Sample size: 30", out)
        self.assertRegex(out.split("[1]")[1].split("[2]")[0], "FAIL")

    def test_large_sample_passes_check_1(self):
        out = run(signals(300, 5))
        self.assertRegex(out.split("[1]")[1].split("[2]")[0], "PASS")

    def test_zero_edge_fails_cost_check(self):
        out = run(signals(400, 0.0, seed=3))
        self.assertRegex(out.split("[6]")[1].split("[7]")[0], "FAIL")

    def test_more_trials_never_helps_dsr(self):
        def dsr(trials):
            line = [l for l in run(signals(400, 6, seed=7), trials=trials).splitlines() if "Deflated Sharpe Ratio" in l][0]
            return float(line.split(":")[1].split("(")[0])
        self.assertGreaterEqual(dsr(3), dsr(95))


if __name__ == "__main__":
    unittest.main()
