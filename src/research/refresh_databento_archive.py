"""
Pulls NEW 1-minute OHLCV bars from Databento (GLBX.MDP3) since each extended archive's last saved
day, resamples to 15-minute bars (matching this project's existing archive format exactly), and
appends one CSV per day - a drop-in continuation of data/raw_{nq,es,ym,rty}_extended, which
already back the flagship Volume-Confirmed Gap strategy, the pairs book, overnight drift, and
day-of-week research (research_log.md Entry 36).

Deliberately does NOT touch the live trading pipeline (gap/vol-confirmed/pairs scripts still use
yfinance for same-day intraday checks) - this only keeps the deeper research archives current.

Prints the exact dollar cost via get_cost() before every pull, and refuses to spend more than
MAX_COST_PER_RUN_USD in a single run - a circuit breaker against a bug (e.g. a corrupted "last
archived date") silently trying to re-pull years of history, same pattern as risk_limits.py's
circuit breaker elsewhere in this project. This is meant to run unattended once installed
(no interactive confirmation - a scheduled job can't answer a prompt), so this cap is the actual
safety net, not a human in the loop each time.

Your account's access has roughly a 1-day delay (confirmed 2026-09-11 via
check_databento_refresh_cost.py - "today" is blocked, "yesterday" works) - this always targets
END_DATE = yesterday, never today, so it doesn't need to guess at that boundary each run.

2026-09-11 BUGFIX (research_log.md Entry 37): the first real run passed bare date.isoformat()
strings (e.g. "2026-09-02") as start/end to Databento's API. Those are parsed as UTC midnight,
not Eastern midnight, and since Eastern is UTC-4 right now, the requested range silently bled
~4 hours into the adjacent Eastern calendar day at BOTH ends. At the start boundary this re-pulled
a sliver of the day *before* the intended start (which was already fully archived), and because
resample_and_save() had no guard, it overwrote 4 already-complete archive files with truncated
~4-hour slices. At the end boundary it truncated the final day of the run (missing the last
~4 hours, 20:00-23:45 ET). Fixed two ways, belt-and-suspenders:
  1. start/end are now built as real Eastern-timezone-aware timestamps (eastern_midnight_iso),
     not bare date strings, so the API gets the correct UTC-equivalent boundary.
  2. resample_and_save() now (a) drops any row outside the intended [start_date, end_date]
     Eastern-calendar range before saving, and (b) refuses to overwrite an existing file with
     one that has fewer rows - so even a future boundary bug can shrink-overwrite a good file.

Run manually first, before scheduling:
    cd ~/nq-research && source venv/bin/activate
    python3 src/research/refresh_databento_archive.py
"""
import os
import sys
import glob
import pandas as pd
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MAX_COST_PER_RUN_USD = 1.00  # circuit breaker - refuses to spend more than this in one run

EASTERN = ZoneInfo("America/New_York")


def eastern_midnight_iso(d):
    """Midnight in America/New_York for calendar date d, as a proper offset-aware ISO8601
    string (e.g. "2026-08-31T00:00:00-04:00"). This is what must be passed to Databento's
    start/end - a bare date.isoformat() string gets parsed as UTC midnight instead, which is
    ~4-5 hours off from Eastern midnight and was the root cause of the 2026-09-11 corruption
    bug (research_log.md Entry 37)."""
    return datetime(d.year, d.month, d.day, tzinfo=EASTERN).isoformat()


