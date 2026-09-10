"""
Generates a local HTML status dashboard (results/dashboard.html) showing what the automated
forward-testing infrastructure is actually doing - the live paper-trading state of every
currently-active track, plus an honest overall research status. Reads only local JSON files
already written by the forward-test scripts; nothing here touches the network or any external
service, consistent with keeping all of this local to this machine.

Regenerated automatically each weekday morning by run_forward_checks.py (right after the forward
checks run), so this file reflects the most recent state without a manual step. Also safe to run
manually anytime:

    cd ~/nq-research && python3 src/generate_dashboard.py

then open results/dashboard.html in a browser.

Rewritten 2026-09-10 (previously generate_dashboard.py/generate_dashboard_auto.py were exact
duplicates, both reading fade_paper_account.json/trend_forward_state.json/old-style
pairs_*_forward_state.json - all abandoned early-project files nothing currently writes to, none
of which reflect what's actually running now). generate_dashboard_auto.py was deleted as a dead,
unreferenced duplicate - see research_log.md Entry 31.

Active, automated tracks shown here: the unfiltered gap strategy (Entry 16/21) and the two
volume-confirmed gap thresholds (Entry 25's 1.2x, Entry 27 Part 5's honestly-selected 1.5x). The
pairs book (Entries 9/13/23) is shown separately as backtest-validated but NOT yet live -
data/pairs_paper_account.json doesn't exist yet for exactly that reason (Entry 24 wired its risk
management and unit-tested it, but it's never been run against real market data).

Also fixes a real scaling bug inherited from the old script: it used a flat multiplier=20
(full-size NQ) for every account's equity curve regardless of what was actually traded (MNQ at
point_value=2), which would have mis-scaled dollar figures by 10x. Each trade now uses its own
recorded point_value_used instead of a hardcoded constant.
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


def panel(title, rows, accent="#2fa8ff", subtitle=None):
    row_html = "".join(
        f'<div class="row"><span class="label">{k}</span><span class="value">{v}</span></div>'
        for k, v in rows
    )
    sub_html = f'<div class="panel-sub">{subtitle}</div>' if subtitle else ""
    return f"""
    <div class="panel">
        <div class="panel-header" style="border-left: 3px solid {accent};">{title}{sub_html}</div>
        <div class="panel-body">{row_html}</div>
    </div>
    """


def live_panel(title, path, accent, note=None):
    s = account_summary(load_json(path))
    if s is None:
        return panel(title, [("STATUS", '<span class="neu">not yet run</span>')], accent=accent, subtitle=note)
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
    ], accent=accent, subtitle=note)


def build_equity_curve():
    def load_trades(filepath):
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r") as f:
            state = json.load(f)
        return state.get("trade_history", [])

    def curve(trades):
        balance = STARTING_BALANCE
        balances = [balance]
        for t in trades:
            points = t.get("points_result", 0)
            # Use each trade's OWN recorded point_value_used, not a flat constant - the old
            # dashboard hardcoded multiplier=20 (full NQ) even for MNQ trades (point_value=2),
            # which would have overstated every one of these balances by 10x.
            point_value = t.get("point_value_used", 2)
            balance += points * point_value
            balances.append(balance)
        return balances

    tracks = [
        ("data/gap_paper_account.json", "GAP (unfiltered)", "#ffb020"),
        ("data/volume_gap_1_2x_paper_account.json", "VOL-CONFIRMED 1.2x", "#00e5a0"),
        ("data/volume_gap_1_5x_paper_account.json", "VOL-CONFIRMED 1.5x", "#2fa8ff"),
        ("data/pairs_paper_account.json", "PAIRS BOOK", "#c86bff"),
    ]

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 4.5), facecolor="#0a0e14")
    ax.set_facecolor("#0a0e14")

    plotted = False
    for path, label, color in tracks:
        trades = load_trades(path)
        if trades:
            ax.plot(curve(trades), color=color, linewidth=1.8, marker="o", markersize=3, label=label)
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
    note="Entry 16/21 - automated weekdays via launchd"
))
panels.append(live_panel(
    "VOLUME-CONFIRMED GAP 1.2x // LIVE", "data/volume_gap_1_2x_paper_account.json", "#00e5a0",
    note="Entry 25 - full-sample-hindsight threshold - automated"
))
panels.append(live_panel(
    "VOLUME-CONFIRMED GAP 1.5x // LIVE", "data/volume_gap_1_5x_paper_account.json", "#2fa8ff",
    note="Entry 27 Part 5 - honest out-of-time threshold - automated"
))

if load_json("data/pairs_paper_account.json") is None:
    panels.append(panel("PAIRS BOOK (NQ/ES, NQ/YM, ES/YM)", [
        ("STATUS", '<span class="neu">BACKTEST-VALIDATED, NOT YET LIVE</span>'),
        ("BACKTEST NET PF", "NQ/ES 2.33 | NQ/YM 2.19 | ES/YM 1.76"),
        ("WHY NOT LIVE", "risk-wired &amp; unit-tested (Entry 24), never run vs. real market data"),
    ], accent="#c86bff", subtitle="Entry 23"))
else:
    panels.append(live_panel(
        "PAIRS BOOK (NQ/ES, NQ/YM, ES/YM) // LIVE", "data/pairs_paper_account.json", "#c86bff",
        note="Entry 23/24"
    ))

honest_assessment = """
<strong style="color:#00e5a0;">Flagship candidate:</strong> Volume-Confirmed Gap Continuation
(Entries 25/27) &mdash; the only strategy to pass all 6 standardized scorecard checks, and the
only one to survive a confound check, a fine threshold sweep, lookback-robustness, AND an honest
out-of-time threshold selection test. Now live forward-testing at both the 1.2x and 1.5x
thresholds, automated daily. Backtest net PF 1.39 (1.2x, 132 trades).<br><br>
<strong style="color:#c86bff;">Strong second contender:</strong> Pairs book (NQ/ES, NQ/YM, ES/YM)
&mdash; higher raw net profit factors (1.76-2.33) but on a thinner, less-scrutinized sample
(37-39 trades each, below the 100-trade bar) and not yet live forward-tested at all.<br><br>
<strong style="color:#ffb020;">Also tracked live:</strong> unfiltered Gap Continuation
(Entry 16/21) &mdash; real edge, but net-of-cost PF (1.17) falls short of the 1.3 bar.<br><br>
<strong style="color:#ff5c5c;">Rejected:</strong> Crude Oil Gap (Entry 22, outlier-dependent),
Gold Gap (Entry 26, no edge), Relative Momentum Rotation (Entry 19, no edge).<br><br>
<strong style="color:#ff5c5c;">Bottom line:</strong> Nothing here has been validated for real
capital. Backtest evidence and live forward-validation are deliberately treated as two separate
bars in this project - the live trade counts above are still very early (single digits to low
tens), nowhere near the roughly 20-30 trade threshold this project uses before that conversation
is even on the table.
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
