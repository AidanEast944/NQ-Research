"""
Strategy DISCOVERY machine (family `discovery_search`). It searches a defined grammar of rule-based futures strategies on
DISCOVERY DATA ONLY, evaluates every candidate with the project cost model, filters out the fragile ones, and writes a ranked
review report. It proposes; it never trades, registers, approves or touches a live file.

HONESTY RULES BUILT IN
  * Every candidate evaluated counts as a trial, winners or not. N = every evaluation ever made across all passes in
    registry/discovery_ledger.json (a rerun counts again); the approved budget counts distinct candidate ids.
  * The Deflated Sharpe Ratio of every candidate is computed with that full N, and the report also prints the Sharpe you would
    expect from the BEST of N pure-luck strategies, so a "good" number can be read against what luck alone produces.
  * Data: only dates <= 2019-12-31 are loaded. Validation (2020-2023) and the sealed holdout (2024+) are never read here.
  * Needs a human-approved `discovery_search` entry in registry/families.json (budget_evaluations); refuses otherwise or when
    the ledger would exceed the budget. Refuses to run on a partial universe.
  * Survivors are only candidates for REVIEW. Testing one on validation costs a trial in a separate, human-approved step.

GRAMMAR (all signals use a roll-adjusted return index, 60-day vol-targeted sizing at 10%, 3x leverage cap, one-day lag):
  tsmom(L, skip) | reversal(L) | breakout(N) | macross(fast, slow) | xsmom(L, skip, within asset class)
  x rebalance weekly/monthly x optional volatility filter (trade a market only while its vol is below its trailing 250-day median)
FILTERS (discovery data only): net Sharpe >= 0.4 | positive net Sharpe in BOTH halves | breadth: >= 60% of markets contribute
  positively | neighbor robustness: neighbouring parameter values keep >= 50% of its Sharpe | turnover/cost sanity.
Run:  python3 src/research/discover.py run   |   python3 src/research/discover.py review
"""
import hashlib
import itertools
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.append("src/research")
import dlt_engine as E
import futures_daily as fd
from deflated_sharpe import deflated_sharpe_ratio, expected_max_sharpe
from scipy import stats

FAMILY = "discovery_search"
DISC_END = pd.Timestamp("2019-12-31")
EVAL_START = pd.Timestamp("2011-09-01")      # after the longest warm-up (315 days from 2010-06-08)
HALF_SPLIT = pd.Timestamp("2015-10-01")
LEDGER = "registry/discovery_ledger.json"
OUT_DIR = "results/discovery"
FILTERS = {"min_sharpe": 0.4, "min_half_sharpe": 0.0, "min_breadth": 0.6, "min_neighbor_ratio": 0.5, "max_cost_drag": 0.03}
TOP_K = 10

LOOKBACKS = [21, 42, 63, 84, 126, 189, 252, 315]
GRID = {
    "tsmom": {"L": LOOKBACKS, "skip": [0, 21], "rebal": ["W", "M"]},
    "reversal": {"L": [3, 5, 10, 21], "rebal": ["W"]},
    "breakout": {"N": [10, 20, 40, 60, 90, 120, 180, 250], "rebal": ["W", "M"]},
    "macross": {"fast": [5, 10, 20, 40, 50], "slow": [20, 50, 100, 150, 200, 250], "rebal": ["W", "M"]},
    "xsmom": {"L": [21, 63, 126, 189, 252], "skip": [0, 21], "rebal": ["W", "M"]},
}
OVERLAYS = [False, True]


def build_grid():
    out = []
    for fam, params in GRID.items():
        keys = list(params)
        for combo in itertools.product(*[params[k] for k in keys]):
            p = dict(zip(keys, combo))
            if fam == "tsmom" and p["L"] <= p["skip"] + 1:
                continue
            if fam == "xsmom" and p["L"] <= p["skip"] + 1:
                continue
            if fam == "macross" and p["fast"] >= p["slow"]:
                continue
            for vf in OVERLAYS:
                out.append({"family": fam, "params": p, "volfilter": vf})
    for c in out:
        c["id"] = cand_id(c)
    return out


