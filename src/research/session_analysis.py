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

# Session windows in Eastern time (approximate, standard convention)
sessions = {
    "Asian (7pm-2am ET)": (pd.Timestamp("19:00").time(), pd.Timestamp("02:00").time()),
    "London (3am-8am ET)": (pd.Timestamp("03:00").time(), pd.Timestamp("08:00").time()),
    "NY (8:30am-4pm ET)": (pd.Timestamp("08:30").time(), pd.Timestamp("16:00").time()),
    "London/NY overlap (8:30am-11am ET)": (pd.Timestamp("08:30").time(), pd.Timestamp("11:00").time()),
}

print(f"{'Session':>35} {'Avg Range':>12} {'Avg Volume':>14}")
for name, (start, end) in sessions.items():
    if start < end:
        mask = (history.index.time >= start) & (history.index.time < end)
    else:
        mask = (history.index.time >= start) | (history.index.time < end)

    session_bars = history[mask]
    daily_range = session_bars.groupby("date").agg(high=("High", "max"), low=("Low", "min"))
    daily_range["range"] = daily_range["high"] - daily_range["low"]
    daily_vol = session_bars.groupby("date")["Volume"].sum()

    print(f"{name:>35} {daily_range['range'].mean():>12.2f} {daily_vol.mean():>14,.0f}")