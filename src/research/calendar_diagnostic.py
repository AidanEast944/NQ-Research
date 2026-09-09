import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import glob
import pandas as pd
import calendar

files = glob.glob("data/raw_nq_extended/*.csv")
all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
history = pd.concat(all_days)
history = history[~history.index.duplicated(keep="first")]
history = history.sort_index()
history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
history["date"] = history.index.date

daily = history.groupby("date").agg(close=("Close", "last"))
daily.index = pd.to_datetime(daily.index)
daily = daily.sort_index()
daily["prior_close"] = daily["close"].shift(1)
daily["return_pct"] = (daily["close"] - daily["prior_close"]) / daily["prior_close"] * 100
daily["day_of_week"] = daily.index.day_name()

print("=" * 50)
print("DAY OF WEEK RETURNS")
print("=" * 50)
dow_stats = daily.groupby("day_of_week")["return_pct"].agg(["mean", "count", lambda x: (x > 0).mean() * 100])
dow_stats.columns = ["avg_return_pct", "days", "win_rate_pct"]
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
print(dow_stats.reindex(day_order))

print("\n" + "=" * 50)
print("TURN-OF-MONTH EFFECT (last 3 trading days + first 2 of month)")
print("=" * 50)

daily["year_month"] = daily.index.to_period("M")
daily["trading_day_of_month"] = daily.groupby("year_month").cumcount() + 1
daily["days_in_month"] = daily.groupby("year_month")["trading_day_of_month"].transform("max")
daily["days_from_month_end"] = daily["days_in_month"] - daily["trading_day_of_month"]

is_turn_of_month = (daily["days_from_month_end"] <= 2) | (daily["trading_day_of_month"] <= 2)
tom_returns = daily[is_turn_of_month]["return_pct"]
other_returns = daily[~is_turn_of_month]["return_pct"]

print(f"Turn-of-month days: {len(tom_returns)}, avg return: {tom_returns.mean():.3f}%, win rate: {(tom_returns > 0).mean()*100:.1f}%")
print(f"Other days: {len(other_returns)}, avg return: {other_returns.mean():.3f}%, win rate: {(other_returns > 0).mean()*100:.1f}%")