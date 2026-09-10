"""
Generates a local HTML status dashboard (results/dashboard.html) showing what the automated
forward-testing infrastructure is actually doing - the live paper-trading state of EVERY
currently-active track on this machine, plus an honest overall research status. Reads only local
JSON files already written by the various forward-test scripts; nothing here touches the network
or any external service.

Rewritten 2026-09-10 (Entry 32), SECOND TIME - the previous rewrite (Entry 31, commit bbac614)
wrongly dropped Fade, Trend, and the pairs book from this dashboard based on misleading mtimes seen
through a mounted filesystem view, not their actual content. All of those are genuinely active,
pre-existing, independently-automated strategies that predate this dashboard's original build and
were never abandoned. This version restores them and adds the two new gap/volume-confirmed
open/resolve tracks (also Entry 32) alongside everything already here. See research_log.md Entry 32
for the full incident writeup.

Regenerated automatically each weekday evening by the existing com.nqresearch.dashboard launchd job
(now pointed at this file - see Entry 32), after all of the day's resolve jobs have run. Also safe
to run manually anytime:

    cd ~/nq-research && python3 src/generate_dashboard.py

then open results/dashboard.html in a browser.
"""
import json
import os
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

STARTING_BALANCE = 10000


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def account_summary(state, starting_balance=STARTING_BALANCE):
    if state is None:
        return None
    trades = state.get("trade_history", [])
    wins = sum(1 for t in trades if t.get("points_result", 0) > 0)
    losses = sum(1 for t in trades if t.get("points_result", 0) < 0)
    total_pnl = state.get("balance", starting_balance) - starting_balance
    return {
        "balance": state.get("balance", starting_balance),
        "total_pnl": total_pnl,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / len(trades) * 100) if trades else 0,
        "open_positions": len(state.get("positions", [])),
        "last_trade": trades[-1] if trades else None,
    }


def colorval(v, prefix="$"):
    sign = "+" if v > 0 else ""
    cls = "pos" if v > 0 else ("neg" if v < 0 else "neu")
    return f'<span class="{cls}">{sign}{prefix}{v:,.2f}</span>'


def panel(title, rows, accent="#2fa8ff", subtitle=None, warning=None):
    row_html = "".join(
        f'<div class="row"><span class="label">{k}</span><span class="value">{v}</span></div>'
        for k, v in rows
    )
    sub_html = f'<div class="panel-sub">{subtitle}</div>' if subtitle else ""
    warn_html = f'<div class="panel-warning">&#9888; {warning}</div>' if warning else ""
    return f"""
    <div class="panel">
        <div class="panel-header" style="border-left: 3px solid {accent};">{title}{sub_html}</div>
        <div class="panel-body">{row_html}{warn_html}</div>
    </div>
    """


def live_panel(title, path, accent, note=None, warning=None):
    s = account_summary(load_json(path))
    if s is None:
        return panel(title, [("STATUS", '<span class="neu">not yet run</span>')], accent=accent, subtitle=note, warning=warning)
    last = s["last_trade"]
    if not last:
        last_str = "none yet"
    else:
        last_str = (f'{last.get("entry_date", "?")} {last.get("direction", "")} '
                    f'{last.get("reason", "")} ({last.get("points_result", 0):+.1f}pt)')
    return panel(title, [
        ("BALANCE", f'{colorval(s["total_pnl"])} <span class="neu">(${s["balance"]:,.2f})</span>'),
        ("LIVE TRADES", s["trades"]),
        ("RECORD", f'{s["wins"]}W - {s["losses"]}L' if s["trades"] else "-"),
        ("OPEN POSITIONS", s["open_positions"]),
        ("LAST TRADE", last_str),
    ], accent=accent, subtitle=note, warning=warning)


