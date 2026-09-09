from strategy import get_pairs_trading_signals_from_archive

signals = get_pairs_trading_signals_from_archive()
signals = signals.sort_values("entry_date").reset_index(drop=True)

print("=" * 60)
print("PAIRS TRADING: DEEP DIVE")
print("=" * 60)
print(f"\nTotal trades: {len(signals)}")

# Drawdown
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
print(f"Max drawdown: ${max_dd:,.2f}")
print(f"Final balance: ${balance:,.2f}")

# Streaks
cur_streak = 0
streak_type = None
worst_loss_streak = 0
for pnl in signals["pnl_dollars"]:
    is_win = pnl > 0
    if streak_type == is_win:
        cur_streak += 1
    else:
        cur_streak = 1
        streak_type = is_win
    if not is_win:
        worst_loss_streak = max(worst_loss_streak, cur_streak)
print(f"Worst losing streak: {worst_loss_streak}")

# Walk-forward: split into 3 sequential windows
n = len(signals)
window_size = n // 3
print(f"\n--- Walk-forward (3 windows, ~{window_size} trades each) ---")
for w in range(3):
    start = w * window_size
    end = start + window_size if w < 2 else n
    window = signals.iloc[start:end]
    if len(window) == 0:
        continue
    win_rate = (window["pnl_dollars"] > 0).mean() * 100
    total = window["pnl_dollars"].sum()
    print(f"Window {w+1} ({window['entry_date'].min()} to {window['entry_date'].max()}): "
          f"{len(window)} trades, {win_rate:.1f}% win rate, ${total:,.2f} total")

# Cost sensitivity - TWO legs per trade (NQ + ES), so double the usual friction
print(f"\n--- Cost sensitivity (2-leg trade: NQ + ES commissions/slippage) ---")
for commission_per_leg in [0, 2.50, 4.50]:
    for slippage_points_nq in [0, 1, 2]:
        slippage_cost = slippage_points_nq * 20 * 2  # both legs affected roughly
        total_commission = commission_per_leg * 2 * 2  # 2 legs x round-turn (open+close)
        net_total = signals["pnl_dollars"].sum() - (slippage_cost * n) - (total_commission * n)
        print(f"  Commission ${commission_per_leg}/leg, slippage {slippage_points_nq}pt: Net P&L ${net_total:,.2f}")