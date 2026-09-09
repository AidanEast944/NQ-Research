from strategy import get_trend_following_signals_from_archive

markets = {
    "NQ": "data/raw",
    "ES": "data/raw_es",
    "YM": "data/raw_ym",
}

MA_PERIOD = 5
STOP_POINTS = 200

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

print(f"Testing 5-DAY TREND FOLLOWING across markets (stop={STOP_POINTS})\n")
print(f"{'Market':>8} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9} {'Avg Days Held':>14}")

for market_name, folder in markets.items():
    try:
        signals = get_trend_following_signals_from_archive(
            ma_period=MA_PERIOD,
            stop_points=STOP_POINTS,
            data_folder=folder
        )
    except FileNotFoundError:
        print(f"{market_name:>8}   no archive data found")
        continue

    if len(signals) == 0:
        print(f"{market_name:>8}        0  no trades")
        continue

    signals["points"] = signals.apply(points_result, axis=1)
    win_rate = (signals["points"] > 0).mean() * 100
    avg_points = signals["points"].mean()
    avg_days = signals["days_held"].mean()

    print(f"{market_name:>8} {len(signals):>7} {win_rate:>8.1f}% {avg_points:>9.2f} {avg_days:>14.1f}")