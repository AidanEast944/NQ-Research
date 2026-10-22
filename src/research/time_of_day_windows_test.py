"""
PRE-REGISTERED time-of-day window scan. Written and committed BEFORE it is run; nothing here may be changed
after seeing output. This asks one question: is there a time-of-day window whose average move is large enough,
and stable enough, to survive trading costs? It is an edge-EXISTENCE test, not a strategy backtest.

WINDOWS (Eastern time, trading day runs 18:00 -> 18:00; the Sunday evening session belongs to Monday):
  ASIA 18:00-02:00 | EUROPE 02:00-08:30 | PRE 08:30-09:30 | OPEN 09:30-10:30 | MID 10:30-12:00 |
  LUNCH 12:00-14:00 | AFTERNOON 14:00-15:00 | CLOSE 15:00-16:00
  (8:30 ET is the economic-data release; 9:30 ET is the stock-market open; 16:00 ET is the cash close.)
For every window and market (NQ, ES, YM) the measured quantity is the percent move from the first bar's open to
the last bar's close, so the unit is scale-free across 2015 (NQ ~4,500) and 2026 (~30,000).

TRIALS DECLARED: 8 (the windows). The three markets are replication of the same idea, not extra search.
24 window-market tests are run, so the significance bar is Bonferroni-adjusted: two-sided alpha 0.05/24 -> |t| >= 3.1.

DISCOVERY era 2015-01-01 -> 2023-12-31.  CONFIRMATION era 2024-01-01 -> today.
The direction of a window (long or short) is the sign of its discovery-era mean and is then fixed.
Costs: 1 point of slippage + $4.50 round trip on the micro contract (MNQ $2, MES $5, MYM $0.50 per point), converted to
percent of the window's opening price each day.

A window is a CANDIDATE only if ALL hold (set in advance):
  (1) discovery |t| >= 3.1 for that market
  (2) mean move in its direction exceeds costs (net mean > 0) in discovery
  (3) same direction has net mean > 0 AND t > 0 in the confirmation era
  (4) at least one OTHER market shows the same direction with discovery |t| >= 2.0
Anything that fails any condition is not a finding. A candidate is not a strategy: it earns a separately
pre-registered, scorecarded strategy test with real entry, stop and exit rules, using more trials.
Beta caveat: index futures drift upward, so long windows can look significant from that alone; condition (2) and
the confirmation era are what keep that honest.

Run:  python3 -u src/research/time_of_day_windows_test.py 2>&1 | tee results/tod_windows_output.txt
(Use research_runner.py to run it so the trial ledger and the commit check are enforced.)
Smoke test of the code path only:  --smoke  (uses a few months around 2024-01-01 and means nothing).
"""
import glob
import math
import os
import sys

import numpy as np
import pandas as pd

CUTOFF = pd.Timestamp("2024-01-01").date()
MARKETS = {"NQ": ("data/raw_nq_extended", 2), "ES": ("data/raw_es_extended", 5), "YM": ("data/raw_ym_extended", 0.5)}
# (name, start, end) in Eastern clock minutes
WINDOWS = [("ASIA", "18:00", "02:00"), ("EUROPE", "02:00", "08:30"), ("PRE", "08:30", "09:30"),
           ("OPEN", "09:30", "10:30"), ("MID", "10:30", "12:00"), ("LUNCH", "12:00", "14:00"),
           ("AFTERNOON", "14:00", "15:00"), ("CLOSE", "15:00", "16:00")]
SLIP_PTS, COMM = 1.0, 4.50
T_BONF, T_REPL = 3.1, 2.0


def clock_min(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def shifted(s):  # minutes since 18:00 Eastern
    return (clock_min(s) + 360) % 1440


def load(folder, smoke):
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if smoke:
        files = [f for f in files if "2023-11" <= os.path.basename(f)[-14:-7] <= "2024-02"]
    df = pd.concat([pd.read_csv(f, index_col="Datetime") for f in files])
    df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    sh = df.index + pd.Timedelta(hours=6)
    df["day"] = [d.date() for d in sh.floor("D")]
    df["smin"] = sh.hour * 60 + sh.minute
    return df


def window_returns(df, start, end, pv):
    a, b = shifted(start), shifted(end)
    if b == 0:
        b = 1440
    sel = df[(df["smin"] >= a) & (df["smin"] < b)]
    expected = (b - a) // 15
    g = sel.groupby("day")
    out = pd.DataFrame({"open": g["Open"].first(), "close": g["Close"].last(), "n": g["Open"].size(),
                        "first_min": g["smin"].first()})
    out = out[(out["n"] >= 0.8 * expected) & (out["first_min"] <= a + 15)]
    out = out[[d.weekday() < 5 for d in pd.to_datetime(out.index)]]
    out["ret"] = (out["close"] - out["open"]) / out["open"] * 100
    out["cost"] = (SLIP_PTS + COMM / pv) / out["open"] * 100
    return out


def tstat(x):
    x = np.asarray(x, dtype=float)
    if len(x) < 30 or x.std(ddof=1) == 0:
        return float("nan")
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))


if __name__ == "__main__":
    smoke = "--smoke" in sys.argv
    rows = {}
    for mkt, (folder, pv) in MARKETS.items():
        print(f"loading {mkt} ...", flush=True)
        df = load(folder, smoke)
        for name, s, e in WINDOWS:
            w = window_returns(df, s, e, pv)
            A, B = w[w.index < CUTOFF], w[w.index >= CUTOFF]
            tA = tstat(A["ret"])
            d = 1 if (len(A) and A["ret"].mean() >= 0) else -1
            netA = (d * A["ret"] - A["cost"]).mean() if len(A) else float("nan")
            netB = (d * B["ret"] - B["cost"]).mean() if len(B) else float("nan")
            tB = tstat(d * B["ret"]) if len(B) else float("nan")
            rows[(mkt, name)] = dict(d=d, nA=len(A), nB=len(B), mA=A["ret"].mean() if len(A) else float("nan"),
                                     tA=tA, netA=netA, netB=netB, tB=tB)
    print("\nWINDOW SCAN (percent moves; direction fixed from the discovery era)")
    print(f"{'mkt':<4}{'window':<10}{'dir':>5}{'nDisc':>7}{'mean%':>8}{'t':>7}{'netDisc%':>10}{'nConf':>7}{'netConf%':>10}{'tConf':>7}")
    for (mkt, name), r in rows.items():
        print(f"{mkt:<4}{name:<10}{('LONG' if r['d']>0 else 'SHORT'):>5}{r['nA']:>7}{r['mA']:>8.4f}{r['tA']:>7.2f}"
              f"{r['netA']:>10.4f}{r['nB']:>7}{r['netB']:>10.4f}{r['tB']:>7.2f}")
    print("\nCANDIDATES under the pre-registered rule (all four conditions):")
    found = False
    for (mkt, name), r in rows.items():
        c1 = abs(r["tA"]) >= T_BONF
        c2 = r["netA"] > 0
        c3 = r["netB"] > 0 and r["tB"] > 0
        c4 = any(o != mkt and rows[(o, name)]["d"] == r["d"] and abs(rows[(o, name)]["tA"]) >= T_REPL for o in MARKETS)
        if c1 and c2 and c3 and c4:
            found = True
            print(f"  {mkt} {name} {'LONG' if r['d']>0 else 'SHORT'}")
    if not found:
        print("  none")
    print("\nJudge ONLY against the pass criteria in this file's docstring.")
