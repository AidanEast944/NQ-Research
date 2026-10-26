import sys, os, json, unittest, tempfile, argparse, contextlib, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import research_runner as rr


def setup(fam_overrides=None):
    d = tempfile.mkdtemp()
    rr.REGISTRY = os.path.join(d, "reg.json"); rr.FAMILIES = os.path.join(d, "fam.json")
    reg = {"baseline_trials": 68, "trial_budget_total": 100,
           "tests": {"old": {"declared_trials": 27, "status": "scored"}}}
    json.dump(reg, open(rr.REGISTRY, "w"))
    fams = {"families": {"frozen_f": {"status": "frozen", "reason": "dead"},
                         "new_f": {"status": "proposed", "approved_by_human": False, "budget_trials": 3},
                         "ok_f": {"status": "active", "approved_by_human": True, "budget_trials": 3}}}
    for k, v in (fam_overrides or {}).items():
        fams["families"][k].update(v)
    json.dump(fams, open(rr.FAMILIES, "w"))
    rr.script_is_frozen = lambda path: (True, "abc12345" * 5)   # skip git
    return reg


def reg_args(id, trials, family=None):
    return argparse.Namespace(id=id, script="x.py", trials=trials, desc="d", family=family)


def try_register(reg, a):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rr.cmd_register(reg, a)
        return None
    except SystemExit as e:
        return str(e)


class TestFamilies(unittest.TestCase):
    def test_global_ledger_unchanged_for_legacy_tests(self):
        reg = setup(); self.assertEqual(rr.used_trials(reg), 95)

    def test_family_test_not_counted_globally(self):
        reg = setup(); self.assertIsNone(try_register(reg, reg_args("a", 2, "ok_f")))
        reg = rr.load(); self.assertEqual(rr.used_trials(reg), 95); self.assertEqual(rr.family_used(reg, "ok_f"), 2)

    def test_frozen_unapproved_unknown_refused(self):
        reg = setup()
        self.assertIn("FROZEN", try_register(reg, reg_args("a", 1, "frozen_f")))
        self.assertIn("no human-approved budget", try_register(reg, reg_args("b", 1, "new_f")))
        self.assertIn("unknown family", try_register(reg, reg_args("c", 1, "zzz")))

    def test_family_budget_enforced(self):
        reg = setup(); self.assertIsNone(try_register(reg, reg_args("a", 3, "ok_f")))
        self.assertIn("exceed family", try_register(rr.load(), reg_args("b", 1, "ok_f")))

    def test_global_budget_still_enforced_without_family(self):
        reg = setup(); self.assertIn("exceed the budget", try_register(reg, reg_args("a", 6)))
        self.assertIsNone(try_register(rr.load(), reg_args("b", 5)))


if __name__ == "__main__":
    unittest.main()
