import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pandas as pd
from strategy import get_gap_signals_from_archive

gap_signals = get_gap_signals_from_archive(min_gap_points=30, stop_points=40, target_points=80, fill_mode=False)

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

gap_signals["gap_points"] = gap_signals.apply(points_result, axis=1)
gap_signals = gap_signals.rename(columns={"date": "trade_date"})[["trade_date", "gap_points"]]

STATE_FILE = "data/pairs_forward_state.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    pairs_history = state.get("history", [])
else:
    pairs_history = []

if not pairs_history:
    print("Not enough pairs trading forward history yet to compare - this will populate over time.")
    print(f"\nFor reference, gap continuation currently has {len(gap_signals)} historical trades.")
else:
    pairs_df = pd.DataFrame(pairs_history)
    pairs_df["trade_date"] = pd.to_datetime(pairs_df["entry_date"]).dt.date
    gap_signals["trade_date"] = pd.to_datetime(gap_signals["trade_date"]).dt.date

    merged = gap_signals.merge(pairs_df[["trade_date"]], on="trade_date", how="inner")
    print(f"Overlapping trade dates found: {len(merged)}")
    if len(merged) < 5:
        print("Too few overlapping dates yet for a meaningful correlation - check back as more live data accumulates.")