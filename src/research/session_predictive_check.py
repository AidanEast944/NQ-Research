import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import glob
import pandas as pd

files = glob.glob("data/raw_nq_extended/*.csv")
all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
history = pd.concat(all_days)
history = history[~history.index.duplicated(keep="first")]
history = history.sort_index()
history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
history["date"] = history.index.date

daily = history.groupby("date").agg(open=("Open", "first"), close=("Close", "last"))
daily.index = pd.to_datetime(daily.index)
daily = daily.sort_index()

def get_price_at_time(target_date, target_time):
    day_data = history[history["date"] == target_date.date()]
    bar = day_data[day_data.index.time == target_time]
    if bar.empty:
        return None
    return bar.iloc[0]["Close"]

overnight_start_time = pd.Timestamp("19:00").time()
ny_open_time = pd.Timestamp("08:30").time()
ny_close_time = pd.Timestamp("15:45").time()

results = []
trading_days = daily.index.tolist()

for i in range(1, len(trading_days)):
    today = trading_days[i]
    prior_day = trading_days[i - 1]

    overnight_start_price = get_price_at_time(prior_day, overnight_start_time)
    ny_open_price = get_price_at_time(today, ny_open_time)
    ny_close_price = get_price_at_time(today, ny_close_time)

    if overnight_start_price is None or ny_open_price is None or ny_close_price is None:
        continue

    overnight_move = ny_open_price - overnight_start_price
    ny_session_move = ny_close_price - ny_open_price

    results.append({
        "date": today.date(),
        "overnight_move": overnight_move,
        "ny_session_move": ny_session_move,
        "same_direction": (overnight_move > 0) == (ny_session_move > 0)
    })

df = pd.DataFrame(results)
print(f"Total days analyzed: {len(df)}")
print(f"Days where NY session moved SAME direction as overnight: {df['same_direction'].sum()} ({df['same_direction'].mean()*100:.1f}%)")

# Also check: does the MAGNITUDE of overnight move matter?
df["overnight_abs"] = df["overnight_move"].abs()
threshold = df["overnight_abs"].quantile(0.75)
big_moves = df[df["overnight_abs"] >= threshold]
print(f"\nFor the biggest 25% of overnight moves ({len(big_moves)} days):")
print(f"Same direction rate: {big_moves['same_direction'].mean()*100:.1f}%")
print(f"Avg NY session move when overnight was up: {big_moves[big_moves['overnight_move']>0]['ny_session_move'].mean():.2f}")
print(f"Avg NY session move when overnight was down: {big_moves[big_moves['overnight_move']<0]['ny_session_move'].mean():.2f}")