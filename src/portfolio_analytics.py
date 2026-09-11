"""
Cross-strategy analytics shared by generate_dashboard.py and generate_morning_brief.py
(research_log.md Entry 33). Everything here is read-only against existing state/account files -
nothing here places, sizes, or resolves a trade. Three things live here that no single
per-strategy script has any business computing on its own:

1. A combined "book" view - total P&L and a merged equity curve across every PaperBroker-backed
   account, since each one currently only knows about itself.
2. Aggregate open risk - how many dollars are actually exposed right now, summed across every
   strategy with an open position, including the pairs book (which sizes risk differently -
   see PAIRS_META below).
3. A live "readiness scorecard" - turns the project's own stated bar (roughly 20-30 live trades
   before a real-capital conversation is even on the table - see research_log.md, multiple
   entries) into an actual computed number per strategy instead of an estimate done by hand.

Deliberately does NOT compute a correlation coefficient between strategies - with single-digit-to-
low-teens live trade counts per track as of this writing, a Pearson correlation would be
statistical noise dressed up as a real number. See MIN_TRADES_FOR_CORRELATION below: once enough
overlapping trade-days exist, this can be added honestly.
"""
import json
import os
from datetime import date, datetime, timedelta

STARTING_BALANCE = 10000
READINESS_TARGET_TRADES = 25  # midpoint of this project's stated 20-30 trade bar
MIN_TRADES_FOR_CORRELATION = 15  # don't report a correlation number below this per strategy


# --- PaperBroker-backed accounts (each has its own balance/trade_history/positions) ---
# default_point_value is only used as a fallback for trade_history entries written before
# point_value_used existed (e.g. Fade's early trades) - see generate_dashboard.py's build_equity_curve.
BROKER_ACCOUNTS = [
    {"key": "gap", "label": "Gap (unfiltered)", "path": "data/gap_paper_account.json",
     "default_point_value": 2, "candidate": True,
     "backtest_note": "WATCH - net PF 1.17, below the 1.3 bar (Entry 21)"},
    {"key": "vol_1_2x", "label": "Vol-Confirmed 1.2x", "path": "data/volume_gap_1_2x_paper_account.json",
     "default_point_value": 2, "candidate": True,
     "backtest_note": "PASS - flagship candidate, net PF 1.39 (Entry 25)"},
    {"key": "vol_1_5x", "label": "Vol-Confirmed 1.5x", "path": "data/volume_gap_1_5x_paper_account.json",
     "default_point_value": 2, "candidate": True,
     "backtest_note": "PASS - honest out-of-time threshold (Entry 27 Part 5)"},
    {"key": "fade", "label": "Fade", "path": "data/fade_paper_account.json",
     "default_point_value": 20, "candidate": False,
     "backtest_note": "RETIRED 2026-09-11 (Entry 35) - re-run scorecard on full archive confirmed "
                       "the ORIGINAL Entry 2 FAIL still holds (0/5, PF 0.69, 102% max drawdown). "
                       "Was live for a week despite that original verdict - historical P&L kept "
                       "here for the record, but excluded from the readiness scorecard below."},
    {"key": "pairs", "label": "Pairs book (NQ/ES + NQ/YM + ES/YM, shared account)",
     "path": "data/pairs_paper_account.json", "default_point_value": 2, "candidate": True,
     "backtest_note": "PASS on all 3 legs - net PF 1.76-2.33, thinner sample (37-39 trades each, Entry 23)"},
]

# --- Pairs z-score trackers (state files, separate from the shared broker account above) ---
# Used only for per-pair trade counts (readiness) and open-position risk, since the shared
# pairs_paper_account.json can't tell NQ/ES's leg apart from ES/YM's on its own.
PAIRS_META = {
    "NQ/ES": {"state_file": "data/pairs_forward_state.json", "avg_loss_per_unit": 514.89},
    "NQ/YM": {"state_file": "data/pairs_nqym_forward_state.json", "avg_loss_per_unit": 981.80},
    "ES/YM": {"state_file": "data/pairs_esym_forward_state.json", "avg_loss_per_unit": 324.92},
}

