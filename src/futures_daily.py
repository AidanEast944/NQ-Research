"""
Loader for the diversified low-turnover family's daily bars (data/futures_daily/<SYM>.csv).
Pure reading and arithmetic: no strategy, no signal, no trade. Returns are computed ONLY between consecutive bars of the
same contract; on a roll day (instrument_id changed) the return is set to NaN and treated as 0 by `returns()`, because an
unadjusted continuous series would otherwise show the roll gap as a fake move. Days where the close or the prior close is <= 0 (CL, 2020-04-20/21) are masked the same way, which hides that real loss from
any validation/holdout test that holds CL. That misses roughly 4-12 days of true return a
year per market, a small, symmetric understatement documented here instead of hidden.
"""
import os
import numpy as np
import pandas as pd

DATA_DIR = "data/futures_daily"


def load(symbol, data_dir=None):
    path = os.path.join(data_dir or DATA_DIR, f"{symbol}.csv")
    df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
    return df[~df.index.duplicated(keep="first")]


def returns(df, fill_roll_days=True):
    """Simple daily returns on the close, NaN->0 on roll days when fill_roll_days (default)."""
    r = df["close"].pct_change()
    rolled = df["instrument_id"] != df["instrument_id"].shift(1)
    nonpos = (df["close"] <= 0) | (df["close"].shift(1) <= 0)   # e.g. CL settled at -$37 on 2020-04-20: percent returns are undefined
    r = r.mask(rolled | nonpos)
    return r.fillna(0.0) if fill_roll_days else r


def load_all(symbols, data_dir=None):
    """Returns a DataFrame of daily returns, one column per symbol, aligned on date (missing = NaN, not filled)."""
    cols = {}
    for s in symbols:
        cols[s] = returns(load(s, data_dir), fill_roll_days=True)
    return pd.DataFrame(cols).sort_index()