def cand_id(c):
    core = "_".join(f"{k}{v}" for k, v in c["params"].items())
    return f"{c['family']}_{core}{'_vf' if c['volfilter'] else ''}"


# ---------- signals: all use only data up to day t ----------
def adj_index(rets):
    return (1 + rets.fillna(0.0)).cumprod()


def sig_tsmom(ix, L, skip):
    lr = np.log(ix).diff()
    sc = lr.shift(skip).rolling(L - skip, min_periods=L - skip).sum() if skip else lr.rolling(L, min_periods=L).sum()
    return np.sign(sc)


def sig_reversal(ix, L):
    return -np.sign(ix / ix.shift(L) - 1)


def sig_breakout(ix, N):
    hi, lo = ix.rolling(N, min_periods=N).max().shift(1), ix.rolling(N, min_periods=N).min().shift(1)
    raw = pd.DataFrame(np.nan, index=ix.index, columns=ix.columns)
    raw[ix > hi] = 1.0
    raw[ix < lo] = -1.0
    return raw.ffill().where(hi.notna())


def sig_macross(ix, f, s):
    mf, ms = ix.rolling(f, min_periods=f).mean(), ix.rolling(s, min_periods=s).mean()
    return np.sign(mf - ms).where(ms.notna())


def sig_xsmom(ix, rets, L, skip, classes=E.CLASSES):
    lr = np.log(ix).diff()
    sc = lr.shift(skip).rolling(L - skip, min_periods=L - skip).sum() if skip else lr.rolling(L, min_periods=L).sum()
    sig = pd.DataFrame(0.0, index=ix.index, columns=ix.columns)
    for cols in classes.values():
        cols = [c for c in cols if c in ix.columns]
        if len(cols) < 2:
            continue
        s = sc[cols]
        rank, n = s.rank(axis=1, method="first"), s.notna().sum(axis=1)
        half = n // 2
        part = rank.gt(n - half, axis=0).astype(float) - rank.le(half, axis=0).astype(float)
        part[s.isna()] = np.nan
        part[n < 2] = np.nan
        sig[cols] = part
    return sig.where(sc.notna())


def signal(c, ix, rets):
    p, f = c["params"], c["family"]
    if f == "tsmom":
        return sig_tsmom(ix, p["L"], p["skip"])
    if f == "reversal":
        return sig_reversal(ix, p["L"])
    if f == "breakout":
        return sig_breakout(ix, p["N"])
    if f == "macross":
        return sig_macross(ix, p["fast"], p["slow"])
    if f == "xsmom":
        return sig_xsmom(ix, rets, p["L"], p["skip"])
    raise ValueError(f)


def rebalance_flags(index, rebal):
    s = pd.Series(index, index=index)
    key = s.dt.to_period("M") if rebal == "M" else s.dt.to_period("W")
    return pd.Series(key.values != key.shift(-1).values, index=index)


def decided_weights(c, rets):
    ix = adj_index(rets)
    sig = signal(c, ix, rets)
    vol = E.realized_vol(rets)
    if c["volfilter"]:
        sig = sig.where(vol <= vol.rolling(250, min_periods=250).median())
    raw = sig * (E.TARGET_VOL / vol).clip(upper=E.MAX_LEV)
    n_active = raw.abs().gt(0).sum(axis=1).clip(lower=1)
    w = raw.div(n_active, axis=0).fillna(0.0)
    flags = rebalance_flags(w.index, c["rebal"] if "rebal" in c else c["params"]["rebal"])
    w = w.copy()
    w.loc[~flags.values] = np.nan
    return w.ffill().fillna(0.0)


