import pandas as pd
import glob
import os

SOURCE_PATTERN = os.path.expanduser("~/.databento/GLBX.MDP3/YM_c_0/ohlcv-1m/*/*.parquet")
OUTPUT_FOLDER = "data/raw_ym_extended"

files = glob.glob(SOURCE_PATTERN)
print(f"Found {len(files)} monthly files.")

all_months = [pd.read_parquet(f) for f in files]
combined = pd.concat(all_months)
combined = combined.sort_values("ts_event")

combined["ts_event"] = combined["ts_event"].dt.tz_convert("America/New_York")
combined = combined.set_index("ts_event")

combined = combined[["open", "high", "low", "close", "volume"]]
combined.columns = ["Open", "High", "Low", "Close", "Volume"]

resampled = combined.resample("15min").agg({
    "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
})
resampled = resampled.dropna(subset=["Open"])
resampled["date"] = resampled.index.date

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

saved_count = 0
for day, group in resampled.groupby("date"):
    filename = f"{OUTPUT_FOLDER}/ym_15m_{day}.csv"
    group_to_save = group.drop(columns=["date"])
    group_to_save.index.name = "Datetime"
    group_to_save.to_csv(filename)
    saved_count += 1

print(f"Saved {saved_count} daily files to {OUTPUT_FOLDER}")