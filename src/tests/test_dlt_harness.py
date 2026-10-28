import sys, os, unittest, tempfile, io, contextlib
import numpy as np
import pandas as pd
HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.append(os.path.join(HERE, "..", "research"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
import dlt_test as T


def make_dir(skip=()):
    d = tempfile.mkdtemp()
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2010-06-08", "2024-06-30")
    for s in T.universe(T.family_cfg()):
        if s in skip:
            continue
        r = rng.normal(0.0002, 0.01, len(idx))
        c = 100 * np.cumprod(1 + r)
        pd.DataFrame({"date": idx, "open": c, "high": c, "low": c, "close": c, "volume": 1000, "instrument_id": 1}).to_csv(
            os.path.join(d, f"{s}.csv"), index=False)
    return d


class TestHarness(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        os.chdir(REPO)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_refuses_partial_universe(self):
        with self.assertRaises(SystemExit):
            T.load_data(T.universe(T.family_cfg()), make_dir(skip=("NQ",)))

    def test_sealed_holdout_is_cut_before_computation(self):
        rets, prices = T.load_data(T.universe(T.family_cfg()), make_dir())
        self.assertLessEqual(rets.index.max(), pd.Timestamp("2023-12-31"))
        self.assertLessEqual(prices.index.max(), pd.Timestamp("2023-12-31"))

    def test_end_to_end_on_synthetic_data_writes_valid_result(self):
        import validator, json
        d = make_dir()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res, verdict = T.run({"id": "dlt_unit", "kind": "tsmom", "months": 6, "declared_trials": 1}, data_dir=d, write=False)
        self.assertIn("look-ahead truncation test on the momentum score: PASS", buf.getvalue())
        self.assertIn(verdict, ("SUPPORTED", "INCONCLUSIVE", "NOT SUPPORTED"))
        pol = json.load(open("lab/policy.json")); fams = json.load(open("registry/families.json"))
        out = validator.check_many(res, pol, fams)
        self.assertTrue(out["dlt_unit"]["passed_deterministic_checks"], out)

    def test_validator_rejects_wrong_family_cost_model(self):
        import validator, json
        pol = json.load(open("lab/policy.json")); fams = json.load(open("registry/families.json"))
        res = {"x": {"family": T.FAMILY, "n_trades": 150, "n_oos_trades": 48, "scorecard_run": True, "leakage_test_passed": True,
                     "cost_model": {"slippage_bps_of_notional": 0.0, "commission_round_trip_per_contract": 0.0},
                     "holdout_touched": False, "declared_trials": 1}}
        out = validator.check_many(res, pol, fams)
        self.assertFalse(out["x"]["passed_deterministic_checks"])


if __name__ == "__main__":
    unittest.main()
