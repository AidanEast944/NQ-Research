import sys, os, unittest, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from paper_broker import PaperBroker


class TestPaperBroker(unittest.TestCase):
    def broker(self):
        return PaperBroker(starting_balance=10000, state_file=os.path.join(tempfile.mkdtemp(), "acct.json"))

    def open(self, b, direction="LONG", price=100.0):
        return b.place_order(symbol="MNQ", direction=direction, entry_price=price, stop_price=90.0, target_price=120.0)

    def test_close_requires_point_value(self):
        b = self.broker(); o = self.open(b)
        with self.assertRaises(ValueError):
            b.close_position(o, 110.0, reason="target")
        self.assertEqual(len(b.positions), 1)      # nothing changed on the refused close
        self.assertEqual(b.balance, 10000)

    def test_long_win_dollars(self):
        b = self.broker(); o = self.open(b)
        b.close_position(o, 110.0, reason="target", point_value=2)
        self.assertEqual(b.balance, 10020)
        self.assertEqual(b.trade_history[0]["points_result"], 10.0)
        self.assertEqual(b.trade_history[0]["point_value_used"], 2)

    def test_short_loss_dollars(self):
        b = self.broker(); o = self.open(b, "SHORT")
        b.close_position(o, 105.0, reason="stop", point_value=5)
        self.assertEqual(b.balance, 10000 - 25)

    def test_state_persists_and_reloads(self):
        b = self.broker(); o = self.open(b)
        b.close_position(o, 110.0, point_value=2)
        b2 = PaperBroker(state_file=b.state_file)
        self.assertEqual(b2.balance, 10020)
        self.assertEqual(len(b2.trade_history), 1)
        self.assertEqual(len(b2.positions), 0)


if __name__ == "__main__":
    unittest.main()
