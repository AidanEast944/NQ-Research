"""
Shared harness for the diversified_lowturnover family's pre-registered tests. Each registered test is a thin committed script
(src/research/dlt_<id>_test.py) that calls run(CANDIDATE). Nothing here is tunable: the rules live in dlt_engine.py.

DATA: only dates <= 2023-12-31 are ever loaded (the sealed holdout, 2024-01-01 onward, is cut off before any computation).
  Discovery = 2010-06-08..2019-12-31, validation = 2020-01-01..2023-12-31 (registry/families.json). The first signal needs
  months of history, so a 12-month candidate starts trading in mid-2011; that is reported, not hidden.
REFUSES TO RUN unless every symbol in the family universe has a daily file (a test on a partial universe is a different test).
TRIALS: the DSR num_trials = 20 + the family's declared trials in registry/research_registry.json (this test included).
SHARPE VARIANCE for the DSR = 1 / (number of validation days), the standard large-sample approximation.

PASS CRITERIA (fixed for every candidate, set before any result exists):
  conditions: net Sharpe >= 0.3 in discovery AND net Sharpe >= 0.3 in validation AND validation cumulative net return > 0
  SUPPORTED     = conditions met AND validation Deflated Sharpe Ratio >= 0.95 (scorecard Check 7 threshold)
  INCONCLUSIVE  = conditions met but DSR < 0.95
  NOT SUPPORTED = any condition fails
A human scores it; the script only prints the mechanical result.
"""
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "src/lab")
sys.path.append("src/research")   # append: a same-named test_paper_broker.py lives there
import dlt_engine as E
import futures_daily as fd
import leakage
from deflated_sharpe import deflated_sharpe_ratio
from scipy import stats

FAMILY = "diversified_lowturnover"
DISC_END, VAL_START, VAL_END = pd.Timestamp("2019-12-31"), pd.Timestamp("2020-01-01"), pd.Timestamp("2023-12-31")


def family_cfg():
    with open("registry/families.json") as f:
        return json.load(f)["families"][FAMILY]


def family_declared_trials():
    try:
        with open("registry/research_registry.json") as f:
            reg = json.load(f)
        return sum(t.get("declared_trials", 0) for t in reg.get("tests", {}).values() if t.get("family") == FAMILY)
    except OSError:
        return 0


def universe(cfg):
    u = cfg["universe"]
    return [s for syms in u.values() for s in syms]


def load_data(syms, data_dir=None):
    missing = [s for s in syms if not os.path.exists(os.path.join(data_dir or fd.DATA_DIR, f"{s}.csv"))]
    if missing:
        raise SystemExit(f"REFUSED: daily data missing for {missing}. The test only runs on the full registered universe.")
    frames = {s: fd.load(s, data_dir) for s in syms}
    frames = {s: d[d.index <= VAL_END] for s, d in frames.items()}      # sealed holdout cut BEFORE any computation
    rets = fd.align_returns(frames)
    prices = pd.DataFrame({s: d["close"] for s, d in frames.items()}).sort_index()
    return rets, prices


def score(bt):
    net = bt["net"]
    disc = net[net.index <= DISC_END]
    val = net[(net.index >= VAL_START) & (net.index <= VAL_END)]
    return disc, val


def dsr_for(val, num_trials):
    v = val.dropna()
    sr_daily = v.mean() / v.std() if v.std() > 0 else 0.0
    return float(deflated_sharpe_ratio(sr_daily, num_trials, 1.0 / max(len(v), 2), len(v),
                                       skewness=float(stats.skew(v)), kurtosis=float(stats.kurtosis(v, fisher=False))))


def run(cand, data_dir=None, write=True):
    cfg = family_cfg()
    syms = universe(cfg)
    rets, prices = load_data(syms, data_dir)
    num_trials = 20 + family_declared_trials()
    print(f"candidate {cand['id']}: {cand['kind']} {cand['months']}m | universe {len(syms)} markets | DSR num_trials = {num_trials}\n")
    ok, msg = leakage.truncation_test(lambda d: E.momentum_score(d["ES"], cand["months"]), rets)
    print(f"look-ahead truncation test on the momentum score: {'PASS' if ok else 'FAIL'} - {msg}")
    bt, w = E.backtest(rets, prices, cand["months"], cand["kind"])
    first = w.abs().sum(axis=1).gt(0).idxmax()
    disc, val = score(bt)
    disc = disc[disc.index >= first]
    g = bt["gross"]
    gd, gv = g[(g.index >= first) & (g.index <= DISC_END)], g[(g.index >= VAL_START) & (g.index <= VAL_END)]
    tv = bt["turnover"]
    print(f"\ntrading starts {first.date()}; discovery {disc.index.min().date()}..{disc.index.max().date()} ({len(disc)} days), "
          f"validation {val.index.min().date()}..{val.index.max().date()} ({len(val)} days)")
    for name, n_, g_ in (("discovery", disc, gd), ("validation", val, gv)):
        print(f"  {name:10s} gross Sharpe {E.sharpe(g_):6.2f} | NET Sharpe {E.sharpe(n_):6.2f} | net ann.ret {n_.mean()*252:7.2%} "
              f"| net ann.vol {n_.std()*np.sqrt(252):6.2%} | max DD {E.max_drawdown(n_):7.2%} | cum net {(1+n_).prod()-1:8.2%}")
    print(f"  turnover (sum |dw|) per year: {tv[tv.index >= first].sum() / ((tv.index.max() - first).days / 365.25):.1f}x"
          f" | cost drag per year: {bt['cost'][bt.index >= first].sum() / ((bt.index.max() - first).days / 365.25):.2%}")
    print("  net return by calendar year: " + ", ".join(f"{y}: {(1+r).prod()-1:+.1%}" for y, r in
                                                          bt["net"][bt.index >= first].groupby(bt.index[bt.index >= first].year)))
    dsr = dsr_for(val, num_trials)
    conds = bool(E.sharpe(disc) >= 0.3 and E.sharpe(val) >= 0.3 and (1 + val).prod() - 1 > 0)
    print(f"\nvalidation Deflated Sharpe Ratio = {dsr:.3f} (needs >= 0.95)")
    print(f"Mechanical check: conditions {'MET' if conds else 'NOT met'} (net Sharpe >= 0.3 in BOTH periods, validation cum net > 0).")
    verdict = "SUPPORTED" if conds and dsr >= 0.95 else ("INCONCLUSIVE" if conds else "NOT SUPPORTED")
    print(f"Mechanical reading: {verdict}. A human scores it against the pre-registered criteria.")
    months_disc = int(disc.index.to_period("M").nunique())
    months_val = int(val.index.to_period("M").nunique())
    res = {cand["id"]: {"family": FAMILY, "n_trades": months_disc + months_val, "n_oos_trades": months_val,
                        "net_sharpe_discovery": E.sharpe(disc), "net_sharpe_validation": E.sharpe(val),
                        "dsr_validation": dsr, "scorecard_run": True, "leakage_test_passed": bool(ok),
                        "cost_model": cfg["cost_model"], "holdout_touched": False,
                        "declared_trials": int(cand.get("declared_trials", 1))}}
    if write:
        os.makedirs("results", exist_ok=True)
        with open(f"results/{cand['id']}_result.json", "w") as f:
            json.dump(res, f, indent=2)
    return res, verdict
