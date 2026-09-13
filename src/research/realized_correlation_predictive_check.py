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

nq = load_15m("data/raw_nq_extended")[["Close", "High", "Low"]].rename(columns={"Close": "nq_close", "High": "nq_high", "Low": "nq_low"})
es = load_15m("data/raw_es_extended")[["Close"]].rename(columns={"Close": "es_close"})

merged = nq.join(es, how="inner")
merged["nq_return"] = merged["nq_close"].pct_change()
merged["es_return"] = merged["es_close"].pct_change()
merged["rolling_corr"] = merged["nq_return"].rolling(20).corr(merged["es_return"])

# What happens to NQ's volatility in the NEXT 20 bars after a breakdown vs normal?
merged["future_range_20bar"] = merged["nq_high"].rolling(20).max().shift(-20) - merged["nq_low"].rolling(20).min().shift(-20)

breakdown_bars = merged[merged["rolling_corr"] < 0.5]
normal_bars = merged[merged["rolling_corr"] >= 0.5]

print(f"Breakdown bars (corr < 0.5): {len(breakdown_bars)}")
print(f"Avg future 20-bar range after breakdown: {breakdown_bars['future_range_20bar'].mean():.2f}")
print(f"Avg future 20-bar range after normal correlation: {normal_bars['future_range_20bar'].mean():.2f}")