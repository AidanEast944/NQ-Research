import json
import os
import base64
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def forward_log_stats():
    if not os.path.exists("data/forward_log.csv"):
        return {}
    log = pd.read_csv("data/forward_log.csv", dtype={"exit_price": "float64", "exit_reason": "object", "status": "object"})
    closed = log[log["status"] == "CLOSED"].copy()
    stats = {}
    for strat in closed["strategy"].unique():
        rows = closed[closed["strategy"] == strat]
        def pts(row):
            if row["signal"] == "LONG":
                return row["exit_price"] - row["entry_price"]
            return row["entry_price"] - row["exit_price"]
        rows = rows.copy()
        rows["points"] = rows.apply(pts, axis=1)
        wins = (rows["points"] > 0).sum()
        stats[strat] = {
            "trades": len(rows), "wins": int(wins), "losses": len(rows) - int(wins),
            "win_rate": (wins / len(rows) * 100) if len(rows) > 0 else 0,
            "total_points": rows["points"].sum()
        }
    return stats

def build_equity_curve():
    def load_trades(filepath):
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r") as f:
            state = json.load(f)
        return state.get("trade_history", [])

    def curve(trades, starting_balance=10000, multiplier=20):
        balance = starting_balance
        balances = [balance]
        for t in trades:
            points = t.get("points", t.get("points_result", 0))
            balance += points * multiplier
            balances.append(balance)
        return balances

    fade_trades = load_trades("data/fade_paper_account.json")
    trend_trades = load_trades("data/trend_forward_state.json")
    gap_trades = load_trades("data/gap_paper_account.json")

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 4.5), facecolor="#0a0e14")
    ax.set_facecolor("#0a0e14")

    plotted = False
    if len(fade_trades) > 0:
        ax.plot(curve(fade_trades), color="#00e5a0", linewidth=1.8, marker="o", markersize=3, label="FADE")
        plotted = True
    if len(trend_trades) > 0:
        ax.plot(curve(trend_trades, multiplier=20), color="#2fa8ff", linewidth=1.8, marker="o", markersize=3, label="TREND")
        plotted = True
    if len(gap_trades) > 0:
        ax.plot(curve(gap_trades, multiplier=20), color="#ffb020", linewidth=1.8, marker="o", markersize=3, label="GAP CONTINUATION")
        plotted = True

    ax.axhline(y=10000, color="#555b66", linestyle="--", linewidth=1)
    ax.set_xlabel("TRADE #", color="#8b909c", fontsize=9, fontfamily="monospace")
    ax.set_ylabel("BALANCE ($)", color="#8b909c", fontsize=9, fontfamily="monospace")
    ax.tick_params(colors="#8b909c", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#2a2e39")
    ax.grid(True, alpha=0.15, color="#8b909c")
    if plotted:
        ax.legend(facecolor="#131722", edgecolor="#2a2e39", labelcolor="#e6e9ef", fontsize=8)
    plt.tight_layout()

    os.makedirs("results", exist_ok=True)
    img_path = "results/equity_curve.png"
    plt.savefig(img_path, dpi=140, facecolor="#0a0e14")
    plt.close()

    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

equity_curve_b64 = build_equity_curve()

fade_account = load_json("data/fade_paper_account.json")
trend_state = load_json("data/trend_forward_state.json")
pairs_state = load_json("data/pairs_forward_state.json")
gap_state = load_json("data/gap_forward_state.json")
nqym_state = load_json("data/pairs_nqym_forward_state.json")
esym_state = load_json("data/pairs_esym_forward_state.json")
fwd_stats = forward_log_stats()

def colorval(v):
    if v > 0:
        return f'<span class="pos">+{v:,.2f}</span>'
    elif v < 0:
        return f'<span class="neg">{v:,.2f}</span>'
    return f'<span class="neu">{v:,.2f}</span>'

def panel(title, rows, accent="#2fa8ff"):
    row_html = "".join(f'<div class="row"><span class="label">{k}</span><span class="value">{v}</span></div>' for k, v in rows)
    return f"""
    <div class="panel">
        <div class="panel-header" style="border-left: 3px solid {accent};">{title}</div>
        <div class="panel-body">{row_html}</div>
    </div>
    """

panels = []

panels.append(panel("FADE // PAPER ACCOUNT", [
    ("BALANCE", colorval((fade_account["balance"] - 10000)) + f' <span class="neu">(${fade_account["balance"]:,.2f})</span>' if fade_account else "N/A"),
    ("CLOSED TRADES", len(fade_account["trade_history"]) if fade_account else 0),
    ("OPEN POSITIONS", len(fade_account["positions"]) if fade_account else 0),
], accent="#00e5a0"))

accent_map = {"breakout": "#ff5c5c", "fade": "#00e5a0"}
for strat_name, s in fwd_stats.items():
    panels.append(panel(f"FORWARD TEST // {strat_name.upper()}", [
        ("TRADES", s["trades"]),
        ("RECORD", f"{s['wins']}W — {s['losses']}L"),
        ("WIN RATE", f"{s['win_rate']:.1f}%"),
        ("TOTAL PTS", colorval(s["total_points"])),
    ], accent=accent_map.get(strat_name, "#8b909c")))

if trend_state:
    panels.append(panel("TREND FOLLOWING", [
        ("CLOSED TRADES", len(trend_state.get("trade_history", []))),
        ("OPEN POSITION", "YES" if trend_state.get("position") else "NO"),
    ], accent="#2fa8ff"))

if pairs_state:
    panels.append(panel("PAIRS TRADING // NQ-ES", [
        ("RESOLVED SIGNALS", len(pairs_state.get("history", []))),
        ("OPEN POSITION", "YES" if pairs_state.get("position") else "NO"),
    ], accent="#c86bff"))

if nqym_state:
    panels.append(panel("PAIRS TRADING // NQ-YM", [
        ("RESOLVED SIGNALS", len(nqym_state.get("history", []))),
        ("OPEN POSITION", "YES" if nqym_state.get("position") else "NO"),
    ], accent="#c86bff"))

if esym_state:
    panels.append(panel("PAIRS TRADING // ES-YM", [
        ("RESOLVED SIGNALS", len(esym_state.get("history", []))),
        ("OPEN POSITION", "YES" if esym_state.get("position") else "NO"),
    ], accent="#c86bff"))

if gap_state:
    trades = gap_state.get("trade_history", [])
    wins = sum(1 for t in trades if t.get("points", 0) > 0)
    total = sum(t.get("points", 0) for t in trades)
    panels.append(panel("GAP CONTINUATION", [
        ("TRADES", len(trades)),
        ("RECORD", f"{wins}W — {len(trades) - wins}L"),
        ("TOTAL PTS", colorval(total)),
    ], accent="#ffb020"))

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
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
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
    .panel-body {{ padding: 10px 14px; }}
    .row {{
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #1a1e28;
        font-size: 13px;
    }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: #6b7280; letter-spacing: 0.5px; }}
    .value {{ font-weight: 600; }}
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
        <div style="font-size: 13px; line-height: 1.6; color: #cfd3dc;">
            <strong style="color:#00e5a0;">Strongest idea family:</strong> Index-futures pairs mean-reversion (NQ/ES, NQ/YM, ES/YM) —
            all three show 70-80% win rates, profit factors 1.97-2.52, and out-of-sample results that
            <em>improved</em> rather than collapsed. Consistent across 3 independent symbol pairs.<br><br>
            <strong style="color:#ffb020;">Also promising:</strong> Gap continuation (NQ) — 70 backtested trades,
            67% win rate, perfect 5/5 walk-forward record.<br><br>
            <strong style="color:#ff5c5c;">Bottom line:</strong> No strategy has crossed the 100-trade validation
            threshold yet. Grade: strong process, incomplete outcome. Nothing here is ready for real capital —
            still accumulating live evidence.
        </div>
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

