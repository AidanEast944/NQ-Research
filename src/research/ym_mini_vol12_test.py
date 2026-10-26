"""
PRE-REGISTERED test (lab spec ym_mini_vol12, lab/proposals/ym_mini_vol12.json, approved by Aidan 2026-10-25):
live volume-filtered YM gap rule on a MINI contract ($5/pt), formal 7-check scorecard, 2015-2023 only.
Nothing here may be tuned after the run.

FROZEN RULES: gap = 08:30 ET bar open minus prior day's last close (points); |gap| >= 30; continuation direction;
only if the 08:30 bar volume >= 1.2x its trailing 20-day average (shifted one day, min 10 days, same as strategy.py);
stop 40 pts, target 80 pts, exit by 16:00 ET close; stop checked before target within a bar. Point value $5.
Costs: project default (1 pt slippage + $4.50 round trip) via trading_costs.apply_costs.

DISCLOSURE: NOT a blind test. Entry 81 (results/cost_sensitivity_output.txt) already showed this slice at about
net PF 1.36 on mini, and the 1.2x threshold was chosen after seeing 2024+ data. This adds the formal scorecard
and a trial-adjusted Deflated Sharpe Ratio. It is not new out-of-sample evidence.

TRIALS DECLARED: 1. num_trials for the DSR = max(trial_count, 68) + 1.

PASS CRITERIA (set in advance):
  conditions: net PF >= 1.3 on 2015-2023 AND net total positive in BOTH 2015-2020 and 2021-2023 AND >= 100 trades
  SUPPORTED    = all conditions met AND scorecard Check 7 (Deflated Sharpe Ratio) passes
  INCONCLUSIVE = conditions met but the DSR check fails
  NOT SUPPORTED = any condition fails

Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run ym_mini_vol12
"""
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "src/lab")
sys.path.insert(0, "src/research")
import scorecard
import trial_count
import leakage
import pct_gap_nq_es_test as base   # frozen, committed helpers: load(), signals(), net_dollars(), pf()

FOLDER = "data/raw_ym_extended"
MIN_GAP, STOP, TARGET, PV, VOL_MIN, LOOKBACK = 30, 40, 80, 5, 1.2, 20
START, END, SPLIT = pd.Timestamp("2015-01-01"), pd.Timestamp("2023-12-31"), pd.Timestamp("2021-01-01")
N_NEW_TRIALS = 1


def vol_ratio_by_date(h):
    e = h[h.index.time == pd.Timestamp("08:30").time()]
    v = e.groupby("date")["Volume"].first()
    return v / v.rolling(LOOKBACK, min_periods=max(5, LOOKBACK // 2)).mean().shift(1)


def vol_feature(d):
    """Volume ratio per bar, NaN before the 08:30 bar. Used only for the look-ahead truncation test."""
    d = d.copy()
    d["date"] = d.index.date
    f = d["date"].map(vol_ratio_by_date(d))
    f[d.index.time < pd.Timestamp("08:30").time()] = np.nan
    return f.astype(float)


def build_signals(h):
    s = base.signals(h, MIN_GAP, STOP, TARGET, pct=False)
    s["vr"] = s["date"].map(vol_ratio_by_date(h))
    return s[s["vr"] >= VOL_MIN].reset_index(drop=True)   # NaN ratios drop out, same as strategy.py


if __name__ == "__main__":
    num_trials = max(trial_count.count_research_trials(), 68) + N_NEW_TRIALS
    print(f"num_trials (DSR) = {num_trials}\n")
    h = base.load(FOLDER, START, END)
    ok, msg = leakage.truncation_test(vol_feature, h.iloc[:6000])
    print(f"YM look-ahead truncation test on the volume feature: {'PASS' if ok else 'FAIL'} - {msg}")
    sigs = build_signals(h)
    nd = base.net_dollars(sigs, PV)
    early, late = nd[sigs["entry_date"] < SPLIT], nd[sigs["entry_date"] >= SPLIT]
    print(f"=== YM mini vol>=1.2x: {len(sigs)} trades {sigs['entry_date'].min().date()} -> {sigs['entry_date'].max().date()}")
    print(f"   exits: {sigs['exit_reason'].value_counts().to_dict()}")
    print(f"   NET PF all {base.pf(nd):.2f} | 2015-2020 PF {base.pf(early):.2f} net ${early.sum():,.0f} (n={len(early)}) | "
          f"2021-2023 PF {base.pf(late):.2f} net ${late.sum():,.0f} (n={len(late)})")
    res = scorecard.run_scorecard(sigs, "YM MINI gap vol>=1.2x (2015-2023, frozen)", num_trials=num_trials,
                                  account_size=10000, point_value=PV, date_col="entry_date")
    conds = bool(base.pf(nd) >= 1.3 and early.sum() > 0 and late.sum() > 0 and len(sigs) >= 100)
    print(f"\nMechanical check: conditions {'MET' if conds else 'NOT met'} "
          f"(PF>=1.3, both halves positive, >=100 trades).")
    print("Criteria: SUPPORTED needs conditions AND DSR pass; conditions met but DSR fail = INCONCLUSIVE; else NOT SUPPORTED.")
    print("A human reads Check 7 in the scorecard above and scores it.")
    os.makedirs("results", exist_ok=True)
    with open("results/ym_mini_vol12_result.json", "w") as f:
        json.dump({"YM": {"n_trades": len(sigs), "n_oos_trades": int((sigs["entry_date"] >= SPLIT).sum()),
                          "net_pf": base.pf(nd), "scorecard_run": True, "leakage_test_passed": bool(ok),
                          "cost_model": {"slippage_points": 1.0, "commission_round_trip": 4.5},
                          "holdout_touched": False, "declared_trials": N_NEW_TRIALS}}, f, indent=2)
