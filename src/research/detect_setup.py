import yfinance as yf
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

nq = yf.Ticker("NQ=F")
history = nq.history(period="60d", interval="15m")

# Add a column containing just the calendar date (no time) for each row
history["date"] = history.index.date

# Group all rows by date, then calculate each day's high and low
daily_levels = history.groupby("date").agg(
    day_high=("High", "max"),
    day_low=("Low", "min")
)

# Shift the daily levels down by 1 row, so each day "sees" the PREVIOUS day's high/low
daily_levels["prior_day_high"] = daily_levels["day_high"].shift(1)
daily_levels["prior_day_low"] = daily_levels["day_low"].shift(1)

# Get just the 8:30 AM candle for each day
opens_830 = history[history.index.time == pd.Timestamp("08:30").time()].copy()

# Attach the prior day's high/low onto each 8:30 candle, matching by date
opens_830 = opens_830.join(daily_levels[["prior_day_high", "prior_day_low"]], on="date")

def get_signal(row):
    if row["Close"] > row["prior_day_high"]:
        return "LONG"
    elif row["Close"] < row["prior_day_low"]:
        return "SHORT"
    else:
        return "NONE"

opens_830["signal"] = opens_830.apply(get_signal, axis=1)

# Keep only rows where an actual signal fired
signals_only = opens_830[opens_830["signal"] != "NONE"]

print(signals_only[["Close", "prior_day_high", "prior_day_low", "signal"]])
print(f"\nTotal signals found: {len(signals_only)}")

# Get the closing price at end of day (4:00 PM) for each day
closes_400 = history[history.index.time == pd.Timestamp("16:00").time()].copy()
closes_400 = closes_400.rename(columns={"Close": "close_400pm"})

# Attach the 4:00 PM close onto each signal row, matching by date
signals_only = signals_only.join(closes_400[["date", "close_400pm"]].set_index("date"), on="date")

# Calculate the price move from entry (8:30 close) to end of day
signals_only["points_gained"] = signals_only["close_400pm"] - signals_only["Close"]

# For SHORT trades, a price DROP is actually a win, so flip the sign
signals_only.loc[signals_only["signal"] == "SHORT", "points_gained"] *= -1

print(signals_only[["signal", "Close", "close_400pm", "points_gained"]])

win_rate = (signals_only["points_gained"] > 0).mean() * 100
print(f"\nWin rate (by end of day): {win_rate:.1f}%")
print(f"Average points gained per trade: {signals_only['points_gained'].mean():.2f}")
STOP_POINTS = 30
TARGET_POINTS = 60

def simulate_trade(row):
    entry_price = row["Close"]
    signal = row["signal"]
    day = row["date"]

    if signal == "LONG":
        stop_price = entry_price - STOP_POINTS
        target_price = entry_price + TARGET_POINTS
    else:
        stop_price = entry_price + STOP_POINTS
        target_price = entry_price - TARGET_POINTS

    # Get all bars AFTER entry, up through 4:00 PM, on the same day
    day_bars = history[
        (history["date"] == day)
        & (history.index.time > pd.Timestamp("08:30").time())
        & (history.index.time <= pd.Timestamp("16:00").time())
    ]

    for _, bar in day_bars.iterrows():
        if signal == "LONG":
            hit_stop = bar["Low"] <= stop_price
            hit_target = bar["High"] >= target_price
        else:
            hit_stop = bar["High"] >= stop_price
            hit_target = bar["Low"] <= target_price

        if hit_stop:
            return -STOP_POINTS  # stop wins ties, per our rule
        elif hit_target:
            return TARGET_POINTS

    # Neither hit all day - exit at final close
    final_close = day_bars.iloc[-1]["Close"]
    if signal == "LONG":
        return final_close - entry_price
    else:
        return entry_price - final_close

signals_only["trade_result"] = signals_only.apply(simulate_trade, axis=1)

print(signals_only[["signal", "Close", "trade_result"]])

win_rate_v2 = (signals_only["trade_result"] > 0).mean() * 100
print(f"\nWith {STOP_POINTS}pt stop / {TARGET_POINTS}pt target:")
print(f"Win rate: {win_rate_v2:.1f}%")
print(f"Average points gained per trade: {signals_only['trade_result'].mean():.2f}")