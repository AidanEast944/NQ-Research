from strategy import get_trend_following_signals_from_archive

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

for ma_period in [5, 10, 20]:
    signals = get_trend_following_signals_from_archive(ma_period=ma_period, stop_points=200)

    if len(signals) == 0:
        print(f"MA={ma_period}: no trades yet")
        continue

    signals["points"] = signals.apply(points_result, axis=1)
    win_rate = (signals["points"] > 0).mean() * 100
    avg_points = signals["points"].mean()
    avg_days_held = signals["days_held"].mean()

    print(f"\n--- MA period: {ma_period} days ---")
    print(signals[["entry_date", "exit_date", "signal", "entry_price", "exit_price", "exit_reason", "days_held", "points"]].to_string(index=False))
    print(f"\nTrades: {len(signals)}, Win rate: {win_rate:.1f}%, Avg points: {avg_points:.2f}, Avg days held: {avg_days_held:.1f}")