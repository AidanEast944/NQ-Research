"""
Cost check ONLY - does not download or write any data. Prints the exact dollar cost (via
Databento's own Historical.metadata.get_cost()) to catch each extended archive up to today,
so you can see the real number before anything is pulled. Run this manually:

    cd ~/nq-research && source venv/bin/activate
    python3 src/research/check_databento_refresh_cost.py

Reads your API key from a DATABENTO_API_KEY environment variable, or from a .env file in the
repo root (already covered by .gitignore's .env / .env.* patterns - never commit it).

2026-09-11 update: the first run hit a 422 dataset_unavailable_range error on every symbol -
"requires a subscription and/or license... try again with an end time before <right now>".
That's a licensing boundary on how RECENT your GLBX.MDP3 access goes (common - CME often prices
real-time/near-real-time access separately from delayed/historical-only access), not a bug in
this script. This version probes several end-date candidates per symbol (today, yesterday, a
week ago, a month ago) to find exactly where that boundary sits, instead of guessing once and
failing silently.

2026-09-11 bugfix (research_log.md Entry 37): switched from bare date.isoformat() strings to
proper Eastern-timezone-aware timestamps for start/end - bare date strings are parsed as UTC
midnight by the API, not Eastern midnight, which skewed these estimates by the UTC/Eastern
offset (this script never writes files, so it never caused data damage - see
refresh_databento_archive.py's docstring for where that same bug DID cause damage).
"""
import os
import glob
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")


def eastern_midnight_iso(d):
    """Midnight in America/New_York for calendar date d, as a proper offset-aware ISO8601
    string - see refresh_databento_archive.py's docstring for why this matters."""
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
    print("The 'databento' package isn't installed in this environment yet. Run:")
    print("    pip install databento")
    raise SystemExit(1)

if not os.environ.get("DATABENTO_API_KEY"):
    print("No DATABENTO_API_KEY found - set it in .env or as an environment variable.")
    raise SystemExit(1)

client = db.Historical()

SYMBOLS = {
    "NQ": ("NQ.c.0", "data/raw_nq_extended"),
    "ES": ("ES.c.0", "data/raw_es_extended"),
    "YM": ("YM.c.0", "data/raw_ym_extended"),
    "RTY": ("RTY.c.0", "data/raw_rty_extended"),
}

today = date.today()

# --- Step 1: find the access boundary using just NQ, so we don't burn time re-discovering it
#     for all 4 symbols separately (the boundary should be the same account-wide restriction). ---
print("=== Step 1: finding how recent your GLBX.MDP3 access actually goes (using NQ) ===\n")
probe_end_candidates = [
    ("today", today),
    ("yesterday", today - timedelta(days=1)),
    ("1 week ago", today - timedelta(days=7)),
    ("1 month ago", today - timedelta(days=30)),
    ("3 months ago", today - timedelta(days=90)),
]
probe_start = today - timedelta(days=120)  # far enough back to not matter here

access_boundary = None
for label, end_date in probe_end_candidates:
    try:
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3", symbols=["NQ.c.0"], schema="ohlcv-1m",
            start=eastern_midnight_iso(probe_start), end=eastern_midnight_iso(end_date + timedelta(days=1)),
            stype_in="continuous",
        )
        print(f"  end={label} ({end_date}): OK, cost for this test range = ${cost:.4f}")
        if access_boundary is None:
            access_boundary = end_date
    except Exception as e:
        msg = str(e).split("\n")[0]
        print(f"  end={label} ({end_date}): BLOCKED - {msg}")

if access_boundary is None:
    print("\nEvery probe failed, including 3 months back - this isn't just a recency limit.")
    print("Paste this full output back and we'll look at the account/subscription itself rather")
    print("than the date range.")
    raise SystemExit(1)

print(f"\nYour access currently reaches through roughly: {access_boundary}")
print("(the real boundary may be a bit more recent than this - these are just probe points,")
print("not a binary search - close enough to plan around)\n")

# --- Step 2: now get the real per-symbol catch-up cost using that boundary as the end date ---
print(f"=== Step 2: catch-up cost per archive, through {access_boundary} ===\n")
total = 0.0
for label, (dbn_symbol, folder) in SYMBOLS.items():
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not files:
        print(f"{label}: no existing archive found at {folder} - skipping.")
        continue

    last_file = os.path.basename(files[-1])
    last_date_str = last_file.replace(".csv", "")[-10:]
    last_date = date.fromisoformat(last_date_str)
    start = last_date + timedelta(days=1)

    if start > access_boundary:
        print(f"{label}: archive ({last_date}) is already as current as your access allows.")
        continue

    try:
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3", symbols=[dbn_symbol], schema="ohlcv-1m",
            start=eastern_midnight_iso(start), end=eastern_midnight_iso(access_boundary + timedelta(days=1)),
            stype_in="continuous",
        )
    except Exception as e:
        print(f"{label}: get_cost() failed - {e}")
        continue

    print(f"{label}: {last_date} -> {access_boundary} ({(access_boundary - last_date).days} days) = ${cost:.4f}")
    total += cost

print(f"\nTOTAL estimated cost to catch up ALL archives to {access_boundary}: ${total:.4f}")
