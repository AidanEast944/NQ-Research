import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import glob
import pandas as pd

def load_15m(folder):
    files = glob.glob(os.path.join(folder, "*.csv"))
    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    hist = pd.concat(all_days)
    hist = hist[~hist.index.duplicated(keep="first")]
    hist = hist.sort_index()
    hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
    return hist

nq = load_15m("data/raw_nq_extended")[["Close"]].rename(columns={"Close": "nq_close"})
es = load_15m("data/raw_es_extended")[["Close"]].rename(columns={"Close": "es_close"})

merged = nq.join(es, how="inner")
merged["nq_return"] = merged["nq_close"].pct_change()
merged["es_return"] = merged["es_close"].pct_change()

# Rolling 20-bar (5-hour) realized correlation of 15-min returns
merged["rolling_corr"] = merged["nq_return"].rolling(20).corr(merged["es_return"])

print("Realized correlation distribution (20-bar rolling window):")
print(merged["rolling_corr"].describe())
print(f"\nBars with correlation below 0.3 (a real breakdown): {(merged['rolling_corr'] < 0.3).sum()}")
print(f"Bars with correlation below 0.0 (negative - very unusual): {(merged['rolling_corr'] < 0.0).sum()}")