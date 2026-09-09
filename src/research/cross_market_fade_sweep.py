from strategy import get_prior_day_fade_signals_from_archive

markets = {
    "NQ": "data/raw",
    "ES": "data/raw_es",
    "YM": "data/raw_ym",
}

STOP_POINTS = 30
TARGET_POINTS = 60

print(f"Testing FADE strategy across markets (stop={STOP_POINTS}, target={TARGET_POINTS})\n")
print(f"{'Market':>8} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9} {'Total Pts':>10}")

for market_name, folder in markets.items():
    try:
        signals = get_prior_day_fade_signals_from_archive(
            stop_points=STOP_POINTS,
            target_points=TARGET_POINTS,
            data_folder=folder
        )
    except FileNotFoundError:
        print(f"{market_name:>8}   no archive data found")
        continue

    if len(signals) == 0:
        print(f"{market_name:>8}        0  no trades")
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

    print(f"{market_name:>8} {len(signals):>7} {win_rate:>8.1f}% {avg_points:>9.2f} {total_points:>10.2f}")