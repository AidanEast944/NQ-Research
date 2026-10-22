"""
Decay monitor (research_log.md Entry 73). Reads each paper account and flags a track whose live record is
drifting away from what it was supposed to do, so nobody has to eyeball the dashboard to notice.

Checks per track (registry/track_expectations.json):
  * MILESTONE  - the closed-trade count crossed 25 / 50 / 100: time for a deliberate review
  * BELOW EXPECTED - live win rate is improbably low versus the backtest rate (binomial p < 0.05, n >= 15)
  * BELOW BREAKEVEN - live win rate is improbably low versus the 1/3 breakeven of a 2:1 reward-to-risk (p < 0.10, n >= 15)
  * DRAWDOWN   - peak-to-trough on cumulative gross dollars is over 20% of the $10,000 start
  * LOSING STREAK - 8 or more consecutive losses
Costs: net dollars use the same cost model as the scorecard (1pt slippage + $4.50 per round trip).
Purely diagnostic: it never changes an account, a strategy or LIVE_STRATEGIES. Only NEW flags trigger a macOS
notification (state in registry/decay_state.json). Pairs and the retired fade track are not covered.

Usage: python3 src/decay_monitor.py
Scheduled 5:45 PM PT by launchd/com.nqresearch.decaymonitor.plist (after the 5:05 resolve and 5:35 coverage jobs).
"""
import json
import math
import os
import subprocess
import sys
from datetime import datetime

CFG = "registry/track_expectations.json"
STATE = "registry/decay_state.json"
REPORT = "results/decay_report.json"
START_BALANCE = 10000.0
SLIP_PTS, COMM = 1.0, 4.50
DEFAULT_PV = {"MNQ": 2, "MES": 5, "MYM": 0.5}


def binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p), no scipy needed."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def analyse(key, spec, cfg):
    out = {"key": key, "label": spec["label"], "flags": [], "info": []}
    if not os.path.exists(spec["account"]):
        out["flags"].append("ACCOUNT FILE MISSING")
        return out
    acct = json.load(open(spec["account"]))
    trades = [t for t in acct.get("trade_history", []) if t.get("status") == "CLOSED"]
    n = len(trades)
    out["trades"] = n
    out["balance"] = acct.get("balance")
    out["open_positions"] = len(acct.get("positions", []))
    if n == 0:
        out["info"].append("no closed trades yet")
        return out
    gross, net = [], []
    for t in trades:
        pv = t.get("point_value_used") or DEFAULT_PV.get(t.get("symbol"), 1)
        g = t["points_result"] * pv
        gross.append(g)
        net.append(g - SLIP_PTS * pv - COMM)
    wins = sum(1 for g in gross if g > 0)
    out.update(wins=wins, win_rate=round(wins / n, 3), gross_dollars=round(sum(gross), 2),
               net_dollars=round(sum(net), 2))
    gp, gl = sum(g for g in net if g > 0), -sum(g for g in net if g < 0)
    out["net_profit_factor"] = round(gp / gl, 2) if gl > 0 else None

    # milestones
    for m in cfg["milestones"]:
        if n >= m:
            out["info"].append(f"MILESTONE {m} trades reached")
    if n in cfg["milestones"]:
        out["flags"].append(f"MILESTONE: {n} trades reached - review")

    # win rate checks
    if n >= 15:
        exp = spec.get("expected_win_rate")
        if exp is not None:
            p = binom_cdf(wins, n, exp)
            out["p_vs_expected"] = round(p, 4)
            if p < 0.05:
                out["flags"].append(f"BELOW EXPECTED: {wins}/{n} wins ({wins/n:.0%}) vs backtest {exp:.0%}, p={p:.3f}")
        p2 = binom_cdf(wins, n, cfg["breakeven_win_rate"])
        out["p_vs_breakeven"] = round(p2, 4)
        if p2 < 0.10:
            out["flags"].append(f"BELOW BREAKEVEN: {wins}/{n} wins ({wins/n:.0%}) vs ~33% needed, p={p2:.3f}")
    else:
        out["info"].append(f"only {n} trades; win-rate checks start at 15")

    # drawdown on cumulative gross dollars
    peak = cum = worst = 0.0
    for g in gross:
        cum += g
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    out["max_drawdown_dollars"] = round(worst, 2)
    if worst > 0.20 * START_BALANCE:
        out["flags"].append(f"DRAWDOWN: ${worst:,.0f} peak-to-trough ({worst/START_BALANCE:.0%} of $10k)")

    # losing streak
    streak = best = 0
    for g in gross:
        streak = streak + 1 if g < 0 else 0
        best = max(best, streak)
    cur = 0
    for g in reversed(gross):
        if g < 0:
            cur += 1
        else:
            break
    out["current_losing_streak"] = cur
    if cur >= 8:
        out["flags"].append(f"LOSING STREAK: {cur} in a row")
    return out


def notify(text):
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e",
                            f'display notification "{text}" with title "Strategy decay monitor"'], timeout=10)
        except Exception:
            pass


def main():
    cfg = json.load(open(CFG))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"announced": []}
    results = [analyse(k, v, cfg) for k, v in cfg["tracks"].items()]
    print(f"Decay monitor - {datetime.now():%Y-%m-%d %H:%M}\n")
    print(f"{'track':<30}{'trades':>7}{'win%':>6}{'netPF':>7}{'net $':>9}{'maxDD$':>8}  flags")
    new_flags = []
    for r in results:
        wr = f"{100*r['win_rate']:.0f}" if "win_rate" in r else "-"
        pf = r.get("net_profit_factor")
        print(f"{r['label']:<30}{r.get('trades',0):>7}{wr:>6}{(f'{pf:.2f}' if pf else '-'):>7}"
              f"{r.get('net_dollars',0):>9.0f}{r.get('max_drawdown_dollars',0):>8.0f}  "
              f"{'; '.join(r['flags']) if r['flags'] else 'ok'}")
        for f in r["flags"]:
            sig = f"{r['key']}|{f.split(':')[0]}|{r.get('trades',0) // 5 if not f.startswith('MILESTONE') else r.get('trades')}"
            if sig not in state["announced"]:
                state["announced"].append(sig)
                new_flags.append(f"{r['label']}: {f}")
    os.makedirs("results", exist_ok=True)
    json.dump({"generated": datetime.now().isoformat(timespec="seconds"), "tracks": results},
              open(REPORT, "w"), indent=2)
    json.dump(state, open(STATE, "w"), indent=2)
    if new_flags:
        print("\nNEW FLAGS:")
        for f in new_flags:
            print("  -", f)
        notify(f"{len(new_flags)} new flag(s): " + new_flags[0][:80])
    else:
        print("\nNo new flags.")


if __name__ == "__main__":
    main()
