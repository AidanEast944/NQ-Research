import yfinance as yf
import os

TICKER = "CL=F"
OUTPUT_FILE = "data/raw_cl_daily_history.csv"

print(f"Fetching maximum available DAILY (not intraday) history for {TICKER}...")
print("This is a free, one-time backfill - yfinance typically has years of daily-close")
print("history even for instruments where intraday (15m) history is capped at ~60 days.")
print("Good enough to start testing daily-frequency ideas (overnight drift, day-of-week")
print("effects) on crude oil immediately, while the 15m intraday archive (raw_cl/, via")
print("save_multi_symbol_data.py) builds up day by day for anything that needs intraday bars.\n")

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