def load_dotenv_manually(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv_manually()

try:
    import databento as db
except ImportError:
    print("The 'databento' package isn't installed. Run: pip install databento")
    sys.exit(1)

if not os.environ.get("DATABENTO_API_KEY"):
    print("No DATABENTO_API_KEY found (.env or environment). Nothing pulled.")
    sys.exit(1)

client = db.Historical()

# label -> (Databento continuous-contract symbol, extended-archive folder, output filename prefix)
SYMBOLS = {
    "NQ": ("NQ.c.0", "data/raw_nq_extended", "nq_15m"),
    "ES": ("ES.c.0", "data/raw_es_extended", "es_15m"),
    "YM": ("YM.c.0", "data/raw_ym_extended", "ym_15m"),
    "RTY": ("RTY.c.0", "data/raw_rty_extended", "rty_15m"),
}

END_DATE = date.today() - timedelta(days=1)  # "yesterday" - see docstring on the access delay


def last_archived_date(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not files:
        return None
    last_file = os.path.basename(files[-1])
    return date.fromisoformat(last_file.replace(".csv", "")[-10:])


def resample_and_save(raw_df, folder, prefix, start_date, end_date):
    """Same transform as the original one-off src/research/convert_databento_*.py scripts -
    kept identical so downstream code (strategy.py's *_from_archive() functions) sees no
    difference between data pulled by hand originally and data appended by this script.

    start_date/end_date (inclusive, Eastern calendar dates) are the intended range - any row
    outside that range is dropped before saving, and any file that would be overwritten with
    FEWER rows than it already has is skipped instead. Both are defensive guards against a
    repeat of the 2026-09-11 boundary-corruption bug, independent of whether the API call
    itself was bounded correctly."""
    df = raw_df[["open", "high", "low", "close", "volume"]].copy()
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    df.index = df.index.tz_convert("America/New_York")

    resampled = df.resample("15min").agg({
        "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
    })
    resampled = resampled.dropna(subset=["Open"])
    resampled["date"] = resampled.index.date

    before = len(resampled)
    resampled = resampled[(resampled["date"] >= start_date) & (resampled["date"] <= end_date)]
    dropped = before - len(resampled)
    if dropped:
        print(f"    (dropped {dropped} row(s) outside the intended {start_date} -> {end_date} "
              f"range - API returned a slightly wider window than requested)")

    os.makedirs(folder, exist_ok=True)
    saved = []
    for day, group in resampled.groupby("date"):
        filename = f"{folder}/{prefix}_{day}.csv"
        group_to_save = group.drop(columns=["date"])

        if os.path.exists(filename):
            with open(filename) as f:
                existing_rows = sum(1 for _ in f) - 1  # minus header
            if len(group_to_save) < existing_rows:
                print(f"    SKIPPING {filename}: new pull has {len(group_to_save)} row(s), "
                      f"existing file already has {existing_rows} - refusing to shrink-overwrite. "
                      f"Investigate before forcing this.")
                continue

        group_to_save.index.name = "Datetime"
        group_to_save.to_csv(filename)
        saved.append(str(day))
    return saved


# --- Step 1: figure out what each symbol needs, and the total cost across all of them ---
plan = []
total_cost = 0.0
for label, (dbn_symbol, folder, prefix) in SYMBOLS.items():
    last_date = last_archived_date(folder)
    if last_date is None:
        print(f"{label}: no existing archive at {folder} - skipping (this script only extends "
              f"an existing archive, it doesn't bootstrap a new one from scratch).")
        continue

    start = last_date + timedelta(days=1)
    if start > END_DATE:
        print(f"{label}: already current through {last_date}. Nothing to do.")
        continue

    try:
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3", symbols=[dbn_symbol], schema="ohlcv-1m",
            start=eastern_midnight_iso(start), end=eastern_midnight_iso(END_DATE + timedelta(days=1)),
            stype_in="continuous",
        )
    except Exception as e:
        print(f"{label}: get_cost() failed - {e} - skipping this symbol this run.")
        continue

    plan.append({"label": label, "dbn_symbol": dbn_symbol, "folder": folder, "prefix": prefix,
                 "start": start, "cost": cost})
    total_cost += cost

if not plan:
    print("Nothing to refresh - every archive is already current through your access boundary.")
    sys.exit()

print(f"Plan: {len(plan)} symbol(s) to refresh, total cost ${total_cost:.4f}")
for p in plan:
    print(f"  {p['label']}: {p['start']} -> {END_DATE}, ${p['cost']:.4f}")

if total_cost > MAX_COST_PER_RUN_USD:
    print(f"\nREFUSING TO PROCEED: total cost ${total_cost:.4f} exceeds the "
          f"${MAX_COST_PER_RUN_USD:.2f} per-run safety cap. This almost always means something "
          f"is wrong (e.g. an archive's last-date detection broke and this is trying to re-pull "
          f"a huge range) rather than a genuinely large legitimate catch-up. Nothing was pulled. "
          f"Investigate before raising MAX_COST_PER_RUN_USD.")
    sys.exit(1)

# --- Step 2: actually pull and save ---
print(f"\nProceeding - total cost ${total_cost:.4f} is under the ${MAX_COST_PER_RUN_USD:.2f} cap.\n")
for p in plan:
    print(f"Pulling {p['label']} ({p['start']} -> {END_DATE})...")
    try:
        store = client.timeseries.get_range(
            dataset="GLBX.MDP3", symbols=[p["dbn_symbol"]], schema="ohlcv-1m",
            start=eastern_midnight_iso(p["start"]), end=eastern_midnight_iso(END_DATE + timedelta(days=1)),
            stype_in="continuous",
        )
        raw_df = store.to_df()
    except Exception as e:
        print(f"  FAILED to pull {p['label']}: {e}")
        continue

    if raw_df.empty:
        print(f"  No data returned for {p['label']} in this range (e.g. a holiday-only gap) - nothing to save.")
        continue

    saved_days = resample_and_save(raw_df, p["folder"], p["prefix"], p["start"], END_DATE)
    if saved_days:
        print(f"  Saved {len(saved_days)} day(s) to {p['folder']}: {saved_days[0]} -> {saved_days[-1]}")
    else:
        print(f"  Nothing saved for {p['label']} this run (all candidate days were skipped - see above).")

print(f"\nDone. Total spent this run: ${total_cost:.4f}")
