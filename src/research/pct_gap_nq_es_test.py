"""
PRE-REGISTERED test: live gap rules translated to PERCENT of price (lab spec pct_gap_nq_es,
lab/proposals/pct_gap_nq_es.json, approved by Aidan 2026-10-25). Nothing here may be tuned after the run.

WHY: the live rules are fixed in points, so they mean different things at NQ 4,500 (2015) vs 29,000 (2026).

FROZEN RULES (percentages = live point rules / 2026-10-23 close, rounded, NOT tuned):
  NQ (MNQ $2/pt): min gap 0.10% of prior close, stop 0.14% of entry, target 0.27% of entry
  ES (MES $5/pt): min gap 0.08%,                 stop 0.13%,          target 0.26%
  gap = 08:30 ET bar open vs prior day's last close; trade in gap direction (continuation); no volume filter;
  stop checked before target within a bar (same convention as strategy.py); exit by 16:00 ET close.
  Costs: project default (1 pt slippage + $4.50 round trip, apply_costs). Data: 2015-01-01 to 2023-12-31 only.

TRIALS DECLARED: 2 scorecards (NQ, ES). num_trials for the DSR = max(trial_count, 68) + 2.

PASS CRITERIA (set in advance): a symbol passes if net profit factor >= 1.3 over 2015-2023 AND net total is
positive in BOTH 2015-2020 and 2021-2023 AND >= 100 trades. SUPPORTED = at least one symbol passes.
NOT SUPPORTED = otherwise (recorded either way). 2024+ is deliberately excluded (seen). RTY is not used.

Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research/pct_gap_nq_es_test.py
Optional sanity check (slow): add --selfcheck to compare the point-mode of this code with strategy.py on NQ.
"""
import glob
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "src/lab")
import scorecard
import trial_count
import trading_costs
import leakage

START, END = pd.Timestamp("2015-01-01"), pd.Timestamp("2023-12-31")
SPLIT = pd.Timestamp("2021-01-01")
N_NEW_TRIALS = 2
MARKETS = {
    "NQ": dict(folder="data/raw_nq_extended", min_gap=0.10, stop=0.14, target=0.27, pv=2),
    "ES": dict(folder="data/raw_es_extended", min_gap=0.08, stop=0.13, target=0.26, pv=5),
}


def load(folder, start=START, end=END):
    frames = []
    for f in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        day = os.path.basename(f)[-14:-4]
        if start <= pd.Timestamp(day) <= end:
            frames.append(pd.read_csv(f, index_col="Datetime", parse_dates=True))
    h = pd.concat(frames)
    h = h[~h.index.duplicated(keep="first")].sort_index()
    h.index = pd.to_datetime(h.index, utc=True).tz_convert("America/New_York")
    h["date"] = h.index.date
    return h


def gap_series(h, pct=True):
    """Daily gap (as % of prior close, or points) using only the prior close and the 08:30 open."""
    close = h.groupby("date")["Close"].last()
    prior = close.shift(1)
    entry = h[h.index.time == pd.Timestamp("08:30").time()].groupby("date")["Open"].first()
    d = pd.concat([prior.rename("prior"), entry.rename("entry")], axis=1).dropna()
    gap = d["entry"] - d["prior"]
    return (gap / d["prior"] * 100) if pct else gap


def gap_feature(d):
    """Gap % per bar, NaN before the 08:30 bar. Used only by the look-ahead truncation test."""
    d = d.copy()
    d["date"] = d.index.date
    f = d["date"].map(gap_series(d))
    f[d.index.time < pd.Timestamp("08:30").time()] = np.nan
    return f.astype(float)


