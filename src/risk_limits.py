import json
import os
from datetime import date

RISK_STATE_FILE = "data/risk_limits_state.json"

MAX_RISK_PER_TRADE_PCT = 2.0
MAX_DAILY_LOSS_PCT = 5.0
MAX_OPEN_POSITIONS = 3
MAX_DRAWDOWN_HALT_PCT = 20.0

def load_risk_state(state_file=None):
    path = state_file or RISK_STATE_FILE
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {
        "peak_balance": None,
        "daily_loss_tracker": {},
        "trading_halted": False,
        "halt_reason": None
    }

def save_risk_state(state, state_file=None):
    path = state_file or RISK_STATE_FILE
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def check_trade_allowed(account_balance, proposed_risk_dollars, current_open_positions, state_file=None):
    """state_file lets a strategy family track its own halt/drawdown/daily-loss state separately
    from the default (used by gap_forward_check.py) instead of sharing one global circuit breaker
    across unrelated paper accounts - added 2026-09-10 when wiring in the pairs book, so pairs'
    drawdown tracking is judged against the pairs book's own equity curve, not silently mixed with
    the gap strategy's. Leave as None for the original single-account behavior (unchanged for any
    existing caller that doesn't pass it)."""
    state = load_risk_state(state_file)

    if state["trading_halted"]:
        return False, f"TRADING HALTED: {state['halt_reason']}"

    if state["peak_balance"] is None or account_balance > state["peak_balance"]:
        state["peak_balance"] = account_balance
        save_risk_state(state, state_file)

    drawdown_pct = ((state["peak_balance"] - account_balance) / state["peak_balance"]) * 100 if state["peak_balance"] else 0
    if drawdown_pct >= MAX_DRAWDOWN_HALT_PCT:
        state["trading_halted"] = True
        state["halt_reason"] = f"Drawdown {drawdown_pct:.1f}% exceeded halt threshold of {MAX_DRAWDOWN_HALT_PCT}%"
        save_risk_state(state, state_file)
        return False, state["halt_reason"]

    risk_pct = (proposed_risk_dollars / account_balance) * 100
    if risk_pct > MAX_RISK_PER_TRADE_PCT:
        return False, f"Proposed risk {risk_pct:.2f}% exceeds max per-trade risk of {MAX_RISK_PER_TRADE_PCT}%"

    if current_open_positions >= MAX_OPEN_POSITIONS:
        return False, f"Already at max open positions ({MAX_OPEN_POSITIONS})"

    today_str = str(date.today())
    today_loss = state["daily_loss_tracker"].get(today_str, 0)
    today_loss_pct = (abs(today_loss) / account_balance) * 100 if today_loss < 0 else 0
    if today_loss_pct >= MAX_DAILY_LOSS_PCT:
        return False, f"Daily loss limit reached ({today_loss_pct:.2f}% of account today)"

    return True, "OK"


def record_trade_result(pnl_dollars, state_file=None):
    state = load_risk_state(state_file)
    today_str = str(date.today())
    state["daily_loss_tracker"][today_str] = state["daily_loss_tracker"].get(today_str, 0) + pnl_dollars
    save_risk_state(state, state_file)


def manual_reset_halt(state_file=None):
    state = load_risk_state(state_file)
    state["trading_halted"] = False
    state["halt_reason"] = None
    save_risk_state(state, state_file)
    print("Trading halt manually cleared.")
