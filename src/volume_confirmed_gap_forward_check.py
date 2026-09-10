"""
Live forward-test OPEN step for the volume-confirmed gap continuation strategy (Entry 25/27).
Runs as a parallel track alongside the unfiltered gap strategy - does NOT replace it. Whether to
ever redirect the unfiltered gap tracking at this definition remains an explicitly open decision,
not made here.

OPEN-ONLY, matching gap_forward_check.py's 2026-09-10 fix (Entry 32) - a trade opened here is
resolved later in the day by volume_confirmed_gap_resolve.py, once the full day's price action is
available. The original single-run design (open + immediately try to resolve within the same
execution) almost never actually saw the real outcome, since it ran too soon after the entry bar
to have any meaningful price history to check against.

Same entry mechanics as gap_forward_check.py (08:30 ET open, 30pt minimum gap, 40pt stop / 80pt
target, MNQ micro sizing), with an added filter: the 08:30 opening-bar volume must be at least the
threshold multiple of its own trailing 20-day average - matching
get_weekday_open_gap_signals_with_volume_from_archive()'s definition in strategy.py.

Tracks BOTH thresholds validated in Entry 27 Part 5, independently: 1.2x (Entry 25, full-sample
hindsight) and 1.5x (Entry 27 Part 5, honest out-of-time selection). Each threshold has its own
PaperBroker account file and risk_limits state file, fully isolated from each other and from the
unfiltered gap strategy's state.
"""
import sys
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from risk_limits import check_trade_allowed

MIN_GAP_POINTS = 30
STOP_POINTS = 40
TARGET_POINTS = 80
POINT_VALUE = 2  # MNQ micro contract
VOLUME_LOOKBACK = 20
ENTRY_TIME = "08:30"

THRESHOLDS = {
    "1.2x": {
        "value": 1.2,
        "account_file": "data/volume_gap_1_2x_paper_account.json",
        "risk_state_file": "data/volume_gap_1_2x_risk_limits_state.json",
    },
    "1.5x": {
        "value": 1.5,
        "account_file": "data/volume_gap_1_5x_paper_account.json",
        "risk_state_file": "data/volume_gap_1_5x_risk_limits_state.json",
    },
}

nq = yf.Ticker("NQ=F")
history = nq.history(period="60d", interval="15m")

if history.empty:
    print("WARNING: No data returned. Skipping.")
    sys.exit()

history["date"] = history.index.date
today = date.today()
today_bars = history[history["date"] == today]

if today_bars.empty:
    print(f"No data yet for {today}.")
    sys.exit()

prior_days = history[history["date"] < today]
if prior_days.empty:
    print("Not enough history.")
    sys.exit()

most_recent_day = prior_days["date"].max()
prior_day_bars = prior_days[prior_days["date"] == most_recent_day]
prior_close = prior_day_bars.iloc[-1]["Close"]

entry_t = pd.Timestamp(ENTRY_TIME).time()

open_bar = today_bars[today_bars.index.time == entry_t]
if open_bar.empty:
    print(f"No {ENTRY_TIME} candle yet for {today}.")
    sys.exit()

open_price = open_bar.iloc[0]["Open"]
today_entry_volume = open_bar.iloc[0]["Volume"]
gap_points = open_price - prior_close

prior_entry_bars = prior_days[prior_days.index.time == entry_t].groupby("date")["Volume"].first()
prior_entry_bars = prior_entry_bars.sort_index()

if len(prior_entry_bars) < max(5, VOLUME_LOOKBACK // 2):
    print(f"Not enough prior {ENTRY_TIME} bars ({len(prior_entry_bars)}) to compute a trustworthy "
          f"{VOLUME_LOOKBACK}-day trailing volume average yet. Skipping.")
    sys.exit()

trailing_avg_volume = prior_entry_bars.tail(VOLUME_LOOKBACK).mean()
volume_ratio = today_entry_volume / trailing_avg_volume if trailing_avg_volume else float("nan")

print(f"Prior close: {prior_close}, Today's open: {open_price}, Gap: {gap_points:.2f} points")
print(f"Today's {ENTRY_TIME} volume: {today_entry_volume:,.0f}, trailing {VOLUME_LOOKBACK}-day avg: "
      f"{trailing_avg_volume:,.0f}, ratio: {volume_ratio:.2f}x")

if abs(gap_points) < MIN_GAP_POINTS:
    print(f"Gap too small ({gap_points:.2f} pts) - no signal for any threshold today.")
    sys.exit()

signal = "LONG" if gap_points > 0 else "SHORT"
entry_price = open_price
stop_price = entry_price - STOP_POINTS if signal == "LONG" else entry_price + STOP_POINTS
target_price = entry_price + TARGET_POINTS if signal == "LONG" else entry_price - TARGET_POINTS

for label, cfg in THRESHOLDS.items():
    print(f"\n--- Threshold {label} ---")
    if volume_ratio < cfg["value"]:
        print(f"Volume ratio {volume_ratio:.2f}x < {cfg['value']}x threshold - no trade for this track today.")
        continue

    broker = PaperBroker(starting_balance=10000, state_file=cfg["account_file"])

    already_processed_today = any(
        t.get("entry_date") == str(today) for t in broker.trade_history
    ) or any(
        p.get("entry_date") == str(today) for p in broker.positions
    )
    if already_processed_today:
        print(f"Already opened/processed a {label} signal for {today}. Skipping to avoid a duplicate.")
        continue

    proposed_risk_dollars = STOP_POINTS * POINT_VALUE
    current_open_positions = len(broker.positions)

    allowed, reason = check_trade_allowed(
        account_balance=broker.balance,
        proposed_risk_dollars=proposed_risk_dollars,
        current_open_positions=current_open_positions,
        state_file=cfg["risk_state_file"],
    )

    if not allowed:
        print(f"TRADE BLOCKED BY RISK LIMITS: {reason}")
        continue

    broker.place_order(
        symbol="MNQ",
        direction=signal,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        entry_date=str(today)
    )

    print(f"{label}: position opened (volume_ratio={volume_ratio:.2f}x) - "
          f"will be resolved end of day by volume_confirmed_gap_resolve.py.")
