import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from risk_limits import check_trade_allowed

MIN_GAP_POINTS = 30
STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 2  # MNQ micro contract
STATE_FILE = "data/gap_paper_account.json"

# OPEN-ONLY - this used to open AND resolve a trade in one run, which meant it was almost never
# actually run late enough in the day to see the real stop/target outcome (this job fires 7
# minutes after the entry bar) - it just fell through to an "eod_pending"/0-point placeholder
# almost every day, and since nothing ever re-checked it, that placeholder became the permanent
# record. Split into this (open) + gap_forward_resolve.py (resolve, run after market close),
# matching fade_paper_check.py/fade_paper_resolve.py's already-correct pattern. Found and fixed
# 2026-09-10 - see research_log.md Entry 32.

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")

if history.empty:
    print("WARNING: No data returned. Skipping.")
    sys.exit()

history["date"] = history.index.date
today = date.today()
today_bars = history[history["date"] == today]

if today_bars.empty:
    print(f"No data yet for {today}.")
    sys.exit()

prior_days = history[history["date"] < today]
if prior_days.empty:
    print("Not enough history.")
    sys.exit()

most_recent_day = prior_days["date"].max()
prior_day_bars = prior_days[prior_days["date"] == most_recent_day]
prior_close = prior_day_bars.iloc[-1]["Close"]

open_bar = today_bars[today_bars.index.time == pd.Timestamp("08:30").time()]
if open_bar.empty:
    print(f"No 08:30 candle yet for {today}.")
    sys.exit()

open_price = open_bar.iloc[0]["Open"]
gap_points = open_price - prior_close

broker = PaperBroker(starting_balance=10000, state_file=STATE_FILE)

# Checks trade_history too, not just open positions - see research_log.md Entry 29. Also blocks
# opening a second position while one from today is already open and awaiting resolve.
already_processed_today = any(
    t.get("entry_date") == str(today) for t in broker.trade_history
) or any(
    p.get("entry_date") == str(today) for p in broker.positions
)
if already_processed_today:
    print(f"Already opened/processed a gap signal for {today}. Skipping to avoid a duplicate.")
    sys.exit()

print(f"Prior close: {prior_close}, Today's open: {open_price}, Gap: {gap_points:.2f} points")

if abs(gap_points) < MIN_GAP_POINTS:
    print(f"Gap too small ({gap_points:.2f} pts) - no signal.")
    sys.exit()

signal = "LONG" if gap_points > 0 else "SHORT"
entry_price = open_price
stop_price = entry_price - STOP_POINTS if signal == "LONG" else entry_price + STOP_POINTS
target_price = entry_price + TARGET_POINTS if signal == "LONG" else entry_price - TARGET_POINTS

# --- RISK CIRCUIT BREAKER CHECK, using the REAL current account balance ---
proposed_risk_dollars = STOP_POINTS * POINT_VALUE
current_open_positions = len(broker.positions)

allowed, reason = check_trade_allowed(
    account_balance=broker.balance,
    proposed_risk_dollars=proposed_risk_dollars,
    current_open_positions=current_open_positions
)

if not allowed:
    print(f"TRADE BLOCKED BY RISK LIMITS: {reason}")
    sys.exit()
# --- END RISK CHECK ---

broker.place_order(
    symbol="MNQ",
    direction=signal,
    entry_price=entry_price,
    stop_price=stop_price,
    target_price=target_price,
    entry_date=str(today)
)

print(f"Position opened - will be resolved end of day by gap_forward_resolve.py.")
