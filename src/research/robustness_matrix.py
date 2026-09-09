from strategy import get_trend_following_signals_from_archive, get_trend_following_atr_signals_from_archive
from analysis_utils import compute_points, full_stats
from trading_costs import apply_costs

print("=" * 60)
print("ROBUSTNESS MATRIX: NQ 5-DAY TREND")
print("=" * 60)

print("\n--- Stop Sensitivity (fixed points) ---")
for stop in [100, 150, 200, 250, 300, 400]:
    signals = get_trend_following_signals_from_archive(ma_period=5, stop_points=stop)
    if len(signals) == 0:
        print(f"Stop {stop}: no trades")
        continue
    signals = compute_points(signals)
    stats = full_stats(signals, label=f"stop={stop}")
    print(f"Stop {stop:>4}: {stats['trades']:>3} trades | WR {stats['win_rate']:>5.1f}% | PF {stats['profit_factor']:>5.2f} | Exp ${stats['expectancy_dollars']:>7.2f}/trade | MaxDD ${stats['max_drawdown_dollars']:>8,.2f}")

print("\n--- ATR Sensitivity ---")
for mult in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    signals = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=mult)
    if len(signals) == 0:
        print(f"ATR x{mult}: no trades")
        continue
    signals = compute_points(signals)
    stats = full_stats(signals, label=f"atr={mult}")
    print(f"ATR x{mult:>4}: {stats['trades']:>3} trades | WR {stats['win_rate']:>5.1f}% | PF {stats['profit_factor']:>5.2f} | Exp ${stats['expectancy_dollars']:>7.2f}/trade | MaxDD ${stats['max_drawdown_dollars']:>8,.2f}")

print("\n--- Cost Sensitivity (ATR x1.0) ---")
signals = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0)
signals = compute_points(signals)
gross = (signals["points"] * 20).sum()
for slip in [0, 1, 2, 5]:
    net = sum(apply_costs(p, slippage_points=slip) for p in signals["points"])
    print(f"Slippage {slip} pts: Net P&L ${net:,.2f} (gross was ${gross:,.2f})")

print("\n--- Market Sensitivity (ATR x1.0, cross-market) ---")
for market, folder in [("NQ", "data/raw"), ("ES", "data/raw_es"), ("YM", "data/raw_ym")]:
    try:
        signals = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0, data_folder=folder)
    except FileNotFoundError:
        print(f"{market}: no archive")
        continue
    if len(signals) == 0:
        print(f"{market}: no trades")
        continue
    signals = compute_points(signals)
    stats = full_stats(signals, label=market)
    print(f"{market}: {stats['trades']:>3} trades | WR {stats['win_rate']:>5.1f}% | PF {stats['profit_factor']:>5.2f} | Exp ${stats['expectancy_dollars']:>7.2f}/trade")