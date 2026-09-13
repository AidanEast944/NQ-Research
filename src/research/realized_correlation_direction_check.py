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
merged["rolling_corr"] = merged["nq_return"].rolling(20).corr(merged["es_return"])
merged["future_return_20bar"] = (merged["nq_close"].shift(-20) - merged["nq_close"]) / merged["nq_close"] * 100

breakdown_bars = merged[merged["rolling_corr"] < 0.5]
normal_bars = merged[merged["rolling_corr"] >= 0.5]

print(f"Breakdown bars: {len(breakdown_bars)}")
print(f"Avg future 20-bar return after breakdown: {breakdown_bars['future_return_20bar'].mean():.4f}%")
print(f"Avg future 20-bar return after normal correlation: {normal_bars['future_return_20bar'].mean():.4f}%")
print(f"Win rate (positive future return) after breakdown: {(breakdown_bars['future_return_20bar'] > 0).mean()*100:.1f}%")