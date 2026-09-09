import json
import os

def load_trades(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        state = json.load(f)
    return state.get("trade_history", [])

def analyze(trades, strategy_name, starting_balance=10000, multiplier=20):
    if not trades:
        print(f"\n--- {strategy_name} ---\nNo trades yet.")
        return

    balance = starting_balance
    peak = starting_balance
    max_drawdown = 0
    max_drawdown_pct = 0

    current_streak = 0
    worst_losing_streak = 0
    worst_winning_streak = 0
    current_streak_type = None

    for trade in trades:
        points = trade.get("points", trade.get("points_result", 0))
        balance += points * multiplier

        if balance > peak:
            peak = balance
        drawdown = peak - balance
        drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_pct = drawdown_pct

        is_win = points > 0
        if current_streak_type == is_win:
            current_streak += 1
        else:
            current_streak = 1
            current_streak_type = is_win

        if is_win:
            worst_winning_streak = max(worst_winning_streak, current_streak)
        else:
            worst_losing_streak = max(worst_losing_streak, current_streak)

    wins = sum(1 for t in trades if t.get("points", t.get("points_result", 0)) > 0)
    losses = len(trades) - wins
    win_rate = (wins / len(trades)) * 100

    print(f"\n--- {strategy_name} ---")
    print(f"Total trades: {len(trades)} ({wins}W - {losses}L, {win_rate:.1f}% win rate)")
    print(f"Current balance: ${balance:,.2f} (started at ${starting_balance:,.2f})")
    print(f"Peak balance reached: ${peak:,.2f}")
    print(f"Max drawdown: ${max_drawdown:,.2f} ({max_drawdown_pct:.1f}% from peak)")
    print(f"Worst losing streak: {worst_losing_streak} trades in a row")
    print(f"Worst winning streak: {worst_winning_streak} trades in a row")

    if losses > 0:
        avg_loss = sum(t.get("points", t.get("points_result", 0)) for t in trades if t.get("points", t.get("points_result", 0)) <= 0) / losses
        potential_streak_loss = abs(avg_loss * multiplier * worst_losing_streak)
        print(f"\nIf your worst losing streak repeated today: ~${potential_streak_loss:,.2f} potential loss")
        print(f"That would be {(potential_streak_loss / balance) * 100:.1f}% of your current balance")

print("=" * 50)
print("RISK ANALYSIS")
print("=" * 50)

fade_trades = load_trades("data/fade_paper_account.json")
analyze(fade_trades, "Fade Strategy")

trend_trades = load_trades("data/trend_forward_state.json")
analyze(trend_trades, "Trend Strategy", multiplier=20)