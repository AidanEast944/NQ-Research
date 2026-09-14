"""
Generates a local HTML status dashboard (results/dashboard.html) showing what the automated
forward-testing infrastructure is actually doing - the live paper-trading state of EVERY
currently-active track on this machine, a portfolio-level view of the combined book, and an
honest overall research status. Reads only local JSON files already written by the various
forward-test scripts; nothing here touches the network or any external service.

Rewritten 2026-09-10 (Entry 32) to restore Fade/Trend/pairs after a mistaken earlier pass dropped
them. Extended 2026-09-11 (Entry 33) with three portfolio-level sections that no single
per-strategy script could produce on its own - a combined book view, aggregate open risk, and a
live readiness scorecard against this project's own ~20-30-live-trade bar. See
src/portfolio_analytics.py for the calculations behind all three; this file is presentation only.

Regenerated automatically each weekday evening by the existing com.nqresearch.dashboard launchd
job, after all of the day's resolve jobs have run. Also safe to run manually anytime:

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
import plotly.graph_objects as go
import portfolio_analytics as pa

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


def combined_book_panel():
    """Portfolio-level view (Entry 33) - sums every PaperBroker-backed account into one book.
    Trend is intentionally excluded (see portfolio_analytics.py's TREND_STATE_FILE comment)."""
    summary = pa.combined_book_summary()
    dd = pa.combined_max_drawdown()
    rows = [
        ("COMBINED P&L", f'{colorval(summary["total_pnl"])} <span class="neu">'
                          f'(${summary["total_balance"]:,.2f} of ${summary["total_starting"]:,.0f})</span>'),
        ("TOTAL LIVE TRADES", summary["total_trades"]),
        ("TOTAL OPEN POSITIONS", summary["total_open"]),
        ("MAX DRAWDOWN (combined)", f'${dd["dollars"]:,.2f} ({dd["pct"]:.1f}%)'),
    ]
    return panel("PORTFOLIO — COMBINED BOOK", rows, accent="#00e5a0",
                 subtitle="Sum of Gap + both Vol-Confirmed + Fade + Pairs (Trend excluded, points-only, see below)")


def open_risk_panel():
    """Aggregate dollars actually at risk right now, across every open position in every
    strategy (Entry 33). See portfolio_analytics.aggregate_open_risk for the three different
    risk models this necessarily blends (price-stop, pairs-sizing-formula, points-only)."""
    risk = pa.aggregate_open_risk()
    rows = [("TOTAL $ AT RISK (priced positions)", f'${risk["total_dollars"]:,.2f}')]
    if risk["lines"]:
        for line in risk["lines"]:
            rows.append((line["label"], f'{line["detail"]} — ${line["risk"]:,.2f}'))
    else:
        rows.append(("PRICED OPEN POSITIONS", "none"))
    if risk["trend_points_at_risk"] is not None:
        rows.append(("Trend (retired, points only)", f'{risk["trend_points_at_risk"]:.0f}pt at risk — no $ value established'))

    warning = None
    if risk["unknown_risk_positions"]:
        warning = (f'{", ".join(risk["unknown_risk_positions"])} has an open position with no recorded '
                   f'contract sizing (pre-broker-wiring, Entry 32) - its risk is real but not quantifiable '
                   f'from current records, so it is NOT included in the total above.')
    return panel("PORTFOLIO — AGGREGATE OPEN RISK", rows, accent="#ff8fd6", warning=warning)


def readiness_panel():
    """Live readiness scorecard (Entry 33) - turns this project's own stated ~20-30-live-trade
    bar into a computed number per strategy, using 25 as the midpoint target."""
    rows_html = ""
    for row in pa.readiness_scorecard():
        bar_width = row["pct"]
        rows_html += f"""
        <div class="readiness-row">
            <div class="readiness-label">{row['label']}<span class="readiness-sub">{row['backtest_note']}</span></div>
            <div class="readiness-bar-track"><div class="readiness-bar-fill" style="width:{bar_width}%;"></div></div>
            <div class="readiness-count">{row['trades']}/{row['target']}</div>
            <div class="readiness-eta">{row['eta_note']}</div>
        </div>
        """
    return f"""
    <div class="chart-panel" style="margin-bottom: 20px;">
        <div class="chart-title">READINESS TOWARD A REAL-CAPITAL CONVERSATION — LIVE TRADE COUNT vs. ~25-TRADE BAR</div>
        <div style="font-size:11px; color:#6b7280; margin-bottom:10px;">
            This bar is a trade-count threshold only, not a go/no-go signal by itself - a strategy still
            needs its live results to actually look like its backtest once it gets there. Pace/ETA figures
            below are rough given how few trades exist so far and will tighten up over time.
        </div>
        {rows_html}
    </div>
    """


def diversification_panel():
    rows_html = ""
    for pair_label, verdict, explanation in pa.diversification_notes():
        color = "#ff5c5c" if "STRUCTURALLY RELATED" in verdict else "#8b909c"
        rows_html += f"""
        <div style="margin-bottom:10px;">
            <span style="color:{color}; font-weight:600;">{pair_label} — {verdict}</span><br>
            <span style="font-size:12px; color:#8b909c;">{explanation}</span>
        </div>
        """
    return f"""
    <div class="chart-panel" style="margin-bottom: 20px;">
        <div class="chart-title">DIVERSIFICATION — QUALITATIVE, NOT A COMPUTED CORRELATION</div>
        <div style="font-size:11px; color:#6b7280; margin-bottom:10px;">
            No strategy here has {pa.MIN_TRADES_FOR_CORRELATION}+ overlapping live trade-days yet, so a
            real Pearson correlation would just be noise - shown as reasoning instead of a fabricated number.
        </div>
        {rows_html}
    </div>
    """


def build_equity_curve():
    def load_trades(filepath):
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r") as f:
            state = json.load(f)
        return state.get("trade_history", [])

    def curve_with_dates(trades, default_point_value):
        balance = STARTING_BALANCE
        balances = [balance]
        dates = ["Start"]
        for t in trades:
            points = t.get("points_result", 0)
            point_value = t.get("point_value_used", default_point_value)
            balance += points * point_value
            balances.append(balance)
            dates.append(t.get("entry_date", t.get("date", "")))
        return balances, dates

    tracks = [
        ("data/gap_paper_account.json", "GAP (unfiltered)", "#ffb020", 2),
        ("data/volume_gap_1_2x_paper_account.json", "VOL-CONFIRMED 1.2x", "#00e5a0", 2),
        ("data/volume_gap_1_5x_paper_account.json", "VOL-CONFIRMED 1.5x", "#2fa8ff", 2),
        ("data/fade_paper_account.json", "FADE", "#ff8fd6", 20),
        ("data/pairs_paper_account.json", "PAIRS BOOK (all 3)", "#c86bff", 2),
    ]

    fig = go.Figure()
    plotted = False

    for path, label, color, default_pv in tracks:
        trades = load_trades(path)
        if trades:
            balances, dates = curve_with_dates(trades, default_pv)
            fig.add_trace(go.Scatter(
                x=list(range(len(balances))),
                y=balances,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2),
                marker=dict(size=5),
                customdata=dates,
                hovertemplate="<b>%{fullData.name}</b><br>Trade #%{x}<br>Balance: $%{y:,.2f}<br>Date: %{customdata}<extra></extra>"
            ))
            plotted = True

    fig.add_hline(y=STARTING_BALANCE, line_dash="dash", line_color="#555b66", line_width=1)

    fig.update_layout(
        paper_bgcolor="#0a0e14",
        plot_bgcolor="#0a0e14",
        font=dict(color="#8b909c", family="SF Mono, Menlo, monospace", size=11),
        xaxis=dict(title="TRADE #", gridcolor="#2a2e39", zerolinecolor="#2a2e39"),
        yaxis=dict(title="BALANCE ($)", gridcolor="#2a2e39", zerolinecolor="#2a2e39"),
        legend=dict(bgcolor="#131722", bordercolor="#2a2e39", borderwidth=1, font=dict(color="#e6e9ef")),
        margin=dict(l=60, r=20, t=20, b=50),
        height=420,
        hovermode="x unified",
    )

    if not plotted:
        fig.add_annotation(text="No live trades yet", showarrow=False,
                            font=dict(color="#6b7280", size=14),
                            xref="paper", yref="paper", x=0.5, y=0.5)

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})