def trend_panel():
    """Trend (Entry 6) is explicitly RETIRED - trend_forward_daily.py's STRATEGY_RETIRED guard
    blocks new entries, but still runs to manage/close whatever was already open at retirement.
    Shown here with its own layout since its state file has no PaperBroker-style balance/history -
    just a raw points-based trade_history and a possible open position."""
    state = load_json("data/trend_forward_state.json")
    if state is None:
        return panel("TREND FOLLOWING // RETIRED", [("STATUS", '<span class="neu">not yet run</span>')],
                      accent="#6b7280", subtitle="Entry 6 - regime-dependent, not durable")

    trades = state.get("trade_history", [])
    total_points = sum(t.get("points", 0) for t in trades)
    position = state.get("position")
    last_run = state.get("last_run_date", "?")

    rows = [
        ("STATUS", '<span class="neu">RETIRED - manage-only, no new entries</span>'),
        ("CLOSED TRADES", f"{len(trades)} ({total_points:+.1f}pt total)" if trades else "0"),
    ]
    warning = None
    if position:
        rows.append(("OPEN POSITION", f'{position.get("direction","?")} from {position.get("entry_date","?")} '
                                       f'@ {position.get("entry_price","?")} (stop {position.get("stop_price","?")})'))
        # Flag if the daily manage job hasn't actually run recently while a position is still open -
        # a retired strategy with an unmanaged open position is a real risk (no one is watching the
        # stop), not just a stale-data curiosity.
        try:
            days_stale = (datetime.now().date() - datetime.strptime(last_run, "%Y-%m-%d").date()).days
            if days_stale >= 2:
                warning = (f"Open position but last managed {last_run} ({days_stale} days ago) - "
                           f"this job should be running daily. Check com.nqresearch.trendforward.")
        except Exception:
            pass
    else:
        rows.append(("OPEN POSITION", "none"))
    rows.append(("LAST MANAGED", last_run))

    return panel("TREND FOLLOWING // RETIRED", rows, accent="#6b7280",
                 subtitle="Entry 6 - regime-dependent, not durable; manage-only", warning=warning)


def pairs_leg_panel(title, state_path, account_path, accent, note):
    """NQ/ES, NQ/YM, and ES/YM (Entries 9/13/23/24) share ONE PaperBroker account file
    (data/pairs_paper_account.json) across all three pairs, with legs tagged uniquely
    (e.g. 'MNQ (NQ/YM)') so closes can't cross-match the wrong pair. This panel shows this specific
    pair's own z-score/position state, plus that shared account's overall figures for context."""
    state = load_json(state_path)
    account = load_json(account_path)
    warning = None

    if state is None:
        return panel(title, [("STATUS", '<span class="neu">not yet run</span>')], accent=accent, subtitle=note)

    position = state.get("position")
    history = state.get("history", [])
    last_run = state.get("last_run_date", "?")

    rows = []
    if position:
        rows.append(("OPEN POSITION", f'{position.get("direction_a","?")} entered {position.get("entry_date","?")} '
                                       f'(entry z {position.get("entry_z", 0):.2f})'))
        if account is None:
            warning = (f"State shows an open position since {position.get('entry_date','?')} but "
                       f"data/pairs_paper_account.json doesn't exist - this position predates the "
                       f"broker/risk wiring (Entry 24, deployed 2026-09-10) and was never recorded "
                       f"to a PaperBroker account. It will be closed out of state with no P&L "
                       f"recorded (not fabricated) when its exit condition triggers - see Entry 32. "
                       f"No action needed, just flagging so this isn't mistaken for live capital at "
                       f"risk with no record.")
    else:
        rows.append(("OPEN POSITION", "none"))

    closed_here = [h for h in history]
    if closed_here:
        realized = [h.get("trade_pnl") for h in closed_here if h.get("trade_pnl") is not None]
        orphaned_ct = sum(1 for h in closed_here if h.get("orphaned_no_broker_record"))
        rows.append(("CLOSED TRADES (this pair)", f"{len(closed_here)}" + (f", {orphaned_ct} unrecorded (pre-broker)" if orphaned_ct else "")))
        if realized:
            rows.append(("REALIZED P&L (this pair)", colorval(sum(realized))))
    else:
        rows.append(("CLOSED TRADES (this pair)", "0"))
    rows.append(("LAST CHECKED", last_run))

    return panel(title, rows, accent=accent, subtitle=note, warning=warning)


