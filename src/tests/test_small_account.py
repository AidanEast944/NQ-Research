import sys, os, unittest, tempfile, json, hashlib
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
import small_account as S


def tr(sym="MNQ", date="2026-09-01", entry=100.0, stop=60.0, pts=-40.0):
    return {"symbol": sym, "direction": "LONG", "entry_price": entry, "stop_price": stop, "target_price": entry + 80,
            "entry_date": date, "status": "CLOSED", "exit_price": entry + pts, "reason": "x", "points_result": pts,
            "point_value_used": 2}


def mk(trades):
    return [dict(symbol=t["symbol"].split()[0], entry_date=t["entry_date"], stop_dist=abs(t["entry_price"] - t["stop_price"]),
                 r=t["points_result"] / abs(t["entry_price"] - t["stop_price"]), pv=S.MICRO_PV[t["symbol"].split()[0]])
            for t in trades]


class TestSmallAccount(unittest.TestCase):
    def test_contract_sizing_floor(self):
        self.assertEqual(S.contracts(1000, 80, 0.05), 0)       # $50 < $80 -> cannot size
        self.assertEqual(S.contracts(1000, 20, 0.05), 2)       # $50 / $20 -> 2
        self.assertEqual(S.contracts(1000, 80, None), 1)

    def test_replay_loss_and_drawdown(self):
        trades = mk([tr(pts=-40.0, date="2026-09-01"), tr(pts=-40.0, date="2026-09-02")])
        r = S.replay(trades, cost=0.0, cap=None)
        self.assertAlmostEqual(r["final_equity"], 840.0)       # 2 x -$80
        self.assertAlmostEqual(r["max_drawdown_pct"], 16.0)
        self.assertEqual(r["trades_taken"], 2)

    def test_costs_reduce_equity(self):
        trades = mk([tr(pts=80.0)])
        a = S.replay(trades, 0.0, None)["final_equity"]
        b = S.replay(trades, 4.5, None)["final_equity"]
        self.assertAlmostEqual(a - b, 4.5)

    def test_stranded_when_cannot_cover_stop(self):
        trades = mk([tr(pts=-40.0, date=f"2026-09-{d:02d}") for d in range(1, 15)])
        r = S.replay(trades, 0.0, None)
        self.assertIsNotNone(r["stranded_at_trade"])
        self.assertGreaterEqual(r["min_equity"], 0.0)
        self.assertLess(r["final_equity"], 80.0)

    def test_skip_when_cap_too_small(self):
        trades = mk([tr()])
        r = S.replay(trades, 0.0, 0.02)
        self.assertEqual(r["trades_taken"], 0)
        self.assertEqual(r["trades_skipped"], 1)
        self.assertEqual(r["final_equity"], 1000.0)

    def test_chronological_sort(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.json")
            json.dump({"trade_history": [tr(date="2026-09-05"), tr(date="2026-09-01")]}, open(p, "w"))
            out = S.load_trades(p)
            self.assertEqual([t["entry_date"] for t in out], ["2026-09-01", "2026-09-05"])

    def test_open_and_stopless_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.json")
            o = tr(); o["status"] = "OPEN"
            n = tr(); n["stop_price"] = None
            json.dump({"trade_history": [o, n, tr()]}, open(p, "w"))
            self.assertEqual(len(S.load_trades(p)), 1)

    def test_bootstrap_deterministic_and_bounds(self):
        trades = mk([tr(pts=-40.0), tr(pts=80.0, date="2026-09-02")])
        a = S.bootstrap_ruin(trades, 0.0, None, n_sims=500)
        b = S.bootstrap_ruin(trades, 0.0, None, n_sims=500)
        self.assertEqual(a, b)
        self.assertTrue(0 <= a["p_ruin_half"] <= 1 and 0 <= a["p_stranded"] <= 1)

    def test_zero_edge_with_costs_is_worse_than_free(self):
        trades = mk([tr(pts=-40.0), tr(pts=80.0, date="2026-09-02"), tr(pts=-40.0, date="2026-09-03")])
        free = S.bootstrap_ruin(trades, 0.0, None, zero_edge=True, n_sims=2000)
        paid = S.bootstrap_ruin(trades, 4.5, None, zero_edge=True, n_sims=2000)
        self.assertGreaterEqual(paid["p_ruin_half"], free["p_ruin_half"])

    def test_pure_winners_never_ruin(self):
        trades = mk([tr(pts=80.0)])
        b = S.bootstrap_ruin(trades, 0.0, None, n_sims=300)
        self.assertEqual(b["p_ruin_half"], 0.0)

    def test_read_only_on_ledgers(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "gap_paper_account.json")
            json.dump({"balance": 1, "positions": [], "trade_history": [tr()]}, open(p, "w"))
            h0 = hashlib.md5(open(p, "rb").read()).hexdigest()
            S.main(["--data-dir", d, "--out-dir", os.path.join(d, "out")])
            self.assertEqual(h0, hashlib.md5(open(p, "rb").read()).hexdigest())


if __name__ == "__main__":
    unittest.main()
