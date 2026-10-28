import sys, os, json, ast, shutil, tempfile, unittest
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
import proposer as P

SRC = os.path.join(HERE, "..", "lab", "proposer.py")
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def sandbox():
    root = tempfile.mkdtemp()
    for rel in ("lab/policy.json", "registry/families.json", "registry/research_registry.json"):
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copy(os.path.join(REPO, rel), os.path.join(root, rel))
    os.makedirs(os.path.join(root, "lab/state"))
    os.makedirs(os.path.join(root, "src/research"))
    with open(os.path.join(root, "lab/state/queue.json"), "w") as f:
        json.dump([], f)
    return root


class TestProposer(unittest.TestCase):
    def test_menu_is_fixed_eight(self):
        self.assertEqual(len(P.ORDER), 8)
        self.assertEqual(len(set(P.ORDER)), 8)
        self.assertEqual({m for k, m in P.ORDER if not k.endswith("carry")}, {3, 6, 12})
        self.assertEqual([k for k, _ in P.ORDER if k.endswith("carry")], ["tscarry", "xscarry"])

    def test_only_carry_drafts_just_the_carry_items(self):
        root = sandbox()
        P.cmd_draft(root, 5, only="carry")
        names = sorted(os.listdir(os.path.join(root, "lab/proposals")))
        self.assertEqual(names, ["dlt_tscarry.json", "dlt_xscarry.json"])
        spec = json.load(open(os.path.join(root, "lab/proposals/dlt_tscarry.json")))
        self.assertIn("carry", spec["parameters"]["kind"])
        self.assertTrue(os.path.exists(os.path.join(root, "src/research/dlt_tscarry_test.py")))

    def test_draft_writes_valid_spec_and_script_in_order(self):
        root = sandbox()
        self.assertEqual(P.cmd_draft(root, 1), 0)
        self.assertTrue(os.path.exists(os.path.join(root, "lab/proposals/dlt_tsmom_12m.json")))
        self.assertTrue(os.path.exists(os.path.join(root, "src/research/dlt_tsmom_12m_test.py")))
        self.assertFalse(os.path.exists(os.path.join(root, "lab/proposals/dlt_xsmom_12m.json")))
        P.cmd_draft(root, 1)
        self.assertTrue(os.path.exists(os.path.join(root, "lab/proposals/dlt_xsmom_12m.json")))

    def test_drafted_spec_passes_lab_shape_and_family_guards(self):
        import specs, guard
        root = sandbox()
        P.cmd_draft(root, 8)
        pol = guard.load_json(os.path.join(root, "lab/policy.json"))
        fams = guard.load_json(os.path.join(root, "registry/families.json"))
        reg = guard.load_json(os.path.join(root, "registry/research_registry.json"))
        for k, m in P.ORDER:
            spec = json.load(open(os.path.join(root, "lab/proposals", f"{P.cand_id(k, m)}.json")))
            fam = fams["families"][P.FAMILY]
            self.assertEqual(specs.validate_shape(spec, pol, fam), [])
            self.assertEqual(guard.family_problems(spec, fams, reg, [])[0], [])
            self.assertEqual(spec["declared_trials"], 1)
            self.assertLess(spec["oos_data"]["end"], "2024-01-01")     # never reaches the sealed holdout

    def test_eight_drafts_then_nothing_left(self):
        root = sandbox()
        P.cmd_draft(root, 10)
        n = len(os.listdir(os.path.join(root, "lab/proposals")))
        self.assertEqual(n, 8)

    def test_does_not_overwrite_existing(self):
        root = sandbox()
        P.cmd_draft(root, 1)
        p = os.path.join(root, "lab/proposals/dlt_tsmom_12m.json")
        open(p, "w").write('{"marker": 1}')
        P.cmd_draft(root, 1)
        self.assertEqual(json.load(open(p)), {"marker": 1})

    def test_proposer_has_no_authority_over_gates_or_live_files(self):
        tree = ast.parse(open(SRC).read())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for banned in ("submit", "decide", "approve", "mark_registered", "live_gate", "save_queue", "append_hyp"):
            self.assertNotIn(banned, names)
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imports |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertNotIn("orchestrator", imports)
        text = open(SRC).read()
        for protected in ("live_gate.py", "families.json\", \"w", "policy.json\", \"w"):
            self.assertNotIn(f"open(os.path.join(root, \"{protected}", text)


if __name__ == "__main__":
    unittest.main()
