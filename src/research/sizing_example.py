import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from position_sizing import recommended_contracts

# Using gap continuation's real historical stats: 67.1% win rate, based on 40pt stop / 80pt target
account_balance = 10000
win_rate = 0.671
avg_win = 80 * 2   # target hit, MNQ point value
avg_loss = 40 * 2  # stop hit, MNQ point value

contracts, risk_pct = recommended_contracts(
    account_balance=account_balance,
    win_rate=win_rate,
    avg_win=avg_win,
    avg_loss=avg_loss,
    stop_points=40,
    point_value=2
)

print(f"Account: ${account_balance:,}")
print(f"Strategy: Gap Continuation (67.1% win rate)")
print(f"Recommended risk: {risk_pct:.2f}% of account")
print(f"Recommended position size: {contracts:.2f} MNQ contracts (round down to {int(contracts)})")