from strategy import get_overnight_range_signals_from_archive

combos_to_test = [
    (15, 30),
    (20, 40),
    (30, 60),
    (40, 40),
    (50, 100),
]

print("Testing OVERNIGHT RANGE BREAK against YOUR SAVED ARCHIVE (data/raw)\n")
print(f"{'Stop':>6} {'Target':>7} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9} {'Total Pts':>10}")

for stop, target in combos_to_test:
    signals = get_overnight_range_signals_from_archive(
        stop_points=stop,
        target_points=target
    )

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