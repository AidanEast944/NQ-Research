import sys, os, unittest, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import portfolio_analytics as pa


class TestPortfolioAnalytics(unittest.TestCase):
    def test_accounts_are_well_formed(self):
        keys = [a["key"] for a in pa.BROKER_ACCOUNTS]
        self.assertEqual(len(keys), len(set(keys)), "duplicate account key")
        for a in pa.BROKER_ACCOUNTS:
            self.assertGreater(a["default_point_value"], 0)
            self.assertTrue(a["path"].startswith("data/") and a["path"].endswith("_paper_account.json"))
        for k in ("vol_es_1_2x", "vol_ym_1_2x", "vol_ym_1_5x"):
            self.assertIn(k, keys)

    def test_pairs_book_counts_round_trips_not_legs(self):
        d = tempfile.mkdtemp()
        legs = [{"status": "CLOSED", "points_result": 1, "point_value_used": 2, "entry_date": "2026-09-01"}] * 4
        path = os.path.join(d, "pairs.json")
        json.dump({"balance": 10000, "positions": [], "trade_history": legs}, open(path, "w"))
        orig = pa.BROKER_ACCOUNTS
        try:
            pa.BROKER_ACCOUNTS = [dict(a, path=path) if a["key"] == "pairs" else dict(a, path=path + ".missing")
                                  for a in orig]
            book = pa.combined_book_summary()
        finally:
            pa.BROKER_ACCOUNTS = orig
        self.assertEqual(book["total_trades"], 2)   # 4 legs = 2 round trips


if __name__ == "__main__":
    unittest.main()
