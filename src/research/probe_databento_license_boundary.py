"""
Probe: which dates will your Databento licence let you pull for CME (GLBX.MDP3)?
The daily refresh has failed since 2026-09-30 with 422 dataset_unavailable_range. get_cost() quotes fine for the
same ranges, so a quote proves nothing about access. The error's "try again with an end time before X" hint just
equals the time of the request, so it is no help either. (research_log.md Entry 76)

This pulls ONE 1-minute bar of NQ at a few dates. One record of 1-minute data costs a tiny fraction of a cent
(the full 3-year backfill of 3 markets was about $14), so the whole probe is far under one cent.
It also prints the dataset's advertised range (a free metadata call).

Run:  python3 src/research/probe_databento_license_boundary.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

for line in (open(".env").read().splitlines() if os.path.exists(".env") else []):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
try:
    import databento as db
except ImportError:
    sys.exit("pip install databento")
if not os.environ.get("DATABENTO_API_KEY"):
    sys.exit("No DATABENTO_API_KEY found.")

client = db.Historical()
ET = ZoneInfo("America/New_York")
print(f"now (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}")
try:
    print("dataset range advertised:", client.metadata.get_dataset_range(dataset="GLBX.MDP3"))
except Exception as e:
    print("get_dataset_range failed:", str(e).replace("\n", " ")[:160])

print(f"\n{'date (15:00 ET)':<18} result")
for d in ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-06", "2026-10-14", "2026-10-21", "2026-10-22", "2026-10-23"]:
    y, m, dd = map(int, d.split("-"))
    start = datetime(y, m, dd, 15, 0, tzinfo=ET)
    end = start + timedelta(minutes=1)
    try:
        df = client.timeseries.get_range(dataset="GLBX.MDP3", symbols=["NQ.c.0"], schema="ohlcv-1m",
                                         start=start.isoformat(), end=end.isoformat(), stype_in="continuous").to_df()
        print(f"{d:<18} OK  ({len(df)} bar)")
    except Exception as e:
        print(f"{d:<18} FAIL {str(e).replace(chr(10), ' ')[:150]}")
