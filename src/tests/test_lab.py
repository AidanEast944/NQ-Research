import sys, os, json, glob, shutil, tempfile, unittest
from datetime import datetime
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
import orchestrator as orch, guard, leakage, validator, specs

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
NOW = datetime(2026, 10, 26, 12, 0)  # a Monday


def make_root(budget_used=0):
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "lab", "proposals")); os.makedirs(os.path.join(root, "registry"))
    shutil.copy(os.path.join(REPO, "lab", "policy.json"), os.path.join(root, "lab", "policy.json"))
    reg = {"baseline_trials": 68 + budget_used, "trial_budget_total": 100, "tests": {}}
    json.dump(reg, open(os.path.join(root, "registry", "research_registry.json"), "w"))
    return root


def spec(i="s1", trials=1, **kw):
    s = {"id": i, "title": "t", "hypothesis": "h", "symbols": ["NQ"],
         "discovery_data": {"start": "2015-01-01", "end": "2020-12-31"},
         "oos_data": {"start": "2021-01-01", "end": "2023-12-31"},
         "rules": {"entry": "gap>0.2%", "exit": "16:00"}, "parameters": {"k": 1},
         "declared_trials": trials, "cost_model": {"slippage_points": 1.0, "commission_round_trip": 4.5},
         "author": "claude"}
    s.update(kw); return s


def put(root, s):
    p = os.path.join(root, "lab", "proposals", s["id"] + ".json")
    json.dump(s, open(p, "w")); return p


class TestSubmit(unittest.TestCase):
    def test_accepts_valid_and_logs(self):
        r = make_root(); ok, m = orch.submit(r, put(r, spec()), NOW)
        self.assertTrue(ok, m)
        ev = [json.loads(l)["event"] for l in open(os.path.join(r, "lab/state/agent_log.jsonl"))]
        self.assertIn("queued", ev)

    def test_duplicate_rejected_and_recorded(self):
        r = make_root(); orch.submit(r, put(r, spec("a")), NOW)
        ok, m = orch.submit(r, put(r, spec("b")), NOW)
        self.assertFalse(ok); self.assertIn("duplicate", m[0])
        ev = [json.loads(l)["event"] for l in open(os.path.join(r, "lab/state/agent_log.jsonl"))]
        self.assertIn("rejected_duplicate", ev)

    def test_parameter_sweep_warns(self):
        r = make_root(); orch.submit(r, put(r, spec("a")), NOW)
        ok, m = orch.submit(r, put(r, spec("b", parameters={"k": 2})), NOW)
        self.assertTrue(ok); self.assertTrue(any("WARNING" in x for x in m))

    def test_weekly_allowance_refuses(self):
        r = make_root(); orch.submit(r, put(r, spec("a", trials=2)), NOW)
        ok, m = orch.submit(r, put(r, spec("b", trials=1, parameters={"k": 9})), NOW)
        self.assertFalse(ok); self.assertIn("weekly", m[0])

    def test_budget_refuses(self):
        r = make_root(budget_used=31)  # 99 used, 1 left
        ok, m = orch.submit(r, put(r, spec("a", trials=2)), NOW)
        self.assertFalse(ok); self.assertIn("remaining", m[0])

    def test_holdout_blocked_for_discovery(self):
        r = make_root(); ok, m = orch.submit(r, put(r, spec(symbols=["RTY"])), NOW)
        self.assertFalse(ok); self.assertIn("holdout", m[0])

    def test_holdout_confirmation_allowed_for_rty_only(self):
        r = make_root(); ok, m = orch.submit(r, put(r, spec(symbols=["RTY"], holdout_confirmation=True)), NOW)
        self.assertTrue(ok, m)

    def test_overlapping_oos_rejected(self):
        r = make_root(); s = spec(); s["oos_data"]["start"] = "2020-06-01"
        ok, m = orch.submit(r, put(r, s), NOW); self.assertFalse(ok)

    def test_wrong_cost_model_rejected(self):
        r = make_root(); ok, m = orch.submit(r, put(r, spec(cost_model={"slippage_points": 0, "commission_round_trip": 0})), NOW)
        self.assertFalse(ok)

    def test_spec_outside_proposals_refused(self):
        r = make_root(); p = os.path.join(r, "elsewhere.json"); json.dump(spec(), open(p, "w"))
        ok, m = orch.submit(r, p, NOW); self.assertFalse(ok)

    def test_approve_is_decision_only(self):
        r = make_root(); orch.submit(r, put(r, spec()), NOW)
        ok, _ = orch.decide(r, "s1", "approved", "ok"); self.assertTrue(ok)
        reg = json.load(open(os.path.join(r, "registry/research_registry.json")))
        self.assertEqual(reg["tests"], {})  # registry untouched


class TestLeakage(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.df = pd.DataFrame({"Close": 100 + rng.normal(0, 1, 400).cumsum()})

    def test_clean_feature_passes(self):
        ok, _ = leakage.truncation_test(lambda d: d["Close"].rolling(10).mean(), self.df)
        self.assertTrue(ok)

    def test_planted_lookahead_detected(self):
        ok, msg = leakage.truncation_test(lambda d: d["Close"].shift(-1) - d["Close"], self.df)
        self.assertFalse(ok); self.assertIn("look-ahead", msg)

    def test_planted_full_sample_normalisation_detected(self):
        ok, _ = leakage.truncation_test(lambda d: (d["Close"] - d["Close"].mean()) / d["Close"].std(), self.df)
        self.assertFalse(ok)


class TestValidator(unittest.TestCase):
    good = {"scorecard_run": True, "n_trades": 150, "n_oos_trades": 30,
            "cost_model": {"slippage_points": 1.0, "commission_round_trip": 4.5},
            "leakage_test_passed": True, "holdout_touched": False, "declared_trials": 2}
    pol = json.load(open(os.path.join(REPO, "lab", "policy.json")))

    def test_good_passes_checks(self):
        self.assertTrue(validator.check_result(self.good, self.pol)["passed_deterministic_checks"])

    def test_each_veto(self):
        for k, v in [("scorecard_run", False), ("n_trades", 10), ("n_oos_trades", 3),
                     ("cost_model", {}), ("leakage_test_passed", None), ("holdout_touched", True),
                     ("declared_trials", None)]:
            r = dict(self.good); r[k] = v
            self.assertFalse(validator.check_result(r, self.pol)["passed_deterministic_checks"], k)


class TestNoLiveAuthority(unittest.TestCase):
    def test_lab_source_never_touches_live_files(self):
        import ast
        banned = ["live_gate", "risk_limits", "paper_broker", "paper_account"]
        for f in glob.glob(os.path.join(REPO, "src", "lab", "*.py")):
            tree = ast.parse(open(f).read())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 200:
                    names = [node.value]  # short string literals (paths); long ones are docstrings
                for n in names:
                    for b in banned:
                        self.assertNotIn(b, n, f"{f} references {b}")

    def test_lab_does_not_write_registry(self):
        for f in glob.glob(os.path.join(REPO, "src", "lab", "*.py")):
            src = open(f).read()
            self.assertNotIn('open(P["registry"], "w")', src)
            self.assertNotIn("research_registry.json\", \"w\"", src)


if __name__ == "__main__":
    unittest.main()
