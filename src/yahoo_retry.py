"""
Retry + alert helper for the evening resolve jobs (research_log.md Entry 76).

On 2026-10-22 the 5:05 PM gap resolve got an empty reply from Yahoo ("possibly delisted; no price data
found" - a transient outage), printed "Skipping this run" and quietly left a paper trade open. These helpers
make the resolve scripts retry and, if Yahoo still returns nothing, tell the user so a stranded trade is seen
the same evening instead of the next day.

fetch_history(): tries up to `attempts` times, `sleep_seconds` apart (default 5 x 60s, finished well inside the
    5 minutes before the next scheduled job). Exceptions and empty frames both count as a failed attempt.
alert_unresolved(): a macOS notification. Only called when positions ARE open and no data could be fetched.
Nothing here changes an account or a trade.
"""
import subprocess
import sys
import time


def fetch_history(ticker, label, period="60d", interval="15m", attempts=5, sleep_seconds=60):
    for i in range(1, attempts + 1):
        try:
            history = ticker.history(period=period, interval=interval)
            if history is not None and not history.empty:
                if i > 1:
                    print(f"[{label}] Yahoo data returned on attempt {i}/{attempts}.")
                return history
            print(f"[{label}] Yahoo returned no data (attempt {i}/{attempts}).")
        except Exception as e:
            print(f"[{label}] Yahoo error on attempt {i}/{attempts}: {e}")
        if i < attempts:
            time.sleep(sleep_seconds)
    import pandas as pd
    return pd.DataFrame()  # empty: callers check history.empty and alert


def alert_unresolved(label):
    msg = f"{label}: could not fetch Yahoo data after retries - open paper position(s) NOT resolved tonight."
    print("ALERT: " + msg)
    if sys.platform == "darwin":
        try:
            safe = msg.replace('"', "'")
            subprocess.run(["osascript", "-e", f'display notification "{safe}" with title "Resolve job needs attention"'],
                           timeout=10, check=False)
        except Exception as e:
            print(f"(notification failed, non-fatal: {e})")
