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

# Resolves open gap-continuation positions against real price action (runs after market close,
# unlike the check step which runs 7 minutes after the open - see research_log.md Entry 32 for why
# this split exists).
#
# FIX (2026-09-30, research_log.md - stale-position resolve bug): this used to only look at
# positions where entry_date == today, fetching only today's bars. That meant a position that
# didn't resolve on its own entry day - e.g. because Yahoo Finance returned no data that run, or
# the job didn't fire - became permanently invisible to this script, since every later run would
# only ever check "today" again. It would sit open indefinitely with its real stop/target action
# silently ignored, even though this strategy is intraday-only by design (every position is
# supposed to close same-day, via stop/target or the EOD fallback below).
#
# Now every open position is checked, each against its OWN entry day's bars (catching up a missed
# run on the correct historical day rather than today's), with the same stop/target-then-EOD logic
# as before. A position only stays open after this script runs if there's genuinely no bar data
# yet for its entry day (i.e. it's today's position and the market hasn't closed/data hasn't
# landed yet) - never because it's "not today" anymore.


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

if not broker.positions:
    print(f"No open gap position to resolve for {today}.")
    sys.exit()

nq = yf.Ticker("NQ=F")
# 60d (not 5d) so a position stuck open for a while can still be caught up against its own real
# entry-day bars, not just whatever the last few days happen to cover.
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

for position in list(broker.positions):
    entry_date = date.fromisoformat(position["entry_date"])
    signal = position["direction"]
    stop_price = position["stop_price"]
    target_price = position["target_price"]

    entry_day_bars = session_bars[session_bars["date"] == entry_date]

    if entry_day_bars.empty:
        print(f"No bars available yet to resolve the position from {entry_date} - try again later.")
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
    record_trade_result(points * POINT_VALUE)

    notify("NQ Research - Gap Continuation",
           f"{signal} closed {exit_reason}: {points:+.1f}pt (${points * POINT_VALUE:+,.2f})")

broker.summary()
