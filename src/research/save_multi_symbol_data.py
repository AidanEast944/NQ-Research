import yfinance as yf
import os

SYMBOLS = {
    "ES=F": "data/raw_es",
    "YM=F": "data/raw_ym",
    "CL=F": "data/raw_cl",  # WTI Crude Oil - added 2026-09-10 as an independent-instrument
                              # candidate (see research_log.md) - a genuinely different risk
                              # driver (energy supply/demand) than the equity index book.
}

for ticker_symbol, save_folder in SYMBOLS.items():
    print(f"\n--- Fetching {ticker_symbol} ---")

    ticker = yf.Ticker(ticker_symbol)
    history = ticker.history(period="60d", interval="15m")

    if history.empty:
        print(f"WARNING: No data returned for {ticker_symbol}. Skipping.")
        continue

    history["date"] = history.index.date
    unique_dates = history["date"].unique()

    os.makedirs(save_folder, exist_ok=True)

    saved_count = 0
    skipped_count = 0

    for day in unique_dates:
        filename = f"{save_folder}/{ticker_symbol.replace('=F', '')}_15m_{day}.csv"

        if os.path.exists(filename):
            skipped_count += 1
            continue

        day_data = history[history["date"] == day]
        day_data.to_csv(filename)
        saved_count += 1

    print(f"Saved {saved_count} new day(s), skipped {skipped_count} already-saved day(s).")
