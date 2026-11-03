"""Small-account feasibility check (READ-ONLY).

Question: could the live paper tracks have been traded with a ~$1,000 account?

It replays each paper track's real closed trades with micro contracts and risk-based sizing,
and reports peak drawdown (% of equity), the largest margin per contract the account could have
survived, and a bootstrap chance of ruin. It never writes to any ledger, never touches
live_gate.py, and registers no trial. It is descriptive, not a test of an edge.

Honesty notes:
  * Ledgers record gross points; costs here are an assumed $ per contract round trip (illustrative).
  * Tracks are NOT independent: the volume variants are subsets of the gap track's trades.
  * Samples are tiny (3-27 trades). Resampling cannot create information the ledger lacks.
  * No broker margin is assumed. We report the margin per contract the account could tolerate.
"""
import os, sys, json, math, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(REPO, "data")
RESULTS = os.path.join(REPO, "results")

# micro point values; mini ledgers are mapped to the micro of the same index
MICRO_PV = {"MNQ": 2.0, "MES": 5.0, "MYM": 0.5, "NQ": 2.0, "ES": 5.0, "YM": 0.5}

TRACKS = {
    "gap (MNQ)": "gap_paper_account.json",
    "NQ vol 1.2x": "volume_gap_1_2x_paper_account.json",
    "NQ vol 1.5x": "volume_gap_1_5x_paper_account.json",
    "ES vol 1.2x": "volume_gap_es_1_2x_paper_account.json",
    "YM vol 1.2x": "volume_gap_ym_1_2x_paper_account.json",
    "YM vol 1.5x": "volume_gap_ym_1_5x_paper_account.json",
    "fade (NQ->MNQ)": "fade_paper_account.json",
}
# pairs has no stop (spread reverts), so risk cannot be sized from a stop: reported but excluded
EXCLUDED = {"pairs": "pairs_paper_account.json"}

START_EQUITY = 1000.0
COSTS = [0.0, 2.0, 4.5]          # $ per contract round trip; illustrative, 4.5 is the repo placeholder
SIZING = [("1 micro always", None), ("risk cap 5%", 0.05), ("risk cap 2%", 0.02)]
RUIN_FRACTION = 0.5               # "ruin" = equity at or below 50% of start
HORIZON = 100
N_SIMS = 5000
SEED = 20261103


def load_trades(path):
    """Closed trades -> list of dicts with symbol, entry_date, stop_dist (points), r (gross R multiple), pv (micro)."""
    with open(path) as f:
        d = json.load(f)
    out = []
    for t in d.get("trade_history", []):
        if t.get("status") != "CLOSED" or t.get("stop_price") is None:
            continue
        stop_dist = abs(float(t["entry_price"]) - float(t["stop_price"]))
        if stop_dist <= 0:
            continue
        sym = str(t["symbol"]).split()[0]
        if sym not in MICRO_PV:
            continue
        out.append({"symbol": sym, "entry_date": t["entry_date"], "stop_dist": stop_dist,
                    "r": float(t["points_result"]) / stop_dist, "pv": MICRO_PV[sym]})
    out.sort(key=lambda x: x["entry_date"])      # stable: ties keep ledger order
    return out


def contracts(equity, risk1, cap):
    """Contracts for a trade whose one-contract stop risk (stop_dist*pv) is risk1."""
    if cap is None:
        return 1
    return int(math.floor(cap * equity / risk1))


