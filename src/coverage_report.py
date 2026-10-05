"""
Daily coverage report (research_log.md Entry 61) - reads data/coverage_log.json (written by each
live check script via coverage_log.py) and says which strategies actually evaluated a signal
today and which didn't. Fires a macOS notification when a weekday has gaps, so a silent skip
(Entries 57/58/60) is visible the same evening instead of weeks later.

Run after the morning checks and the 5 PM resolve jobs (scheduled 5:35 PM PT). Purely diagnostic.
Usage: python3 src/coverage_report.py [YYYY-MM-DD]   (date optional, defaults to today)
"""
import json
import os
import subprocess
import sys
from datetime import date

COVERAGE_FILE = "data/coverage_log.json"

EXPECTED = {
    "gap_unfiltered": "Gap (unfiltered)",
    "volume_confirmed_gap_nq": "Volume-Confirmed Gap NQ",
    "volume_confirmed_gap_ym": "Volume-Confirmed Gap YM",
    "volume_confirmed_gap_es": "Volume-Confirmed Gap ES",
    "vol_momentum_reversal_nq": "Vol+Momentum Reversal NQ",
    "pairs_nq_es": "Pairs NQ/ES",
    "pairs_nq_ym": "Pairs NQ/YM",
    "pairs_es_ym": "Pairs ES/YM",
}


def notify(title, message):
    try:
        safe_message = message.replace('"', '\\"').replace("\\", "\\\\")
        safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
            timeout=10, check=False,
        )
    except Exception as e:
        print(f"(notification failed, non-fatal: {e})")


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else str(date.today())
    weekday = date.fromisoformat(day).weekday()
    if weekday >= 5:
        print(f"{day} is a weekend - futures closed, nothing expected to evaluate. OK.")
        return

    data = {}
    if os.path.exists(COVERAGE_FILE):
        with open(COVERAGE_FILE) as f:
            data = json.load(f)
    today_rec = data.get(day, {})

    missing = []
    print(f"=== Coverage report for {day} ===")
    for key, label in EXPECTED.items():
        rec = today_rec.get(key)
        if rec is None:
            print(f"  MISSING        {label}: no record at all (script never ran, or crashed before registering)")
            missing.append(label)
        elif rec["status"] == "EVALUATED":
            print(f"  evaluated      {label}: {rec['detail']}")
        else:
            print(f"  NOT EVALUATED  {label}: {rec['detail']}")
            missing.append(label)

    print()
    if not missing:
        print("All live strategies evaluated today.")
        return

    if len(missing) == len(EXPECTED):
        msg = (f"No strategy evaluated on {day} - likely a market holiday or a data outage. "
               f"If it was a normal trading day, check the logs.")
    else:
        msg = f"{len(missing)} of {len(EXPECTED)} checks did not evaluate on {day}: " + ", ".join(missing)
    print("GAP: " + msg)
    notify("NQ Research - coverage gap", msg)


if __name__ == "__main__":
    main()
