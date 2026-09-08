import json
import os

class PaperBroker:
    def __init__(self, starting_balance=10000, state_file=None):
        self.state_file = state_file
        self.balance = starting_balance
        self.positions = []
        self.trade_history = []

        if state_file and os.path.exists(state_file):
            self.load_state()

    def place_order(self, symbol, direction, entry_price, stop_price, target_price, entry_date=None):
        order = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "entry_date": entry_date,
            "status": "OPEN"
        }
        self.positions.append(order)
        print(f"[PAPER TRADE] Opened {direction} {symbol} at {entry_price} "
              f"(stop: {stop_price}, target: {target_price})")
        self.save_state()
        return order

    def close_position(self, order, exit_price, reason="manual", point_value=20):
        """point_value MUST match the contract actually being traded (e.g. 20 for NQ,
        2 for MNQ, 50 for ES, 5 for MES, 5 for YM, 0.50 for MYM, 50 for RTY, 5 for M2K).
        Defaults to 20 (full-size NQ) for backward compatibility with existing callers -
        pass it explicitly for anything else. Getting this wrong silently mis-states P&L
        by whatever multiple separates the intended contract from a full NQ contract."""
        order["exit_price"] = exit_price
        order["status"] = "CLOSED"
        order["reason"] = reason

        if order["direction"] == "LONG":
            points = exit_price - order["entry_price"]
        else:
            points = order["entry_price"] - exit_price

        order["points_result"] = points
        order["point_value_used"] = point_value
        dollars = points * point_value
        self.balance += dollars
        self.positions.remove(order)
        self.trade_history.append(order)

        print(f"[PAPER TRADE] Closed {order['direction']} {order['symbol']} "
              f"at {exit_price} ({reason}) — {points:+.2f} points (${dollars:+,.2f} @ ${point_value}/pt), "
              f"balance now ${self.balance:,.2f}")
        self.save_state()

    def summary(self):
        print(f"\n--- Paper Account Summary ---")
        print(f"Balance: ${self.balance:,.2f}")
        print(f"Open positions: {len(self.positions)}")
        print(f"Closed trades: {len(self.trade_history)}")

    def save_state(self):
        if not self.state_file:
            return
        state = {
            "balance": self.balance,
            "positions": self.positions,
            "trade_history": self.trade_history
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        with open(self.state_file, "r") as f:
            state = json.load(f)
        self.balance = state["balance"]
        self.positions = state["positions"]
        self.trade_history = state["trade_history"]
