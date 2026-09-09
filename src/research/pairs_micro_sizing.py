from strategy import get_pairs_trading_signals_from_archive

# Micro contracts: MNQ = $2/point (vs NQ $20), MES = $5/point (vs ES $50)
# Both are exactly 1/10th their full-size counterpart
SCALE_FACTOR = 0.1

signals = get_pairs_trading_signals_from_archive()
signals = signals.sort_values("entry_date").reset_index(drop=True)
signals["pnl_dollars"] = signals["pnl_dollars"] * SCALE_FACTOR

print("=" * 60)
print("PAIRS TRADING - MICRO SIZING (MNQ + MES)")
print("=" * 60)

n = len(signals)
wins = signals[signals["pnl_dollars"] > 0]["pnl_dollars"]
losses = signals[signals["pnl_dollars"] <= 0]["pnl_dollars"]
pf = wins.sum() / abs(losses.sum()) if len(losses) > 0 and losses.sum() != 0 else float("inf")
win_rate = len(wins) / n * 100
total_pnl = signals["pnl_dollars"].sum()

balance = 0
peak = 0
max_dd = 0
for pnl in signals["pnl_dollars"]:
    balance += pnl
    if balance > peak:
        peak = balance
    dd = peak - balance
    if dd > max_dd:
        max_dd = dd

print(f"\nTrades: {n}")
print(f"Win rate: {win_rate:.1f}%")
print(f"Profit factor: {pf:.2f}")
print(f"Total P&L: ${total_pnl:,.2f}")
print(f"Max drawdown: ${max_dd:,.2f}")

for account_size in [2000, 5000, 10000]:
    dd_pct = (max_dd / account_size) * 100
    print(f"\nAt ${account_size:,} account: drawdown = {dd_pct:.1f}% of account")