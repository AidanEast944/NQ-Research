from results_logger import log_result
from strategy import get_prior_day_fade_signals_atr_from_archive

# Same smaller multipliers that worked (scale-wise) for the breakout ATR test
combos_to_test = [
    (0.05, 0.10),
    (0.10, 0.20),
    (0.15, 0.30),
    (0.20, 0.40),
    (0.30, 0.60),
]

print("Testing FADE with ATR-BASED DYNAMIC STOPS against YOUR SAVED ARCHIVE (data/raw)\n")
print(f"{'ATR Stop':>9} {'ATR Target':>11} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9} {'Total Pts':>10}")

for stop_mult, target_mult in combos_to_test:
    signals = get_prior_day_fade_signals_atr_from_archive(
        atr_multiplier=stop_mult,
        target_multiplier=target_mult
    )

    if len(signals) == 0:
        print(f"{stop_mult:>9} {target_mult:>11}       0  no trades")
        continue

    def points_result(row):
        if row["signal"] == "LONG":
            return row["exit_price"] - row["Close"]
        else:
            return row["Close"] - row["exit_price"]

    signals["points"] = signals.apply(points_result, axis=1)

    win_rate = (signals["points"] > 0).mean() * 100
    avg_points = signals["points"].mean()
    total_points = signals["points"].sum()

    print(f"{stop_mult:>9} {target_mult:>11} {len(signals):>7} {win_rate:>8.1f}% {avg_points:>9.2f} {total_points:>10.2f}")
    log_result("prior_day_fade_atr", f"atr_stop={stop_mult},atr_target={target_mult}", len(signals), win_rate, avg_points, total_points)