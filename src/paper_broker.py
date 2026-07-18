class PaperBroker:
    def __init__(self, starting_balance=10000):
        self.balance = starting_balance
        self.positions = []       # currently open trades
        self.trade_history = []   # closed trades

    def place_order(self, symbol, direction, entry_price, stop_price, target_price):
        order = {
            "symbol": symbol,
            "direction": direction,      # "LONG" or "SHORT"
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "status": "OPEN"
        }
        self.positions.append(order)
        print(f"[PAPER TRADE] Opened {direction} {symbol} at {entry_price} "
              f"(stop: {stop_price}, target: {target_price})")
        return order

    def close_position(self, order, exit_price, reason="manual"):
        order["exit_price"] = exit_price
        order["status"] = "CLOSED"
        order["reason"] = reason

        if order["direction"] == "LONG":
            points = exit_price - order["entry_price"]
        else:
            points = order["entry_price"] - exit_price

        order["points_result"] = points
        self.balance += points * 20  # NQ = $20 per point
        self.positions.remove(order)
        self.trade_history.append(order)

        print(f"[PAPER TRADE] Closed {order['direction']} {order['symbol']} "
              f"at {exit_price} ({reason}) — {points:+.2f} points, "
              f"balance now ${self.balance:,.2f}")

    def summary(self):
        print(f"\n--- Paper Account Summary ---")
        print(f"Balance: ${self.balance:,.2f}")
        print(f"Open positions: {len(self.positions)}")
        print(f"Closed trades: {len(self.trade_history)}")