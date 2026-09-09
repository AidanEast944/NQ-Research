from strategy import get_volatility_squeeze_signals_from_archive

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["Close"]
    else:
        return row["Close"] - row["exit_price"]

signals = get_volatility_squeeze_signals_from_archive()
if len(signals) == 0:
    print("No signals generated.")
else:
    signals["points"] = signals.apply(points_result, axis=1)
    win_rate = (signals["points"] > 0).mean() * 100
    avg_points = signals["points"].mean()
    total = signals["points"].sum()
    print(f"Trades: {len(signals)}, Win rate: {win_rate:.1f}%, Avg points: {avg_points:.2f}, Total: {total:.2f}")