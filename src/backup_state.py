"""
Nightly backup of everything that cannot be recreated from git or re-downloaded cheaply.
  DAILY  state_YYYY-MM-DD.tar.gz : data/*.json, data/*.csv, data/*.txt (paper accounts, forward logs, coverage log, job logs),
                                   registry/, results/, lab/, research_log.md, and the launchd plists in ~/Library/LaunchAgents
  WEEKLY (Sundays) archives_YYYY-MM-DD.tar.gz : data/raw_*_extended and data/raw (the paid Databento / Yahoo bar archives)
Never includes .env or any credential, and never touches git or a trading file (read-only copy).
Destination: iCloud Drive folder if it exists (~/Library/Mobile Documents/com~apple~CloudDocs/nq-research-backups),
otherwise ~/Backups/nq-research. Override with --dest. Keeps the newest 14 daily and 4 weekly files.
Each archive is re-opened after writing to check it is readable; a failure raises a Mac notification and exit code 1.
Run: python3 src/backup_state.py [--dest DIR] [--force-weekly]      Scheduled: launchd/com.nqresearch.backup.plist 5:55 PM PT
"""
import argparse
import glob
import os
import subprocess
import sys
import tarfile
from datetime import date

KEEP_DAILY, KEEP_WEEKLY = 14, 4
DAILY_PATTERNS = ["data/*.json", "data/*.csv", "data/*.txt", "data/*.bak*"]
DAILY_DIRS = ["registry", "results", "lab", "launchd"]
DAILY_FILES = ["research_log.md"]
WEEKLY_DIRS_GLOB = ["data/raw_*_extended", "data/raw"]
EXCLUDE_NAMES = {".env", ".DS_Store"}


def default_dest():
    icloud = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
    if os.path.isdir(icloud):
        return os.path.join(icloud, "nq-research-backups")
    return os.path.expanduser("~/Backups/nq-research")


def _filter(ti):
    base = os.path.basename(ti.name)
    if base in EXCLUDE_NAMES or base.startswith(".env") or base.endswith((".key", ".pem")):
        return None
    return ti


def make_archive(path, members, extra=()):
    with tarfile.open(path, "w:gz") as tar:
        for m in members:
            if os.path.exists(m):
                tar.add(m, filter=_filter)
        for src, arc in extra:
            if os.path.exists(src):
                tar.add(src, arcname=arc, filter=_filter)
    with tarfile.open(path, "r:gz") as tar:   # verify it reads back
        n = len(tar.getnames())
    if n == 0:
        raise RuntimeError(f"{path} is empty")
    return n


def prune(dest, prefix, keep):
    files = sorted(glob.glob(os.path.join(dest, prefix + "_*.tar.gz")))
    for old in files[:-keep]:
        os.remove(old)


def run(dest, today=None, force_weekly=False):
    today = today or date.today()
    os.makedirs(dest, exist_ok=True)
    results = []
    members = []
    for pat in DAILY_PATTERNS:
        members += glob.glob(pat)
    members += [d for d in DAILY_DIRS] + DAILY_FILES
    la = os.path.expanduser("~/Library/LaunchAgents")
    extra = [(p, "LaunchAgents/" + os.path.basename(p)) for p in glob.glob(os.path.join(la, "com.nqresearch.*.plist"))]
    daily = os.path.join(dest, f"state_{today}.tar.gz")
    results.append((daily, make_archive(daily, members, extra)))
    prune(dest, "state", KEEP_DAILY)
    if today.weekday() == 6 or force_weekly:   # Sunday
        dirs = []
        for g in WEEKLY_DIRS_GLOB:
            dirs += glob.glob(g)
        weekly = os.path.join(dest, f"archives_{today}.tar.gz")
        results.append((weekly, make_archive(weekly, dirs)))
        prune(dest, "archives", KEEP_WEEKLY)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=default_dest())
    ap.add_argument("--force-weekly", action="store_true")
    a = ap.parse_args()
    try:
        for path, n in run(a.dest, force_weekly=a.force_weekly):
            print(f"backup ok: {path} ({n} entries, {os.path.getsize(path)/1e6:.1f} MB)")
    except Exception as e:
        print("BACKUP FAILED:", e)
        subprocess.run(["osascript", "-e", 'display notification "backup failed" with title "nq-research"'], capture_output=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
