from strategy import get_prior_day_fade_signals_atr_from_archive

combos_to_test = [
    (0.05, 0.10),
    (0.10, 0.20),
    (0.15, 0.30),
    (0.20, 0.40),
    (0.30, 0.60),
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

print("FADE + ATR: In-Sample vs Out-of-Sample\n")
print(f"{'ATR Stop':>9} {'ATR Target':>11} | {'IN-SAMPLE':^24} | {'OUT-OF-SAMPLE':^24}")
print(f"{'':>9} {'':>11} | {'Trades':>7}{'WinR':>8}{'AvgPts':>9} | {'Trades':>7}{'WinR':>8}{'AvgPts':>9}")

for stop_mult, target_mult in combos_to_test:
    signals = get_prior_day_fade_signals_atr_from_archive(
        atr_multiplier=stop_mult,
        target_multiplier=target_mult
    )

    if len(signals) == 0:
        print(f"{stop_mult:>9} {target_mult:>11} |   no trades")
        continue

    signals["points"] = signals.apply(points_result, axis=1)
    signals = signals.sort_values("date")

    split_point = int(len(signals) * 0.7)
    in_sample = signals.iloc[:split_point]
    out_sample = signals.iloc[split_point:]

    in_n, in_wr, in_avg = stats(in_sample)
    out_n, out_wr, out_avg = stats(out_sample)

    print(f"{stop_mult:>9} {target_mult:>11} | {in_n:>7}{in_wr:>7.1f}%{in_avg:>9.2f} | {out_n:>7}{out_wr:>7.1f}%{out_avg:>9.2f}")