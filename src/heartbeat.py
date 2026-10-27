"""
Heartbeat: one check that EVERY scheduled nq-research launchd job actually ran and exited cleanly.
Why: the Databento refresh failed silently for 3.5 weeks (Entries 76/77) because each job only checked itself.

For each com.nqresearch.* plist in ~/Library/LaunchAgents (falls back to ./launchd if that folder has none) it reads
`launchctl print gui/<uid>/<label>` and checks:
  1. the job is loaded at all
  2. last exit code is 0 (or the job has never run yet)
  3. if a scheduled slot (+15 min grace) fell between the previous snapshot and now, its run counter increased
     (so a job asleep through its slot is caught; launchd runs missed slots on wake, which counts)
  4. its stderr file got no new Traceback/Error text since the last snapshot (plain warnings are ignored)
Problems raise ONE Mac notification and are written to results/heartbeat.json. State lives in data/heartbeat_state.json.
Read-only with respect to trading: touches no account, strategy or live file.
Scheduled by launchd/com.nqresearch.heartbeat.plist at 6:10 PM PT (after the 5:50 PM shadow ledger).
Run by hand: python3 src/heartbeat.py
Limitation: nothing watches the heartbeat itself; src/status.py shows how old its last result is.
"""
import glob
import json
import os
import plistlib
import re
import subprocess
import sys
from datetime import datetime, timedelta

STATE = "data/heartbeat_state.json"
OUT = "results/heartbeat.json"
GRACE_MIN = 15
SELF_LABEL = "com.nqresearch.heartbeat"


def plist_files():
    home = os.path.expanduser("~/Library/LaunchAgents")
    files = sorted(glob.glob(os.path.join(home, "com.nqresearch.*.plist")))
    return files or sorted(glob.glob("launchd/com.nqresearch.*.plist"))


def read_plist(path):
    with open(path, "rb") as f:
        return plistlib.load(f)


def scheduled_slots(p):
    """List of (hour, minute, weekday_or_None) from StartCalendarInterval; [] for non-calendar jobs."""
    sci = p.get("StartCalendarInterval")
    if sci is None:
        return []
    items = sci if isinstance(sci, list) else [sci]
    return [(d.get("Hour"), d.get("Minute", 0), d.get("Weekday")) for d in items]


def due_today(slots, now, since=None):
    """True if a scheduled slot fell inside (since, now - grace]: i.e. a run was owed since the last snapshot.
    since=None (no earlier snapshot time known) -> False, so nothing is flagged without evidence."""
    if since is None:
        return False
    cutoff = now - timedelta(minutes=GRACE_MIN)
    for hour, minute, weekday in slots:
        if hour is None:
            continue
        for back in range(0, 9):
            day = (now - timedelta(days=back)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            if day > cutoff:
                continue
            wd = (day.weekday() + 1) % 7   # launchd: 0/7 = Sunday, 1 = Monday ... 6 = Saturday
            if weekday is not None and weekday % 7 != wd:
                continue
            if day > since:
                return True
            break   # most recent eligible occurrence is not after the snapshot
    return False


ERR_PATTERN = re.compile(r"Traceback|\bError\b|Exception|\bFATAL\b|\bCRITICAL\b")


def new_error_text(path, offset):
    """Text appended to the error file since byte `offset` (bytes past EOF reset to 0 if the file was truncated)."""
    try:
        with open(path, "rb") as f:
            f.seek(offset if offset <= os.path.getsize(path) else 0)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def launchctl_print(label):
    r = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True, text=True)
    return r.returncode, r.stdout


def parse_print(text):
    runs = re.search(r"\bruns = (\d+)", text)
    code = re.search(r"last exit code = (-?\d+|\(never exited\))", text)
    return {"runs": int(runs.group(1)) if runs else None,
            "last_exit": (None if (not code or "never" in code.group(1)) else int(code.group(1)))}


def file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def check(now=None, print_fn=launchctl_print, plists=None, state=None):
    """Returns (problems, new_state, report). Pure apart from print_fn and file sizes."""
    now = now or datetime.now()
    plists = plists if plists is not None else plist_files()
    state = state or {}
    new_state, problems, report = {}, [], {}
    for path in plists:
        p = read_plist(path)
        label = p["Label"]
        if label == SELF_LABEL:
            continue
        rc, text = print_fn(label)
        err_path = p.get("StandardErrorPath")
        size = file_size(err_path) if err_path else 0
        prev = state.get(label, {})
        prev_at = datetime.fromisoformat(prev["at"]) if prev.get("at") else None
        info = {"loaded": rc == 0}
        if rc != 0:
            problems.append(f"{label}: not loaded in launchd")
            report[label] = info
            new_state[label] = {"runs": prev.get("runs"), "err_size": size, "at": now.isoformat(timespec="seconds")}
            continue
        parsed = parse_print(text)
        info.update(parsed)
        runs = parsed["runs"]
        if parsed["last_exit"] not in (None, 0):
            problems.append(f"{label}: last exit code {parsed['last_exit']}")
        if (runs is not None and prev.get("runs") is not None and due_today(scheduled_slots(p), now, prev_at)
                and runs <= prev["runs"]):
            problems.append(f"{label}: scheduled today but did not run (runs still {runs})")
        if err_path and prev.get("err_size") is not None and size != prev["err_size"]:
            added = new_error_text(err_path, prev["err_size"])
            if ERR_PATTERN.search(added):
                problems.append(f"{label}: error file has new Traceback/Error text ({size - prev['err_size']} bytes)")
        new_state[label] = {"runs": runs, "err_size": size, "at": now.isoformat(timespec="seconds")}
        report[label] = info
    return problems, new_state, report


def notify(msg):
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "nq-research heartbeat"'], capture_output=True)
    except Exception:
        pass


def main():
    now = datetime.now()
    state = {}
    if os.path.exists(STATE):
        with open(STATE) as f:
            state = json.load(f)
    problems, new_state, report = check(now, state=state)
    os.makedirs("results", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"checked_at": now.isoformat(timespec="seconds"), "ok": not problems,
                   "problems": problems, "jobs": report}, f, indent=2)
    with open(STATE + ".tmp", "w") as f:
        json.dump(new_state, f, indent=2)
    os.replace(STATE + ".tmp", STATE)
    first = not state
    print(f"{now:%Y-%m-%d %H:%M} heartbeat: {len(report)} jobs checked, "
          f"{'ALL OK' if not problems else str(len(problems)) + ' PROBLEM(S)'}"
          f"{' (first run: baseline recorded, run-counter checks start tomorrow)' if first else ''}")
    for pr in problems:
        print("   PROBLEM:", pr)
    if problems:
        notify(f"{len(problems)} job problem(s): " + "; ".join(problems)[:200].replace('"', "'"))
        sys.exit(1)


if __name__ == "__main__":
    main()
