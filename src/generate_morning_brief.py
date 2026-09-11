"""
Generates a short daily HTML brief (results/morning_brief.html) - what resolved overnight, what
opened this morning, what's still open from before, and a one-line readiness snapshot - so there's
something to read in 30 seconds instead of opening the full dashboard cold every morning
(research_log.md Entry 33, requested directly by the user).

Reuses src/portfolio_analytics.py for the combined P&L/risk figures shown here - this file is
presentation only, same relationship generate_dashboard.py has to that module.

Meant to run once each weekday morning, AFTER the morning open-side jobs (com.nqresearch.gapforward
5:37 AM, fadepapercheck 5:36 AM, volumegapcheck 5:38 AM) but before the afternoon jobs
(trendforward/pairsforward/genericpairs, ~14:15-14:25 PM) - so Trend and the pairs book are
reported "as of last check" (yesterday afternoon), not "as of this morning", and that's called out
explicitly rather than implied to be current. Safe to run manually anytime:

    cd ~/nq-research && python3 src/generate_morning_brief.py
"""
import json
import os
import subprocess
from datetime import date, timedelta, datetime
import portfolio_analytics as pa

STARTING_BALANCE = 10000
today = date.today()
yesterday = today - timedelta(days=1)


def notify(title, message):
    """Best-effort macOS notification - never lets a notification failure break the run."""
    try:
        safe_message = message.replace('"', '\\"').replace("\\", "\\\\")
        safe_title = title.replace('"', '\\"').replace("\\", "\\\\")
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
            timeout=10, check=False
        )
    except Exception as e:
        print(f"(notification failed, non-fatal: {e})")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def resolved_yesterday():
    """Full round-trip trades (entry_date == yesterday) - these tracks open and resolve same-day
    by design, so a trade dated yesterday is a completed, known outcome."""
    rows = []
    for acct in pa.BROKER_ACCOUNTS:
        state = load_json(acct["path"])
        if not state:
            continue
        for t in state.get("trade_history", []):
            if t.get("entry_date") == str(yesterday):
                pv = t.get("point_value_used", acct["default_point_value"])
                dollars = t.get("points_result", 0) * pv
                rows.append({
                    "strategy": acct["label"], "direction": t.get("direction"),
                    "reason": t.get("reason"), "points": t.get("points_result", 0),
                    "dollars": dollars,
                })
    return rows


def opened_this_morning():
    """Currently-open positions with entry_date == today - opened by this morning's jobs, not
    yet resolved (resolve jobs run after market close)."""
    rows = []
    for acct in pa.BROKER_ACCOUNTS:
        state = load_json(acct["path"])
        if not state:
            continue
        for p in state.get("positions", []):
            if p.get("entry_date") == str(today):
                rows.append({
                    "strategy": acct["label"], "direction": p.get("direction"),
                    "symbol": p.get("symbol"), "entry_price": p.get("entry_price"),
                    "stop_price": p.get("stop_price"), "target_price": p.get("target_price"),
                })
    return rows


def carried_over_positions():
    """Open positions NOT opened today - i.e. genuinely still open from a prior day (Trend's
    known-stale position, or a pairs position mid-hold)."""
    rows = []
    for acct in pa.BROKER_ACCOUNTS:
        state = load_json(acct["path"])
        if not state:
            continue
        for p in state.get("positions", []):
            if p.get("entry_date") != str(today):
                rows.append({"strategy": acct["label"], "direction": p.get("direction"),
                             "symbol": p.get("symbol"), "since": p.get("entry_date")})

    trend = load_json(pa.TREND_STATE_FILE)
    if trend and trend.get("position"):
        pos = trend["position"]
        rows.append({"strategy": "Trend (retired)", "direction": pos.get("direction"),
                     "symbol": "NQ", "since": pos.get("entry_date")})

    for pair_label, meta in pa.PAIRS_META.items():
        state = load_json(meta["state_file"])
        if state and state.get("position"):
            pos = state["position"]
            rows.append({"strategy": f"Pairs: {pair_label}", "direction": pos.get("direction_a"),
                         "symbol": pair_label, "since": pos.get("entry_date")})
    return rows


def afternoon_tracks_last_check():
    """Trend + all 3 pairs run in the afternoon (~14:15-14:25 PT), after this brief - so their
    status here is only as fresh as their last actual run, called out explicitly."""
    rows = []
    trend = load_json(pa.TREND_STATE_FILE)
    if trend:
        rows.append({"label": "Trend (retired)", "last_run": trend.get("last_run_date", "?"),
                     "status": "position open" if trend.get("position") else "flat"})
    for pair_label, meta in pa.PAIRS_META.items():
        state = load_json(meta["state_file"])
        if state:
            rows.append({"label": f"Pairs: {pair_label}", "last_run": state.get("last_run_date", "?"),
                         "status": "position open" if state.get("position") else "flat"})
    return rows


resolved = resolved_yesterday()
opened = opened_this_morning()
carried = carried_over_positions()
afternoon = afternoon_tracks_last_check()
book = pa.combined_book_summary()
risk = pa.aggregate_open_risk()
readiness = pa.readiness_scorecard()

# --- Best-effort notification, one line, non-fatal ---
resolved_pnl = sum(r["dollars"] for r in resolved)
notif_bits = []
if resolved:
    notif_bits.append(f"{len(resolved)} resolved yesterday ({resolved_pnl:+,.0f})")
if opened:
    notif_bits.append(f"{len(opened)} opened this morning")
