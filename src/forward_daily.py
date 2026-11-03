"""
Forward tracker for frozen daily-futures candidates (registry/forward_roster.json). Free, clean evidence: it reports ONLY daily net returns
on dates strictly AFTER the roster's forward_start. Earlier history is used purely as signal warm-up and its strategy returns are
never reported, so the sealed holdout (2024-01-01 to forward_start) stays unscored. No orders, no accounts, no trials.

Every run also applies the silent-skip guard (all universe markets must be sized at some point in the available history).
Carry entries need data/futures_daily_c1 for all 19 markets; until then they report status "waiting_for_data".
Writes results/forward_daily.json. Run: python3 src/forward_daily.py   (scheduled daily by launchd/com.nqresearch.forwarddaily.plist)
"""
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "research"))
import futures_daily as fd
import carry as C
import dlt_engine as E
import discover as D

MIN_DAYS_FOR_SHARPE = 60
OUT = "results/forward_daily.json"


def load_inputs(syms, data_dir=None, c1_dir=None):
    fronts = {s: fd.load(s, data_dir) for s in syms}
    rets = fd.align_returns(fronts)
    prices = pd.DataFrame({s: d["close"] for s, d in fronts.items()}).sort_index()
    c1_dir = c1_dir or (os.path.join(data_dir, "c1") if data_dir else "data/futures_daily_c1")
    seconds = None
    if all(os.path.exists(os.path.join(c1_dir, f"{s}.csv")) for s in syms):
        seconds = {s: fd.load(s, c1_dir) for s in syms}
    return fronts, rets, prices, seconds


def forward_slice(net, forward_start):
    """Only dates strictly after forward_start. The single place the cut is made."""
    return net[net.index > pd.Timestamp(forward_start)]


def stats(f):
    n = int(len(f))
    out = {"days": n, "last_date": str(f.index.max().date()) if n else None, "cum_net": float((1 + f).prod() - 1) if n else None,
           "max_dd": E.max_drawdown(f) if n else None, "net_sharpe": None}
    if n >= MIN_DAYS_FOR_SHARPE:
        out["net_sharpe"] = E.sharpe(f)
    return out


def run(roster_path="registry/forward_roster.json", data_dir=None, c1_dir=None, write=True):
    with open(roster_path) as f:
        roster = json.load(f)
    syms = D.universe()
    fronts, rets, prices, seconds = load_inputs(syms, data_dir, c1_dir)
    grid = {c["id"]: c for c in D.build_grid()}
    res = {"generated": datetime.now().isoformat(timespec="seconds"), "forward_start": roster["forward_start"],
           "data_last_date": str(rets.index.max().date()), "entries": {}}
    for e in roster["entries"]:
        rec = {"kind": e["kind"], "note": e.get("note", "")}
        try:
            if e["kind"] == "discover":
                w_dec = D.decided_weights(grid[e["id"]], rets)
                bt, w = E.run_weights(w_dec, rets, prices)
            else:
                if seconds is None:
                    rec["status"] = "waiting_for_data"; res["entries"][e["id"]] = rec; continue
                score = C.carry_panel(fronts, seconds, rets.index)
                bt, w = E.backtest(rets, prices, 0, e["carry_kind"], score=score)
            E.require_all_markets_trade(w, syms, e["id"])
            rec.update(stats(forward_slice(bt["net"], roster["forward_start"])))
            rec["status"] = "ok" if rec["days"] else "no_forward_days_yet"
        except SystemExit as x:
            rec["status"] = "guard_refused"; rec["detail"] = str(x)
        res["entries"][e["id"]] = rec
    if write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT + ".tmp", "w") as f:
            json.dump(res, f, indent=2)
        os.replace(OUT + ".tmp", OUT)
    return res


def main():
    res = run()
    print(f"forward tracker: data through {res['data_last_date']}, forward start {res['forward_start']}")
    for k, r in res["entries"].items():
        if r["status"] == "ok":
            sh = f"{r['net_sharpe']:.2f}" if r["net_sharpe"] is not None else f"n/a (<{MIN_DAYS_FOR_SHARPE} days)"
            print(f"  {k:30s} {r['days']:4d} days  cum net {r['cum_net']:+.2%}  max DD {r['max_dd']:.2%}  Sharpe {sh}")
        else:
            print(f"  {k:30s} {r['status']}" + (f" - {r['detail'][:90]}" if r.get("detail") else ""))
    if any(r["status"] == "guard_refused" for r in res["entries"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