# ---------- evaluation ----------
def evaluate(c, rets, prices):
    w_dec = decided_weights(c, rets)
    bt, w = E.run_weights(w_dec, rets, prices)
    bt = bt[(bt.index >= EVAL_START) & (bt.index <= DISC_END)]
    w = w.loc[bt.index]
    net = bt["net"]
    contrib = (w * rets.fillna(0.0).loc[bt.index]).sum()
    active = (w.abs().sum() > 0)
    breadth = float((contrib[active] > 0).mean()) if active.any() else 0.0
    h1, h2 = net[net.index < HALF_SPLIT], net[net.index >= HALF_SPLIT]
    years = max((net.index.max() - net.index.min()).days / 365.25, 1e-9)
    return {"id": c["id"], "family": c["family"], "params": c["params"], "volfilter": c["volfilter"],
            "sharpe_net": E.sharpe(net), "sharpe_gross": E.sharpe(bt["gross"]),
            "sharpe_h1": E.sharpe(h1), "sharpe_h2": E.sharpe(h2), "ann_ret": float(net.mean() * 252),
            "ann_vol": float(net.std() * np.sqrt(252)), "max_dd": E.max_drawdown(net), "breadth": breadth,
            "turnover_yr": float(bt["turnover"].sum() / years), "cost_drag_yr": float(bt["cost"].sum() / years),
            "n_days": int(len(net)), "skew": float(stats.skew(net.dropna())),
            "kurt": float(stats.kurtosis(net.dropna(), fisher=False))}, net


