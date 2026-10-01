"""
Resolves open positions from volume_confirmed_gap_forward_check.py, for BOTH the 1.2x and 1.5x
tracks independently, against real price action (runs after market close). See research_log.md
Entry 32 for why the open/resolve split exists.

FIX (2026-09-30, research_log.md - stale-position resolve bug): used to only check positions where
entry_date == today, using only today's bars - see gap_forward_resolve.py's docstring for the full
reasoning (same bug, same fix, applied here too). Now every open position is checked against its
own entry day's bars, so a position that missed its same-day resolve run can't get stranded open
indefinitely.
"""
import sys
import subprocess
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from dashboard_trigger import refresh_dashboard
from risk_limits import record_trade_result

STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 2  # MNQ micro contract

THRESHOLDS = {
    "1.2x": {
        "account_file": "data/volume_gap_1_2x_paper_account.json",
        "risk_state_file": "data/volume_gap_1_2x_risk_limits_state.json",
    },
    "1.5x": {
        "account_file": "data/volume_gap_1_5x_paper_account.json",
        "risk_state_file": "data/volume_gap_1_5x_risk_limits_state.json",
    },
}


def notify(title, message):
    """Best-effort macOS notification - never lets a notification failure break the run."""
    try:
        safe_message = message.replace('"', '\\"').replace("\\", "\\\\")
        safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
            timeout=10, check=False
        )
    except Exception as e:
        print(f"(notification failed, non-fatal: {e})")


today = date.today()

any_open = any(
    PaperBroker(starting_balance=10000, state_file=cfg["account_file"]).positions
    for cfg in THRESHOLDS.values()
)

if not any_open:
    print(f"No open volume-confirmed positions to resolve for {today}.")
    sys.exit()

nq = yf.Ticker("NQ=F")
history = nq.history(period="60d", interval="15m")

if history.empty:
    print("WARNING: No data returned from Yahoo Finance. Skipping this run.")
    sys.exit()

history["date"] = history.index.date
history["time"] = history.index.time

session_bars = history[
    (history["time"] > pd.Timestamp("08:30").time())
    & (history["time"] <= pd.Timestamp("16:00").time())
].sort_index()

for label, cfg in THRESHOLDS.items():
    print(f"\n--- Threshold {label} ---")
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
            print(f"No bars available yet to resolve the {label} position from {entry_date} - try again later.")
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

        points = (exit_price - position["entry_price"]) if signal == "LONG" else (position["entry_price"] - exit_price)
        record_trade_result(points * POINT_VALUE, state_file=cfg["risk_state_file"])

        notify(f"NQ Research - Vol-Confirmed {label}",
               f"{signal} closed {exit_reason}: {points:+.1f}pt (${points * POINT_VALUE:+,.2f})")

    broker.summary()
