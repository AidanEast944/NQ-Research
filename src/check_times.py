import yfinance as yf

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="1h")

# Show the unique times-of-day present in the hourly data
unique_times = sorted(set(history.index.time))
print(unique_times)