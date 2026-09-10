import sys
import json
import os
import yfinance as yf
import pandas as pd
from datetime import date
from paper_broker import PaperBroker
from position_sizing import fixed_fractional_size
import risk_limits

LOOKBACK = 20
ENTRY_Z = 2.0
STOP_Z = 3.5        # matches get_generic_pairs_signals_from_archive()'s default in strategy.py -
                     # this is the stop that was actually backtested and produced the PF 1.97-2.25
                     # quoted for Entry 13 in research_log.md, not a fresh guess
MAX_HOLD_DAYS = 15   # same - matches the archive backtest's default, not a fresh guess

# --- Risk wiring added 2026-09-10 (research_log.md Entry 24) - same design as pairs_forward_check.py ---
PAIRS_ACCOUNT_FILE = "data/pairs_paper_account.json"          # shared across all 3 pairs scripts
PAIRS_RISK_STATE_FILE = "data/pairs_risk_limits_state.json"   # shared across all 3 pairs scripts,
                                                                # kept separate from gap_forward_check.py's
                                                                # risk_limits_state.json
PAIRS_STARTING_BALANCE = 10000  # placeholder paper-trading capital, same assumption as pairs_forward_check.py
RISK_PERCENT = risk_limits.MAX_RISK_PER_TRADE_PCT / 2  # half the hard cap, as a buffer against a
                                                          # single loss exceeding the historical average


