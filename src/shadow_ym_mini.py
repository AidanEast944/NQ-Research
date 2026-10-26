"""
Shadow ledger: re-costs the LIVE YM volume>=1.2x paper trades as if they had been taken on a MINI YM contract ($5/pt)
with the project default costs (1 pt slippage + $4.50 round trip). READ-ONLY: never edits a paper account, places a trade,
or touches live_gate.py. Written for Entry 82's follow-up: forward trades are the only evidence not contaminated by the
2015-2023 data already used.
Run: python3 src/shadow_ym_mini.py        Output: console + results/ym_mini_shadow.json
"""
import json
import os
import sys

sys.path.insert(0, "src")
import trading_costs

ACCOUNT = "data/volume_gap_ym_1_2x_paper_account.json"
POINT_VALUE_MINI = 5
TARGET_TRADES = 100   # same forward bar the promotion queue uses


def pf(x):
    w = sum(v for v in x if v > 0)
    l = -sum(v for v in x if v < 0)
    return w / l if l > 0 else float("nan")


if __name__ == "__main__":
    with open(ACCOUNT) as f:
        trades = [t for t in json.load(f)["trade_history"] if t.get("status") == "CLOSED"]
    pts = [t["points_result"] for t in trades]
    net = [trading_costs.apply_costs(p, point_value=POINT_VALUE_MINI) for p in pts]
    wins = sum(1 for n in net if n > 0)
    cum, peak, dd = 0.0, 0.0, 0.0
    for n in net:
        cum += n; peak = max(peak, cum); dd = max(dd, peak - cum)
    out = {"source": ACCOUNT, "contract": "YM mini ($5/pt)", "closed_trades": len(trades),
           "wins": wins, "net_dollars": round(sum(net), 2), "net_pf": None if not trades else round(pf(net), 2),
           "max_drawdown_dollars": round(dd, 2), "target_trades": TARGET_TRADES,
           "last_trade": trades[-1]["entry_date"] if trades else None}
    os.makedirs("results", exist_ok=True)
    with open("results/ym_mini_shadow.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"YM volume>=1.2x live trades re-costed as a MINI: {len(trades)} closed, {wins} wins")
    print(f"   net ${sum(net):,.2f} after default costs, net PF {out['net_pf']}, max drawdown ${dd:,.2f}")
    for t, p, n in zip(trades, pts, net):
        print(f"   {t['entry_date']} {t['direction']:<5} {p:+6.1f} pts -> ${n:+8.2f}")
    print(f"\nProgress to {TARGET_TRADES} forward trades: {len(trades)}/{TARGET_TRADES}. "
          f"Too few to conclude anything; this exists to accumulate honest forward evidence.")
