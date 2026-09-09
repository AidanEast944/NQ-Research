import sys
import json
import os
import yfinance as yf
import pandas as pd
from datetime import date

LOOKBACK = 20
ENTRY_Z = 2.0
STOP_Z = 3.5        # matches get_pairs_trading_signals_from_archive()'s default in strategy.py -
                     # this is the stop that was actually backtested and produced the PF 2.52
                     # quoted for Entry 9 in research_log.md, not a fresh guess
MAX_HOLD_DAYS = 15   # same - matches the archive backtest's default, not a fresh guess
STATE_FILE = "data/pairs_forward_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"position": None, "history": [], "last_run_date": None}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

state = load_state()
today = date.today()

if state.get("last_run_date") == str(today):
    print(f"Already processed {today}. Skipping.")
    sys.exit()
state["last_run_date"] = str(today)

nq = yf.Ticker("NQ=F").history(period="60d", interval="1d")
es = yf.Ticker("ES=F").history(period="60d", interval="1d")

if nq.empty or es.empty:
    print("WARNING: No data returned. Skipping this run.")
    save_state(state)
    sys.exit()

nq = nq[["Close"]].rename(columns={"Close": "close_nq"})
es = es[["Close"]].rename(columns={"Close": "close_es"})
nq.index = nq.index.date
es.index = es.index.date

merged = nq.join(es, how="inner")
merged["ratio"] = merged["close_nq"] / merged["close_es"]
merged["ratio_mean"] = merged["ratio"].rolling(LOOKBACK).mean()
merged["ratio_std"] = merged["ratio"].rolling(LOOKBACK).std()
merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]

if str(today) not in [str(d) for d in merged.index]:
    print(f"No data yet for {today}.")
    save_state(state)
    sys.exit()

current_z = merged.loc[merged.index == today, "zscore"].iloc[0]
print(f"Current NQ/ES z-score: {current_z:.2f}")

if state["position"] is None:
    if current_z > ENTRY_Z:
        state["position"] = {"direction_nq": "SHORT", "entry_date": str(today), "entry_z": current_z}
        print(f"OPENED: SHORT NQ / LONG ES (z-score {current_z:.2f})")
    elif current_z < -ENTRY_Z:
        state["position"] = {"direction_nq": "LONG", "entry_date": str(today), "entry_z": current_z}
        print(f"OPENED: LONG NQ / SHORT ES (z-score {current_z:.2f})")
    else:
        print(f"No signal - z-score {current_z:.2f} within normal range.")
else:
    direction = state["position"]["direction_nq"]
    entry_z = state["position"]["entry_z"]
    reverted = (direction == "SHORT" and current_z <= 0.5) or (direction == "LONG" and current_z >= -0.5)
    hit_z_stop = (direction == "SHORT" and current_z >= STOP_Z) or (direction == "LONG" and current_z <= -STOP_Z)

    entry_date_str = state["position"]["entry_date"]
    days_held = None
    try:
        idx_list = list(merged.index)
        days_held = idx_list.index(today) - idx_list.index(date.fromisoformat(entry_date_str))
    except ValueError:
        pass  # entry date has rolled out of the lookback window - skip the time-stop check this run
    hit_time_stop = days_held is not None and days_held >= MAX_HOLD_DAYS

    if reverted:
        print(f"Position CLOSED (reverted): entered at z={entry_z:.2f}, now z={current_z:.2f}")
        state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z, "exit_reason": "reverted"})
        state["position"] = None
    elif hit_z_stop:
        print(f"STOPPED OUT: z-score diverged past +/-{STOP_Z} (entered z={entry_z:.2f}, now z={current_z:.2f}) "
              f"- reversion thesis failing, cutting the position")
        state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z, "exit_reason": "z_stop"})
        state["position"] = None
    elif hit_time_stop:
        print(f"STOPPED OUT: held {days_held} trading days without reverting (max {MAX_HOLD_DAYS}) "
              f"- entered z={entry_z:.2f}, now z={current_z:.2f}, closing")
        state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z, "exit_reason": "time_stop"})
        state["position"] = None
    else:
        held_str = f", held {days_held}d" if days_held is not None else ""
        print(f"Position still open: {direction} from {entry_date_str} "
              f"(entry z={entry_z:.2f}, now z={current_z:.2f}{held_str})")

save_state(state)
