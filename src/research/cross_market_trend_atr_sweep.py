from strategy import get_trend_following_atr_signals_from_archive

markets = {"NQ": "data/raw", "ES": "data/raw_es", "YM": "data/raw_ym"}

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

for atr_mult in [1.0, 1.5, 2.0]:
    print(f"\n=== ATR multiplier: {atr_mult} ===")
    print(f"{'Market':>8} {'Trades':>7} {'Win Rate':>9} {'Avg Pts':>9}")
    for market_name, folder in markets.items():
        try:
            signals = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=atr_mult, data_folder=folder)
        except FileNotFoundError:
            print(f"{market_name:>8}   no data")
            continue
        if len(signals) == 0:
            print(f"{market_name:>8}        0  no trades")
            continue
        signals["points"] = signals.apply(points_result, axis=1)
        win_rate = (signals["points"] > 0).mean() * 100
        avg_points = signals["points"].mean()
        print(f"{market_name:>8} {len(signals):>7} {win_rate:>8.1f}% {avg_points:>9.2f}")