"""
Resolve step for the volume-confirmed gap continuation strategy on ES. Companion to
volume_confirmed_gap_es_forward_check.py.
"""
import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from dashboard_trigger import refresh_dashboard

STOP_POINTS = 10
TARGET_POINTS = 20
POINT_VALUE = 5  # MES micro contract
ENTRY_TIME = "08:30"

THRESHOLDS = {
    "1.2x": {"account_file": "data/volume_gap_es_1_2x_paper_account.json"},
}

es = yf.Ticker("ES=F")
history = es.history(period="5d", interval="15m")

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
    print(f"\n--- [ES] Resolving {label} ---")
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
        refresh_dashboard()
        print(f"{label}: closed {signal} at {exit_price} ({exit_reason})")

    print(f"{label} balance: ${broker.balance:,.2f}")