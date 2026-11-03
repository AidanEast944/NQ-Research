import sys, os, json, unittest, tempfile
import numpy as np
import pandas as pd
HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lab"))
sys.path.append(os.path.join(HERE, "..", "research"))
import forward_daily as FD
import refresh_daily_futures as R
import test_discover as TD
import test_carry as TC


def roster(tmp, start):
    p = os.path.join(tmp, "roster.json")
    json.dump({"forward_start": start, "entries": [
        {"id": "tsmom_L252_skip21_rebalM", "kind": "discover"},
        {"id": "dlt_tscarry", "kind": "carry", "carry_kind": "tscarry"}]}, open(p, "w"))
    return p


class TestRefreshMerge(unittest.TestCase):
    def test_new_rows_win_and_file_never_shrinks(self):
        idx = pd.to_datetime(["2026-10-20", "2026-10-21", "2026-10-22"])
        old = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=idx)
        new = pd.DataFrame({"close": [2.5, 3.5, 4.0]}, index=pd.to_datetime(["2026-10-21", "2026-10-22", "2026-10-23"]))
        m = R.merge_new(old, new)
        self.assertEqual(list(m["close"]), [1.0, 2.5, 3.5, 4.0])
        self.assertGreaterEqual(len(m), len(old))

    def test_plan_skips_current_files_and_missing_folders(self):
        root = tempfile.mkdtemp(); os.makedirs(os.path.join(root, "data/futures_daily"))
        pd.DataFrame({"date": ["2026-10-20"], "close": [1.0]}).to_csv(os.path.join(root, "data/futures_daily/ES.csv"), index=False)
        pd.DataFrame({"date": ["2026-11-02"], "close": [1.0]}).to_csv(os.path.join(root, "data/futures_daily/NQ.csv"), index=False)
        jobs = R.plan(root, ["ES", "NQ", "ZN"], today=pd.Timestamp("2026-11-03").date())
        self.assertEqual([(r, s) for r, s, _ in jobs], [(0, "ES")])       # NQ already current, ZN has no file, no c1 folder


class TestForward(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd(); os.chdir(REPO)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_only_days_after_forward_start_are_reported(self):
        d = TD.synth_dir(trend=True); tmp = tempfile.mkdtemp()
        res = FD.run(roster(tmp, "2024-01-02"), data_dir=d, write=False)
        e = res["entries"]["tsmom_L252_skip21_rebalM"]
        self.assertEqual(e["status"], "ok")
        self.assertGreater(e["days"], 100)
        self.assertGreater(e["last_date"], "2024-01-02")
        # the cut itself: a series with dates before and after keeps only the later ones
        s = pd.Series(1.0, index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
        self.assertEqual(list(FD.forward_slice(s, "2024-01-02").index.astype(str)), ["2024-01-03"])
        self.assertIsNone(e["net_sharpe"] if e["days"] < FD.MIN_DAYS_FOR_SHARPE else None)

    def test_carry_waits_for_data_then_works_when_second_contract_present(self):
        d = TD.synth_dir(); tmp = tempfile.mkdtemp()
        res = FD.run(roster(tmp, "2024-01-02"), data_dir=d, write=False)
        self.assertEqual(res["entries"]["dlt_tscarry"]["status"], "waiting_for_data")
        d2 = TC.TestCarryHarness()._dirs()                                # has c1 for every market
        res2 = FD.run(roster(tmp, "2024-01-02"), data_dir=d2, write=False)
        self.assertEqual(res2["entries"]["dlt_tscarry"]["status"], "ok")

    def test_no_forward_days_yet_when_data_ends_before_start(self):
        d = TD.synth_dir(); tmp = tempfile.mkdtemp()
        res = FD.run(roster(tmp, "2030-01-01"), data_dir=d, write=False)
        self.assertEqual(res["entries"]["tsmom_L252_skip21_rebalM"]["status"], "no_forward_days_yet")


class TestMonthlyReport(unittest.TestCase):
    def test_builds_from_a_minimal_root_and_reports_change_next_time(self):
        import monthly_report as M
        root = tempfile.mkdtemp(); os.makedirs(os.path.join(root, "data")); os.makedirs(os.path.join(root, "results"))
        json.dump({"balance": 10000, "positions": [], "trade_history": []}, open(os.path.join(root, "data/gap_paper_account.json"), "w"))
        sys.path.insert(0, os.path.join(HERE, ".."))
        p1, t1 = M.build(root, today=pd.Timestamp("2026-11-01").date())
        self.assertIn("first report", t1)
        json.dump({"balance": 10100, "positions": [], "trade_history": [{"x": 1}]}, open(os.path.join(root, "data/gap_paper_account.json"), "w"))
        p2, t2 = M.build(root, today=pd.Timestamp("2026-12-01").date())
        self.assertIn("+100 (+1 trades)", t2)
        self.assertTrue(os.path.exists(os.path.join(root, p2)))


if __name__ == "__main__":
    unittest.main()
