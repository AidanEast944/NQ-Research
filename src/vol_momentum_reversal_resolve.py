"""
Resolve step for Vol+Momentum Reversal (Entry 54). Companion to
vol_momentum_reversal_forward_check.py - checks any open position against the full day's real
price action and closes it with its actual stop/target/eod outcome.
"""
import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from dashboard_trigger import refresh_dashboard

STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 2
ENTRY_TIME = "08:30"
ACCOUNT_FILE = "data/vol_momentum_reversal_paper_account.json"

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")

if history.empty:
    print("WARNING: No data returned. Skipping.")
    sys.exit()

history["date"] = history.index.date
today = date.today()

entry_t = pd.Timestamp(ENTRY_TIME).time()
day_bars = history[
    (history["date"] == today)
    & (history.index.time > entry_t)
    & (history.index.time <= pd.Timestamp("16:00").time())
]

broker = PaperBroker(starting_balance=10000, state_file=ACCOUNT_FILE)
todays_positions = [p for p in broker.positions if p.get("entry_date") == str(today)]

if not todays_positions:
    print(f"No open position to resolve for {today}.")
    sys.exit()

if day_bars.empty:
    print(f"No price bars available yet for {today} - will retry next scheduled run.")
    sys.exit()

for position in todays_positions:
    stop_price = position["stop_price"]
    target_price = position["target_price"]

    exit_price = None
    exit_reason = None
    for _, bar in day_bars.iterrows():
        if bar["High"] >= stop_price:
            exit_price, exit_reason = stop_price, "stop"
            break
        elif bar["Low"] <= target_price:
            exit_price, exit_reason = target_price, "target"
            break

    if exit_price is None:
        exit_price = day_bars.iloc[-1]["Close"]
        exit_reason = "eod"

    broker.close_position(position, exit_price, reason=exit_reason, point_value=POINT_VALUE)
    refresh_dashboard()
    print(f"Closed SHORT at {exit_price} ({exit_reason})")

print(f"Balance: ${broker.balance:,.2f}")