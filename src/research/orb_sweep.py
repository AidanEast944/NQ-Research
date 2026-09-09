from results_logger import log_result
from strategy import get_orb_signals_from_archive

combos_to_test = [
    (15, 30),
    (20, 40),
    (30, 60),
    (40, 40),
    (50, 100),
]

print("Testing OPENING RANGE BREAKOUT against YOUR SAVED ARCHIVE (data/raw)\n")
print(f"{'Stop':>6} {'Target':>7} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9} {'Total Pts':>10}")

for stop, target in combos_to_test:
    signals = get_orb_signals_from_archive(stop_points=stop, target_points=target)

    if len(signals) == 0:
        print(f"{stop:>6} {target:>7} {'0':>7}  no trades")
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

    print(f"{stop:>6} {target:>7} {len(signals):>7} {win_rate:>8.1f}% {avg_points:>9.2f} {total_points:>10.2f}")
    log_result("opening_range_breakout", f"stop={stop},target={target}", len(signals), win_rate, avg_points, total_points)