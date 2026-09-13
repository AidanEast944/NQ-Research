import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import glob
import pandas as pd
import calendar
from datetime import date, timedelta

def get_nfp_dates(start_year, start_month, end_year, end_month):
    """NFP releases at 8:30 AM ET on the first Friday of every month - a fixed, publicly
    scheduled date, computable exactly without any external calendar data."""
    dates = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        cal = calendar.monthcalendar(year, month)
        first_week = cal[0]
        if first_week[calendar.FRIDAY] == 0:
            first_friday = cal[1][calendar.FRIDAY]
        else:
            first_friday = first_week[calendar.FRIDAY]
        dates.append(date(year, month, first_friday))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return dates

files = glob.glob("data/raw_nq_extended/*.csv")
all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
history = pd.concat(all_days)
history = history[~history.index.duplicated(keep="first")]
history = history.sort_index()
history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
history["date"] = history.index.date

daily = history.groupby("date").agg(open=("Open", "first"), high=("High", "max"),
                                      low=("Low", "min"), close=("Close", "last"))
daily.index = pd.to_datetime(daily.index)
daily = daily.sort_index()
daily["prior_close"] = daily["close"].shift(1)
daily["day_range"] = daily["high"] - daily["low"]
daily["return_pct"] = (daily["close"] - daily["prior_close"]) / daily["prior_close"] * 100

nfp_dates = get_nfp_dates(2024, 1, 2026, 9)
nfp_dates_set = set(nfp_dates)
daily["is_nfp"] = [d.date() in nfp_dates_set for d in daily.index]

nfp_days = daily[daily["is_nfp"] == True]
normal_days = daily[daily["is_nfp"] == False]

print(f"NFP days found in archive: {len(nfp_days)}")
print(f"Normal days: {len(normal_days)}")
print(f"\nNFP day avg range: {nfp_days['day_range'].mean():.2f} pts")
print(f"Normal day avg range: {normal_days['day_range'].mean():.2f} pts")
print(f"\nNFP day avg |return|: {nfp_days['return_pct'].abs().mean():.3f}%")
print(f"Normal day avg |return|: {normal_days['return_pct'].abs().mean():.3f}%")
print(f"\nNFP day return std dev: {nfp_days['return_pct'].std():.3f}%")
print(f"Normal day return std dev: {normal_days['return_pct'].std():.3f}%")