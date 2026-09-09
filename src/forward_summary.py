import pandas as pd
import os

LOG_FILE = "data/forward_log.csv"

if not os.path.exists(LOG_FILE):
    print("No forward log file exists yet - nothing to summarize.")
    exit()

log = pd.read_csv(LOG_FILE)

if len(log) == 0:
    print("Forward log exists but is empty - no predictions logged yet.")
    exit()

def points_result(row):
    if pd.isna(row["exit_price"]):
        return None
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

log["points"] = log.apply(points_result, axis=1)

print("=== FORWARD TEST SUMMARY ===\n")
print(f"Total predictions logged: {len(log)}")
print(f"Date range: {log['date'].min()} to {log['date'].max()}\n")

for strategy_name in log["strategy"].unique():
    strategy_rows = log[log["strategy"] == strategy_name]
    closed = strategy_rows[strategy_rows["status"] == "CLOSED"]
    open_rows = strategy_rows[strategy_rows["status"] == "OPEN"]

    print(f"--- {strategy_name.upper()} ---")
    print(f"Total signals: {len(strategy_rows)} ({len(closed)} closed, {len(open_rows)} still open)")

    if len(closed) > 0:
        win_rate = (closed["points"] > 0).mean() * 100
        avg_points = closed["points"].mean()
        total_points = closed["points"].sum()
        wins = (closed["points"] > 0).sum()
        losses = (closed["points"] <= 0).sum()

        print(f"Record: {wins}W - {losses}L ({win_rate:.1f}% win rate)")
        print(f"Avg points per trade: {avg_points:.2f}")
        print(f"Total points: {total_points:.2f}")

        exit_reasons = closed["exit_reason"].value_counts()
        print(f"Exit reasons: {dict(exit_reasons)}")
    else:
        print("No closed trades yet to score.")

    print()