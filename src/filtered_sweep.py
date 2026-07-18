import glob
import os
import pandas as pd
from strategy import get_prior_day_break_signals_from_archive

STOP_POINTS = 30
TARGET_POINTS = 60

# Load the raw archive again, just to compute volume/volatility context
files = glob.glob(os.path.join("data/raw", "*.csv"))
all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
history = pd.concat(all_days)
history = history[~history.index.duplicated(keep="first")]
history = history.sort_index()
history["date"] = history.index.date

# For each calendar day, compute total volume and day range (high - low)
daily_stats = history.groupby("date").agg(
    day_volume=("Volume", "sum"),
    day_high=("High", "max"),
    day_low=("Low", "min")
)
daily_stats["day_range"] = daily_stats["day_high"] - daily_stats["day_low"]

# Rolling 10-day averages, shifted so we only use info known BEFORE that day
daily_stats["avg_volume_10d"] = daily_stats["day_volume"].shift(1).rolling(10).mean()
daily_stats["avg_range_10d"] = daily_stats["day_range"].shift(1).rolling(10).mean()

# Get our existing signals
signals = get_prior_day_break_signals_from_archive(stop_points=STOP_POINTS, target_points=TARGET_POINTS)

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["Close"]
    else:
        return row["Close"] - row["exit_price"]

signals["points"] = signals.apply(points_result, axis=1)

# Attach the volatility/volume context for the PRIOR day to each signal
signals = signals.join(daily_stats[["day_volume", "avg_volume_10d", "day_range", "avg_range_10d"]], on="date")

signals["high_volume"] = signals["day_volume"] > signals["avg_volume_10d"]
signals["high_volatility"] = signals["day_range"] > signals["avg_range_10d"]

def report(label, subset):
    if len(subset) == 0:
        print(f"{label}: no trades")
        return
    win_rate = (subset["points"] > 0).mean() * 100
    avg_points = subset["points"].mean()
    print(f"{label}: {len(subset)} trades, {win_rate:.1f}% win rate, {avg_points:.2f} avg points")

print(f"\n--- Stop {STOP_POINTS} / Target {TARGET_POINTS} ---\n")

report("ALL signals", signals)
print()
report("High volume days", signals[signals["high_volume"] == True])
report("Low volume days", signals[signals["high_volume"] == False])
print()
report("High volatility days", signals[signals["high_volatility"] == True])
report("Low volatility days", signals[signals["high_volatility"] == False])