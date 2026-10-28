"""
Pulls DAILY bars (Databento GLBX.MDP3, ohlcv-1d, continuous front-month '<SYM>.c.0') for the diversified low-turnover
family's universe in registry/families.json, 2010-06-07 to yesterday. Saves data/futures_daily/<SYM>.csv with the columns
date, open, high, low, close, volume, instrument_id. instrument_id changes on every contract roll, which is how the loader masks
roll-day returns. Daily bars are UTC-day bars (close is roughly 19:00-20:00 Eastern), a consistent grid that is fine for monthly signals.

TWO MODES - nothing is spent in the default mode:
  QUOTE (default): prints the exact get_cost() for every symbol and the total.
      cd ~/nq-research && source venv/bin/activate && python3 src/research/pull_daily_futures.py
  PULL (explicit): requires --pull and --max-cost. Re-quotes, refuses if the total is above --max-cost, then pulls each symbol
      (3 retries with backoff). An existing file is never replaced by one with fewer rows.
      python3 src/research/pull_daily_futures.py --pull --max-cost 2.00 [--symbols ZN,ZB]
Pulling data is not a trial and looks at no results; it only fills the folder. Needs DATABENTO_API_KEY (.env or environment).
"""
import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

OUT_DIR = "data/futures_daily"
START = date(2010, 6, 7)
EASTERN = ZoneInfo("America/New_York")


def universe():
    with open("registry/families.json") as f:
        fam = json.load(f)["families"]["diversified_lowturnover"]
    return [s for syms in fam["universe"].values() for s in syms]


def load_dotenv_manually(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def eastern_midnight_iso(d):
    return datetime(d.year, d.month, d.day, tzinfo=EASTERN).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--max-cost", type=float, default=None)
    ap.add_argument("--symbols", default=None)
    a = ap.parse_args()
    load_dotenv_manually()
    if not os.environ.get("DATABENTO_API_KEY"):
        print("No DATABENTO_API_KEY found (.env or environment). Nothing done."); sys.exit(1)
    import databento as db
    client = db.Historical()
    syms = [s.strip().upper() for s in a.symbols.split(",")] if a.symbols else universe()
    # Exclusive end = yesterday (Eastern midnight). Today's date at Eastern midnight is 04:00 UTC, which is AFTER the dataset's
    # available end (today 00:00 UTC) and made every quote fail with 422 on the first attempt (2026-10-26).
    end = date.today() - timedelta(days=1)
    total, quotes = 0.0, {}
    for s in syms:
        c = float("nan")
        for attempt in range(3):   # a gateway timeout (504) on one symbol is transient; retry before giving up
            try:
                c = client.metadata.get_cost(dataset="GLBX.MDP3", symbols=[f"{s}.c.0"], schema="ohlcv-1d",
                                             start=eastern_midnight_iso(START), end=eastern_midnight_iso(end), stype_in="continuous")
                break
            except Exception as e:
                print(f"{s}: quote attempt {attempt + 1} failed - {str(e)[:120]}")
                time.sleep(3 * (attempt + 1))
        quotes[s] = c
        total += 0 if c != c else c
        print(f"{s:<4} quote ${c:.4f}")
    failed = [x for x, c in quotes.items() if c != c]
    print(f"TOTAL quote ${total:.4f} for {len(syms) - len(failed)} of {len(syms)} symbols, {START} -> {end - timedelta(days=1)}")
    if failed:
        print(f"WARNING: {len(failed)} quote(s) FAILED ({', '.join(failed)}); the total above is incomplete and no pull is allowed.")
    if not a.pull:
        print("\nQUOTE ONLY - nothing pulled or spent. To pull: --pull --max-cost N"); return
    if a.max_cost is None:
        print("--pull requires --max-cost."); sys.exit(1)
    if failed:
        print("REFUSING: some quotes failed, so the real cost is unknown. Nothing pulled."); sys.exit(1)
    if total > a.max_cost:
        print(f"REFUSING: quote ${total:.4f} is above --max-cost ${a.max_cost:.2f}. Nothing pulled."); sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)
    spent = 0.0
    for s in syms:
        df = None
        for attempt in range(4):
            try:
                store = client.timeseries.get_range(dataset="GLBX.MDP3", symbols=[f"{s}.c.0"], schema="ohlcv-1d",
                                                    start=eastern_midnight_iso(START), end=eastern_midnight_iso(end),
                                                    stype_in="continuous")
                df = store.to_df(); break
            except Exception as e:
                print(f"  {s} attempt {attempt+1} failed: {e}"); time.sleep(20 * (attempt + 1))
        if df is None or df.empty:
            print(f"WARNING: {s} returned nothing."); continue
        out = df[["open", "high", "low", "close", "volume", "instrument_id"]].copy()
        out.index = out.index.tz_convert("UTC").date
        out.index.name = "date"
        path = os.path.join(OUT_DIR, f"{s}.csv")
        if os.path.exists(path):
            with open(path) as f:
                old = sum(1 for _ in f) - 1
            if len(out) < old:
                print(f"  SKIPPING {s}: new {len(out)} rows < existing {old}"); continue
        out.to_csv(path)
        spent += 0 if quotes[s] != quotes[s] else quotes[s]
        print(f"  saved {s}: {len(out)} rows {out.index.min()} -> {out.index.max()}")
    print(f"\nDone. Quoted cost of pulls that succeeded: ${spent:.4f}")


if __name__ == "__main__":
    main()