def build_equity_curve():
    def load_trades(filepath):
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r") as f:
            state = json.load(f)
        return state.get("trade_history", [])

    def curve(trades, default_point_value):
        balance = STARTING_BALANCE
        balances = [balance]
        for t in trades:
            points = t.get("points_result", 0)
            # Use each trade's own recorded point_value_used when present. Older trade records
            # (e.g. Fade's, written before this field existed) don't have it - fall back to that
            # track's own actual contract size (passed in per-track below), NOT a single global
            # guess, since Fade trades full-size NQ (20/pt) while the gap tracks trade MNQ (2/pt) -
            # a shared default would silently mis-scale whichever one didn't match it.
            point_value = t.get("point_value_used", default_point_value)
            balance += points * point_value
            balances.append(balance)
        return balances

    tracks = [
        ("data/gap_paper_account.json", "GAP (unfiltered)", "#ffb020", 2),
        ("data/volume_gap_1_2x_paper_account.json", "VOL-CONFIRMED 1.2x", "#00e5a0", 2),
        ("data/volume_gap_1_5x_paper_account.json", "VOL-CONFIRMED 1.5x", "#2fa8ff", 2),
        ("data/fade_paper_account.json", "FADE", "#ff8fd6", 20),
        ("data/pairs_paper_account.json", "PAIRS BOOK (all 3)", "#c86bff", 2),
    ]

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 4.5), facecolor="#0a0e14")
    ax.set_facecolor("#0a0e14")

    plotted = False
    for path, label, color, default_pv in tracks:
        trades = load_trades(path)
        if trades:
            ax.plot(curve(trades, default_pv), color=color, linewidth=1.8, marker="o", markersize=3, label=label)
            plotted = True

    ax.axhline(y=STARTING_BALANCE, color="#555b66", linestyle="--", linewidth=1)
    ax.set_xlabel("TRADE #", color="#8b909c", fontsize=9, fontfamily="monospace")
    ax.set_ylabel("BALANCE ($)", color="#8b909c", fontsize=9, fontfamily="monospace")
    ax.tick_params(colors="#8b909c", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#2a2e39")
    ax.grid(True, alpha=0.15, color="#8b909c")
    if plotted:
        ax.legend(facecolor="#131722", edgecolor="#2a2e39", labelcolor="#e6e9ef", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No live trades yet", color="#6b7280", fontsize=12,
                ha="center", va="center", transform=ax.transAxes)
    plt.tight_layout()

    os.makedirs("results", exist_ok=True)
    img_path = "results/equity_curve.png"
    plt.savefig(img_path, dpi=140, facecolor="#0a0e14")
    plt.close()

    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


equity_curve_b64 = build_equity_curve()

panels = []
panels.append(live_panel(
    "GAP CONTINUATION (unfiltered) // LIVE", "data/gap_paper_account.json", "#ffb020",
    note="Entry 16/21 - open/resolve split 2026-09-10 (Entry 32) - automated"
))
panels.append(live_panel(
    "VOLUME-CONFIRMED GAP 1.2x // LIVE", "data/volume_gap_1_2x_paper_account.json", "#00e5a0",
    note="Entry 25 - full-sample-hindsight threshold - automated"
))
panels.append(live_panel(
    "VOLUME-CONFIRMED GAP 1.5x // LIVE", "data/volume_gap_1_5x_paper_account.json", "#2fa8ff",
    note="Entry 27 Part 5 - honest out-of-time threshold - automated"
))
panels.append(live_panel(
    "FADE (prior-day break) // LIVE", "data/fade_paper_account.json", "#ff8fd6",
    note="Entry 2 - full-size NQ - automated"
))
panels.append(trend_panel())
panels.append(pairs_leg_panel(
    "PAIRS: NQ/ES // LIVE", "data/pairs_forward_state.json", "data/pairs_paper_account.json",
    "#c86bff", note="Entry 9/13/23/24"
))
panels.append(pairs_leg_panel(
    "PAIRS: NQ/YM // LIVE", "data/pairs_nqym_forward_state.json", "data/pairs_paper_account.json",
    "#c86bff", note="Entry 13/23/24"
))
panels.append(pairs_leg_panel(
    "PAIRS: ES/YM // LIVE", "data/pairs_esym_forward_state.json", "data/pairs_paper_account.json",
    "#c86bff", note="Entry 13/23/24"
))

honest_assessment = """
<strong style="color:#00e5a0;">Flagship candidate:</strong> Volume-Confirmed Gap Continuation
(Entries 25/27) &mdash; the only strategy to pass all 6 standardized scorecard checks, and the
only one to survive a confound check, a fine threshold sweep, lookback-robustness, AND an honest
out-of-time threshold selection test. Live forward-testing at both the 1.2x and 1.5x thresholds,
automated daily. Backtest net PF 1.39 (1.2x, 132 trades).<br><br>
<strong style="color:#c86bff;">Strong second contender:</strong> Pairs book (NQ/ES, NQ/YM, ES/YM)
&mdash; higher raw backtest net profit factors (1.76-2.33) but on a thinner, less-scrutinized
sample (37-39 trades each, below the 100-trade bar). Has actually been running live since
~2026-09-03 (Entry 24's risk wiring), earlier than previously tracked here.<br><br>
<strong style="color:#ffb020;">Also tracked live:</strong> unfiltered Gap Continuation
(Entry 16/21) &mdash; real edge, but net-of-cost PF (1.17) falls short of the 1.3 bar &mdash; and
Fade (Entry 2), running since early in this project.<br><br>
<strong style="color:#6b7280;">Retired:</strong> Trend Following (Entry 6) &mdash; regime-dependent,
not durable. No new entries; still manages any position open at retirement.<br><br>
<strong style="color:#ff5c5c;">Rejected:</strong> Crude Oil Gap (Entry 22, outlier-dependent),
Gold Gap (Entry 26, no edge), Relative Momentum Rotation (Entry 19, no edge).<br><br>
<strong style="color:#ff5c5c;">Bottom line:</strong> Nothing here has been validated for real
capital. Backtest evidence and live forward-validation are deliberately treated as two separate
bars in this project - live trade counts are still early across every track, nowhere near the
roughly 20-30 trade threshold this project uses before that conversation is even on the table.
"""

html = f"""
<html>
<head>
<title>NQ RESEARCH // TERMINAL</title>
<style>
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
        background: #0a0e14;
        color: #e6e9ef;
        margin: 0;
        padding: 24px 32px;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        border-bottom: 1px solid #2a2e39;
        padding-bottom: 14px;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .header h1 {{
        margin: 0;
        font-size: 20px;
        letter-spacing: 2px;
        color: #00e5a0;
        text-shadow: 0 0 8px rgba(0,229,160,0.4);
    }}
    .timestamp {{ color: #6b7280; font-size: 12px; letter-spacing: 1px; }}
    .chart-panel {{
        background: #10141c;
        border: 1px solid #2a2e39;
        padding: 12px;
    }}
    .chart-panel img {{ width: 100%; display: block; }}
    .chart-title {{
        font-size: 11px; letter-spacing: 2px; color: #8b909c; margin-bottom: 8px;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 14px;
        margin-bottom: 20px;
    }}
    .panel {{
        background: #10141c;
        border: 1px solid #2a2e39;
    }}
    .panel-header {{
        padding: 10px 14px;
        font-size: 11px;
        letter-spacing: 1.5px;
        color: #cfd3dc;
        background: #131722;
    }}
    .panel-sub {{ font-size: 9px; color: #6b7280; letter-spacing: 0.5px; margin-top: 2px; }}
    .panel-body {{ padding: 10px 14px; }}
    .row {{
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #1a1e28;
        font-size: 13px;
        gap: 10px;
    }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: #6b7280; letter-spacing: 0.5px; flex-shrink: 0; }}
    .value {{ font-weight: 600; text-align: right; }}
    .pos {{ color: #00e5a0; }}
    .neg {{ color: #ff5c5c; }}
    .neu {{ color: #cfd3dc; }}
    .panel-warning {{
        margin-top: 8px;
        padding: 8px 10px;
        background: rgba(255, 176, 32, 0.1);
        border: 1px solid rgba(255, 176, 32, 0.35);
        color: #ffb020;
        font-size: 11px;
        line-height: 1.5;
    }}
</style>
</head>
<body>
    <div class="header">
        <h1>NQ RESEARCH TERMINAL</h1>
        <div class="timestamp">LAST UPDATE: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>

    <div class="chart-panel" style="margin-bottom: 20px;">
        <div class="chart-title">RESEARCH STATUS — HONEST ASSESSMENT</div>
        <div style="font-size: 13px; line-height: 1.6; color: #cfd3dc;">{honest_assessment}</div>
    </div>

    <div class="grid">
        {"".join(panels)}
    </div>

    <div class="chart-panel">
        <div class="chart-title">EQUITY CURVE — LIVE PAPER / FORWARD ACCOUNTS</div>
        <img src="data:image/png;base64,{equity_curve_b64}" />
    </div>
</body>
</html>
"""

os.makedirs("results", exist_ok=True)
output_path = os.path.abspath("results/dashboard.html")
with open(output_path, "w") as f:
    f.write(html)

print(f"Dashboard saved to {output_path}")
