"""
One-off repair script: re-pulls ONLY 2026-09-09 (full Eastern calendar day) for NQ/ES/YM/RTY to
replace the truncated versions left by the 2026-09-11 timezone bug (research_log.md Entry 37).
Uses the same eastern_midnight_iso() fix and resample_and_save() shrink-guard as the main
refresh_databento_archive.py, so this can only GROW those 4 files, never shrink them further.

Cost confirmed via check_909_repair_cost.py: $0.0198 total (NQ $0.0050, ES $0.0050, YM $0.0049,
RTY $0.0049) - trivial, well under the $1.00 per-run safety cap used elsewhere in this project.

Run manually:
    cd ~/nq-research && source venv/bin/activate
    python3 src/research/repair_909_archive.py
"""
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")


def eastern_midnight_iso(d):
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

REPAIR_DATE = date(2026, 9, 9)
SYMBOLS = {
    "NQ": ("NQ.c.0", "data/raw_nq_extended", "nq_15m"),
    "ES": ("ES.c.0", "data/raw_es_extended", "es_15m"),
    "YM": ("YM.c.0", "data/raw_ym_extended", "ym_15m"),
    "RTY": ("RTY.c.0", "data/raw_rty_extended", "rty_15m"),
}

start_iso = eastern_midnight_iso(REPAIR_DATE)
end_iso = eastern_midnight_iso(date(2026, 9, 10))  # exclusive end = midnight of the next day


def resample_and_save_one_day(raw_df, folder, prefix, target_date):
    df = raw_df[["open", "high", "low", "close", "volume"]].copy()
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    df.index = df.index.tz_convert("America/New_York")

    resampled = df.resample("15min").agg({
        "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
    })
    resampled = resampled.dropna(subset=["Open"])
    resampled["date"] = resampled.index.date
    resampled = resampled[resampled["date"] == target_date]  # only the one day we're repairing

    filename = f"{folder}/{prefix}_{target_date}.csv"
    group_to_save = resampled.drop(columns=["date"])

    existing_rows = 0
    if os.path.exists(filename):
        with open(filename) as f:
            existing_rows = sum(1 for _ in f) - 1  # minus header

    if len(group_to_save) < existing_rows:
        print(f"    SKIPPING {filename}: new pull has {len(group_to_save)} row(s), existing "
              f"file already has {existing_rows} - refusing to shrink-overwrite. Investigate.")
        return None

    group_to_save.index.name = "Datetime"
    group_to_save.to_csv(filename)
    return len(group_to_save), existing_rows


print(f"Repairing {REPAIR_DATE} only, all 4 symbols.\n")
for label, (dbn_symbol, folder, prefix) in SYMBOLS.items():
    print(f"Pulling {label}...")
    try:
        store = client.timeseries.get_range(
            dataset="GLBX.MDP3", symbols=[dbn_symbol], schema="ohlcv-1m",
            start=start_iso, end=end_iso, stype_in="continuous",
        )
        raw_df = store.to_df()
    except Exception as e:
        print(f"  FAILED to pull {label}: {e}")
        continue

    if raw_df.empty:
        print(f"  No data returned for {label} - nothing to save.")
        continue

    result = resample_and_save_one_day(raw_df, folder, prefix, REPAIR_DATE)
    if result is not None:
        new_rows, old_rows = result
        print(f"  Saved {new_rows} row(s) to {folder}/{prefix}_{REPAIR_DATE}.csv "
              f"(was {old_rows} row(s) before this repair)")

print("\nDone.")
