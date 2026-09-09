import json
import os
import matplotlib.pyplot as plt

def load_trades(filepath, label):
    if not os.path.exists(filepath):
        return [], label
    with open(filepath, "r") as f:
        state = json.load(f)
    trades = state.get("trade_history", [])
    return trades, label

def build_curve(trades, starting_balance=10000, points_key="points", multiplier=20):
    balance = starting_balance
    dates = []
    balances = [balance]
    for trade in trades:
        points = trade.get(points_key, trade.get("points_result", 0))
        balance += points * multiplier
        exit_date = trade.get("exit_date", "")
        dates.append(exit_date)
        balances.append(balance)
    return dates, balances

fade_trades, _ = load_trades("data/fade_paper_account.json", "Fade")
trend_trades, _ = load_trades("data/trend_forward_state.json", "Trend")

fade_dates, fade_balances = build_curve(fade_trades)
trend_dates, trend_balances = build_curve(trend_trades)

plt.figure(figsize=(10, 6))

if len(fade_balances) > 1:
    plt.plot(range(len(fade_balances)), fade_balances, marker="o", label="Fade Strategy")

if len(trend_balances) > 1:
    plt.plot(range(len(trend_balances)), trend_balances, marker="o", label="Trend Strategy")

plt.axhline(y=10000, color="gray", linestyle="--", linewidth=1, label="Starting Balance")
plt.xlabel("Trade Number")
plt.ylabel("Balance ($)")
plt.title("Paper Trading Equity Curve")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()

os.makedirs("results", exist_ok=True)
plt.savefig("results/equity_curve.png", dpi=150)
print("Saved chart to results/equity_curve.png")