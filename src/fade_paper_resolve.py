import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from dashboard_trigger import refresh_dashboard

STATE_FILE = "data/fade_paper_account.json"

broker = PaperBroker(starting_balance=10000, state_file=STATE_FILE)

today = date.today()
todays_positions = [p for p in broker.positions if p["entry_date"] == str(today)]

if not todays_positions:
    print(f"No open paper positions to resolve for {today}.")
    sys.exit()

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")

if history.empty:
    print("WARNING: No data returned from Yahoo Finance. Skipping this run.")
    sys.exit()

history["date"] = history.index.date

today_bars = history[
    (history["date"] == today)
    & (history.index.time > pd.Timestamp("08:30").time())
    & (history.index.time <= pd.Timestamp("16:00").time())
]

for position in todays_positions:
    signal = position["direction"]
    stop_price = position["stop_price"]
    target_price = position["target_price"]

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
        broker.close_position(position, exit_price, reason=exit_reason)
        refresh_dashboard()

broker.summary()