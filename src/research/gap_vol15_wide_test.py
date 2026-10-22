"""
PRE-REGISTERED single-variant test: volume-confirmed gap, STRICTER filters. Written and committed
BEFORE it is run. Nothing here may be changed after seeing output.

VARIANT (one, fixed in advance, same for all three markets):
  volume ratio >= 1.5x (instead of 1.2x)  AND  min gap = 1.5 x the frozen min gap
  NQ and YM: min gap 45 (was 30);  ES: min gap 9 (was 6).  Stops/targets/entry time unchanged
  (NQ/YM 40/80, ES 10/20; 08:30 ET entry, exit by 16:00).

HONESTY NOTE ON DATA: the 1.5x volume cut was already seen DESCRIPTIVELY on 2015-2023 (Entry 68), so
2015-2023 is NOT a clean development set for the volume threshold. It is reported for context. The
only genuinely unseen check is the 2024-01-01 -> present window, but the live strategies were designed
on that window, so it is not independent of them either. Expected 2024+ trade counts are small
(well under 100), so that window cannot be statistically confirmatory; it is directional only.

TRIALS DECLARED: 6 scorecards = 3 markets x {2015-2023, 2024+}. num_trials = max(count, 68) + 6 + 6 = 80
(the extra 6 are Entry 68's trials).

PASS CRITERIA (set in advance), per market:
  - 2015-2023: PF after costs >= 1.10 on >= 100 trades.
  - 2024+:     PF after costs >= 1.10 (direction only).
  Variant is "supported" for a market only if BOTH hold. If supported on >= 2 of 3 markets it earns a
  paper-only shadow track, NOT a LIVE_STRATEGIES entry. Anything else is logged as not supported.

Run:
    cd ~/nq-research && source venv/bin/activate
    python3 -u src/research/gap_vol15_wide_test.py 2>&1 | tee results/gap_vol15_wide_output.txt
(Expect several minutes of silence per market: the gap function rescans history per day.)
"""
import sys
import pandas as pd

sys.path.insert(0, "src")
import strategy
import scorecard
import trial_count

CUTOFF = pd.Timestamp("2024-01-01")
VOL_MIN = 1.5
MARKETS = {
    "NQ": dict(folder="data/raw_nq_extended", min_gap=45, stop=40, target=80, pv=2),
    "ES": dict(folder="data/raw_es_extended", min_gap=9, stop=10, target=20, pv=5),
    "YM": dict(folder="data/raw_ym_extended", min_gap=45, stop=40, target=80, pv=0.5),
}
SLIP_PTS, COMM = 1.0, 4.50


def pts(df):
    return (df["exit_price"] - df["entry_price"]).where(df["signal"] == "LONG",
                                                        df["entry_price"] - df["exit_price"])


def pf(x):
    w, l = x[x > 0].sum(), -x[x < 0].sum()
    return w / l if l > 0 else float("nan")


if __name__ == "__main__":
    num_trials = max(trial_count.count_research_trials(), 68) + 12
    print(f"num_trials (DSR) = {num_trials}\n")
    rows = []
    for mkt, p in MARKETS.items():
        sigs = strategy.get_weekday_open_gap_signals_with_volume_from_archive(
            min_gap_points=p["min_gap"], stop_points=p["stop"], target_points=p["target"],
            data_folder=p["folder"], volume_lookback=20)
        sigs["entry_date"] = pd.to_datetime(sigs["date"])
        sigs = sigs[sigs["volume_ratio"] >= VOL_MIN].reset_index(drop=True)
        for period, df in (("2015-2023", sigs[sigs["entry_date"] < CUTOFF]),
                           ("2024+", sigs[sigs["entry_date"] >= CUTOFF])):
            df = df.reset_index(drop=True)
            if len(df) == 0:
                print(f"{mkt} {period}: no trades")
                continue
            g = pts(df)
            net = g * p["pv"] - SLIP_PTS * p["pv"] - COMM
            rows.append((mkt, period, len(df), (g > 0).mean(), pf(g * p["pv"]), pf(net)))
            scorecard.run_scorecard(df, f"{mkt} gap vol>={VOL_MIN}x gap>={p['min_gap']} ({period})",
                                    num_trials=num_trials, account_size=10000,
                                    point_value=p["pv"], date_col="entry_date")
    print("\nSUMMARY (variant fixed in advance)")
    print(f"{'mkt':<4}{'period':<11}{'trades':>7}{'win%':>7}{'grossPF':>9}{'netPF':>8}")
    for m, per, n, w, gp, np_ in rows:
        print(f"{m:<4}{per:<11}{n:>7}{100*w:>6.0f}%{gp:>9.2f}{np_:>8.2f}")
    print("\nJudge ONLY against the pass criteria in this file's docstring.")
