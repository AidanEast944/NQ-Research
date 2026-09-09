from strategy import get_trend_following_signals_from_archive

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

print("5-DAY TREND: Stop-size ro bustness (NQ)\n")
print(f"{'Stop':>6} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9}")

for stop in [100, 150, 200, 300]:
    signals = get_trend_following_signals_from_archive(ma_period=5, stop_points=stop)
    if len(signals) == 0:
        print(f"{stop:>6}        0  no trades")
        continue
    signals["points"] = signals.apply(points_result, axis=1)
    win_rate = (signals["points"] > 0).mean() * 100
    avg_points = signals["points"].mean()
    print(f"{stop:>6} {len(signals):>7} {win_rate:>8.1f}% {avg_points:>9.2f}")