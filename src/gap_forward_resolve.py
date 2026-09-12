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
STATE_FILE = "data/gap_paper_account.json"

# Resolves any position gap_forward_check.py opened today, using the FULL day's bars (this runs
# after market close, unlike the check step which runs 7 minutes after the open) - see
# research_log.md Entry 32 for why this split exists.


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


broker = PaperBroker(starting_balance=10000, state_file=STATE_FILE)

today = date.today()
todays_positions = [p for p in broker.positions if p.get("entry_date") == str(today)]

if not todays_positions:
    print(f"No open gap position to resolve for {today}.")
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
            exit_price, exit_reason = stop_price, "stop"
            break
        elif hit_target:
            exit_price, exit_reason = target_price, "target"
            break

    if exit_price is None and not today_bars.empty:
        exit_price = today_bars.iloc[-1]["Close"]
        exit_reason = "eod"

    if exit_price is None:
        print(f"No bars available yet to resolve today's position - try again later.")
        continue

    broker.close_position(position, exit_price, reason=exit_reason, point_value=POINT_VALUE)
    refresh_dashboard()

    points = (exit_price - position["entry_price"]) if signal == "LONG" else (position["entry_price"] - exit_price)
    record_trade_result(points * POINT_VALUE)

    notify("NQ Research - Gap Continuation",
           f"{signal} closed {exit_reason}: {points:+.1f}pt (${points * POINT_VALUE:+,.2f})")

broker.summary()
