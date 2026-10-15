"""
Per-strategy daily "did this check actually evaluate a signal today?" heartbeat (research_log.md
Entry 61). Each live *_forward_check.py script calls start(key, label) near the top and
evaluated(key, detail) the moment it has genuinely evaluated its signal (candle found, volume
computed, z-score computed - whatever "I really looked at today's conditions" means for that
strategy). An atexit handler then records the outcome to data/coverage_log.json no matter how the
script exits - normal finish, sys.exit(), or an uncaught exception.

If evaluated() was never reached, the day is recorded as NOT_EVALUATED. That is the failure mode
behind Entries 57, 58 and 60: a script exiting quietly ("No 08:30 candle yet", Yahoo returned
nothing) so that nothing looked at the day, with nothing recording that it didn't. A later,
separate job (coverage_report.py) reads this file and flags gaps.

A rerun later the same day never downgrades an EVALUATED record to NOT_EVALUATED (e.g. a manual
rerun that hits an "already processed today" early exit).
"""
import atexit
import fcntl
import random
import time
import json
import os
from datetime import date, datetime

COVERAGE_FILE = "data/coverage_log.json"
KEEP_DAYS = 60
_pending = {}


def _load():
    if not os.path.exists(COVERAGE_FILE):
        return {}
    try:
        with open(COVERAGE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    # Per-process temp name: a shared ".tmp" let one writer's os.replace consume another writer's
    # temp file (Entry 66: ENOENT on replace, seen on 2026-10-15 even with the Entry 65 lock).
    tmp = f"{COVERAGE_FILE}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, COVERAGE_FILE)


def start(key, label):
    _pending[key] = {
        "label": label,
        "status": "NOT_EVALUATED",
        "detail": "exited before a signal could be evaluated (no data/candle yet, error, or early exit)",
    }
    atexit.register(_flush, key)


def evaluated(key, detail=""):
    if key in _pending:
        _pending[key]["status"] = "EVALUATED"
        _pending[key]["detail"] = detail


def _flush(key):
    rec = _pending.get(key)
    if rec is None:
        return
    last_error = None
    # Lock, write, then re-read to confirm our own record is really there; retry a few times with a
    # small random pause if it is not. Belt and braces: does not depend on flock being honoured.
    for attempt in range(5):
        try:
            with open(COVERAGE_FILE + ".lock", "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                today = str(date.today())
                data = _load()
                day = data.setdefault(today, {})
                existing = day.get(key)
                if existing and existing.get("status") == "EVALUATED" and rec["status"] != "EVALUATED":
                    return
                day[key] = {**rec, "recorded_at": datetime.now().isoformat(timespec="seconds")}
                for old_day in sorted(data)[:-KEEP_DAYS]:
                    del data[old_day]
                _save(data)
                saved = _load().get(today, {}).get(key)
                if saved and saved.get("status") == rec["status"]:
                    return
                last_error = "record not present after write"
        except Exception as e:
            last_error = e
        time.sleep(random.uniform(0.1, 0.6))
    print(f"(coverage log write failed after retries, non-fatal: {last_error})")