def build_combined_equity_curve():
    """The portfolio-level counterpart to build_equity_curve() above - one line, the whole
    book's combined balance over calendar time, instead of one line per strategy (Entry 33)."""
    curve = pa.combined_equity_curve()
    balances = [b for _, b in curve]
    dates = [d for d, _ in curve]

    starting = STARTING_BALANCE * len(pa.BROKER_ACCOUNTS)

    fig = go.Figure()

    if len(balances) > 1:
        x_vals = list(range(len(balances)))

        # Starting-balance reference line, added as a real trace so we can fill against it
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=[starting] * len(balances),
            mode="lines",
            line=dict(color="#555b66", width=1, dash="dash"),
            hoverinfo="skip",
            showlegend=False
        ))

        fig.add_trace(go.Scatter(
            x=x_vals,
            y=balances,
            mode="lines+markers",
            line=dict(color="#00e5a0", width=2),
            marker=dict(size=5),
            fill="tonexty",
            fillcolor="rgba(0, 229, 160, 0.08)",
            customdata=dates,
            hovertemplate="Trade #%{x}<br>Combined Balance: $%{y:,.2f}<br>Date: %{customdata}<extra></extra>",
            showlegend=False
        ))
    else:
        fig.add_annotation(text="No live trades yet across any strategy", showarrow=False,
                            font=dict(color="#6b7280", size=14),
                            xref="paper", yref="paper", x=0.5, y=0.5)

    fig.update_layout(
        paper_bgcolor="#0a0e14",
        plot_bgcolor="#0a0e14",
        font=dict(color="#8b909c", family="SF Mono, Menlo, monospace", size=11),
        xaxis=dict(title="TRADE # (combined, calendar order across all strategies)",
                   gridcolor="#2a2e39", zerolinecolor="#2a2e39"),
        yaxis=dict(title="COMBINED BALANCE ($)", gridcolor="#2a2e39", zerolinecolor="#2a2e39"),
        margin=dict(l=60, r=20, t=20, b=50),
        height=350,
        hovermode="x unified",
    )

    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar": False})


