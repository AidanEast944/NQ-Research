"""
Resolve step for Vol+Momentum Reversal (Entry 54). Companion to
vol_momentum_reversal_forward_check.py - checks any open position against real price action and
closes it with its actual stop/target/eod outcome.

FIX (2026-09-30, research_log.md Entry 57/58 - stale-position resolve bug): used to only check
positions where entry_date == today, using only today's bars - same bug as gap_forward_resolve.py
and its siblings (see that file's docstring for the full reasoning). Hadn't bitten this strategy
yet since it had never opened a trade, but the same silent-stranding failure mode was latent here
too. Now every open position is checked against its own entry day's bars.
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

today = date.today()

broker = PaperBroker(starting_balance=10000, state_file=ACCOUNT_FILE)

if not broker.positions:
    print(f"No open position to resolve for {today}.")
    sys.exit()

nq = yf.Ticker("NQ=F")
history = nq.history(period="60d", interval="15m")

if history.empty:
    print("WARNING: No data returned. Skipping.")
    sys.exit()

history["date"] = history.index.date
history["time"] = history.index.time

entry_t = pd.Timestamp(ENTRY_TIME).time()
session_bars = history[
    (history["time"] > entry_t)
    & (history["time"] <= pd.Timestamp("16:00").time())
].sort_index()

for position in list(broker.positions):
    entry_date = date.fromisoformat(position["entry_date"])
    stop_price = position["stop_price"]
    target_price = position["target_price"]

    entry_day_bars = session_bars[session_bars["date"] == entry_date]

    if entry_day_bars.empty:
        print(f"No price bars available yet for the position from {entry_date} - will retry next scheduled run.")
        continue

    exit_price = None
    exit_reason = None
    for _, bar in entry_day_bars.iterrows():
        if bar["High"] >= stop_price:
            exit_price, exit_reason = stop_price, "stop"
            break
        elif bar["Low"] <= target_price:
            exit_price, exit_reason = target_price, "target"
            break

    if exit_price is None:
        exit_price = entry_day_bars.iloc[-1]["Close"]
        exit_reason = "eod"

    broker.close_position(position, exit_price, reason=exit_reason, point_value=POINT_VALUE)
    refresh_dashboard()
    print(f"Closed SHORT at {exit_price} ({exit_reason})")

print(f"Balance: ${broker.balance:,.2f}")