def replay(trades, cost, cap, start=START_EQUITY):
    """Chronological replay. Returns summary dict. A trade is skipped if sizing gives 0 contracts,
    and trading stops ('stranded') once equity cannot cover one contract's stop risk plus cost."""
    eq = start
    peak = start
    max_dd = 0.0
    min_eq = start
    skipped = 0
    taken = 0
    stranded_at = None
    worst_trade_pct = 0.0
    margin_tol = float("inf")          # largest margin/contract that never exceeded equity at entry
    max_contracts = 0
    for i, t in enumerate(trades):
        risk1 = t["stop_dist"] * t["pv"]
        if eq < risk1 + cost:
            stranded_at = i
            break
        n = contracts(eq, risk1, cap)
        if n < 1:
            skipped += 1
            continue
        taken += 1
        max_contracts = max(max_contracts, n)
        margin_tol = min(margin_tol, eq / n)
        pnl = n * (t["r"] * risk1 - cost)
        worst_trade_pct = min(worst_trade_pct, pnl / eq)
        eq += pnl
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak if peak > 0 else 1.0)
        min_eq = min(min_eq, eq)
    return {"final_equity": round(eq, 2), "max_drawdown_pct": round(100 * max_dd, 1),
            "min_equity": round(min_eq, 2), "trades_taken": taken, "trades_skipped": skipped,
            "stranded_at_trade": stranded_at, "worst_trade_pct_of_equity": round(100 * worst_trade_pct, 1),
            "max_contracts": max_contracts,
            "margin_per_contract_tolerable": None if margin_tol == float("inf") else round(margin_tol, 2)}


def bootstrap_ruin(trades, cost, cap, zero_edge=False, horizon=HORIZON, n_sims=N_SIMS, seed=SEED,
                   start=START_EQUITY):
    """Resample trades with replacement for `horizon` trades. Returns P(equity <= 50% of start at any time)
    and P(stranded: cannot afford one more stop). zero_edge demeans R first (isolates variance + costs)."""
    if not trades:
        return None
    rng = np.random.default_rng(seed)
    r = np.array([t["r"] for t in trades])
    if zero_edge:
        r = r - r.mean()
    sd = np.array([t["stop_dist"] for t in trades])
    pv = np.array([t["pv"] for t in trades])
    risk1_all = sd * pv
    idx = rng.integers(0, len(trades), size=(n_sims, horizon))
    eq = np.full(n_sims, start, dtype=float)
    ruined = np.zeros(n_sims, bool)
    stranded = np.zeros(n_sims, bool)
    finals_alive = None
    for k in range(horizon):
        j = idx[:, k]
        risk1 = risk1_all[j]
        active = ~stranded
        can = eq >= risk1 + cost
        newly = active & ~can
        stranded |= newly
        active = active & can
        if cap is None:
            n = np.ones(n_sims)
        else:
            n = np.floor(cap * eq / risk1)
        n = np.where(active, n, 0.0)
        pnl = n * (r[j] * risk1 - cost)
        eq = eq + pnl
        ruined |= eq <= RUIN_FRACTION * start
    return {"p_ruin_half": round(float(ruined.mean()), 3), "p_stranded": round(float(stranded.mean()), 3),
            "median_final": round(float(np.median(eq)), 0)}


def analyze(data_dir=DATA):
    out = {"assumptions": {"start_equity": START_EQUITY, "costs_per_contract_rt": COSTS,
                           "ruin": f"equity <= {int(RUIN_FRACTION*100)}% of start at any point within {HORIZON} trades",
                           "bootstrap": f"{N_SIMS} sims, iid resample of observed trades, seed {SEED}",
                           "margin": "no broker margin assumed; 'margin_per_contract_tolerable' is the largest margin that "
                                     "equity at entry could have covered for every taken trade"},
           "tracks": {}, "excluded": {}}
    for name, fn in TRACKS.items():
        p = os.path.join(data_dir, fn)
        if not os.path.exists(p):
            out["tracks"][name] = {"error": "ledger missing"}
            continue
        trades = load_trades(p)
        if not trades:
            out["tracks"][name] = {"n_trades": 0}
            continue
        risk1 = trades[0]["stop_dist"] * trades[0]["pv"]
        rec = {"n_trades": len(trades), "one_contract_stop_risk_usd": round(risk1, 2),
               "one_contract_stop_risk_pct_of_start": round(100 * risk1 / START_EQUITY, 1),
               "mean_r_gross": round(float(np.mean([t["r"] for t in trades])), 3), "scenarios": {}}
        for sname, cap in SIZING:
            for cost in COSTS:
                key = f"{sname} | cost ${cost:.2f}"
                if cap is not None and contracts(START_EQUITY, risk1, cap) < 1:
                    rec["scenarios"][key] = {"tradeable_at_start": False,
                                             "why": f"one contract risks {100*risk1/START_EQUITY:.1f}% > cap {100*cap:.0f}%"}
                    continue
                rec["scenarios"][key] = {"tradeable_at_start": True,
                                         "replay": replay(trades, cost, cap),
                                         "bootstrap_observed_edge": bootstrap_ruin(trades, cost, cap),
                                         "bootstrap_zero_edge": bootstrap_ruin(trades, cost, cap, zero_edge=True)}
        out["tracks"][name] = rec
    for name, fn in EXCLUDED.items():
        p = os.path.join(data_dir, fn)
        if os.path.exists(p):
            with open(p) as f:
                th = json.load(f).get("trade_history", [])
            out["excluded"][name] = {"closed_legs": len(th),
                                     "reason": "no stop price (spread exit), so risk cannot be sized; also needs 2 legs "
                                               "(e.g. MNQ + MES) at once",
                                     "worst_leg_usd": min((float(t["points_result"]) * float(t.get("point_value_used", 0))
                                                           for t in th), default=None)}
    return out