# Trend is intentionally excluded from every dollar total below - it's RETIRED (Entry 6) and its
# trade_history has always been points-only, with no point_value ever established for it (it was
# built and killed before this project started sizing trades in real contracts). Showing a
# fabricated dollar figure for it would be worse than showing nothing.
TREND_STATE_FILE = "data/trend_forward_state.json"


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def combined_book_summary():
    """Sums current balance, total realized P&L, open-position count, and total closed-trade
    count across every PaperBroker-backed account. Accounts that don't exist yet (no live trade
    ever recorded) count as their untouched starting balance, same as an individual panel would."""
    total_balance = 0.0
    total_trades = 0
    total_open = 0
    per_account = []
    for acct in BROKER_ACCOUNTS:
        state = load_json(acct["path"])
        balance = state.get("balance", STARTING_BALANCE) if state else STARTING_BALANCE
        trades = len(state.get("trade_history", [])) if state else 0
        open_ct = len(state.get("positions", [])) if state else 0
        total_balance += balance
        total_trades += trades
        total_open += open_ct
        per_account.append({
            "label": acct["label"], "balance": balance,
            "pnl": balance - STARTING_BALANCE, "trades": trades, "open": open_ct,
        })
    return {
        "total_balance": total_balance,
        "total_starting": STARTING_BALANCE * len(BROKER_ACCOUNTS),
        "total_pnl": total_balance - STARTING_BALANCE * len(BROKER_ACCOUNTS),
        "total_trades": total_trades,
        "total_open": total_open,
        "per_account": per_account,
    }


def combined_equity_curve():
    """Merges every broker account's trade_history into one calendar-ordered series. Uses each
    trade's entry_date as the merge key (trade_history has no separate exit_date field) - exact
    for the gap/vol-confirmed/Fade tracks, which open and resolve same-day by design; an
    approximation for the pairs book, which can hold up to 15 days, but that account has no
    trades yet as of this writing so it doesn't currently matter. Returns a list of
    (date_str, cumulative_balance) points, starting capital included as the first point."""
    events = []  # (date, dollar_pnl)
    for acct in BROKER_ACCOUNTS:
        state = load_json(acct["path"])
        if not state:
            continue
        for t in state.get("trade_history", []):
            d = t.get("entry_date")
            if not d:
                continue
            pv = t.get("point_value_used", acct["default_point_value"])
            pnl = t.get("points_result", 0) * pv
            events.append((d, pnl))

    events.sort(key=lambda e: e[0])
    starting = STARTING_BALANCE * len(BROKER_ACCOUNTS)
    curve = [("start", starting)]
    running = starting
    for d, pnl in events:
        running += pnl
        curve.append((d, running))
    return curve


def combined_max_drawdown():
    """Peak-to-trough drawdown on the combined equity curve above, in dollars and as a percent
    of the combined starting capital."""
    curve = combined_equity_curve()
    balances = [b for _, b in curve]
    peak = balances[0]
    max_dd_dollars = 0.0
    for b in balances:
        peak = max(peak, b)
        dd = peak - b
        max_dd_dollars = max(max_dd_dollars, dd)
    starting = STARTING_BALANCE * len(BROKER_ACCOUNTS)
    return {"dollars": max_dd_dollars, "pct": (max_dd_dollars / starting * 100) if starting else 0}


def aggregate_open_risk():
    """Dollars actually at risk right now, summed across every open position in every strategy.
    Three different risk models are in play here, all pre-existing to this project:
      - Broker-backed tracks (gap/vol-confirmed/Fade/pairs legs already opened via place_order):
        (entry - stop) * point_value_used-if-known-else-account-default, per open leg.
      - Trend: has a price stop but no established point_value - reported in POINTS, not dollars,
        same reasoning as the exclusion above.
      - Pairs (z-score based, no price stop): uses each pair's own proposed_risk_dollars formula
        (contracts_a * avg_loss_per_unit) from the live scripts themselves, when contracts_a was
        recorded. The orphaned ES/YM position (Entry 32) has no contracts_a on record - flagged
        as unknown rather than guessed.
    """
    lines = []
    total_dollars = 0.0
    unknown_flags = []

    for acct in BROKER_ACCOUNTS:
        if acct["key"] == "pairs":
            continue  # pairs legs are risk-sized via PAIRS_META below, not per-leg price stops
        state = load_json(acct["path"])
        if not state:
            continue
        for p in state.get("positions", []):
            if p.get("stop_price") is None:
                continue
            pv = p.get("point_value_used", acct["default_point_value"])
            risk = abs(p["entry_price"] - p["stop_price"]) * pv
            total_dollars += risk
            lines.append({"label": acct["label"], "detail": f'{p["direction"]} {p["symbol"]}', "risk": risk})

    for pair_label, meta in PAIRS_META.items():
        state = load_json(meta["state_file"])
        if not state or not state.get("position"):
            continue
        pos = state["position"]
        contracts_a = pos.get("contracts_a")
        if contracts_a is None:
            unknown_flags.append(pair_label)
            continue
        risk = contracts_a * meta["avg_loss_per_unit"]
        total_dollars += risk
        lines.append({"label": f"Pairs: {pair_label}", "detail": f'{pos["direction_a"]} since {pos["entry_date"]}', "risk": risk})

    trend_state = load_json(TREND_STATE_FILE)
    trend_points_at_risk = None
    if trend_state and trend_state.get("position"):
        pos = trend_state["position"]
        trend_points_at_risk = abs(pos["entry_price"] - pos["stop_price"])

    return {
        "total_dollars": total_dollars,
        "lines": lines,
        "unknown_risk_positions": unknown_flags,  # pairs positions with no recorded sizing
        "trend_points_at_risk": trend_points_at_risk,  # None if no open Trend position
    }


