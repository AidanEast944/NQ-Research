"""
Live forward-test OPEN step for Vol+Momentum Reversal (research_log.md Entry 54, discovered via
src/research/pattern_scanner.py's bounded 27-combination scan). SHORT NQ when the prior day showed
high realized volatility (range > 10-day average) AND strong upward momentum (5-day return >
10-day rolling std of momentum) - betting on exhaustion/reversal, not continuation.

OPEN-ONLY - resolved later in the day by vol_momentum_reversal_resolve.py, matching the pattern
established after Entry 32's same-run-resolve-too-early bug.

Gated via live_gate.py - must be explicitly added to LIVE_STRATEGIES before this can open any
real position, regardless of what this script's own logic decides.
"""
import sys
import time
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from risk_limits import check_trade_allowed
from dashboard_trigger import refresh_dashboard
from live_gate import gate_new_entry
import coverage_log as cov
cov.start("vol_momentum_reversal_nq", "Vol+Momentum Reversal NQ")

STRATEGY_KEY = "vol_momentum_reversal_nq"
VOL_LOOKBACK = 10
MOMENTUM_LOOKBACK = 5
STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 2  # MNQ micro contract
ENTRY_TIME = "08:30"
ACCOUNT_FILE = "data/vol_momentum_reversal_paper_account.json"
RISK_STATE_FILE = "data/vol_momentum_reversal_risk_limits_state.json"

if not gate_new_entry(STRATEGY_KEY, label="Vol+Momentum Reversal"):
    sys.exit()

nq = yf.Ticker("NQ=F")
history = nq.history(period="60d", interval="1d")

if history.empty:
    print("WARNING: No data returned. Skipping.")
    sys.exit()

history["range"] = history["High"] - history["Low"]
history["vol_avg"] = history["range"].rolling(VOL_LOOKBACK).mean()
history["high_vol"] = history["range"] > history["vol_avg"]
history["momentum"] = history["Close"].pct_change(MOMENTUM_LOOKBACK)
history["strong_up_momentum"] = history["momentum"] > history["momentum"].rolling(VOL_LOOKBACK).std()

if len(history) < VOL_LOOKBACK + MOMENTUM_LOOKBACK + 1:
    print("Not enough history to compute a trustworthy signal yet.")
    sys.exit()

yesterday_row = history.iloc[-2]
is_signal = bool(yesterday_row["high_vol"]) and bool(yesterday_row["strong_up_momentum"])

print(f"Yesterday: range={yesterday_row['range']:.2f} (avg={yesterday_row['vol_avg']:.2f}), "
      f"momentum={yesterday_row['momentum']:.4f}")
print(f"Signal conditions met: {is_signal}")

if not is_signal:
    print("No signal today.")
    cov.evaluated("vol_momentum_reversal_nq", "signal conditions not met")
    sys.exit()

today = date.today()
entry_t = pd.Timestamp(ENTRY_TIME).time()

# FIX (2026-10-02, research_log.md - 08:30 candle timing bug): see gap_forward_check.py's
# docstring for the full reasoning - same bug, same fix, applied here too.
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 90

open_bar = None
today_bars = None

for attempt in range(1, MAX_RETRIES + 1):
    candidate_intraday = nq.history(period="5d", interval="15m")
    if candidate_intraday.empty:
        print(f"WARNING: No intraday data returned (attempt {attempt}/{MAX_RETRIES}).")
    else:
        candidate_intraday["date"] = candidate_intraday.index.date
        candidate_today_bars = candidate_intraday[candidate_intraday["date"] == today]
        candidate_open_bar = candidate_today_bars[candidate_today_bars.index.time == entry_t]
        if not candidate_open_bar.empty:
            today_bars = candidate_today_bars
            open_bar = candidate_open_bar
            break

    if attempt < MAX_RETRIES:
        print(f"No {ENTRY_TIME} candle yet for {today} (attempt {attempt}/{MAX_RETRIES}) - retrying in {RETRY_SLEEP_SECONDS}s.")
        time.sleep(RETRY_SLEEP_SECONDS)

if open_bar is None:
    print(f"No {ENTRY_TIME} candle for {today} after {MAX_RETRIES} attempts "
          f"({(MAX_RETRIES - 1) * RETRY_SLEEP_SECONDS}s total) - giving up for today.")
    sys.exit()

entry_price = open_bar.iloc[0]["Open"]
cov.evaluated("vol_momentum_reversal_nq", "signal fired, entry candle found")
stop_price = entry_price + STOP_POINTS
target_price = entry_price - TARGET_POINTS

broker = PaperBroker(starting_balance=10000, state_file=ACCOUNT_FILE)

already_processed_today = any(
    t.get("entry_date") == str(today) for t in broker.trade_history
) or any(
    p.get("entry_date") == str(today) for p in broker.positions
)
if already_processed_today:
    print(f"Already processed {today}. Skipping.")
    sys.exit()

proposed_risk_dollars = STOP_POINTS * POINT_VALUE
current_open_positions = len(broker.positions)

allowed, reason = check_trade_allowed(
    account_balance=broker.balance,
    proposed_risk_dollars=proposed_risk_dollars,
    current_open_positions=current_open_positions,
    state_file=RISK_STATE_FILE,
)

if not allowed:
    print(f"TRADE BLOCKED BY RISK LIMITS: {reason}")
    sys.exit()

broker.place_order(
    symbol="MNQ",
    direction="SHORT",
    entry_price=entry_price,
    stop_price=stop_price,
    target_price=target_price,
    entry_date=str(today)
)

print(f"Position opened - will be resolved end of day by vol_momentum_reversal_resolve.py.")