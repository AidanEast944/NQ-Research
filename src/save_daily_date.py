import yfinance as yf
import os

nq = yf.Ticker("NQ=F")
history = nq.history(period="60d", interval="15m")

if history.empty:
    print("WARNING: No data returned from Yahoo Finance. This may be a temporary outage "
          "or futures contract rollover issue. Skipping this run - will retry next scheduled time.")
    exit()

# Add a plain date column, same technique as before
history["date"] = history.index.date

# Get the list of unique dates present in this data pull
unique_dates = history["date"].unique()

# Make sure the folder we're saving into actually exists
save_folder = "data/raw"
os.makedirs(save_folder, exist_ok=True)

saved_count = 0
skipped_count = 0

for day in unique_dates:
    filename = f"{save_folder}/nq_15m_{day}.csv"

    if os.path.exists(filename):
        skipped_count += 1
        continue

    day_data = history[history["date"] == day]
    day_data.to_csv(filename)
    saved_count += 1

print(f"Saved {saved_count} new day(s), skipped {skipped_count} already-saved day(s).")