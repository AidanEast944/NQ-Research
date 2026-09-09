import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from strategy import get_prior_day_fade_signals_from_archive

times_to_test = ["08:30", "09:00", "09:30", "10:00", "10:30", "11:00",
                  "12:00", "13:00", "14:00", "15:00", "15:30"]

print(f"{'Time':>8} {'Trades':>8} {'Win Rate':>10} {'Avg Pts':>10} {'Total Pts':>10}")

for t in times_to_test:
    try:
        signals = get_prior_day_fade_signals_from_archive(
            stop_points=30, target_points=60, entry_time=t
        )
    except Exception as e:
        print(f"{t:>8}  error: {e}")
        continue

    if len(signals) == 0:
        print(f"{t:>8}        0  no trades")
        continue

    def pts(row):
        return row["exit_price"] - row["Close"] if row["signal"] == "LONG" else row["Close"] - row["exit_price"]

    signals["points"] = signals.apply(pts, axis=1)
    win_rate = (signals["points"] > 0).mean() * 100
    avg_pts = signals["points"].mean()
    total = signals["points"].sum()
    print(f"{t:>8} {len(signals):>8} {win_rate:>9.1f}% {avg_pts:>10.2f} {total:>10.2f}")