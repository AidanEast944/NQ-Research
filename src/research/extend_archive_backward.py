"""
Extends the extended archives BACKWARD in time (before 2024-01-01) so the frozen gap rules can be
tested on history they have never seen (research_log.md plan after Entry 66).

TWO MODES - nothing is ever spent in the default mode:

  QUOTE (default): prints the exact get_cost() for each symbol and each candidate start year.
      cd ~/nq-research && source venv/bin/activate
      python3 src/research/extend_archive_backward.py

  PULL (explicit): requires --pull, a --start date, and --max-cost. It re-quotes, refuses if the
  quote is above --max-cost, then pulls one calendar year at a time and writes one CSV per
  Eastern day in exactly the same format as refresh_databento_archive.py. Existing files are never
  shrunk or overwritten with fewer rows. Safe to re-run: years already on disk are skipped and not re-bought.
      python3 src/research/extend_archive_backward.py --pull --start 2018-01-01 --max-cost 5.00 --symbols NQ,ES,YM

END of the new range is the day before each folder's earliest archived file, so it joins the
existing archive with no gap or overlap. Timestamps are Eastern-aware (Entry 37 fix).
"""
import os
import sys
import glob
import argparse
import pandas as pd
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
SYMBOLS = {
    "NQ": ("NQ.c.0", "data/raw_nq_extended", "nq_15m"),
    "ES": ("ES.c.0", "data/raw_es_extended", "es_15m"),
    "YM": ("YM.c.0", "data/raw_ym_extended", "ym_15m"),
}
QUOTE_STARTS = [date(2015, 1, 1), date(2018, 1, 1), date(2020, 1, 1), date(2022, 1, 1)]


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


def first_archived_date(folder):
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not files:
        return None
    return date.fromisoformat(os.path.basename(files[0]).replace(".csv", "")[-10:])


def resample_and_save(raw_df, folder, prefix, start_date, end_date):
    df = raw_df[["open", "high", "low", "close", "volume"]].copy()
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    df.index = df.index.tz_convert("America/New_York")
    r = df.resample("15min").agg({"Open": "first", "High": "max", "Low": "min",
                                  "Close": "last", "Volume": "sum"})
    r = r.dropna(subset=["Open"])
    r["date"] = r.index.date
    r = r[(r["date"] >= start_date) & (r["date"] <= end_date)]
    os.makedirs(folder, exist_ok=True)
    saved = 0
    for day, g in r.groupby("date"):
        fn = f"{folder}/{prefix}_{day}.csv"
        g = g.drop(columns=["date"])
        if os.path.exists(fn):
            with open(fn) as f:
                existing = sum(1 for _ in f) - 1
            if len(g) < existing:
                print(f"    SKIPPING {fn}: new {len(g)} rows < existing {existing}")
                continue
        g.index.name = "Datetime"
        g.to_csv(fn)
        saved += 1
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--start", type=str, default=None)
    ap.add_argument("--max-cost", type=float, default=None)
    ap.add_argument("--symbols", type=str, default="NQ,ES,YM")
    args = ap.parse_args()

    load_dotenv_manually()
    if not os.environ.get("DATABENTO_API_KEY"):
        print("No DATABENTO_API_KEY found (.env or environment). Nothing done.")
        sys.exit(1)
    try:
        import databento as db
    except ImportError:
        print("Run: pip install databento")
        sys.exit(1)
    client = db.Historical()
    labels = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    def quote(sym, start, end_excl):
        dbn, _, _ = SYMBOLS[sym]
        return client.metadata.get_cost(
            dataset="GLBX.MDP3", symbols=[dbn], schema="ohlcv-1m",
            start=eastern_midnight_iso(start), end=eastern_midnight_iso(end_excl),
            stype_in="continuous")

    ends = {}
    for s in labels:
        first = first_archived_date(SYMBOLS[s][1])
        if first is None:
            print(f"{s}: no existing archive folder, skipping.")
            continue
        ends[s] = date(2024, 1, 1)  # fixed exclusive end: the original archive starts 2024-01-01

    if not args.pull:
        print("QUOTE ONLY - nothing is being pulled or spent.\n")
        print(f"{'start':<12}" + "".join(f"{s:>12}" for s in ends) + f"{'TOTAL':>12}")
        for st in QUOTE_STARTS:
            row, tot = [], 0.0
            for s, end in ends.items():
                try:
                    c = quote(s, st, end)
                except Exception as e:
                    print(f"{s} {st}: quote failed - {e}")
                    c = float("nan")
                row.append(c)
                tot += 0 if c != c else c
            print(f"{str(st):<12}" + "".join(f"{c:>12.4f}" for c in row) + f"{tot:>12.4f}")
        print("\nPaste this table back. To pull, rerun with --pull --start YYYY-MM-DD --max-cost N")
        return

    if not args.start or args.max_cost is None:
        print("--pull requires both --start YYYY-MM-DD and --max-cost.")
        sys.exit(1)
    start = date.fromisoformat(args.start)
    import time

    def year_done(folder, prefix, y):
        # a year is complete if it already has >= 300 day files (a full year is ~310)
        return len(glob.glob(f"{folder}/{prefix}_{y}-*.csv")) >= 300

    chunks = []  # (symbol, seg_start, seg_end_excl, quote)
    total = 0.0
    for s, end in ends.items():
        dbn, folder, prefix = SYMBOLS[s]
        for y in range(start.year, end.year + 1):
            seg_start = max(start, date(y, 1, 1))
            seg_end_excl = min(end, date(y + 1, 1, 1))
            if seg_start >= seg_end_excl:
                continue
            if year_done(folder, prefix, y):
                print(f"{s} {y}: already on disk, skipping (no charge)")
                continue
            c = quote(s, seg_start, seg_end_excl)
            chunks.append((s, seg_start, seg_end_excl, c))
            total += c
            print(f"{s} {y}: needs pull, quote ${c:.4f}")
    print(f"TOTAL quote for MISSING chunks only: ${total:.4f}  (limit ${args.max_cost:.2f})")
    if total > args.max_cost:
        print("REFUSING: quote exceeds --max-cost. Nothing pulled.")
        sys.exit(1)

    for s, seg_start, seg_end_excl, c in chunks:
        dbn, folder, prefix = SYMBOLS[s]
        ok = False
        for attempt in range(1, 4):
            print(f"Pulling {s} {seg_start.year} (attempt {attempt}/3) ...")
            try:
                store = client.timeseries.get_range(
                    dataset="GLBX.MDP3", symbols=[dbn], schema="ohlcv-1m",
                    start=eastern_midnight_iso(seg_start), end=eastern_midnight_iso(seg_end_excl),
                    stype_in="continuous")
                raw = store.to_df()
            except Exception as e:
                print(f"  FAILED: {e}")
                time.sleep(15 * attempt)
                continue
            if raw.empty:
                print("  no data returned")
            else:
                n = resample_and_save(raw, folder, prefix, seg_start, seg_end_excl - timedelta(days=1))
                print(f"  saved {n} day file(s)")
            ok = True
            break
        if not ok:
            print(f"  GAVE UP on {s} {seg_start.year} - rerun later; completed years are skipped")
    print("\nDone.")


if __name__ == "__main__":
    main()
