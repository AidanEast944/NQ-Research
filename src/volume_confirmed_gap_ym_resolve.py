"""
Resolve step for the volume-confirmed gap continuation strategy on YM. Companion to
volume_confirmed_gap_ym_forward_check.py - checks any open YM positions against the full day's
real price action and closes them with their actual stop/target/eod outcome.
"""
import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker

STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 0.5  # MYM micro contract
ENTRY_TIME = "08:30"

THRESHOLDS = {
    "1.2x": {"account_file": "data/volume_gap_ym_1_2x_paper_account.json"},
    "1.5x": {"account_file": "data/volume_gap_ym_1_5x_paper_account.json"},
}

ym = yf.Ticker("YM=F")
history = ym.history(period="5d", interval="15m")

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

for label, cfg in THRESHOLDS.items():
    print(f"\n--- [YM] Resolving {label} ---")
    broker = PaperBroker(starting_balance=10000, state_file=cfg["account_file"])

    todays_positions = [p for p in broker.positions if p.get("entry_date") == str(today)]

    if not todays_positions:
        print(f"No open {label} position to resolve for {today}.")
        continue

    if day_bars.empty:
        print(f"No price bars available yet for {today} - will retry next scheduled run.")
        continue

    for position in todays_positions:
        signal = position["direction"]
        stop_price = position["stop_price"]
        target_price = position["target_price"]

        exit_price = None
        exit_reason = None

        for _, bar in day_bars.iterrows():
            if signal == "LONG":
                hit_stop = bar["Low"] <= stop_price
                hit_target = bar["High"] >= target_price
            else:
                hit_stop = bar["High"] >= stop_price
                hit_target = bar["Low"] <= target_price

            if hit_stop:
                exit_price, exit_reason = stop_price, "stop"
                break
            elif hit_target:
                exit_price, exit_reason = target_price, "target"
                break

        if exit_price is None:
            exit_price = day_bars.iloc[-1]["Close"]
            exit_reason = "eod"

        broker.close_position(position, exit_price, reason=exit_reason, point_value=POINT_VALUE)
        print(f"{label}: closed {signal} at {exit_price} ({exit_reason})")

    print(f"{label} balance: ${broker.balance:,.2f}")