if not notif_bits:
    notif_bits.append("no new activity")
notify("NQ Research — Morning Brief", ", ".join(notif_bits) + f" | book {book['total_pnl']:+,.0f}")


def row_html(strategy, detail):
    return f'<div class="brief-row"><span class="brief-strategy">{strategy}</span><span class="brief-detail">{detail}</span></div>'


resolved_html = "".join(
    row_html(r["strategy"], f'{r["direction"]} {r["reason"]} — <span class="{"pos" if r["dollars"]>=0 else "neg"}">{r["points"]:+.1f}pt (${r["dollars"]:+,.2f})</span>')
    for r in resolved
) or '<div class="brief-empty">No trades resolved yesterday.</div>'

opened_html = "".join(
    row_html(o["strategy"], f'{o["direction"]} {o["symbol"]} @ {o["entry_price"]} (stop {o["stop_price"]}, target {o["target_price"] or "n/a - z-score exit"})')
    for o in opened
) or '<div class="brief-empty">Nothing opened yet this morning.</div>'

carried_html = "".join(
    row_html(c["strategy"], f'{c["direction"]} {c["symbol"]} — open since {c["since"]}')
    for c in carried
) or '<div class="brief-empty">Nothing carried over — everything else is flat.</div>'

afternoon_html = "".join(
    row_html(a["label"], f'{a["status"]}, last checked {a["last_run"]}')
    for a in afternoon
)

readiness_html = "".join(
    f'<div class="brief-row"><span class="brief-strategy">{r["label"]}</span>'
    f'<span class="brief-detail">{r["trades"]}/{r["target"]} trades ({r["pct"]}%)</span></div>'
    for r in readiness
)

risk_note = ""
if risk["unknown_risk_positions"]:
    risk_note = (f'<div class="brief-warning">&#9888; {", ".join(risk["unknown_risk_positions"])} has open '
                 f'exposure with no recorded sizing (see dashboard) — not included in the risk total below.</div>')

html = f"""
<html>
<head>
<title>NQ RESEARCH // MORNING BRIEF</title>
<style>
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
        background: #0a0e14;
        color: #e6e9ef;
        margin: 0;
        padding: 24px 32px;
        max-width: 720px;
    }}
    h1 {{
        margin: 0 0 4px 0;
        font-size: 18px;
        letter-spacing: 2px;
        color: #00e5a0;
        text-shadow: 0 0 8px rgba(0,229,160,0.4);
    }}
    .timestamp {{ color: #6b7280; font-size: 11px; letter-spacing: 1px; margin-bottom: 20px; }}
    .section {{
        background: #10141c;
        border: 1px solid #2a2e39;
        margin-bottom: 14px;
    }}
    .section-title {{
        padding: 8px 14px;
        font-size: 10px;
        letter-spacing: 1.5px;
        color: #8b909c;
        background: #131722;
    }}
    .brief-row {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        padding: 7px 14px;
        border-bottom: 1px solid #1a1e28;
        font-size: 12px;
    }}
    .brief-row:last-child {{ border-bottom: none; }}
    .brief-strategy {{ color: #cfd3dc; flex-shrink: 0; }}
    .brief-detail {{ color: #8b909c; text-align: right; }}
    .brief-empty {{ padding: 10px 14px; color: #555b66; font-size: 12px; font-style: italic; }}
    .pos {{ color: #00e5a0; }}
    .neg {{ color: #ff5c5c; }}
    .brief-warning {{
        margin: 8px 14px 12px 14px;
        padding: 8px 10px;
        background: rgba(255, 176, 32, 0.1);
        border: 1px solid rgba(255, 176, 32, 0.35);
        color: #ffb020;
        font-size: 11px;
        line-height: 1.5;
    }}
    .headline {{
        font-size: 14px;
        padding: 12px 14px;
        color: #cfd3dc;
    }}
</style>
</head>
<body>
    <h1>MORNING BRIEF</h1>
    <div class="timestamp">{today.strftime("%A, %B %d %Y")} — generated {datetime.now().strftime("%H:%M:%S")}</div>

    <div class="section">
        <div class="headline">
            Combined book: <span class="{'pos' if book['total_pnl']>=0 else 'neg'}">{book['total_pnl']:+,.2f}</span>
            (${book['total_balance']:,.2f} of ${book['total_starting']:,.0f}) —
            {book['total_trades']} live trades total, {book['total_open']} open right now.<br>
            Total $ at risk (priced positions): ${risk['total_dollars']:,.2f}
        </div>
        {risk_note}
    </div>

    <div class="section">
        <div class="section-title">RESOLVED YESTERDAY ({yesterday})</div>
        {resolved_html}
    </div>

    <div class="section">
        <div class="section-title">OPENED THIS MORNING ({today})</div>
        {opened_html}
    </div>

    <div class="section">
        <div class="section-title">STILL OPEN FROM BEFORE</div>
        {carried_html}
    </div>

    <div class="section">
        <div class="section-title">AFTERNOON TRACKS (TREND / PAIRS) — AS OF LAST CHECK, NOT YET RUN TODAY</div>
        {afternoon_html}
    </div>

    <div class="section">
        <div class="section-title">READINESS SNAPSHOT (full detail on the dashboard)</div>
        {readiness_html}
    </div>
</body>
</html>
"""

os.makedirs("results", exist_ok=True)
output_path = os.path.abspath("results/morning_brief.html")
with open(output_path, "w") as f:
    f.write(html)

print(f"Morning brief saved to {output_path}")
