import sys, os, unittest
import numpy as np
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "research"))   # append: src/research has a same-named test_paper_broker.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dlt_engine as E
from lab import leakage


def synth(n=900, cols=("ES", "NQ", "ZN", "ZB", "CL", "GC"), seed=1, drift=None):
    idx = pd.bdate_range("2012-01-02", periods=n)
    rng = np.random.default_rng(seed)
    d = rng.normal(0, 0.01, (n, len(cols)))
    if drift is not None:
        d = d + np.array(drift)
    r = pd.DataFrame(d, index=idx, columns=list(cols))
    p = 100 * (1 + r).cumprod()
    return r, p


class TestEngine(unittest.TestCase):
    def test_no_lookahead_in_score(self):
        r, _ = synth()
        fn = lambda d: E.momentum_score(d["ES"], 6)
        ok, msg = leakage.truncation_test(fn, r)
        self.assertTrue(ok, msg)

    def test_weights_are_lagged_one_day(self):
        # A huge return on the LAST day cannot change any earlier weight or return
        r, p = synth()
        a, _ = E.backtest(r, p, 6, "tsmom", classes={"x": ["ES", "NQ"]})
        r2 = r.copy(); r2.iloc[-1] = 0.5
        b, _ = E.backtest(r2, p, 6, "tsmom", classes={"x": ["ES", "NQ"]})
        pd.testing.assert_series_equal(a["gross"].iloc[:-1], b["gross"].iloc[:-1])

    def test_trending_market_makes_money_gross(self):
        r, p = synth(drift=[0.001, 0.001, -0.001, -0.001, 0.001, -0.001], n=1200)
        bt, _ = E.backtest(r, p, 6, "tsmom")
        self.assertGreater(E.sharpe(bt["gross"].iloc[300:]), 1.0)

    def test_costs_reduce_returns(self):
        r, p = synth()
        bt, _ = E.backtest(r, p, 3, "tsmom")
        self.assertTrue((bt["net"] <= bt["gross"] + 1e-12).all())
        self.assertGreater(bt["cost"].sum(), 0)

    def test_rebalances_only_at_month_end(self):
        r, p = synth()
        _, w = E.backtest(r, p, 3, "tsmom")
        changed = w.diff().abs().sum(axis=1) > 1e-12
        flags = E.month_end_flags(r.index).shift(1).fillna(False).astype(bool)
        self.assertFalse((changed & ~flags).any())

    def test_xsmom_is_roughly_dollar_neutral_within_class(self):
        r, p = synth(cols=("6E", "6J", "6B", "6A"), n=700)
        w = E.target_weights(r, 6, "xsmom", classes={"fx": ["6E", "6J", "6B", "6A"]}).dropna(how="all")
        signs = np.sign(w.iloc[-1])
        self.assertEqual(int(signs.sum()), 0)
        self.assertEqual(int((signs != 0).sum()), 4)

    def test_leverage_capped(self):
        r, p = synth()
        r["ES"] = r["ES"] * 0.0001          # near-zero vol would blow up the scale without the cap
        w = E.target_weights(r, 6, "tsmom").dropna(how="all")
        self.assertLessEqual(w.abs().max().max(), E.MAX_LEV + 1e-9)

    def test_bad_kind_rejected(self):
        r, p = synth()
        with self.assertRaises(ValueError):
            E.target_weights(r, 6, "magic")


if __name__ == "__main__":
    unittest.main()
