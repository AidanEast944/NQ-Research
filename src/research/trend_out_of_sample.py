from strategy import get_trend_following_signals_from_archive

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

def stats(subset):
    if len(subset) == 0:
        return 0, float("nan"), 0
    win_rate = (subset["points"] > 0).mean() * 100
    avg_points = subset["points"].mean()
    return len(subset), win_rate, avg_points

signals = get_trend_following_signals_from_archive(ma_period=5, stop_points=200)
signals["points"] = signals.apply(points_result, axis=1)
signals = signals.sort_values("entry_date")

split_point = int(len(signals) * 0.7)
in_sample = signals.iloc[:split_point]
out_sample = signals.iloc[split_point:]

in_n, in_wr, in_avg = stats(in_sample)
out_n, out_wr, out_avg = stats(out_sample)

print("5-DAY TREND FOLLOWING: In-Sample vs Out-of-Sample\n")
print(f"{'':>12} | {'Trades':>7} {'WinR':>8} {'AvgPts':>9}")
print(f"{'In-Sample':>12} | {in_n:>7} {in_wr:>7.1f}% {in_avg:>9.2f}")
print(f"{'Out-Sample':>12} | {out_n:>7} {out_wr:>7.1f}% {out_avg:>9.2f}")

print(f"\n--- In-Sample trades ---")
print(in_sample[["entry_date", "exit_date", "signal", "exit_reason", "days_held", "points"]].to_string(index=False))
print(f"\n--- Out-of-Sample trades ---")
print(out_sample[["entry_date", "exit_date", "signal", "exit_reason", "days_held", "points"]].to_string(index=False))