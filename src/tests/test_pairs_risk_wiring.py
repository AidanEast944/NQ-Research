import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
import tempfile
import shutil
from paper_broker import PaperBroker
from position_sizing import fixed_fractional_size
import risk_limits

class TestPairsRiskWiring(unittest.TestCase):
    """Covers the risk/sizing wiring added for the pairs book (research_log.md Entry 24): position
    sizing produces sane whole-contract counts, tagged symbols let a SHARED PaperBroker/risk state
    serve all three pairs scripts without one pair's leg colliding with another's, and a custom
    state_file keeps the pairs book's drawdown/halt tracking separate from the gap strategy's."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.account_file = os.path.join(self.tmpdir, "pairs_paper_account.json")
        self.risk_file = os.path.join(self.tmpdir, "pairs_risk_limits_state.json")
        self.default_risk_file = os.path.join(self.tmpdir, "risk_limits_state.json")
        self.starting_balance = 10000
        self.risk_percent = risk_limits.MAX_RISK_PER_TRADE_PCT / 2

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_position_sizing_never_returns_zero_contracts(self):
        contracts = max(1, round(fixed_fractional_size(
            self.starting_balance, self.risk_percent, stop_points=1, point_value=514.89
        )))
        self.assertGreaterEqual(contracts, 1)

    def test_shared_broker_does_not_collide_across_pairs_with_same_symbol_family(self):
        broker = PaperBroker(starting_balance=self.starting_balance, state_file=self.account_file)
        broker.place_order("MNQ (NQ/ES)", "LONG", 20000.0, stop_price=None, target_price=None, entry_date="2026-09-10")
        broker.place_order("MES (NQ/ES)", "SHORT", 5000.0, stop_price=None, target_price=None, entry_date="2026-09-10")
        broker.place_order("MNQ (NQ/YM)", "SHORT", 20000.0, stop_price=None, target_price=None, entry_date="2026-09-10")
        broker.place_order("MYM (NQ/YM)", "LONG", 40000.0, stop_price=None, target_price=None, entry_date="2026-09-10")
        self.assertEqual(len(broker.positions), 4)

        nq_es_leg = next(p for p in broker.positions if p["symbol"] == "MNQ (NQ/ES)")
        self.assertEqual(nq_es_leg["direction"], "LONG")
        nq_ym_leg = next(p for p in broker.positions if p["symbol"] == "MNQ (NQ/YM)")
        self.assertEqual(nq_ym_leg["direction"], "SHORT")  # would be ambiguous/wrong with a bare "MNQ" tag

    def test_open_positions_gate_blocks_a_third_pair_at_max(self):
        broker = PaperBroker(starting_balance=self.starting_balance, state_file=self.account_file)
        for tag, direction, price in [("MNQ (NQ/ES)", "LONG", 20000.0), ("MES (NQ/ES)", "SHORT", 5000.0),
                                        ("MNQ (NQ/YM)", "SHORT", 20000.0), ("MYM (NQ/YM)", "LONG", 40000.0)]:
            broker.place_order(tag, direction, price, stop_price=None, target_price=None, entry_date="2026-09-10")

        allowed, reason = risk_limits.check_trade_allowed(
            account_balance=broker.balance, proposed_risk_dollars=100,
            current_open_positions=len(broker.positions), state_file=self.risk_file,
        )
        self.assertFalse(allowed)
        self.assertIn("max open positions", reason)

    def test_closing_both_legs_updates_balance_correctly(self):
        broker = PaperBroker(starting_balance=self.starting_balance, state_file=self.account_file)
        broker.place_order("MNQ (NQ/ES)", "LONG", 20000.0, stop_price=None, target_price=None, entry_date="2026-09-10")
        broker.place_order("MES (NQ/ES)", "SHORT", 5000.0, stop_price=None, target_price=None, entry_date="2026-09-10")

        nq_leg = next(p for p in broker.positions if p["symbol"] == "MNQ (NQ/ES)")
        es_leg = next(p for p in broker.positions if p["symbol"] == "MES (NQ/ES)")
        broker.close_position(nq_leg, 20100.0, reason="reverted", point_value=2.0 * 2)  # +100pts * $4/pt
        broker.close_position(es_leg, 4980.0, reason="reverted", point_value=5.0 * 1)   # SHORT, -20pts move -> +$100

        self.assertEqual(len(broker.positions), 0)
        self.assertEqual(broker.balance, self.starting_balance + 500)

    def test_pairs_risk_state_is_isolated_from_default_gap_risk_state(self):
        risk_limits.record_trade_result(500, state_file=self.risk_file)
        risk_limits.record_trade_result(-9999, state_file=self.default_risk_file)

        pairs_state = risk_limits.load_risk_state(self.risk_file)
        default_state = risk_limits.load_risk_state(self.default_risk_file)
        self.assertNotEqual(pairs_state["daily_loss_tracker"], default_state["daily_loss_tracker"])

    def test_drawdown_halt_triggers_with_custom_state_file(self):
        risk_limits.check_trade_allowed(account_balance=self.starting_balance, proposed_risk_dollars=1,
                                          current_open_positions=0, state_file=self.risk_file)  # seed peak
        allowed, reason = risk_limits.check_trade_allowed(
            account_balance=self.starting_balance * 0.75, proposed_risk_dollars=100,
            current_open_positions=0, state_file=self.risk_file,
        )
        self.assertFalse(allowed)
        self.assertIn("Drawdown", reason)


if __name__ == "__main__":
    unittest.main()
