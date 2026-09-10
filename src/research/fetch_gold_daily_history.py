import yfinance as yf
import os

TICKER = "GC=F"
OUTPUT_FILE = "data/raw_gc_daily_history.csv"

print(f"Fetching maximum available DAILY (not intraday) history for {TICKER}...")
print("Same free, one-time backfill approach used for crude oil (fetch_crude_oil_daily_history.py) -")
print("gold futures typically have decades of daily-close history via yfinance even though intraday")
print("(15m) history is capped at ~60 days.\n")

ticker = yf.Ticker(TICKER)
history = ticker.history(period="max", interval="1d")

if history.empty:
    print("WARNING: No data returned. Check the ticker symbol or your network connection.")
else:
    os.makedirs("data", exist_ok=True)
    history.index.name = "Date"
    to_save = history[["Open", "High", "Low", "Close", "Volume"]]
    to_save.to_csv(OUTPUT_FILE)
    print(f"Saved {len(to_save)} daily bars ({to_save.index.min().date()} to "
          f"{to_save.index.max().date()}) to {OUTPUT_FILE}")
