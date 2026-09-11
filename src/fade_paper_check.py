import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker

STOP_POINTS = 30
TARGET_POINTS = 60
ENTRY_TIME = "08:30"
STATE_FILE = "data/fade_paper_account.json"

# RETIRED 2026-09-11 (research_log.md Entry 35): this strategy's ORIGINAL backtest (Entry 2) was
# already a FAIL (0/5 scorecard at 32 trades) - it was live this whole time despite that verdict,
# apparently never retired the way Trend (Entry 6) correctly was on its own FAIL. Re-run against
# the current 108-day archive via run_scorecards.py (results/scorecard_2026-09-06.txt) confirms it
# STILL fails 0/5 - profit factor 0.69, 102% max drawdown, negative out-of-sample expectancy - not
# a small-sample fluke that improved with more data, same as Entry 2 originally found. This guard
# matches trend_forward_daily.py's STRATEGY_RETIRED pattern: no new positions opened; there is no
# open position to manage as of retirement (checked directly - data/fade_paper_account.json has
# zero open positions), so no separate manage-only resolve step is needed the way Trend's has one.
# Remove this guard only after a fresh, explicit decision to re-test the strategy.
STRATEGY_RETIRED = True
if STRATEGY_RETIRED:
    print("Strategy RETIRED (research_log.md Entry 35: FAIL, 0/5 scorecard on the full archive) - "
          "no new positions will be opened.")
    sys.exit()

nq = yf.Ticker("NQ=F")
history = nq.history(period="5d", interval="15m")

if history.empty:
    print("WARNING: No data returned from Yahoo Finance. Skipping this run.")
    sys.exit()

history["date"] = history.index.date

today = date.today()
today_bars = history[history["date"] == today]

if today_bars.empty:
    print(f"No data yet for {today} - market may not be open, or too early.")
    sys.exit()

entry_bar = today_bars[today_bars.index.time == pd.Timestamp(ENTRY_TIME).time()]

if entry_bar.empty:
    print(f"No {ENTRY_TIME} candle found yet for {today}.")
    sys.exit()

prior_days = history[history["date"] < today]
if prior_days.empty:
    print("Not enough history to determine prior day high/low.")
    sys.exit()

most_recent_day = prior_days["date"].max()
prior_day_bars = prior_days[prior_days["date"] == most_recent_day]
prior_day_high = prior_day_bars["High"].max()
prior_day_low = prior_day_bars["Low"].min()

entry_price = entry_bar.iloc[0]["Close"]

if entry_price > prior_day_high:
    fade_signal = "SHORT"
elif entry_price < prior_day_low:
    fade_signal = "LONG"
else:
    print(f"No signal today ({today}). Nothing to trade.")
    sys.exit()

broker = PaperBroker(starting_balance=10000, state_file=STATE_FILE)

already_open_today = any(p["entry_date"] == str(today) for p in broker.positions)
if already_open_today:
    print(f"Already have an open paper position for {today}. Skipping.")
    sys.exit()

if fade_signal == "LONG":
    stop_price = entry_price - STOP_POINTS
    target_price = entry_price + TARGET_POINTS
else:
    stop_price = entry_price + STOP_POINTS
    target_price = entry_price - TARGET_POINTS

broker.place_order(
    symbol="NQ",
    direction=fade_signal,
    entry_price=entry_price,
    stop_price=stop_price,
    target_price=target_price,
    entry_date=str(today)
)