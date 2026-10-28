import sys, os, json, unittest, io, contextlib
HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
sys.path.append(os.path.join(HERE, "..", "research"))
import dv_test as V
import test_discover as TD


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd(); os.chdir(REPO)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_runs_end_to_end_cuts_holdout_and_passes_validator(self):
        import validator
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res, verdict = V.run("tsmom_L252_skip21_rebalM", data_dir=TD.synth_dir(trend=True), write=False)
        out = buf.getvalue()
        self.assertIn("look-ahead truncation test on the signal: PASS", out)
        self.assertRegex(out, r"validation 2020-01-0\d\.\.2023-12-\d\d")   # window ends before the sealed holdout
        self.assertNotIn("2024-", out)
        pol = json.load(open("lab/policy.json")); fams = json.load(open("registry/families.json"))
        v = validator.check_many(res, pol, fams)
        self.assertTrue(list(v.values())[0]["passed_deterministic_checks"], v)

    def test_unknown_candidate_refused(self):
        with self.assertRaises(SystemExit):
            V.candidate_from_id("not_a_candidate")

    def test_refuses_partial_universe(self):
        d = TD.synth_dir(); os.remove(os.path.join(d, "NQ.csv"))
        with self.assertRaises(SystemExit):
            V.run("tsmom_L252_skip21_rebalM", data_dir=d, write=False)

    def test_all_three_specs_pass_lab_guards(self):
        import specs, guard
        pol = json.load(open("lab/policy.json")); fams = json.load(open("registry/families.json")); reg = json.load(open("registry/research_registry.json"))
        for cid in ("dv_tsmom_L252_skip21_rebalM", "dv_macross_fast40_slow250_rebalM", "dv_xsmom_L252_skip0_rebalW"):
            spec = json.load(open(f"lab/proposals/{cid}.json"))
            self.assertEqual(specs.validate_shape(spec, pol, fams["families"]["discovery_validation"]), [])
            self.assertEqual(guard.family_problems(spec, fams, reg, [])[0], [])
            self.assertLess(spec["oos_data"]["end"], "2024-01-01")
            V.candidate_from_id(cid[3:])


if __name__ == "__main__":
    unittest.main()
