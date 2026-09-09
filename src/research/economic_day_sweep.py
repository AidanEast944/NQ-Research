import pandas as pd
from strategy import get_prior_day_break_signals_from_archive
from results_logger import log_result

STOP_POINTS = 30
TARGET_POINTS = 60

# Load the economic calendar
econ_calendar = pd.read_csv("data/economic_calendar.csv", parse_dates=["date"])
econ_dates = set(econ_calendar["date"].dt.date)

# Get our existing signals
signals = get_prior_day_break_signals_from_archive(stop_points=STOP_POINTS, target_points=TARGET_POINTS)

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["Close"]
    else:
        return row["Close"] - row["exit_price"]

signals["points"] = signals.apply(points_result, axis=1)
signals["is_econ_day"] = signals["date"].isin(econ_dates)

def report(label, subset, log_name):
    if len(subset) == 0:
        print(f"{label}: no trades")
        return
    win_rate = (subset["points"] > 0).mean() * 100
    avg_points = subset["points"].mean()
    total_points = subset["points"].sum()
    print(f"{label}: {len(subset)} trades, {win_rate:.1f}% win rate, {avg_points:.2f} avg points")
    log_result(log_name, f"stop={STOP_POINTS},target={TARGET_POINTS}", len(subset), win_rate, avg_points, total_points)

print(f"\n--- Prior Day Break, Stop {STOP_POINTS} / Target {TARGET_POINTS} ---\n")

report("ALL signals", signals, "prior_day_break_all")
print()
report("Economic data days", signals[signals["is_econ_day"] == True], "prior_day_break_econ_day")
report("Normal days", signals[signals["is_econ_day"] == False], "prior_day_break_normal_day")