def readiness_scorecard():
    """Per-strategy progress toward this project's own stated bar of ~20-30 live trades before a
    real-capital conversation is even on the table (uses 25 as the midpoint target). Pace is
    trades-so-far / days-since-first-live-trade - very rough with only a handful of trades so far,
    which is called out explicitly rather than presented as a confident estimate."""
    today = date.today()
    rows = []

    for acct in BROKER_ACCOUNTS:
        if acct["key"] == "pairs":
            continue  # pairs are scored per-leg below, using their own trade counts
        if not acct["candidate"]:
            continue  # retired/failed strategies (Fade, Entry 35) don't count toward the live-
                       # capital readiness bar - there's no scenario where more of their trades
                       # leads anywhere
        state = load_json(acct["path"])
        trades = state.get("trade_history", []) if state else []
        rows.append(_readiness_row(acct["label"], trades, acct["backtest_note"], today))

    for pair_label, meta in PAIRS_META.items():
        state = load_json(meta["state_file"])
        history = state.get("history", []) if state else []
        closed = [h for h in history if h.get("trade_pnl") is not None]  # excludes the Entry 32
                                                                          # orphaned-record case
        rows.append(_readiness_row(f"Pairs: {pair_label}", closed, "PASS - see Pairs book note above", today,
                                     date_key="entry_date"))

    return rows


def _readiness_row(label, trades, backtest_note, today, date_key="entry_date"):
    n = len(trades)
    pct = min(100, round(n / READINESS_TARGET_TRADES * 100))
    dates = [t.get(date_key) for t in trades if t.get(date_key)]
    eta_note = "no live trades yet"
    if dates:
        try:
            first = date.fromisoformat(min(dates))
            days_elapsed = max(1, (today - first).days)
            pace_per_day = n / days_elapsed
            if pace_per_day > 0 and n < READINESS_TARGET_TRADES:
                remaining = READINESS_TARGET_TRADES - n
                eta_days = remaining / pace_per_day
                eta_note = (f"~{eta_days:.0f} more days at current pace (rough - based on only "
                             f"{n} trade{'s' if n != 1 else ''} over {days_elapsed}d)")
            elif n >= READINESS_TARGET_TRADES:
                eta_note = "trade-count bar reached"
        except Exception:
            eta_note = "n/a"
    return {
        "label": label, "trades": n, "target": READINESS_TARGET_TRADES, "pct": pct,
        "eta_note": eta_note, "backtest_note": backtest_note,
    }


def diversification_notes():
    """Deliberately qualitative, not a computed correlation (see MIN_TRADES_FOR_CORRELATION at
    top of file) - every live track here has far too few trades yet for a statistically
    meaningful Pearson correlation. What CAN be said honestly right now:"""
    notes = [
        ("Gap (unfiltered) vs. Vol-Confirmed 1.2x/1.5x", "STRUCTURALLY RELATED, not diversifying",
         "Vol-Confirmed is a strict subset of Gap's own entry signal (same 08:30 gap, same "
         "direction) with an added volume filter - any day a Vol-Confirmed trade fires, the "
         "unfiltered Gap track fires the same trade too. Don't count these three as three "
         "independent bets."),
        ("Fade vs. everything else", "likely independent, unconfirmed",
         "Fade trades a break of yesterday's high/low, mechanically unrelated to the gap family "
         "or the pairs book's relative-value signal - plausibly a real diversifier, but with only "
         f"a handful of live trades there isn't yet enough data ({MIN_TRADES_FOR_CORRELATION}+ "
         "overlapping trade-days needed) to confirm that statistically."),
        ("Pairs book vs. everything else", "likely independent, unconfirmed",
         "Trades the NQ/ES/YM ratio, not any single market's direction - plausibly the best real "
         "diversifier in the book, but has no live trades yet to check against."),
    ]
    return notes
