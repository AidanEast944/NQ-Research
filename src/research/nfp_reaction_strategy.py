import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import glob
import pandas as pd
import calendar
from datetime import date

def get_nfp_dates(start_year, start_month, end_year, end_month):
    dates = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        cal = calendar.monthcalendar(year, month)
        first_week = cal[0]
        if first_week[calendar.FRIDAY] == 0:
            first_friday = cal[1][calendar.FRIDAY]
        else:
            first_friday = first_week[calendar.FRIDAY]
        dates.append(date(year, month, first_friday))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return dates

def get_nfp_reaction_signals(min_move_points=20, stop_points=40, target_points=80,
                               data_folder="data/raw_nq_extended"):
    files = glob.glob(os.path.join(data_folder, "*.csv"))
    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    history = pd.concat(all_days)
    history = history[~history.index.duplicated(keep="first")]
    history = history.sort_index()
    history.index = pd.to_datetime(history.index, utc=True).tz_convert("America/New_York")
    history["date"] = history.index.date

    nfp_dates = set(get_nfp_dates(2024, 1, 2026, 9))

    results = []
    for nfp_date in nfp_dates:
        day_bars = history[history["date"] == nfp_date]
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

        signal = "LONG" if reaction_move > 0 else "SHORT"
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
            "date": nfp_date, "signal": signal, "reaction_move": reaction_move,
            "entry_price": entry_price, "exit_price": exit_price, "exit_reason": exit_reason
        })

    return pd.DataFrame(results)

if __name__ == "__main__":
    signals = get_nfp_reaction_signals()

    def pts(row):
        return row["exit_price"] - row["entry_price"] if row["signal"] == "LONG" else row["entry_price"] - row["exit_price"]

    if len(signals) == 0:
        print("No NFP reaction signals found.")
    else:
        signals["points"] = signals.apply(pts, axis=1)
        wins = (signals["points"] > 0).sum()
        win_rate = wins / len(signals) * 100
        gross_win = signals[signals["points"] > 0]["points"].sum()
        gross_loss = abs(signals[signals["points"] <= 0]["points"].sum())
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        print(f"Trades: {len(signals)}, Win rate: {win_rate:.1f}%, PF: {pf:.2f}")
        print(f"\nAll trades:")
        print(signals[["date", "signal", "reaction_move", "points", "exit_reason"]].to_string(index=False))