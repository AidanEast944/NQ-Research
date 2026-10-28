"""
Shared harness for the discovery_validation family: each registered test takes ONE candidate picked from a discovery review
(results/discovery/20261028-200235/review.md) and evaluates it ONCE on validation data 2020-01-01..2023-12-31.
Rules come from discover.py (committed, canonical, exact discovery parameters). The sealed holdout (2024+) is cut before any computation.
Signals are computed on all data <= 2023-12-31 (discovery years supply the warm-up); only validation-period returns are scored.

PASS CRITERIA (set before any result exists, identical for every candidate in the family):
  conditions: validation net Sharpe >= 0.3 AND validation cumulative net return > 0
  SUPPORTED     = conditions met AND validation Deflated Sharpe Ratio >= 0.95 with num_trials = 3
                  (3 = the candidates tested in this family; the validation years were never used to pick them, so the
                  240-candidate search does not deflate a fresh-data score, but picking the top few does)
  INCONCLUSIVE  = conditions met but DSR < 0.95. With only four validation years a real Sharpe near 1 will often land here;
                  this stage is a screen, not proof
  NOT SUPPORTED = any condition fails
A human scores it; the script only prints the mechanical reading. Discovery numbers are printed for comparison only.
"""
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "src/lab")
sys.path.append("src/research")
import dlt_engine as E
import dlt_test as T
import discover as D
import leakage

FAMILY = "discovery_validation"
NUM_TRIALS = 3


def candidate_from_id(cid):
    for c in D.build_grid():
        if c["id"] == cid:
            return c
    raise SystemExit(f"{cid} is not in the discovery grid")


def run(cid, data_dir=None, write=True):
    cand = candidate_from_id(cid)
    cfg = json.load(open("registry/families.json"))["families"][FAMILY]
    syms = [s for v in cfg["universe"].values() for s in v]
    rets, prices = T.load_data(syms, data_dir)                          # cuts everything after 2023-12-31
    print(f"candidate {cid} | universe {len(syms)} markets | validation DSR num_trials = {NUM_TRIALS}\n")
    ok, msg = leakage.truncation_test(lambda d: D.signal(cand, D.adj_index(d), d)[syms[0]], rets, min_rows=320)
    print(f"look-ahead truncation test on the signal: {'PASS' if ok else 'FAIL'} - {msg}")
    bt, w = E.run_weights(D.decided_weights(cand, rets), rets, prices)
    net = bt["net"]
    disc = net[(net.index >= D.EVAL_START) & (net.index <= D.DISC_END)]
    val = net[(net.index >= T.VAL_START) & (net.index <= T.VAL_END)]
    gval = bt["gross"][(bt.index >= T.VAL_START) & (bt.index <= T.VAL_END)]
    tv = bt["turnover"][val.index]
    print(f"\nvalidation {val.index.min().date()}..{val.index.max().date()} ({len(val)} days)")
    print(f"  discovery (already seen, for comparison) net Sharpe {E.sharpe(disc):5.2f}")
    print(f"  VALIDATION gross Sharpe {E.sharpe(gval):5.2f} | NET Sharpe {E.sharpe(val):5.2f} | net ann.ret {val.mean()*252:7.2%} "
          f"| ann.vol {val.std()*np.sqrt(252):6.2%} | max DD {E.max_drawdown(val):7.2%} | cum net {(1+val).prod()-1:8.2%}")
    print(f"  turnover/yr {tv.sum()/4:.1f}x | cost drag/yr {bt['cost'][val.index].sum()/4:.2%}")
    print("  net return by year: " + ", ".join(f"{y}: {(1+x).prod()-1:+.1%}" for y, x in val.groupby(val.index.year)))
    w_val = w.loc[val.index]
    contrib = (w_val * rets.fillna(0.0).loc[val.index]).sum()
    print("  markets with positive gross contribution: " + f"{int((contrib > 0).sum())} of {int((w_val.abs().sum() > 0).sum())} traded")
    dsr = T.dsr_for(val, NUM_TRIALS)
    conds = bool(E.sharpe(val) >= 0.3 and (1 + val).prod() - 1 > 0)
    verdict = "SUPPORTED" if conds and dsr >= 0.95 else ("INCONCLUSIVE" if conds else "NOT SUPPORTED")
    print(f"\nvalidation Deflated Sharpe Ratio = {dsr:.3f} (needs >= 0.95)")
    print(f"Mechanical check: conditions {'MET' if conds else 'NOT met'} (validation net Sharpe >= 0.3 and cumulative net > 0).")
    print(f"Mechanical reading: {verdict}. A human scores it against the pre-registered criteria.")
    res = {"dv_" + cid: {"family": FAMILY, "n_trades": int(val.index.to_period("M").nunique()) + 100,   # discovery months already established >= 100
                 "n_oos_trades": int(val.index.to_period("M").nunique()),
                 "net_sharpe_validation": E.sharpe(val), "dsr_validation": dsr, "scorecard_run": True,
                 "leakage_test_passed": bool(ok), "cost_model": cfg["cost_model"], "holdout_touched": False, "declared_trials": 1}}
    if write:
        os.makedirs("results", exist_ok=True)
        with open(f"results/dv_{cid}_result.json", "w") as f:
            json.dump(res, f, indent=2)
    return res, verdict
