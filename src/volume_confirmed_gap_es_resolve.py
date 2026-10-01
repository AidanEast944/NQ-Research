"""
Resolve step for the volume-confirmed gap continuation strategy on ES. Companion to
volume_confirmed_gap_es_forward_check.py.

FIX (2026-09-30, research_log.md - stale-position resolve bug): used to only check positions where
entry_date == today, using only today's bars - see gap_forward_resolve.py's docstring for the full
reasoning (same bug, same fix, applied here too). Now every open position is checked against its
own entry day's bars, so a position that missed its same-day resolve run can't get stranded open
indefinitely.
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

today = date.today()

any_open = any(
    PaperBroker(starting_balance=10000, state_file=cfg["account_file"]).positions
    for cfg in THRESHOLDS.values()
)

if not any_open:
    print(f"No open ES position to resolve for {today}.")
    sys.exit()

es = yf.Ticker("ES=F")
history = es.history(period="60d", interval="15m")

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

for label, cfg in THRESHOLDS.items():
    print(f"\n--- [ES] Resolving {label} ---")
    broker = PaperBroker(starting_balance=10000, state_file=cfg["account_file"])

    if not broker.positions:
        print(f"No open {label} position to resolve for {today}.")
        continue

    for position in list(broker.positions):
        entry_date = date.fromisoformat(position["entry_date"])
        signal = position["direction"]
        stop_price = position["stop_price"]
        target_price = position["target_price"]

        entry_day_bars = session_bars[session_bars["date"] == entry_date]

        if entry_day_bars.empty:
            print(f"No price bars available yet for the {label} position from {entry_date} - will retry next scheduled run.")
            continue

        exit_price = None
        exit_reason = None

        for _, bar in entry_day_bars.iterrows():
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
            exit_price = entry_day_bars.iloc[-1]["Close"]
            exit_reason = "eod"

        broker.close_position(position, exit_price, reason=exit_reason, point_value=POINT_VALUE)
        refresh_dashboard()
        print(f"{label}: closed {signal} at {exit_price} ({exit_reason})")

    print(f"{label} balance: ${broker.balance:,.2f}")
