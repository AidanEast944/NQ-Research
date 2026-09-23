import sys
import json
import os
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from position_sizing import fixed_fractional_size
import risk_limits
from live_gate import gate_new_entry

LOOKBACK = 20
ENTRY_Z = 2.0
STOP_Z = 3.5        # matches get_pairs_trading_signals_from_archive()'s default in strategy.py -
                     # this is the stop that was actually backtested and produced the PF 2.52
                     # quoted for Entry 9 in research_log.md, not a fresh guess
MAX_HOLD_DAYS = 15   # same - matches the archive backtest's default, not a fresh guess
STATE_FILE = "data/pairs_forward_state.json"  # z-score/position-tracking state (unchanged from before)

# --- Risk wiring added 2026-09-10 (research_log.md Entry 24) ---
# MNQ/MES micro contracts, matching the sizing pairs_scorecard_v2.py validated in Entry 23.
POINT_VALUE_NQ = 2.0
POINT_VALUE_ES = 5.0
PAIRS_ACCOUNT_FILE = "data/pairs_paper_account.json"     # shared across all 3 pairs scripts
PAIRS_RISK_STATE_FILE = "data/pairs_risk_limits_state.json"  # shared across all 3 pairs scripts,
                                                               # kept SEPARATE from gap_forward_check.py's
                                                               # risk_limits_state.json so the two
                                                               # strategy families' drawdown/halt
                                                               # tracking don't get mixed together.
PAIRS_STARTING_BALANCE = 100000  # bumped from 10000 on 2026-09-23 (research_log.md Entry 51) -
                                  # at $10,000, even a single micro contract's risk (see
                                  # AVG_LOSS_PER_UNIT_DOLLARS below) already exceeded
                                  # risk_limits.MAX_RISK_PER_TRADE_PCT (2%), so every proposed
                                  # entry was blocked before it could open. $100,000 is the
                                  # smallest clean number that lets all three pairs (NQ/ES, NQ/YM,
                                  # ES/YM - this constant is shared across pairs_forward_check.py
                                  # and generic_pairs_forward_check.py) size at least 1 contract
                                  # within RISK_PERCENT below, comfortably under the 2% hard cap.
                                  # Still a placeholder paper-trading assumption - update if you
                                  # want a different assumed size for the pairs book specifically.
# Average losing-trade size at 1x leg-A-contract-equivalent sizing, from Entry 23's real
# backtest (39 trades) - used as the "risk per contract" basis for position sizing below. This is
# the historical AVERAGE loss, not the worst case, so RISK_PERCENT is set to half of
# risk_limits.MAX_RISK_PER_TRADE_PCT as a buffer against any single loss exceeding the average -
# still an estimate, not a guarantee, and worth revisiting once more live trades accumulate.
AVG_LOSS_PER_UNIT_DOLLARS = 514.89
RISK_PERCENT = risk_limits.MAX_RISK_PER_TRADE_PCT / 2


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"position": None, "history": [], "last_run_date": None}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

state = load_state()
today = date.today()

if state.get("last_run_date") == str(today):
    print(f"Already processed {today}. Skipping.")
    sys.exit()
state["last_run_date"] = str(today)

nq = yf.Ticker("NQ=F").history(period="60d", interval="1d")
es = yf.Ticker("ES=F").history(period="60d", interval="1d")

if nq.empty or es.empty:
    print("WARNING: No data returned. Skipping this run.")
    save_state(state)
    sys.exit()

nq = nq[["Close"]].rename(columns={"Close": "close_nq"})
es = es[["Close"]].rename(columns={"Close": "close_es"})
nq.index = nq.index.date
es.index = es.index.date

merged = nq.join(es, how="inner")
merged["ratio"] = merged["close_nq"] / merged["close_es"]
merged["ratio_mean"] = merged["ratio"].rolling(LOOKBACK).mean()
merged["ratio_std"] = merged["ratio"].rolling(LOOKBACK).std()
merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]

if str(today) not in [str(d) for d in merged.index]:
    print(f"No data yet for {today}.")
    save_state(state)
    sys.exit()

