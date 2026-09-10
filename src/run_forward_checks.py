"""
Runs both live forward-test scripts (the unfiltered gap strategy and the volume-confirmed
parallel track) back-to-back, for use by a scheduled launchd job - see launchd/README.md for
setup and launchd/com.nq-research.forward-check.plist for the schedule itself.

Everything here runs locally: this script, both strategy scripts, and launchd itself all execute
entirely on this machine using this machine's own network connection. Nothing about account
balances, trades, or strategy logic is sent anywhere as part of running this.

Safe to run unattended and safe to run more than once on the same day - both underlying scripts
skip an already-processed day rather than duplicating a trade record (fixed 2026-09-10, Entry 29).

Fires a macOS desktop notification (via `osascript`, best-effort - a notification failure never
breaks the run) only on a line indicating a trade actually opened or closed, so a quiet no-signal
day stays quiet and a real trade day gets your attention without checking the log file.
"""
import subprocess
import sys
import os
from datetime import datetime

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
# The underlying scripts use relative paths like "data/risk_limits_state.json" that are meant to
# resolve from the REPO ROOT (nq-research/), not from inside src/ - matching how they've always
# been run by hand (`python3 src/gap_forward_check.py` from the repo root). Bug found 2026-09-10:
# this used to pass cwd=SRC_DIR, which made every "data/..." path resolve to a nonexistent
# src/data/... and crash inside risk_limits.py's save_risk_state() before place_order() was ever
# reached - no trade data was corrupted (it crashed too early for that), it just never ran.
REPO_ROOT = os.path.dirname(SRC_DIR)
SCRIPTS = ["gap_forward_check.py", "volume_confirmed_gap_forward_check.py"]


def notify(title, message):
    """Best-effort macOS notification - failures here are printed but never raised."""
    try:
        safe_message = message.replace('"', '\\"').replace("\\", "\\\\")
        safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
            timeout=10, check=False
        )
    except Exception as e:
        print(f"(notification failed, non-fatal: {e})")


def run_script(script_name):
    print(f"\n{'=' * 70}\n{datetime.now().isoformat()} - running {script_name}\n{'=' * 70}")
    # cwd=REPO_ROOT (not SRC_DIR) so the child script's relative "data/..." paths resolve
    # correctly, matching how these scripts are meant to be run - see the note above.
    result = subprocess.run(
        [sys.executable, os.path.join("src", script_name)],
        cwd=REPO_ROOT,
        capture_output=True, text=True
    )
    output = (result.stdout or "") + (result.stderr or "")
    print(output)

    if result.returncode != 0:
        print(f"WARNING: {script_name} exited with code {result.returncode}")
        notify("NQ Research - Error", f"{script_name} exited with code {result.returncode} - check the log")
        return

    trade_lines = [line.strip() for line in output.splitlines() if "[PAPER TRADE]" in line]
    if trade_lines:
        summary = " | ".join(trade_lines)
        notify(f"NQ Research - {script_name}", summary[:250])


if __name__ == "__main__":
    for script in SCRIPTS:
        run_script(script)
    print(f"\n{'=' * 70}\n{datetime.now().isoformat()} - done\n{'=' * 70}")
