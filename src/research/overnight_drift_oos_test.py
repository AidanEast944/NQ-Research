"""
PRE-REGISTERED out-of-sample test of overnight drift with a stop. Written and committed BEFORE running.

WHAT IS FROZEN: the rule from Entries 17/20 - LONG at the prior day's 16:00 ET close, exit at today's
08:30 ET open, with a stop checked bar-by-bar through the overnight session. No other filter.
  NQ (MNQ $2/pt):  stop 100 points (the Entry 20 value; ~0.5% of price)
  ES (MES $5/pt):  stop 25 points   (scaled to the same ~0.5%)
  YM (MYM $0.5/pt): stop 200 points (scaled to the same ~0.5%)
Stops are assumed to fill at the stop price. That is optimistic: overnight gaps and fast markets can fill
worse, so real results would be a little worse than anything printed here.

SAMPLE: the clean test window is 2015-01-01 -> 2023-12-31, which the strategy has never seen (Entry 20
used 2024-2026 only). 2024+ is printed DESCRIPTIVELY, not scorecarded and not counted as a trial.

TRIALS DECLARED: 4 scorecards on 2015-2023: NQ all weekdays, NQ Wednesday-only (the post-hoc Entry 20
finding, which already carried a multiple-comparisons caveat), ES all weekdays, YM all weekdays.
num_trials = max(68 + 6 + 6 + 4, trial_count + 4).

PASS CRITERIA (set in advance), per scorecard on 2015-2023:
  (a) >= 100 trades and PF after costs >= 1.10
  (b) max drawdown < 30% of a $10,000 account at 1 micro contract
  (c) the 5 biggest winning trades make up < 50% of total after-cost profit (Entry 20 found 92% - an edge
      carried by a handful of outliers is not an edge)
Supported only if all three hold. NQ-Wednesday additionally has to beat NQ-all-weekdays on after-cost PF,
otherwise it is just a slice of a result that already failed.

Run (slow: several minutes of silence per market):
    cd ~/nq-research && source venv/bin/activate
    python3 -u src/research/overnight_drift_oos_test.py 2>&1 | tee results/overnight_drift_oos_output.txt
"""
import sys
import pandas as pd

sys.path.insert(0, "src")
import strategy
import scorecard
import trial_count

CUTOFF = pd.Timestamp("2024-01-01")
MARKETS = {
    "NQ": dict(folder="data/raw_nq_extended", stop=100, pv=2),
    "ES": dict(folder="data/raw_es_extended", stop=25, pv=5),
    "YM": dict(folder="data/raw_ym_extended", stop=200, pv=0.5),
}
SLIP_PTS, COMM = 1.0, 4.50


def net_dollars(df, pv):
    pts = df["exit_price"] - df["entry_price"]  # always LONG
    return pts * pv - SLIP_PTS * pv - COMM


def pf(x):
    w, l = x[x > 0].sum(), -x[x < 0].sum()
    return w / l if l > 0 else float("nan")


def stats(df, pv):
    n = net_dollars(df, pv)
    total = n.sum()
    top5 = n.sort_values(ascending=False).head(5).sum()
    share = top5 / total if total > 0 else float("nan")
    return len(df), pf(n), total, share, n.median()


if __name__ == "__main__":
    num_trials = max(68 + 6 + 6 + 4, trial_count.count_research_trials() + 4)
    print(f"num_trials (DSR) = {num_trials}\n")
    summary = []
    nq_all_pf = None
    for mkt, p in MARKETS.items():
        sigs = strategy.get_overnight_drift_signals_with_stop_from_archive(
            data_folder=p["folder"], stop_points=p["stop"])
        sigs["entry_date"] = pd.to_datetime(sigs["date"])
        old = sigs[sigs["entry_date"] < CUTOFF].reset_index(drop=True)
        new = sigs[sigs["entry_date"] >= CUTOFF].reset_index(drop=True)
        slices = [(f"{mkt} overnight drift all weekdays", old)]
        if mkt == "NQ":
            slices.append(("NQ overnight drift Wednesday-only",
                           old[old["exit_weekday"] == "Wednesday"].reset_index(drop=True)))
        for name, df in slices:
            if df.empty:
                print(f"{name}: no trades")
                continue
            scorecard.run_scorecard(df, f"{name} (2015-2023, stop {p['stop']})", num_trials=num_trials,
                                    account_size=10000, point_value=p["pv"], date_col="entry_date")
            n, pfv, tot, share, med = stats(df, p["pv"])
            summary.append((name, n, pfv, tot, share, med))
        if not new.empty:
            n, pfv, tot, share, med = stats(new, p["pv"])
            print(f"(descriptive only) {mkt} 2024+: {n} trades, net PF {pfv:.2f}, total ${tot:,.0f}, top5 share {share:.0%}")
    print("\nSUMMARY (2015-2023, after costs, rules fixed in advance)")
    print(f"{'slice':<40}{'trades':>7}{'netPF':>7}{'net $':>10}{'top5%':>8}{'median$':>9}")
    for name, n, pfv, tot, share, med in summary:
        print(f"{name:<40}{n:>7}{pfv:>7.2f}{tot:>10,.0f}{share:>8.0%}{med:>9.1f}")
    print("\nJudge ONLY against the pass criteria in this file's docstring.")
