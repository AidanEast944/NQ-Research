"""
Live forward-test OPEN step for the volume-confirmed gap continuation strategy, applied to ES
(S&P 500 futures). Uses ES-specific scaled parameters, not NQ/YM's raw values - ES trades at
roughly 1/5th NQ's price level, so a proportionally scaled gap threshold and stop/target were
backtested and validated separately: 113 trades, 41.6% win rate, PF 1.42 in-sample, PF 1.40
out-of-sample (no collapse) at min_gap=6pts, stop=10pts, target=20pts, 1.2x volume threshold.

OPEN-ONLY - resolved later in the day by volume_confirmed_gap_es_resolve.py.
Uses MES (S&P 500 micro contract, $5/point) sizing.
"""
import sys
import time
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from risk_limits import check_trade_allowed
from live_gate import gate_new_entry
import coverage_log as cov
cov.start("volume_confirmed_gap_es", "Volume-Confirmed Gap ES")
from dashboard_trigger import refresh_dashboard

MIN_GAP_POINTS = 6
STOP_POINTS = 10
TARGET_POINTS = 20
POINT_VALUE = 5  # MES micro contract
VOLUME_LOOKBACK = 20
ENTRY_TIME = "08:30"

THRESHOLDS = {
    "1.2x": {
        "value": 1.2,
        "account_file": "data/volume_gap_es_1_2x_paper_account.json",
        "risk_state_file": "data/volume_gap_es_1_2x_risk_limits_state.json",
    },
}

es = yf.Ticker("ES=F")
today = date.today()
entry_t = pd.Timestamp(ENTRY_TIME).time()

# FIX (2026-10-02, research_log.md - 08:30 candle timing bug): see gap_forward_check.py's
# docstring for the full reasoning - same bug, same fix, applied here too.
# 2026-10-05 (research_log.md Entry 61): the retry above caught the 08:30 candle the moment it
# appeared, while it was still FORMING - volume read as ~0 (NQ 0, YM 0.02x, ES 0.03x of normal), so
# every volume-confirmed track rejected a valid -76pt gap. The volume filter is defined on the
# COMPLETE 15-min bar, so we now also require the next bar (08:45) to exist before trusting it,
# and poll longer (12 x 60s) to cover posting lag past 08:45.
MAX_RETRIES = 12
RETRY_SLEEP_SECONDS = 60
NEXT_BAR_T = (pd.Timestamp(ENTRY_TIME) + pd.Timedelta(minutes=15)).time()

history = None
open_bar = None
today_bars = None

for attempt in range(1, MAX_RETRIES + 1):
    candidate_history = es.history(period="60d", interval="15m")
    if candidate_history.empty:
        print(f"WARNING: No data returned (attempt {attempt}/{MAX_RETRIES}).")
    else:
        candidate_history["date"] = candidate_history.index.date
        candidate_today_bars = candidate_history[candidate_history["date"] == today]
        candidate_open_bar = candidate_today_bars[candidate_today_bars.index.time == entry_t]
        entry_bar_complete = not candidate_today_bars[candidate_today_bars.index.time == NEXT_BAR_T].empty
        if not candidate_open_bar.empty and entry_bar_complete:
            history = candidate_history
            today_bars = candidate_today_bars
            open_bar = candidate_open_bar
            break

    if attempt < MAX_RETRIES:
        print(f"No {ENTRY_TIME} candle not complete yet for {today} (attempt {attempt}/{MAX_RETRIES}) - retrying in {RETRY_SLEEP_SECONDS}s.")
        time.sleep(RETRY_SLEEP_SECONDS)

if open_bar is None:
    print(f"No {ENTRY_TIME} candle for {today} after {MAX_RETRIES} attempts "
          f"({(MAX_RETRIES - 1) * RETRY_SLEEP_SECONDS}s total) - giving up for today.")
    sys.exit()

prior_days = history[history["date"] < today]
if prior_days.empty:
    print("Not enough history.")
    sys.exit()

most_recent_day = prior_days["date"].max()
prior_day_bars = prior_days[prior_days["date"] == most_recent_day]
prior_close = prior_day_bars.iloc[-1]["Close"]

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
cov.evaluated("volume_confirmed_gap_es", f"gap {gap_points:.2f}pt, volume ratio {volume_ratio:.2f}x")

print(f"[ES] Prior close: {prior_close}, Today's open: {open_price}, Gap: {gap_points:.2f} points")
print(f"[ES] Today's {ENTRY_TIME} volume: {today_entry_volume:,.0f}, trailing {VOLUME_LOOKBACK}-day avg: "
      f"{trailing_avg_volume:,.0f}, ratio: {volume_ratio:.2f}x")

if abs(gap_points) < MIN_GAP_POINTS:
    print(f"[ES] Gap too small ({gap_points:.2f} pts) - no signal today.")
    sys.exit()

signal = "LONG" if gap_points > 0 else "SHORT"
entry_price = open_price
stop_price = entry_price - STOP_POINTS if signal == "LONG" else entry_price + STOP_POINTS
target_price = entry_price + TARGET_POINTS if signal == "LONG" else entry_price - TARGET_POINTS

# --- LIVE GATE: default-closed, must be explicitly registered in live_gate.py (2026-09-15) ---
if not gate_new_entry("volume_confirmed_gap_es", label="Volume-Confirmed Gap ES"):
    sys.exit()
# --- END LIVE GATE ---

for label, cfg in THRESHOLDS.items():
    print(f"\n--- [ES] Threshold {label} ---")
    if volume_ratio < cfg["value"]:
        print(f"Volume ratio {volume_ratio:.2f}x < {cfg['value']}x threshold - no trade today.")
        continue

    broker = PaperBroker(starting_balance=10000, state_file=cfg["account_file"])

    already_processed_today = any(
        t.get("entry_date") == str(today) for t in broker.trade_history
    ) or any(
        p.get("entry_date") == str(today) for p in broker.positions
    )
    if already_processed_today:
        print(f"Already opened/processed a {label} signal for {today}. Skipping.")
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
        symbol="MES",
        direction=signal,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        entry_date=str(today)
    )

    print(f"{label}: position opened (volume_ratio={volume_ratio:.2f}x) - "
          f"will be resolved end of day by volume_confirmed_gap_es_resolve.py.")