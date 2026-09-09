import yfinance as yf
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")

# Filter to only rows where the time is 8:30 AM
opens_830 = history[history.index.time == pd.Timestamp("08:30").time()]
print(opens_830)