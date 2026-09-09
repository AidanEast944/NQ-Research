import sys
import glob
import os
import pandas as pd
from datetime import date

LOG_FILE = "data/forward_log.csv"
DATA_FOLDER = "data/raw"

if not os.path.exists(LOG_FILE):
    print("No forward log file exists yet - nothing to resolve.")
    sys.exit()

log = pd.read_csv(LOG_FILE, dtype={"exit_price": "float64", "exit_reason": "object", "status": "object"})
log["date"] = pd.to_datetime(log["date"]).dt.date

open_rows = log[log["status"] == "OPEN"]

if open_rows.empty:
    print("No open predictions to resolve.")
    sys.exit()

files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
if not files:
    print("No archive data available to resolve against.")
    sys.exit()

all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
history = pd.concat(all_days)
history = history[~history.index.duplicated(keep="first")]
history = history.sort_index()
history["date"] = history.index.date

resolved_count = 0
still_open_count = 0

for idx, row in open_rows.iterrows():
    trade_date = row["date"]
    signal = row["signal"]
    stop_price = row["stop_price"]
    target_price = row["target_price"]
    strategy_name = row["strategy"]

    day_bars = history[
        (history["date"] == trade_date)
        & (history.index.time > pd.Timestamp("08:30").time())
        & (history.index.time <= pd.Timestamp("16:00").time())
    ]

    if day_bars.empty:
        still_open_count += 1
        continue

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
            exit_price = stop_price
            exit_reason = "stop"
            break
        elif hit_target:
            exit_price = target_price
            exit_reason = "target"
            break

    if exit_price is None:
        exit_price = day_bars.iloc[-1]["Close"]
        exit_reason = "eod"

    log.loc[idx, "status"] = "CLOSED"
    log.loc[idx, "exit_price"] = exit_price
    log.loc[idx, "exit_reason"] = exit_reason
    resolved_count += 1
    print(f"RESOLVED [{strategy_name}] {trade_date}: {signal} closed at {exit_price} ({exit_reason})")

log.to_csv(LOG_FILE, index=False)
print(f"\nDone. Resolved {resolved_count} prediction(s), {still_open_count} still awaiting data.")