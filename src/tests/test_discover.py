import sys, os, json, unittest, tempfile, shutil
import numpy as np
import pandas as pd
HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
sys.path.append(os.path.join(HERE, "..", "research"))
import discover as D
import leakage


def synth_dir(trend=False):
    d = tempfile.mkdtemp()
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2010-06-08", "2024-06-30")
    for k, s in enumerate(D.universe()):
        r = rng.normal(0.0001, 0.01, len(idx))
        if trend:   # slow persistent regimes so trend rules have something to find
            reg = np.sign(np.sin(np.arange(len(idx)) / (150 + 10 * k)))
            r = r + 0.0008 * reg
        c = 100 * np.cumprod(1 + r)
        pd.DataFrame({"date": idx, "open": c, "high": c, "low": c, "close": c, "volume": 1000, "instrument_id": 1}).to_csv(
            os.path.join(d, f"{s}.csv"), index=False)
    return d


def small_grid():
    return [c for c in D.build_grid() if (c["family"], c["params"].get("L"), c["params"].get("N"), c["params"].get("fast"),
                                          c["params"].get("slow"), c["params"].get("skip")) in
            {("tsmom", 126, None, None, None, 0), ("tsmom", 63, None, None, None, 0), ("tsmom", 189, None, None, None, 0),
             ("breakout", None, 60, None, None, None), ("breakout", None, 40, None, None, None), ("breakout", None, 90, None, None, None),
             ("macross", None, None, 20, 100, None), ("macross", None, None, 20, 150, None), ("macross", None, None, 10, 100, None),
             ("reversal", 5, None, None, None, None), ("xsmom", 126, None, None, None, 0)}]


class TestDiscover(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd(); os.chdir(REPO)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_grid_is_deterministic_and_ids_unique(self):
        a, b = D.build_grid(), D.build_grid()
        self.assertEqual([c["id"] for c in a], [c["id"] for c in b])
        self.assertEqual(len({c["id"] for c in a}), len(a))
        self.assertEqual(len(a), 240)

    def test_every_signal_family_is_free_of_lookahead(self):
        rng = np.random.default_rng(1)
        idx = pd.bdate_range("2012-01-02", periods=900)
        rets = pd.DataFrame(rng.normal(0, 0.01, (900, 4)), index=idx, columns=["ES", "NQ", "ZN", "ZB"])
        ix = D.adj_index(rets)
        for c in D.build_grid():
            if c["volfilter"] or c["params"].get("rebal") == "M":
                continue
            fn = lambda d, c=c: D.signal(c, D.adj_index(d), d)["ES"]
            ok, msg = leakage.truncation_test(fn, rets, min_rows=320)
            self.assertTrue(ok, f"{c['id']}: {msg}")

    def test_future_shock_changes_nothing_earlier(self):
        import dlt_engine as E
        rets, prices = D.load_discovery_data(D.universe(), synth_dir())
        for c in small_grid()[:6]:
            a, _ = E.run_weights(D.decided_weights(c, rets), rets, prices)
            r2 = rets.copy(); r2.iloc[-1] = 0.9
            b, _ = E.run_weights(D.decided_weights(c, r2), r2, prices)
            pd.testing.assert_series_equal(a["net"].iloc[:-1], b["net"].iloc[:-1], check_exact=False, atol=1e-12)

    def test_data_after_2019_is_never_loaded(self):
        rets, prices = D.load_discovery_data(D.universe(), synth_dir())
        self.assertLessEqual(rets.index.max(), pd.Timestamp("2019-12-31"))

    def test_refuses_partial_universe(self):
        d = synth_dir(); os.remove(os.path.join(d, "NQ.csv"))
        with self.assertRaises(SystemExit):
            D.load_discovery_data(D.universe(), d)

    def test_gate_refuses_without_human_approval(self):
        root = tempfile.mkdtemp(); os.makedirs(os.path.join(root, "registry"))
        json.dump({"families": {"discovery_search": {"status": "active", "approved_by_human": False, "budget_evaluations": 300}}},
                  open(os.path.join(root, "registry/families.json"), "w"))
        with self.assertRaises(SystemExit):
            D.gate(root)

    def test_run_counts_trials_dedupes_and_enforces_budget(self):
        root = tempfile.mkdtemp(); d = synth_dir()
        g = small_grid()
        rows, review, out = D.run(root=root, data_dir=d, grid=g, gate_check=False)
        led = D.load_ledger(root)
        self.assertEqual(len(led["evaluated"]), len(g))
        self.assertTrue(os.path.exists(os.path.join(out, "review.md")))
        self.assertIn("Validation (2020-2023) and the sealed holdout (2024+) were not read", review)
        D.run(root=root, data_dir=d, grid=g, gate_check=False)           # same grid again: no new trials
        self.assertEqual(len(D.load_ledger(root)["evaluated"]), len(g))
        # budget check through the real gate with a tiny approved budget
        os.makedirs(os.path.join(root, "registry"), exist_ok=True)
        json.dump({"families": {"discovery_search": {"status": "active", "approved_by_human": True, "budget_evaluations": len(g)}}},
                  open(os.path.join(root, "registry/families.json"), "w"))
        with self.assertRaises(SystemExit):
            D.run(root=root, data_dir=d, grid=D.build_grid()[:len(g) + 5] + g, gate_check=True)

    def test_filters_flag_each_failure(self):
        base = {"id": "x", "family": "tsmom", "params": {"L": 126, "skip": 0, "rebal": "M"}, "volfilter": False, "sharpe_net": 0.8,
                "sharpe_h1": 0.5, "sharpe_h2": 0.4, "breadth": 0.7, "cost_drag_yr": 0.01}
        rows = [dict(base)]
        D.apply_filters(rows)
        self.assertIn("neighbors", rows[0]["fails"])       # no neighbours present -> not robust
        self.assertFalse(rows[0]["passes"])
        bad = dict(base, sharpe_h2=-0.1, breadth=0.3, sharpe_net=0.1, cost_drag_yr=0.05, id="y")
        rows = [bad]; D.apply_filters(rows)
        for f in ("sharpe", "half2", "breadth", "costs"):
            self.assertIn(f, rows[0]["fails"])

    def test_neighbour_robustness_rewards_a_plateau_not_a_spike(self):
        def row(L, s):
            return {"id": D.cand_id({"family": "tsmom", "params": {"L": L, "skip": 0, "rebal": "M"}, "volfilter": False}),
                    "family": "tsmom", "params": {"L": L, "skip": 0, "rebal": "M"}, "volfilter": False, "sharpe_net": s}
        plateau = {r["id"]: r for r in (row(63, 0.7), row(84, 0.8), row(126, 0.75))}
        spike = {r["id"]: r for r in (row(63, 0.0), row(84, 0.8), row(126, 0.0))}
        self.assertGreater(D.neighbor_ratio(list(plateau.values())[1], plateau), 0.5)
        self.assertLess(D.neighbor_ratio(list(spike.values())[1], spike), 0.5)

    def test_discovery_module_has_no_authority_over_gates_or_live_files(self):
        import ast
        tree = ast.parse(open(os.path.join(HERE, "..", "research", "discover.py")).read())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for banned in ("live_gate", "paper_broker", "orchestrator", "research_runner", "mark_registered", "subprocess"):
            self.assertNotIn(banned, names)


if __name__ == "__main__":
    unittest.main()
