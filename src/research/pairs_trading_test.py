from strategy import get_pairs_trading_signals_from_archive

signals = get_pairs_trading_signals_from_archive()

if len(signals) == 0:
    print("No pairs trades generated.")
else:
    wins = (signals["pnl_dollars"] > 0).sum()
    losses = (signals["pnl_dollars"] <= 0).sum()
    win_rate = wins / len(signals) * 100
    total_pnl = signals["pnl_dollars"].sum()
    avg_pnl = signals["pnl_dollars"].mean()
    gross_win = signals[signals["pnl_dollars"] > 0]["pnl_dollars"].sum()
    gross_loss = abs(signals[signals["pnl_dollars"] <= 0]["pnl_dollars"].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")

    print(f"Trades: {len(signals)}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Total P&L: ${total_pnl:,.2f}")
    print(f"Avg P&L per trade: ${avg_pnl:,.2f}")
    print(f"Profit factor: {pf:.2f}")
    print(f"\nExit reasons: {signals['exit_reason'].value_counts().to_dict()}")