current_z = merged.loc[merged.index == today, "zscore"].iloc[0]
current_nq_price = merged.loc[merged.index == today, "close_nq"].iloc[0]
current_es_price = merged.loc[merged.index == today, "close_es"].iloc[0]
print(f"Current NQ/ES z-score: {current_z:.2f}")

# Symbols are tagged with the pair name (not just "MNQ"/"MES") because PAIRS_ACCOUNT_FILE and
# PAIRS_RISK_STATE_FILE are shared across all three pairs scripts (that's what makes the risk
# checks portfolio-wide instead of siloed per-pair) - plain "MNQ" would collide if this pair and
# NQ/YM both had an open MNQ leg on the same entry date, and the wrong leg could get closed.
SYMBOL_NQ = "MNQ (NQ/ES)"
SYMBOL_ES = "MES (NQ/ES)"

broker = PaperBroker(starting_balance=PAIRS_STARTING_BALANCE, state_file=PAIRS_ACCOUNT_FILE)

if state["position"] is None:
    if abs(current_z) > ENTRY_Z:
        # --- LIVE GATE: default-closed, must be explicitly registered in live_gate.py (2026-09-15) ---
        if not gate_new_entry("pairs_nq_es", label="NQ/ES"):
            save_state(state)
            sys.exit()
        # --- END LIVE GATE ---

        direction_nq = "SHORT" if current_z > ENTRY_Z else "LONG"
        direction_es = "LONG" if direction_nq == "SHORT" else "SHORT"

        hedge_ratio = (current_nq_price * POINT_VALUE_NQ) / (current_es_price * POINT_VALUE_ES)

        # --- POSITION SIZING FIX 2026-09-23 (research_log.md Entry 51) ---
        # This used to be `max(1, round(fixed_fractional_size(...)))`, which forced a 1-contract
        # floor whenever the ideal size rounded to 0. But fixed_fractional_size()'s own docstring
        # says to round DOWN for real trading, since you can't buy partial contracts - and for
        # this pair, 1 forced contract's risk (contracts * AVG_LOSS_PER_UNIT_DOLLARS) could itself
        # exceed risk_limits.MAX_RISK_PER_TRADE_PCT, so the circuit breaker blocked every single
        # entry, silently, no matter how strong the z-score signal was. Genuinely flooring to 0 and
        # skipping the trade (instead of forcing 1 and getting blocked downstream) makes that
        # failure visible and correct - see the PAIRS_STARTING_BALANCE comment above for the other
        # half of this fix, which is what actually lets a real trade open again.
        raw_size_nq = fixed_fractional_size(
            PAIRS_STARTING_BALANCE, RISK_PERCENT, stop_points=1, point_value=AVG_LOSS_PER_UNIT_DOLLARS
        )
        contracts_nq = int(raw_size_nq)  # genuine floor, not round-to-nearest-with-min-1
        if contracts_nq < 1:
            print(f"NQ/ES: z-score {current_z:.2f} would trigger an entry, but position sizing "
                  f"yields {raw_size_nq:.3f} contracts at ${PAIRS_STARTING_BALANCE:,.0f} balance / "
                  f"{RISK_PERCENT:.2f}% risk - skipping rather than forcing a 1-contract minimum "
                  f"that would only get blocked by the risk cap anyway.")
            save_state(state)
            sys.exit()
        # --- END POSITION SIZING FIX ---

        contracts_es = max(1, round(contracts_nq * hedge_ratio))

        # --- RISK CIRCUIT BREAKER CHECK, using the pairs book's own paper balance/state ---
        proposed_risk_dollars = contracts_nq * AVG_LOSS_PER_UNIT_DOLLARS
        current_open_positions = len(broker.positions)  # each leg counts as one open position,
                                                          # so a single pairs trade (2 legs) uses
                                                          # 2 of MAX_OPEN_POSITIONS' 3 slots - a
                                                          # deliberately conservative reading of
                                                          # "how much simultaneous market exposure
                                                          # is open right now."
        allowed, reason = risk_limits.check_trade_allowed(
            account_balance=broker.balance,
            proposed_risk_dollars=proposed_risk_dollars,
            current_open_positions=current_open_positions,
            state_file=PAIRS_RISK_STATE_FILE,
        )
        if not allowed:
            print(f"TRADE BLOCKED BY RISK LIMITS: {reason}")
            save_state(state)
            sys.exit()
        # --- END RISK CHECK ---

        broker.place_order(SYMBOL_NQ, direction_nq, current_nq_price, stop_price=None,
                            target_price=None, entry_date=str(today))
        broker.place_order(SYMBOL_ES, direction_es, current_es_price, stop_price=None,
                            target_price=None, entry_date=str(today))

        state["position"] = {
            "direction_nq": direction_nq, "entry_date": str(today), "entry_z": current_z,
            "contracts_nq": contracts_nq, "contracts_es": contracts_es,
        }
        print(f"OPENED: {direction_nq} {contracts_nq}x MNQ / {direction_es} {contracts_es}x MES "
              f"(z-score {current_z:.2f}, proposed risk ${proposed_risk_dollars:,.2f})")
    else:
        print(f"No signal - z-score {current_z:.2f} within normal range.")