def to_markdown(res):
    L = ["# Small-account feasibility ($1,000 start) - paper tracks, read-only", "",
         "Descriptive only. Costs are illustrative; no broker margin is assumed; samples are tiny and the tracks overlap.", ""]
    for name, rec in res["tracks"].items():
        if "error" in rec or rec.get("n_trades", 0) == 0:
            L.append(f"## {name}: no usable trades"); L.append(""); continue
        L.append(f"## {name} ({rec['n_trades']} trades, one contract risks ${rec['one_contract_stop_risk_usd']} "
                 f"= {rec['one_contract_stop_risk_pct_of_start']}% of $1,000; mean gross R {rec['mean_r_gross']})")
        L.append("")
        L.append("| sizing | cost/ct | final $ | max DD | worst trade | margin tol/ct | P(ruin) observed | P(ruin) zero-edge |")
        L.append("|---|---|---|---|---|---|---|---|")
        for key, s in rec["scenarios"].items():
            sz, c = [x.strip() for x in key.split("|")]
            if not s.get("tradeable_at_start"):
                L.append(f"| {sz} | {c.replace('cost ','')} | not tradeable | | | | | {s['why']} |")
                continue
            r, b1, b0 = s["replay"], s["bootstrap_observed_edge"], s["bootstrap_zero_edge"]
            strand = f" (stranded at #{r['stranded_at_trade']})" if r["stranded_at_trade"] is not None else ""
            L.append(f"| {sz} | {c.replace('cost ','')} | {r['final_equity']}{strand} | {r['max_drawdown_pct']}% | "
                     f"{r['worst_trade_pct_of_equity']}% | ${r['margin_per_contract_tolerable']} | "
                     f"{b1['p_ruin_half']:.0%} | {b0['p_ruin_half']:.0%} |")
        L.append("")
    for name, e in res["excluded"].items():
        L.append(f"## {name}: excluded - {e['reason']} (worst leg ${e['worst_leg_usd']})")
    L += ["", "Ruin = equity at or below 50% of start at any point within 100 resampled trades. "
          "'Zero-edge' removes the average R first, so it shows risk from variance and costs alone."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DATA)
    ap.add_argument("--out-dir", default=RESULTS)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    res = analyze(a.data_dir)
    md = to_markdown(res)
    if not a.no_write:
        os.makedirs(a.out_dir, exist_ok=True)
        with open(os.path.join(a.out_dir, "small_account_feasibility.json"), "w") as f:
            json.dump(res, f, indent=2)
        with open(os.path.join(a.out_dir, "small_account_feasibility.md"), "w") as f:
            f.write(md + "\n")
    print(md)
    return res


if __name__ == "__main__":
    main()
