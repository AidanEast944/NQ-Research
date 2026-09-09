from strategy import get_prior_day_fade_signals_from_archive

signals = get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60)

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["Close"]
    else:
        return row["Close"] - row["exit_price"]

signals["points"] = signals.apply(points_result, axis=1)
signals = signals.sort_values("date")

split_point = int(len(signals) * 0.7)
out_sample = signals.iloc[split_point:]

print("--- OUT-OF-SAMPLE TRADES (stop=30, target=60) ---\n")
print(out_sample[["date", "signal", "Close", "exit_price", "exit_reason", "points"]].to_string(index=False))