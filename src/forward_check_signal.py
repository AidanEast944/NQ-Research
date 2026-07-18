print("SCRIPT STARTED")
import sys
import yfinance as yf
import pandas as pd
import os
from datetime import date

STOP_POINTS = 30
TARGET_POINTS = 60
ENTRY_TIME = "08:30"
LOG_FILE = "data/forward_log.csv"

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")
history["date"] = history.index.date

today = date.today()
today_bars = history[history["date"] == today]

if today_bars.empty:
    print(f"No data yet for {today} - market may not be open, or too early.")
    sys.exit()

entry_bar = today_bars[today_bars.index.time == pd.Timestamp(ENTRY_TIME).time()]

if entry_bar.empty:
    print(f"No {ENTRY_TIME} candle found yet for {today}. Try again after that time.")
    sys.exit()

prior_days = history[history["date"] < today]
if prior_days.empty:
    print("Not enough history to determine prior day high/low.")
    sys.exit()

most_recent_day = prior_days["date"].max()
prior_day_bars = prior_days[prior_days["date"] == most_recent_day]
prior_day_high = prior_day_bars["High"].max()
prior_day_low = prior_day_bars["Low"].min()

entry_price = entry_bar.iloc[0]["Close"]

if entry_price > prior_day_high:
    breakout_signal = "LONG"
    fade_signal = "SHORT"
elif entry_price < prior_day_low:
    breakout_signal = "SHORT"
    fade_signal = "LONG"
else:
    print(f"No signal today ({today}). Entry price {entry_price} was inside prior day range "
          f"({prior_day_low} - {prior_day_high}).")
    sys.exit()

os.makedirs("data", exist_ok=True)
file_exists = os.path.exists(LOG_FILE)

if not file_exists:
    with open(LOG_FILE, "a") as f:
        f.write("date,strategy,signal,entry_price,stop_price,target_price,status,exit_price,exit_reason\n")

def log_signal(strategy_name, signal):
    if signal == "LONG":
        stop_price = entry_price - STOP_POINTS
        target_price = entry_price + TARGET_POINTS
    else:
        stop_price = entry_price + STOP_POINTS
        target_price = entry_price - TARGET_POINTS

    with open(LOG_FILE, "a") as f:
        f.write(f"{today},{strategy_name},{signal},{entry_price},{stop_price},{target_price},OPEN,,\n")

    print(f"SIGNAL LOGGED [{strategy_name}]: {signal} at {entry_price} (stop: {stop_price}, target: {target_price})")