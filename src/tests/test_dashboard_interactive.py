import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dashboard_interactive as di


class TestTradeTable(unittest.TestCase):
    def test_empty_history_renders_nothing(self):
        self.assertEqual(di.trade_table_html([], 2), "")

    def test_newest_first_and_dollars_use_recorded_point_value(self):
        trades = [
            {"entry_date": "2026-01-01", "direction": "LONG", "reason": "stop", "points_result": -40.0, "point_value_used": 0.5},
            {"entry_date": "2026-01-02", "direction": "SHORT", "reason": "target", "points_result": 80.0, "point_value_used": 0.5},
        ]
        html = di.trade_table_html(trades, 2)
        self.assertLess(html.index("2026-01-02"), html.index("2026-01-01"))
        self.assertIn("+40.00", html)    # 80 pts * $0.5, not the $2 default
        self.assertIn("-20.00", html)

    def test_falls_back_to_default_point_value(self):
        html = di.trade_table_html([{"entry_date": "d", "direction": "LONG", "reason": "x", "points_result": 10}], 20)
        self.assertIn("+200.00", html)


if __name__ == "__main__":
    unittest.main()
