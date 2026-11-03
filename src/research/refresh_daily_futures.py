"""
Incremental refresh of the daily-futures files (Databento ohlcv-1d). Pulls only the last few days per market and MERGES them into
data/futures_daily (front, .c.0) and data/futures_daily_c1 (second contract, .c.1) so the forward tracker has fresh bars every day.
Not a trial and looks at no results. Cost is cents per run. Needs DATABENTO_API_KEY (.env or environment).

  python3 src/research/refresh_daily_futures.py                     quote only (default)
  python3 src/research/refresh_daily_futures.py --pull [--max-cost 0.25]
Rules: window starts OVERLAP_DAYS before each file's last date; the merge keeps existing rows, replaces overlapping dates with the new
values, never shrinks a file; a market that fails (after retries) is skipped and reported, and the run exits 1 so the heartbeat alerts.
"""
import argparse
import os
import sys
import time
from datetime import date, timedelta

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))   # append: src/research has a same-named test_paper_broker.py
import pull_daily_futures as P

OVERLAP_DAYS = 7
DEFAULT_MAX_COST = 0.25
RANK_DIRS = {0: "data/futures_daily", 1: "data/futures_daily_c1"}


def merge_new(old, new):
    """old, new: DataFrames indexed by date with identical columns. New rows win on overlapping dates; the result is never shorter."""
    if old is None or old.empty:
        return new.sort_index()
    merged = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
    assert len(merged) >= len(old), "merge would shrink the file"
    return merged


def last_date(path):
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    return None if df.empty else df.index.max().date()


def plan(root, symbols, today=None):
    """[(rank, symbol, start_date)] for every existing file; ranks whose folder lacks a symbol are skipped (nothing to extend)."""
    today = today or date.today()
    out = []
    for rank, d in RANK_DIRS.items():
        for s in symbols:
            ld = last_date(os.path.join(root, d, f"{s}.csv"))
            if ld is None:
                continue
            start = ld - timedelta(days=OVERLAP_DAYS)
            if ld < today - timedelta(days=1):          # yesterday's bar is missing -> refresh; otherwise the file is current
                out.append((rank, s, start))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--max-cost", type=float, default=DEFAULT_MAX_COST)
    a = ap.parse_args()
    P.load_dotenv_manually()
    if not os.environ.get("DATABENTO_API_KEY"):
        print("No DATABENTO_API_KEY found (.env or environment). Nothing done."); sys.exit(1)
    import databento as db
    client = db.Historical()
    end = date.today() - timedelta(days=1)
    jobs = plan(".", P.universe())
    if not jobs:
        print("Nothing to refresh (all files already current)."); return
    total, failed, quotes = 0.0, [], {}
    for rank, s, start in jobs:
        for attempt in range(3):
            try:
                c = client.metadata.get_cost(dataset="GLBX.MDP3", symbols=[f"{s}.c.{rank}"], schema="ohlcv-1d",
                                             start=P.eastern_midnight_iso(start), end=P.eastern_midnight_iso(end), stype_in="continuous")
                quotes[(rank, s)] = float(c); total += float(c); break
            except Exception as e:
                time.sleep(10 * (attempt + 1))
        else:
            failed.append(f"{s}.c.{rank}")
    print(f"{len(jobs)} refreshes, TOTAL quote ${total:.4f}" + (f", quotes failed: {failed}" if failed else ""))
    if not a.pull:
        print("QUOTE ONLY - nothing pulled."); return
    if failed or total > a.max_cost:
        print(f"REFUSING: {'quotes failed' if failed else f'${total:.4f} above --max-cost ${a.max_cost:.2f}'}. Nothing pulled."); sys.exit(1)
    bad = []
    for rank, s, start in jobs:
        df = None
        for attempt in range(4):
            try:
                store = client.timeseries.get_range(dataset="GLBX.MDP3", symbols=[f"{s}.c.{rank}"], schema="ohlcv-1d",
                                                    start=P.eastern_midnight_iso(start), end=P.eastern_midnight_iso(end), stype_in="continuous")
                df = store.to_df(); break
            except Exception as e:
                print(f"  {s}.c.{rank} attempt {attempt + 1} failed: {e}"); time.sleep(20 * (attempt + 1))
        if df is None or df.empty:
            bad.append(f"{s}.c.{rank}"); continue
        new = df[["open", "high", "low", "close", "volume", "instrument_id"]].copy()
        new.index = new.index.tz_convert("UTC").date
        new.index.name = "date"
        new.index = pd.to_datetime(new.index)
        path = os.path.join(RANK_DIRS[rank], f"{s}.csv")
        old = pd.read_csv(path, parse_dates=["date"], index_col="date")
        merge_new(old, new).to_csv(path)
        print(f"  refreshed {s}.c.{rank}: now through {merge_new(old, new).index.max().date()}")
    if bad:
        print(f"WARNING: could not refresh {bad}"); sys.exit(1)


if __name__ == "__main__":
    main()
