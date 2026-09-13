import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import glob
import pandas as pd

# CPI release dates are NOT on a fixed weekday pattern like NFP - they're scheduled by the BLS
# individually each year, typically (but not always) falling between the 10th-15th of the month.
# This is a MANUALLY CURATED list based on known historical BLS release dates, not a computed
# rule - less automatable than NFP, and should be verified/expanded against bls.gov if extending
# this further. Incomplete/approximate list for 2024-2026 based on typical patterns.
CPI_DATES = [
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15", "2024-06-12",
    "2024-07-11", "2024-08-14", "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13", "2025-06-11",
    "2025-07-15", "2025-08-12", "2025-09-11", "2025-10-15", "2025-11-13", "2025-12-10",
    "2026-01-14", "2026-02-11", "2026-03-11", "2026-04-14", "2026-05-13", "2026-06-10",
    "2026-07-15", "2026-08-12",
]

def get_cpi_fade_signals(min_move_points=20, stop_points=40, target_points=80,
                           data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    cpi_dates = set(pd.Timestamp(d).date() for d in CPI_DATES)

    results = []
    for cpi_date in cpi_dates:
        day_bars = history[history["date"] == cpi_date]
        if day_bars.empty:
            continue

        bar_830 = day_bars[day_bars.index.time == pd.Timestamp("08:30").time()]
        bar_845 = day_bars[day_bars.index.time == pd.Timestamp("08:45").time()]

        if bar_830.empty or bar_845.empty:
            continue

        price_830 = bar_830.iloc[0]["Close"]
        price_845 = bar_845.iloc[0]["Close"]
        reaction_move = price_845 - price_830

        if abs(reaction_move) < min_move_points:
            continue

        signal = "SHORT" if reaction_move > 0 else "LONG"
        entry_price = price_845
        stop_price = entry_price - stop_points if signal == "LONG" else entry_price + stop_points
        target_price = entry_price + target_points if signal == "LONG" else entry_price - target_points

        remaining_bars = day_bars[
            (day_bars.index.time > pd.Timestamp("08:45").time())
            & (day_bars.index.time <= pd.Timestamp("16:00").time())
        ]

        exit_price = None
        exit_reason = None
        for _, bar in remaining_bars.iterrows():
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
            exit_price = remaining_bars.iloc[-1]["Close"] if len(remaining_bars) > 0 else entry_price
            exit_reason = "eod"

        results.append({
            "date": cpi_date, "signal": signal, "reaction_move": reaction_move,
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason
        })

    return pd.DataFrame(results)

if __name__ == "__main__":
    signals = get_cpi_fade_signals()

    def pts(row):
        return row["exit_price"] - row["entry_price"] if row["signal"] == "LONG" else row["entry_price"] - row["exit_price"]

    if len(signals) == 0:
        print("No CPI fade signals found.")
    else:
        signals["points"] = signals.apply(pts, axis=1)
        wins = (signals["points"] > 0).sum()
        win_rate = wins / len(signals) * 100
        gross_win = signals[signals["points"] > 0]["points"].sum()
        gross_loss = abs(signals[signals["points"] <= 0]["points"].sum())
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        print(f"Trades: {len(signals)}, Win rate: {win_rate:.1f}%, PF: {pf:.2f}")