def run_pairs_check(symbol_a, symbol_b, state_file, label, tag_a, tag_b,
                     point_value_a, point_value_b, avg_loss_per_unit):
    """tag_a/tag_b (e.g. 'MNQ (NQ/YM)') uniquely identify this pair's legs in the SHARED
    PAIRS_ACCOUNT_FILE, since NQ/YM and ES/YM (and pairs_forward_check.py's NQ/ES) can all have an
    open MNQ or MES leg on the same day - a plain symbol like 'MNQ' would collide and risk closing
    the wrong pair's leg. avg_loss_per_unit is that pair's average losing-trade size at 1x leg-A
    sizing from Entry 23's backtest - used as the position-sizing basis (see
    pairs_forward_check.py's AVG_LOSS_PER_UNIT_DOLLARS for the full explanation)."""
    def load_state():
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                return json.load(f)
        return {"position": None, "history": [], "last_run_date": None}

    def save_state(state):
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    state = load_state()
    today = date.today()

    if state.get("last_run_date") == str(today):
        print(f"[{label}] Already processed {today}. Skipping.")
        return
    state["last_run_date"] = str(today)

    a = yf.Ticker(symbol_a).history(period="60d", interval="1d")
    b = yf.Ticker(symbol_b).history(period="60d", interval="1d")

    if a.empty or b.empty:
        print(f"[{label}] WARNING: No data returned. Skipping this run.")
        save_state(state)
        return

    a = a[["Close"]].rename(columns={"Close": "close_a"})
    b = b[["Close"]].rename(columns={"Close": "close_b"})
    a.index = a.index.date
    b.index = b.index.date

    merged = a.join(b, how="inner")
    merged["ratio"] = merged["close_a"] / merged["close_b"]
    merged["ratio_mean"] = merged["ratio"].rolling(LOOKBACK).mean()
    merged["ratio_std"] = merged["ratio"].rolling(LOOKBACK).std()
    merged["zscore"] = (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]

    if str(today) not in [str(d) for d in merged.index]:
        print(f"[{label}] No data yet for {today}.")
        save_state(state)
        return

    current_z = merged.loc[merged.index == today, "zscore"].iloc[0]
    current_a_price = merged.loc[merged.index == today, "close_a"].iloc[0]
    current_b_price = merged.loc[merged.index == today, "close_b"].iloc[0]
    print(f"[{label}] Current z-score: {current_z:.2f}")

    broker = PaperBroker(starting_balance=PAIRS_STARTING_BALANCE, state_file=PAIRS_ACCOUNT_FILE)

    if state["position"] is None:
        if abs(current_z) > ENTRY_Z:
            direction_a = "SHORT" if current_z > ENTRY_Z else "LONG"
            direction_b = "LONG" if direction_a == "SHORT" else "SHORT"

            hedge_ratio = (current_a_price * point_value_a) / (current_b_price * point_value_b)
            contracts_a = max(1, round(fixed_fractional_size(
                PAIRS_STARTING_BALANCE, RISK_PERCENT, stop_points=1, point_value=avg_loss_per_unit
            )))
            contracts_b = max(1, round(contracts_a * hedge_ratio))

            # --- RISK CIRCUIT BREAKER CHECK, using the pairs book's own paper balance/state ---
            proposed_risk_dollars = contracts_a * avg_loss_per_unit
            current_open_positions = len(broker.positions)  # each leg = 1 slot, shared across all
                                                              # 3 pairs scripts - see
                                                              # pairs_forward_check.py for why
            allowed, reason = risk_limits.check_trade_allowed(
                account_balance=broker.balance,
                proposed_risk_dollars=proposed_risk_dollars,
                current_open_positions=current_open_positions,
                state_file=PAIRS_RISK_STATE_FILE,
            )
            if not allowed:
                print(f"[{label}] TRADE BLOCKED BY RISK LIMITS: {reason}")
                save_state(state)
                return
            # --- END RISK CHECK ---

            broker.place_order(tag_a, direction_a, current_a_price, stop_price=None,
                                target_price=None, entry_date=str(today))
            broker.place_order(tag_b, direction_b, current_b_price, stop_price=None,
                                target_price=None, entry_date=str(today))

            state["position"] = {
                "direction_a": direction_a, "entry_date": str(today), "entry_z": current_z,
                "contracts_a": contracts_a, "contracts_b": contracts_b,
            }
            print(f"[{label}] OPENED: {direction_a} {contracts_a}x {symbol_a} / "
                  f"{direction_b} {contracts_b}x {symbol_b} (z-score {current_z:.2f}, "
                  f"proposed risk ${proposed_risk_dollars:,.2f})")
        else:
            print(f"[{label}] No signal - z-score {current_z:.2f} within normal range.")
    else:
        direction = state["position"]["direction_a"]
        entry_z = state["position"]["entry_z"]
        contracts_a = state["position"].get("contracts_a", 1)
        contracts_b = state["position"].get("contracts_b", 1)
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
            a_leg = next(p for p in broker.positions if p["symbol"] == tag_a and p["entry_date"] == entry_date_str)
            b_leg = next(p for p in broker.positions if p["symbol"] == tag_b and p["entry_date"] == entry_date_str)

            broker.close_position(a_leg, current_a_price, reason=exit_reason, point_value=point_value_a * contracts_a)
            broker.close_position(b_leg, current_b_price, reason=exit_reason, point_value=point_value_b * contracts_b)

            a_points = (current_a_price - a_leg["entry_price"]) if a_leg["direction"] == "LONG" else (a_leg["entry_price"] - current_a_price)
            b_points = (current_b_price - b_leg["entry_price"]) if b_leg["direction"] == "LONG" else (b_leg["entry_price"] - current_b_price)
            trade_pnl = a_points * point_value_a * contracts_a + b_points * point_value_b * contracts_b
            risk_limits.record_trade_result(trade_pnl, state_file=PAIRS_RISK_STATE_FILE)

            print(f"[{label}] Position CLOSED ({exit_reason}): entered z={entry_z:.2f}, now z={current_z:.2f}, "
                  f"trade P&L ${trade_pnl:+,.2f}, balance now ${broker.balance:,.2f}")
            state["history"].append({**state["position"], "exit_date": str(today), "exit_z": current_z,
                                       "exit_reason": exit_reason, "trade_pnl": trade_pnl})
            state["position"] = None
        else:
            held_str = f", held {days_held}d" if days_held is not None else ""
            print(f"[{label}] Position still open: {direction} from {entry_date_str} "
                  f"(entry z={entry_z:.2f}, now z={current_z:.2f}{held_str})")

    save_state(state)


# Point values are micro contracts (MNQ/MES/MYM), matching pairs_scorecard_v2.py's Entry 23
# sizing. avg_loss_per_unit values are each pair's average losing-trade size at 1x leg-A sizing,
# taken directly from Entry 23's backtest (research_log.md).
run_pairs_check("NQ=F", "YM=F", "data/pairs_nqym_forward_state.json", "NQ/YM",
                tag_a="MNQ (NQ/YM)", tag_b="MYM (NQ/YM)",
                point_value_a=2.0, point_value_b=0.5, avg_loss_per_unit=981.80)
run_pairs_check("ES=F", "YM=F", "data/pairs_esym_forward_state.json", "ES/YM",
                tag_a="MES (ES/YM)", tag_b="MYM (ES/YM)",
                point_value_a=5.0, point_value_b=0.5, avg_loss_per_unit=324.92)
