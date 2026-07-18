import pandas as pd
from strategy import get_prior_day_fade_signals_from_archive

combos_to_test = [
    (15, 30),
    (20, 40),
    (30, 60),
    (40, 40),
    (50, 100),
]

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["Close"]
    else:
        return row["Close"] - row["exit_price"]

def stats(subset):
    if len(subset) == 0:
        return 0, float("nan"), 0
    win_rate = (subset["points"] > 0).mean() * 100
    avg_points = subset["points"].mean()
    return len(subset), win_rate, avg_points

print(f"{'Stop':>6} {'Target':>7} | {'IN-SAMPLE':^24} | {'OUT-OF-SAMPLE':^24}")
print(f"{'':>6} {'':>7} | {'Trades':>7}{'WinR':>8}{'AvgPts':>9} | {'Trades':>7}{'WinR':>8}{'AvgPts':>9}")

for stop, target in combos_to_test:
    signals = get_prior_day_fade_signals_from_archive(stop_points=stop, target_points=target)
    signals["points"] = signals.apply(points_result, axis=1)
    signals = signals.sort_values("date")

    split_point = int(len(signals) * 0.7)
    in_sample = signals.iloc[:split_point]
    out_sample = signals.iloc[split_point:]

    in_n, in_wr, in_avg = stats(in_sample)
    out_n, out_wr, out_avg = stats(out_sample)

    print(f"{stop:>6} {target:>7} | {in_n:>7}{in_wr:>7.1f}%{in_avg:>9.2f} | {out_n:>7}{out_wr:>7.1f}%{out_avg:>9.2f}")