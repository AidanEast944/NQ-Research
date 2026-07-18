import sys
import yfinance as yf
import pandas as pd
import os
from datetime import date

LOG_FILE = "data/forward_log.csv"

if not os.path.exists(LOG_FILE):
    print("No forward log file exists yet - nothing to resolve.")
    sys.exit()

log = pd.read_csv(LOG_FILE)
log["date"] = pd.to_datetime(log["date"]).dt.date

today = date.today()
open_today = log[(log["date"] == today) & (log["status"] == "OPEN")]

if open_today.empty:
    print(f"No open predictions to resolve for {today}.")
    sys.exit()

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")
history["date"] = history.index.date

today_bars = history[
    (history["date"] == today)
    & (history.index.time > pd.Timestamp("08:30").time())
    & (history.index.time <= pd.Timestamp("16:00").time())
]

for idx, row in open_today.iterrows():
    signal = row["signal"]
    stop_price = row["stop_price"]
    target_price = row["target_price"]
    strategy_name = row["strategy"]

    exit_price = None
    exit_reason = None

    for _, bar in today_bars.iterrows():
        if signal == "LONG":
            hit_stop = bar["Low"] <= stop_price
            hit_target = bar["High"] >= target_price
        else:
            hit_stop = bar["High"] >= stop_price
            hit_target = bar["Low"] <= target_price

        if hit_stop:
            exit_price = stop_price
            exit_reason = "stop"
            break
        elif hit_target:
            exit_price = target_price
            exit_reason = "target"
            break

    if exit_price is None and not today_bars.empty:
        exit_price = today_bars.iloc[-1]["Close"]
        exit_reason = "eod"

    if exit_price is not None:
        log.loc[idx, "status"] = "CLOSED"
        log.loc[idx, "exit_price"] = exit_price
        log.loc[idx, "exit_reason"] = exit_reason
        print(f"RESOLVED [{strategy_name}]: {signal} closed at {exit_price} ({exit_reason})")

log.to_csv(LOG_FILE, index=False)
print("Forward log updated.")