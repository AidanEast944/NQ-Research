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
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from risk_limits import check_trade_allowed
from dashboard_trigger import refresh_dashboard
from live_gate import gate_new_entry

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
    sys.exit()

today = date.today()
intraday = nq.history(period="5d", interval="15m")
if intraday.empty:
    print("WARNING: No intraday data returned. Skipping.")
    sys.exit()

intraday["date"] = intraday.index.date
today_bars = intraday[intraday["date"] == today]
entry_t = pd.Timestamp(ENTRY_TIME).time()
open_bar = today_bars[today_bars.index.time == entry_t]

if open_bar.empty:
    print(f"No {ENTRY_TIME} candle yet for {today}.")
    sys.exit()

entry_price = open_bar.iloc[0]["Open"]
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