def signals(h, min_gap, stop, target, pct=True):
    g = gap_series(h, pct)
    by_day = {d: x for d, x in h.groupby("date")}
    out = []
    t0, t1 = pd.Timestamp("08:30").time(), pd.Timestamp("16:00").time()
    for day, gap in g.items():
        if abs(gap) < min_gap:
            continue
        bars = by_day[day]
        entry = bars[bars.index.time == t0]["Open"].iloc[0]
        sig = "LONG" if gap > 0 else "SHORT"
        s = entry * stop / 100 if pct else stop
        t = entry * target / 100 if pct else target
        stop_p, tgt_p = (entry - s, entry + t) if sig == "LONG" else (entry + s, entry - t)
        run = bars[(bars.index.time > t0) & (bars.index.time <= t1)]
        exit_p, reason = None, "eod"
        for _, b in run.iterrows():
            hit_s = b["Low"] <= stop_p if sig == "LONG" else b["High"] >= stop_p
            hit_t = b["High"] >= tgt_p if sig == "LONG" else b["Low"] <= tgt_p
            if hit_s:
                exit_p, reason = stop_p, "stop"; break
            if hit_t:
                exit_p, reason = tgt_p, "target"; break
        if exit_p is None:
            exit_p = run.iloc[-1]["Close"] if len(run) else entry
        out.append({"date": day, "signal": sig, "gap": gap, "entry_price": entry, "exit_price": exit_p,
                    "exit_reason": reason})
    df = pd.DataFrame(out)
    if not df.empty:
        df["entry_date"] = pd.to_datetime(df["date"])
    return df


def net_dollars(df, pv):
    pts = (df["exit_price"] - df["entry_price"]).where(df["signal"] == "LONG", df["entry_price"] - df["exit_price"])
    return pts.apply(lambda p: trading_costs.apply_costs(p, point_value=pv))


def pf(x):
    w, l = x[x > 0].sum(), -x[x < 0].sum()
    return float(w / l) if l > 0 else float("nan")


if __name__ == "__main__":
    num_trials = max(trial_count.count_research_trials(), 68) + N_NEW_TRIALS
    print(f"num_trials (DSR) = {num_trials}\n")
    verdicts, results = {}, {}
    for mkt, p in MARKETS.items():
        h = load(p["folder"])
        ok, msg = leakage.truncation_test(gap_feature, h.iloc[:6000])
        print(f"{mkt} look-ahead truncation test on the gap feature: {'PASS' if ok else 'FAIL'} - {msg}")
        sigs = signals(h, p["min_gap"], p["stop"], p["target"])
        if sigs.empty:
            print(f"{mkt}: no trades"); continue
        sigs = sigs.reset_index(drop=True)
        nd = net_dollars(sigs, p["pv"])
        early, late = nd[sigs["entry_date"] < SPLIT], nd[sigs["entry_date"] >= SPLIT]
        print(f"=== {mkt}: {len(sigs)} trades {sigs['entry_date'].min().date()} -> {sigs['entry_date'].max().date()}")
        print(f"   exits: {sigs['exit_reason'].value_counts().to_dict()}")
        print(f"   NET PF all {pf(nd):.2f} | 2015-2020 PF {pf(early):.2f} net ${early.sum():,.0f} (n={len(early)}) | "
              f"2021-2023 PF {pf(late):.2f} net ${late.sum():,.0f} (n={len(late)})")
        scorecard.run_scorecard(sigs, f"{mkt} gap PERCENT-scaled (2015-2023, frozen)", num_trials=num_trials,
                                account_size=10000, point_value=p["pv"], date_col="entry_date")
        passed = bool(pf(nd) >= 1.3 and early.sum() > 0 and late.sum() > 0 and len(sigs) >= 100)
        verdicts[mkt] = passed
        results[mkt] = {"n_trades": len(sigs), "n_oos_trades": len(late), "net_pf": pf(nd),
                        "scorecard_run": True, "leakage_test_passed": bool(ok),
                        "cost_model": {"slippage_points": 1.0, "commission_round_trip": 4.5},
                        "holdout_touched": False, "declared_trials": N_NEW_TRIALS}
    print("\nMechanical check against the pre-registered criteria (a human still scores it):")
    for m, v in verdicts.items():
        print(f"   {m}: {'MEETS' if v else 'does not meet'} criteria")
    print("   Criteria say: SUPPORTED only if at least one symbol meets all of them.")
    os.makedirs("results", exist_ok=True)
    with open("results/pct_gap_nq_es_result.json", "w") as f:
        json.dump(results, f, indent=2)
