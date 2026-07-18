import os
import csv
from datetime import datetime

RESULTS_FILE = "results/all_test_results.csv"

def log_result(strategy_name, params, trades, win_rate, avg_points, total_points):
    os.makedirs("results", exist_ok=True)
    file_exists = os.path.exists(RESULTS_FILE)

    with open(RESULTS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "strategy", "params",
                "trades", "win_rate", "avg_points", "total_points"
            ])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            strategy_name,
            params,
            trades,
            round(win_rate, 2),
            round(avg_points, 2),
            round(total_points, 2)
        ])