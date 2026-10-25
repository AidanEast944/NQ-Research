"""
Daily coverage report (research_log.md Entry 61) - reads data/coverage_log.json (written by each
live check script via coverage_log.py) and says which strategies actually evaluated a signal
today and which didn't. Fires a macOS notification when a weekday has gaps, so a silent skip
(Entries 57/58/60) is visible the same evening instead of weeks later.

Run after the morning checks and the 5 PM resolve jobs (scheduled 5:35 PM PT). Purely diagnostic.
Usage: python3 src/coverage_report.py [YYYY-MM-DD]   (date optional, defaults to today)
"""
import glob
import json
import os
import subprocess
import sys
from datetime import date, timedelta

COVERAGE_FILE = "data/coverage_log.json"

# Archive freshness (research_log.md Entry 78). The Databento refresh failed silently from 2026-09-30 to
# 2026-10-24 because nothing watched the research archives. The newest archived day should normally be yesterday
# or the last trading day; a gap of this many missing WEEKDAYS (a single market holiday gives one) raises an alert.
ARCHIVES = {"NQ": "data/raw_nq_extended", "ES": "data/raw_es_extended",
            "YM": "data/raw_ym_extended", "RTY": "data/raw_rty_extended"}
MAX_MISSING_WEEKDAYS = 2

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


def check_archives(day):
    """Return (lines, stale_messages). A symbol is stale when 2 or more weekdays between its newest archived day
    and today (exclusive) have no file."""
    today = date.fromisoformat(day)
    lines, stale = [], []
    for sym, folder in ARCHIVES.items():
        files = sorted(glob.glob(os.path.join(folder, "*.csv")))
        if not files:
            stale.append(f"{sym}: no archive files found in {folder}")
            lines.append(f"  ARCHIVE EMPTY  {sym}")
            continue
        newest = date.fromisoformat(os.path.basename(files[-1]).replace(".csv", "")[-10:])
        have = {os.path.basename(f).replace(".csv", "")[-10:] for f in files}
        d, missing = newest + timedelta(days=1), 0
        while d < today:
            if d.weekday() < 5 and d.isoformat() not in have:
                missing += 1
            d += timedelta(days=1)
        if missing >= MAX_MISSING_WEEKDAYS:
            stale.append(f"{sym} archive ends {newest} ({missing} weekdays behind)")
            lines.append(f"  ARCHIVE STALE  {sym}: newest {newest}, {missing} weekdays missing")
        else:
            lines.append(f"  archive ok     {sym}: newest {newest}")
    return lines, stale


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else str(date.today())
    weekday = date.fromisoformat(day).weekday()
    if weekday >= 5:
        print(f"{day} is a weekend - futures closed, nothing expected to evaluate. OK.")
        return

    arch_lines, arch_stale = check_archives(day)
    print(f"=== Data archive freshness for {day} ===")
    for line in arch_lines:
        print(line)
    if arch_stale:
        amsg = "Research data archive is behind: " + "; ".join(arch_stale) + ". Check data/databentorefresh_log.txt."
        print("ARCHIVE GAP: " + amsg)
        notify("NQ Research - data archive stale", amsg)
    print()

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
