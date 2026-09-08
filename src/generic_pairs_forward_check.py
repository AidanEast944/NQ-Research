import sys
import json
import os
import yfinance as yf
import pandas as pd
from datetime import date

LOOKBACK = 20
ENTRY_Z = 2.0
STOP_Z = 4.0        # if the spread keeps diverging past this, the mean-reversion thesis is failing - cut it
MAX_HOLD_DAYS = 20   # trading days; if it hasn't reverted by now, stop waiting on a broken thesis

def run_pairs_check(symbol_a, symbol_b, state_file, label):
    def load_state():
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                return json.load(f)
        return {"position": None, "history": [], "last_run_date": None}

    def save_state(state):
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    state = load_state()
    today = date.today()

    if state.get("last_run_date") == str(today):
        print(f"[{label}] Already processed {today}. Skipping.")
        return
    state["last_run_date"] = str(today)

    a = yf.Ticker(symbol_a).history(period="60d", interval="1d")
    b = yf.Ticker(symbol_b).history(period="60d", interval="1d")

    if a.empty or b.empty:
        print(f"[{label}] WARNING: No data returned. Skipping this run.")
        save_state(state)
        return

    a = a[["Close"]].rename(columns={"Close": "close_a"})
    b = b[["Close"]].rename(columns={"Close": "close_b"})
    a.index = a.index.date
    b.index = b.index.date

    merged = a.join(b, how="inner")
    merged["ratio"] = merged["close_a"] / merged["close_b"]
    merged["ratio_mean"] = merged["ratio"].rolling(LOOKBACK).mean()
    merged["ratio_std"] = merged["ratio"].rolling(LOOKBACK).std()
    merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]

    if str(today) not in [str(d) for d in merged.index]:
        print(f"[{label}] No data yet for {today}.")
        save_state(state)
        return

    current_z = merged.loc[merged.index == today, "zscore"].iloc[0]
    print(f"[{label}] Current z-score: {current_z:.2f}")

    if state["position"] is None:
        if current_z > ENTRY_Z:
            state["position"] = {"direction_a": "SHORT", "entry_date": str(today), "entry_z": current_z}
            print(f"[{label}] OPENED: SHORT {symbol_a} / LONG {symbol_b} (z-score {current_z:.2f})")
        elif current_z < -ENTRY_Z:
            state["position"] = {"direction_a": "LONG", "entry_date": str(today), "entry_z": current_z}
            print(f"[{label}] OPENED: LONG {symbol_a} / SHORT {symbol_b} (z-score {current_z:.2f})")
        else:
            print(f"[{label}] No signal - z-score {current_z:.2f} within normal range.")
    else:
        direction = state["position"]["direction_a"]
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
            print(f"[{label}] Position CLOSED (reverted): entered z={entry_z:.2f}, now z={current_z:.2f}")
            state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z, "exit_reason": "reverted"})
            state["position"] = None
        elif hit_z_stop:
            print(f"[{label}] STOPPED OUT: z-score diverged past +/-{STOP_Z} (entered z={entry_z:.2f}, now z={current_z:.2f}) "
                  f"- reversion thesis failing, cutting the position")
            state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z, "exit_reason": "z_stop"})
            state["position"] = None
        elif hit_time_stop:
            print(f"[{label}] STOPPED OUT: held {days_held} trading days without reverting (max {MAX_HOLD_DAYS}) "
                  f"- entered z={entry_z:.2f}, now z={current_z:.2f}, closing")
            state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z, "exit_reason": "time_stop"})
            state["position"] = None
        else:
            held_str = f", held {days_held}d" if days_held is not None else ""
            print(f"[{label}] Position still open: {direction} from {entry_date_str} "
                  f"(entry z={entry_z:.2f}, now z={current_z:.2f}{held_str})")

    save_state(state)

run_pairs_check("NQ=F", "YM=F", "data/pairs_nqym_forward_state.json", "NQ/YM")
run_pairs_check("ES=F", "YM=F", "data/pairs_esym_forward_state.json", "ES/YM")