def neighbor_ratio(row, rows):
    """Median Sharpe of one-step parameter neighbours (same family, overlay, other params) divided by this one's Sharpe."""
    fam = GRID[row["family"]]
    neigh = []
    for k, vals in fam.items():
        if k == "rebal" or len(vals) < 2 or not isinstance(vals[0], int):
            continue
        i = vals.index(row["params"][k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                p2 = dict(row["params"]); p2[k] = vals[j]
                cid = cand_id({"family": row["family"], "params": p2, "volfilter": row["volfilter"]})
                if cid in rows:
                    neigh.append(rows[cid]["sharpe_net"])
    if not neigh or row["sharpe_net"] <= 0:
        return 0.0
    return float(np.median(neigh) / row["sharpe_net"])


def apply_filters(rows, f=FILTERS):
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        r["neighbor_ratio"] = neighbor_ratio(r, by_id)
        r["fails"] = [name for name, bad in (
            ("sharpe", r["sharpe_net"] < f["min_sharpe"]),
            ("half1", r["sharpe_h1"] <= f["min_half_sharpe"]), ("half2", r["sharpe_h2"] <= f["min_half_sharpe"]),
            ("breadth", r["breadth"] < f["min_breadth"]),
            ("neighbors", r["neighbor_ratio"] < f["min_neighbor_ratio"]),
            ("costs", r["cost_drag_yr"] > f["max_cost_drag"])) if bad]
        r["passes"] = not r["fails"]
    return rows


def add_dsr(rows, nets, n_total):
    sr_daily = {r["id"]: (nets[r["id"]].mean() / nets[r["id"]].std() if nets[r["id"]].std() > 0 else 0.0) for r in rows}
    var = float(np.var(list(sr_daily.values()))) or 1e-6
    for r in rows:
        n = nets[r["id"]].dropna()
        r["dsr"] = float(deflated_sharpe_ratio(sr_daily[r["id"]], n_total, var, len(n),
                                               skewness=r["skew"], kurtosis=r["kurt"]))
    chance_daily = expected_max_sharpe(n_total, var)
    return chance_daily * np.sqrt(252)


# ---------- governance ----------
PROPOSED_FAMILY = {
    "status": "active", "approved_by_human": True, "approved_at": "<fill when approved>",
    "budget_evaluations": 300,
    "note": "Search-only family: counts every candidate EVALUATED. Reads discovery data (<= 2019-12-31) only. Raising this number "
            "after seeing results is not allowed; lowering it is.",
}


def gate(root="."):
    with open(os.path.join(root, "registry/families.json")) as f:
        fam = json.load(f)["families"].get(FAMILY)
    if not fam or fam.get("status") != "active" or fam.get("approved_by_human") is not True or not fam.get("budget_evaluations"):
        raise SystemExit("REFUSED: registry/families.json has no human-approved active `discovery_search` family with "
                         "budget_evaluations. Proposed entry:\n" + json.dumps({FAMILY: PROPOSED_FAMILY}, indent=2))
    return fam


def load_ledger(root="."):
    p = os.path.join(root, LEDGER)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"evaluated": {}, "runs": []}


def save_ledger(led, root="."):
    p = os.path.join(root, LEDGER)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        json.dump(led, f, indent=2)
    os.replace(p + ".tmp", p)


def universe():
    with open("registry/families.json") as f:
        u = json.load(f)["families"]["diversified_lowturnover"]["universe"]
    return [s for syms in u.values() for s in syms]


def load_discovery_data(syms, data_dir=None):
    missing = [s for s in syms if not os.path.exists(os.path.join(data_dir or fd.DATA_DIR, f"{s}.csv"))]
    if missing:
        raise SystemExit(f"REFUSED: daily data missing for {missing}. Discovery runs on the full universe only.")
    frames = {s: fd.load(s, data_dir) for s in syms}
    frames = {s: d[d.index <= DISC_END] for s, d in frames.items()}     # validation + sealed holdout never loaded
    rets = fd.align_returns(frames)
    prices = pd.DataFrame({s: d["close"] for s, d in frames.items()}).sort_index()
    return rets, prices


def run(root=".", data_dir=None, grid=None, gate_check=True):
    fam = gate(root) if gate_check else {"budget_evaluations": 10**9}
    led = load_ledger(root)
    grid = grid or build_grid()
    new = [c for c in grid if c["id"] not in led["evaluated"]]
    total_after = len(led["evaluated"]) + len(new)
    if total_after > fam["budget_evaluations"]:
        raise SystemExit(f"REFUSED: would bring cumulative evaluations to {total_after}, over the approved budget "
                         f"{fam['budget_evaluations']}. Nothing was evaluated.")
    rets, prices = load_discovery_data(universe(), data_dir)
    rows, nets = [], {}
    for c in grid:
        r, net = evaluate(c, rets, prices)
        rows.append(r); nets[r["id"]] = net
    for c in new:
        led["evaluated"][c["id"]] = datetime.now().isoformat(timespec="seconds")
    # Every pass over the grid is a fresh look at the data, so the deflation counts EVERY evaluation ever made (a rerun after a bug fix
    # counts again, voided runs included). The approved budget counts distinct candidate ids; the deflation counts looks.
    n_total = sum(r["grid_size"] for r in led["runs"]) + len(grid)
    chance = add_dsr(rows, nets, n_total)
    apply_filters(rows)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    led["runs"].append({"run_id": run_id, "grid_size": len(grid), "new": len(new), "cumulative": len(led["evaluated"]),
                        "passed": sum(r["passes"] for r in rows)})
    out = os.path.join(root, OUT_DIR, run_id)
    os.makedirs(out, exist_ok=True)
    pd.DataFrame([{**{k: v for k, v in r.items() if k not in ("params", "fails")}, "params": json.dumps(r["params"]),
                   "fails": ",".join(r["fails"])} for r in rows]).to_csv(os.path.join(out, "all_candidates.csv"), index=False)
    pd.DataFrame(nets).to_csv(os.path.join(out, "daily_net_returns.csv"))
    review = write_review(rows, nets, n_total, chance, out, run_id)
    save_ledger(led, root)
    with open(os.path.join(root, OUT_DIR, "latest.txt"), "w") as f:
        f.write(run_id)
    return rows, review, out


def write_review(rows, nets, n_total, chance_sharpe, out, run_id):
    passed = sorted([r for r in rows if r["passes"]], key=lambda r: -r["sharpe_net"])
    top = passed[:TOP_K]
    best = max(rows, key=lambda r: r["sharpe_net"])
    L = [f"# Strategy discovery review {run_id}", "",
         f"**Searched {len(rows)} strategies on 2011-09 to 2019-12 only** (cumulative trials counted: {n_total}). "
         f"Validation (2020-2023) and the sealed holdout (2024+) were not read.", "",
         f"- Passed all filters: **{len(passed)} of {len(rows)}**.",
         f"- Best net Sharpe in the whole search: {best['sharpe_net']:.2f} ({best['id']}).",
         f"- Best Sharpe you would expect from {n_total} strategies with NO real edge: about **{chance_sharpe:.2f}**. "
         f"Anything near or below that is indistinguishable from luck.", "",
         "Filters: net Sharpe >= 0.4, positive in both halves, >= 60% of markets contribute, neighbouring parameters keep >= 50% of the Sharpe, "
         "cost drag <= 3%/yr.", ""]
    if not top:
        L += ["**Nothing survived the filters.** That is a real result: the grammar searched has no robust edge on this data after costs.", ""]
    else:
        L += ["## Candidates for review (ranked by discovery net Sharpe)", "",
              "| # | strategy | net Sharpe | gross | half 1 | half 2 | breadth | neighbours | turnover/yr | cost/yr | max DD | DSR@N |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(top, 1):
            L.append(f"| {i} | `{r['id']}` | {r['sharpe_net']:.2f} | {r['sharpe_gross']:.2f} | {r['sharpe_h1']:.2f} | {r['sharpe_h2']:.2f} | "
                     f"{r['breadth']:.0%} | {r['neighbor_ratio']:.2f} | {r['turnover_yr']:.0f}x | {r['cost_drag_yr']:.2%} | {r['max_dd']:.0%} | {r['dsr']:.2f} |")
        L += ["", "DSR@N = probability the Sharpe is real after correcting for trying N strategies; 0.95 is the project bar. "
              "Most survivors will sit well below it on discovery data alone, which is expected: this stage only chooses what is worth "
              "spending a validation trial on.", "", "## Net return by year (top 3)", ""]
        for r in top[:3]:
            n = nets[r["id"]]
            L.append(f"- `{r['id']}`: " + ", ".join(f"{y}: {(1+x).prod()-1:+.1%}" for y, x in n.groupby(n.index.year)))
    L += ["", "## What happens next (your decision)",
          "Pick at most a few candidates worth a validation trial. Each becomes a pre-registered spec tested once on 2020-2023, "
          "then (only if it passes) once on the sealed holdout. Nothing here is validated, and nothing trades."]
    text = "\n".join(L)
    with open(os.path.join(out, "review.md"), "w") as f:
        f.write(text)
    with open(os.path.join(out, "review.json"), "w") as f:
        json.dump({"run_id": run_id, "n_searched": len(rows), "n_total_trials": n_total, "n_passed": len(passed),
                   "chance_best_sharpe": chance_sharpe, "top": [{k: r[k] for k in ("id", "family", "params", "volfilter", "sharpe_net",
                                                                                  "sharpe_h1", "sharpe_h2", "breadth", "neighbor_ratio", "dsr")}
                                                                 for r in top]}, f, indent=2)
    return text


def main(argv=None):
    argv = argv or sys.argv[1:]
    if argv[:1] == ["run"]:
        rows, review, out = run()
        print(review)
        print(f"\nfull results: {out}/")
    elif argv[:1] == ["review"]:
        with open(os.path.join(OUT_DIR, "latest.txt")) as f:
            rid = f.read().strip()
        print(open(os.path.join(OUT_DIR, rid, "review.md")).read())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