else:
    direction = state["position"]["direction_nq"]
    entry_z = state["position"]["entry_z"]
    contracts_nq = state["position"].get("contracts_nq", 1)
    contracts_es = state["position"].get("contracts_es", 1)
    reverted = (direction == "SHORT" and current_z <= 0.5) or (direction == "LONG" and current_z >= -0.5)
    hit_z_stop = (direction == "SHORT" and current_z >= STOP_Z) or (direction == "LONG" and current_z <= -STOP_Z)

    entry_date_str = state["position"]["entry_date"]
    days_held = None
    try:
        idx_list = list(merged.index)
        days_held = idx_list.index(today) - idx_list.index(date.fromisoformat(entry_date_str))
    except ValueError:
        pass  # entry date has rolled out of the lookback window - skip the time-stop check this run
    hit_time_stop = days_held is not None and days_held >= MAX_HOLD_DAYS

    exit_reason = None
    if reverted:
        exit_reason = "reverted"
    elif hit_z_stop:
        exit_reason = "z_stop"
    elif hit_time_stop:
        exit_reason = "time_stop"

    if exit_reason:
        # Find this pair's two open legs by their tagged symbol + entry date.
        nq_leg = next(p for p in broker.positions if p["symbol"] == SYMBOL_NQ and p["entry_date"] == entry_date_str)
        es_leg = next(p for p in broker.positions if p["symbol"] == SYMBOL_ES and p["entry_date"] == entry_date_str)

        # point_value * contracts is the same adapter trick used elsewhere in this project to
        # represent an N-contract position through a single-contract-shaped function: PaperBroker
        # has no native "quantity" field, so scaling point_value by the contract count produces
        # the identical total dollar P&L as N separate 1-contract fills would.
        broker.close_position(nq_leg, current_nq_price, reason=exit_reason, point_value=POINT_VALUE_NQ * contracts_nq)
        broker.close_position(es_leg, current_es_price, reason=exit_reason, point_value=POINT_VALUE_ES * contracts_es)

        nq_points = (current_nq_price - nq_leg["entry_price"]) if nq_leg["direction"] == "LONG" else (nq_leg["entry_price"] - current_nq_price)
        es_points = (current_es_price - es_leg["entry_price"]) if es_leg["direction"] == "LONG" else (es_leg["entry_price"] - current_es_price)
        trade_pnl = nq_points * POINT_VALUE_NQ * contracts_nq + es_points * POINT_VALUE_ES * contracts_es
        risk_limits.record_trade_result(trade_pnl, state_file=PAIRS_RISK_STATE_FILE)

        print(f"Position CLOSED ({exit_reason}): entered z={entry_z:.2f}, now z={current_z:.2f}, "
              f"trade P&L ${trade_pnl:+,.2f}, balance now ${broker.balance:,.2f}")
        state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z,
                                   "exit_reason": exit_reason, "trade_pnl": trade_pnl})
        state["position"] = None
    else:
        held_str = f", held {days_held}d" if days_held is not None else ""
        print(f"Position still open: {direction} from {entry_date_str} "
              f"(entry z={entry_z:.2f}, now z={current_z:.2f}{held_str})")

save_state(state)
