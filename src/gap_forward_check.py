import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from risk_limits import check_trade_allowed, record_trade_result

MIN_GAP_POINTS = 30
STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 2  # MNQ micro contract
STATE_FILE = "data/gap_paper_account.json"

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

# Checks trade_history, not just open positions - place_order()+close_position() run
# back-to-back within a single script execution, so `positions` is always empty by the time this
# check runs. Checking only positions never catches a same-day re-run (bug found live on
# 2026-09-10: running this script twice on the same day recorded the same gap trade twice).
already_processed_today = any(
    t.get("entry_date") == str(today) for t in broker.trade_history
) or any(
    p.get("entry_date") == str(today) for p in broker.positions
)
if already_processed_today:
    print(f"Already processed a gap signal for {today}. Skipping to avoid a duplicate trade record.")
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

day_bars = today_bars[
    (today_bars.index.time > pd.Timestamp("08:30").time())
    & (today_bars.index.time <= pd.Timestamp("16:00").time())
]

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
    exit_price = day_bars.iloc[-1]["Close"] if len(day_bars) > 0 else entry_price
    exit_reason = "eod_pending"

trade = broker.place_order(
    symbol="MNQ",
    direction=signal,
    entry_price=entry_price,
    stop_price=stop_price,
    target_price=target_price,
    entry_date=str(today)
)

# point_value=POINT_VALUE is the fix: without it, PaperBroker defaulted to $20/pt (full NQ)
# regardless of the MNQ symbol above, overstating every fill on this account by 10x.
broker.close_position(trade, exit_price, reason=exit_reason, point_value=POINT_VALUE)

points = (exit_price - entry_price) if signal == "LONG" else (entry_price - exit_price)
record_trade_result(points * POINT_VALUE)

print(f"Balance: ${broker.balance:,.2f}")