equity_curve_html = build_equity_curve()
combined_equity_curve_html = build_combined_equity_curve()

portfolio_panels = [combined_book_panel(), open_risk_panel()]

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
    "FADE (prior-day break) // RETIRED", "data/fade_paper_account.json", "#6b7280",
    note="Entry 2/35 - FAIL on full archive (0/5, PF 0.69) - was live a week despite the "
         "original Entry 2 FAIL before being caught and retired 2026-09-11",
    warning="This strategy's own original backtest (Entry 2) was already a FAIL. It ran live "
            "anyway for roughly 3 weeks before this was caught. Re-verified against the current "
            "108-day archive (Entry 35) - still fails 0/5. Retired, no new positions. Its balance "
            "above is a real historical record, not an endorsement."
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
(Entry 16/21) &mdash; real edge, but net-of-cost PF (1.17) falls short of the 1.3 bar.<br><br>
<strong style="color:#6b7280;">Retired:</strong> Trend Following (Entry 6) &mdash; regime-dependent,
not durable. No new entries; managed the last open position to close 2026-09-10 (Entry 34).
Fade (Entry 2/35) &mdash; failed its OWN original backtest (0/5 scorecard) yet ran live anyway
until caught and retired 2026-09-11; re-verified against the full current archive and still
fails 0/5 (PF 0.69, 102% max drawdown).<br><br>
<strong style="color:#ff5c5c;">Rejected:</strong> Crude Oil Gap (Entry 22, outlier-dependent),
Gold Gap (Entry 26, no edge), Relative Momentum Rotation (Entry 19, no edge).<br><br>
<strong style="color:#ff5c5c;">Bottom line:</strong> Nothing here has been validated for real
capital. Backtest evidence and live forward-validation are deliberately treated as two separate
bars in this project - live trade counts are still early across every track, nowhere near the
roughly 20-30 trade threshold this project uses before that conversation is even on the table
(see the readiness scorecard below for exactly how far each strategy actually is).
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
    .readiness-row {{
        display: grid;
        grid-template-columns: minmax(160px, 260px) 1fr 60px minmax(140px, 260px);
        align-items: center;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px solid #1a1e28;
        font-size: 12px;
    }}
    .readiness-row:last-child {{ border-bottom: none; }}
    .readiness-label {{ color: #cfd3dc; display: flex; flex-direction: column; }}
    .readiness-sub {{ font-size: 9px; color: #6b7280; margin-top: 2px; }}
    .readiness-bar-track {{ background: #1a1e28; height: 8px; border-radius: 4px; overflow: hidden; }}
    .readiness-bar-fill {{ background: #00e5a0; height: 100%; }}
    .readiness-count {{ color: #cfd3dc; text-align: right; font-weight: 600; }}
    .readiness-eta {{ color: #8b909c; font-size: 10px; }}
</style>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>NQ RESEARCH TERMINAL</h1>
        <div class="timestamp">LAST UPDATE: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>

        <div class="chart-panel" style="margin-bottom: 20px;">
        <div class="chart-title">RESEARCH STATUS — HONEST ASSESSMENT (updated w/ Deflated Sharpe Ratio, 2026-09-12)</div>
        <div style="font-size: 13px; line-height: 1.6; color: #cfd3dc;">
            <strong style="color:#ffb020;">Volume-Confirmed Gap (NQ/YM/ES):</strong> 6/7 scorecard checks pass on all
            three symbols. Blocked only by Deflated Sharpe Ratio (28-40% probability of genuine skill after
            correcting for the 43 strategy variations tested to find this one) - large sample (113-134 trades),
            survives real costs, but not yet statistically distinguishable from a lucky find.<br><br>
            <strong style="color:#c86bff;">Pairs Trading (NQ/ES, NQ/YM, ES/YM):</strong> Highest Deflated Sharpe
            Ratio in the project (65-71%) - the most statistically convincing signal found so far. Blocked by
            small sample size (39 trades) and drawdown, not by the underlying edge itself.<br><br>
            <strong style="color:#ff5c5c;">Unfiltered Gap Continuation:</strong> Now FAILS decisively (DSR 0.1%)
            once honestly re-scored against all 43 tested variations - retired as a live-tracking priority in
            favor of its volume-confirmed refinement.<br><br>
            <strong style="color:#ff5c5c;">Bottom line:</strong> Nothing currently passes all 7 checks. No
            strategy is validated for real capital. Deflated Sharpe Ratio - which corrects for the number of
            strategies tried before finding these - is the honest reason why: statistical confidence requires
            more real trades, which only time can provide.
        </div>
    </div>

    <div class="grid">
        {"".join(portfolio_panels)}
    </div>

    <div class="chart-panel" style="margin-bottom: 20px;">
        <div class="chart-title">PORTFOLIO — COMBINED EQUITY CURVE (ALL STRATEGIES, ONE BOOK)</div>
        {combined_equity_curve_html}
    </div>

    {readiness_panel()}
    {diversification_panel()}

    <div class="grid">
        {"".join(panels)}
    </div>

    <div class="chart-panel">
        <div class="chart-title">EQUITY CURVE — LIVE PAPER / FORWARD ACCOUNTS (PER STRATEGY)</div>
        {equity_curve_html}
    </div>
</body>
</html>
"""

os.makedirs("results", exist_ok=True)
output_path = os.path.abspath("results/dashboard.html")
with open(output_path, "w") as f:
    f.write(html)

print(f"Dashboard saved to {output_path}")
