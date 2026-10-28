import sys, os, unittest, tempfile, io, contextlib, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
sys.path.append(os.path.join(HERE, "..", "research"))
import carry as C
import dlt_engine as E
import dlt_test as T
import leakage


def frames(n=800, roll_every=91, spread=0.01, seed=0):
    idx = pd.bdate_range("2012-01-02", periods=n)
    rng = np.random.default_rng(seed)
    c = 100 * np.cumprod(1 + rng.normal(0, 0.005, n))
    ids = (np.arange(n) // int(roll_every * 5 / 7)) + 1
    front = pd.DataFrame({"close": c, "instrument_id": ids}, index=idx)
    second = pd.DataFrame({"close": c * np.exp(-spread)}, index=idx)      # second cheaper than front -> backwardation
    return front, second


class TestCarry(unittest.TestCase):
    def test_spacing_from_past_rolls(self):
        f, _ = frames()
        sp = C.spacing_days(f)
        self.assertTrue(sp.iloc[:60].isna().all())
        self.assertAlmostEqual(float(sp.iloc[-1]), 91, delta=4)

    def test_backwardation_positive_contango_negative_and_scaled(self):
        f, s = frames(spread=0.01)
        cr = C.carry_series(f, s)
        self.assertAlmostEqual(float(cr.iloc[-1]), 0.01 * 365 / 91, delta=0.05)
        f2, s2 = frames(spread=-0.01)
        self.assertLess(float(C.carry_series(f2, s2).iloc[-1]), 0)

    def test_no_lookahead(self):
        f, s = frames()
        both = f.join(s.rename(columns={"close": "close2"}))
        fn = lambda d: C.carry_series(d[["close", "instrument_id"]], d[["close2"]].rename(columns={"close2": "close"}))
        ok, msg = leakage.truncation_test(fn, both, min_rows=120)
        self.assertTrue(ok, msg)

    def test_tscarry_follows_sign_and_xscarry_is_balanced(self):
        idx = pd.bdate_range("2012-01-02", periods=400)
        rng = np.random.default_rng(2)
        cols = ["6E", "6J", "6B", "6A"]
        rets = pd.DataFrame(rng.normal(0, 0.005, (400, 4)), index=idx, columns=cols)
        score = pd.DataFrame({"6E": 0.03, "6J": -0.02, "6B": 0.01, "6A": -0.04}, index=idx)
        w = E.target_weights(rets, 0, "tscarry", classes={"fx": cols}, score=score).dropna(how="all").iloc[-1]
        self.assertEqual(list(np.sign(w)), [1, -1, 1, -1])
        wx = E.target_weights(rets, 0, "xscarry", classes={"fx": cols}, score=score).dropna(how="all").iloc[-1]
        self.assertEqual(list(np.sign(wx)), [1, -1, 1, -1])      # top two long, bottom two short
        with self.assertRaises(ValueError):
            E.target_weights(rets, 0, "tscarry")


class TestCarryHarness(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd(); os.chdir(os.path.abspath(os.path.join(HERE, "..", "..")))

    def tearDown(self):
        os.chdir(self.cwd)

    def _dirs(self):
        d, c1 = tempfile.mkdtemp(), None
        c1 = os.path.join(d, "c1"); os.makedirs(c1)
        idx = pd.bdate_range("2010-06-08", "2024-06-30")
        rng = np.random.default_rng(9)
        for k, s in enumerate(T.universe(T.family_cfg())):
            r = rng.normal(0.0001, 0.01, len(idx)); c = 100 * np.cumprod(1 + r)
            ids = (np.arange(len(idx)) // 64) + 1
            pd.DataFrame({"date": idx, "open": c, "high": c, "low": c, "close": c, "volume": 1000, "instrument_id": ids}).to_csv(
                os.path.join(d, f"{s}.csv"), index=False)
            pd.DataFrame({"date": idx, "open": c, "high": c, "low": c, "close": c * np.exp(0.004 * np.sign(np.sin(k + np.arange(len(idx)) / 300))),
                          "volume": 1000, "instrument_id": ids}).to_csv(os.path.join(c1, f"{s}.csv"), index=False)
        return d

    def test_end_to_end_both_carry_kinds_pass_validator_and_cut_holdout(self):
        import validator
        d = self._dirs()
        pol = json.load(open("lab/policy.json")); fams = json.load(open("registry/families.json"))
        for kind in ("tscarry", "xscarry"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res, verdict = T.run({"id": f"dlt_{kind}", "kind": kind, "months": 0, "declared_trials": 1}, data_dir=d, write=False)
            out = buf.getvalue()
            self.assertIn("look-ahead truncation test on the carry score: PASS", out)
            self.assertNotIn("2024-", out)
            v = validator.check_many(res, pol, fams)
            self.assertTrue(v[f"dlt_{kind}"]["passed_deterministic_checks"], v)

    def test_refuses_without_second_contract_files(self):
        d = self._dirs()
        os.remove(os.path.join(d, "c1", "ZN.csv"))
        with self.assertRaises(SystemExit):
            T.run({"id": "dlt_tscarry", "kind": "tscarry", "months": 0, "declared_trials": 1}, data_dir=d, write=False)


if __name__ == "__main__":
    unittest.main()
