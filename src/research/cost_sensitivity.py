"""
DESCRIPTIVE cost-sensitivity analysis of the LIVE gap rules (no new hypothesis, no tuning, no trial used).
Question: how much does the cost assumption (slippage points, commission per round trip, micro vs mini contract)
decide whether the live rules look viable? Rules are the frozen live point rules; periods 2015-2023 and 2024-2026.
Per trade cost in POINTS = slippage_points + commission_round_trip / point_value, so a mini contract (bigger point value)
pays far less cost per point than a micro for the same commission.
Run: python3 src/research/cost_sensitivity.py
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "src/research")
import pct_gap_nq_es_test as t

MARKETS = {  # folder, min gap, stop, target (live point rules); point values micro / mini
    "NQ": ("data/raw_nq_extended", 30, 40, 80, 2, 20),
    "ES": ("data/raw_es_extended", 6, 10, 20, 5, 50),
    "YM": ("data/raw_ym_extended", 30, 40, 80, 0.5, 5),
}
SCENARIOS = [("project default (1pt slip, $4.50)", 1.0, 4.5), ("0.5pt slip, $2.00", 0.5, 2.0),
             ("0.25pt slip, $1.00", 0.25, 1.0), ("zero costs", 0.0, 0.0)]


def vol_ratio(h, lookback=20):
    e = h[h.index.time == pd.Timestamp("08:30").time()]
    v = e.groupby("date")["Volume"].first()
    return v / v.rolling(lookback, min_periods=max(5, lookback // 2)).mean().shift(1)


def pf(x):
    w, l = x[x > 0].sum(), -x[x < 0].sum()
    return float(w / l) if l > 0 else float("nan")


for mkt, (folder, mg, st, tg, pv_micro, pv_mini) in MARKETS.items():
    h = t.load(folder, pd.Timestamp("2015-01-01"), pd.Timestamp("2026-12-31"))
    sig = t.signals(h, mg, st, tg, pct=False)
    sig["pts"] = (sig["exit_price"] - sig["entry_price"]).where(sig["signal"] == "LONG", sig["entry_price"] - sig["exit_price"])
    sig["vr"] = sig["date"].map(vol_ratio(h))
    for period, mask in (("2015-2023", sig["entry_date"] < "2024-01-01"), ("2024-2026", sig["entry_date"] >= "2024-01-01")):
        for var, vm in (("unfiltered", sig["vr"].notna() | True), ("vol>=1.2x", sig["vr"] >= 1.2), ("vol>=1.5x", sig["vr"] >= 1.5)):
            d = sig[mask & vm]
            if len(d) < 20:
                continue
            g = d["pts"]
            print(f"\n{mkt} {period} {var}: n={len(d)}  gross {g.mean():+.2f} pts/trade (PF {pf(g):.2f})  "
                  f"= ${g.mean()*pv_micro:+.2f} micro / ${g.mean()*pv_mini:+.2f} mini per trade")
            for label, slip, comm in SCENARIOS:
                for contract, pv in (("micro", pv_micro), ("mini", pv_mini)):
                    c = slip + comm / pv
                    net = g - c
                    print(f"     {label:<34} {contract:<5} cost {c:5.2f} pts  net {net.mean():+7.2f} pts  PF {pf(net):.2f}")
            print(f"     breakeven cost per trade = {g.mean():.2f} pts (project default is "
                  f"{1.0+4.5/pv_micro:.2f} pts micro / {1.0+4.5/pv_mini:.2f} pts mini)")
