import sys
import json
import os
import glob
import pandas as pd
from datetime import date

MA_PERIOD = 5
STOP_POINTS = 200
STATE_FILE = "data/trend_forward_state.json"
DATA_FOLDER = "data/raw"

# RETIRED: Entry 6 in research_log.md - FAIL (regime-dependent, not durable; walk-forward
# was front-loaded and a regime filter made results worse). Not part of the Tier-1 live
# candidates. This script still runs to manage/close any position that was already open
# at the time of retirement, but it will not open any new ones - remove this guard only
# after a fresh, explicit decision to re-test the strategy.
STRATEGY_RETIRED = True

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"position": None, "trade_history": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
if not files:
    print("No archive data available.")
    sys.exit()

all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
history = pd.concat(all_days)
history = history[~history.index.duplicated(keep="first")]
history = history.sort_index()
history["date"] = history.index.date

daily = history.groupby("date").agg(high=("High", "max"), low=("Low", "min"), close=("Close", "last"))
daily = daily.sort_index()
daily["ma"] = daily["close"].rolling(MA_PERIOD).mean()

today = date.today()
if today not in daily.index:
    print(f"No archived data for {today} yet. Run save_daily_date.py first, or check back later.")
    sys.exit()

today_row = daily.loc[today]
state = load_state()
position = state["position"]

already_processed_today = any(
    trade.get("exit_date") == str(today) for trade in state["trade_history"]
) or (position is not None and position["entry_date"] == str(today) and "already_ran_today" in state and state["already_ran_today"] == str(today))

if "last_run_date" in state and state["last_run_date"] == str(today):
    print(f"Already processed {today}. Skipping to avoid duplicate action.")
    sys.exit()

state["last_run_date"] = str(today)

if position is not None:
    signal = position["direction"]
    stop_price = position["stop_price"]

    hit_stop = (signal == "LONG" and today_row["low"] <= stop_price) or \
               (signal == "SHORT" and today_row["high"] >= stop_price)

    hit_reversal = (not pd.isna(today_row["ma"])) and (
        (signal == "LONG" and today_row["close"] < today_row["ma"]) or
        (signal == "SHORT" and today_row["close"] > today_row["ma"])
    )

    if hit_stop or hit_reversal:
        exit_price = stop_price if hit_stop else today_row["close"]
        exit_reason = "stop" if hit_stop else "trend_reversal"

        if signal == "LONG":
            points = exit_price - position["entry_price"]
        else:
            points = position["entry_price"] - exit_price

        position["exit_date"] = str(today)
        position["exit_price"] = exit_price
        position["exit_reason"] = exit_reason
        position["points"] = points
        state["trade_history"].append(position)
        state["position"] = None
        print(f"CLOSED {signal} position: entry {position['entry_price']} -> exit {exit_price} "
              f"({exit_reason}), {points:+.2f} points")
    else:
        print(f"Position still open: {signal} from {position['entry_date']} at {position['entry_price']} "
              f"(currently {today_row['close']}).")

if STRATEGY_RETIRED:
    if state["position"] is None:
        print("Strategy RETIRED (research_log.md Entry 6: FAIL) - no new positions will be opened.")
elif state["position"] is None and not pd.isna(today_row["ma"]):
    if today_row["close"] > today_row["ma"]:
        new_signal = "LONG"
    elif today_row["close"] < today_row["ma"]:
        new_signal = "SHORT"
    else:
        new_signal = None

    if new_signal:
        entry_price = today_row["close"]
        stop_price = entry_price - STOP_POINTS if new_signal == "LONG" else entry_price + STOP_POINTS

        state["position"] = {
            "direction": new_signal,
            "entry_date": str(today),
            "entry_price": entry_price,
            "stop_price": stop_price
        }
        print(f"OPENED {new_signal} position at {entry_price} (stop: {stop_price})")

save_state(state)
print(f"\nState saved. Open position: {state['position']}")
print(f"Total closed trades: {len(state['trade_history'])}")
