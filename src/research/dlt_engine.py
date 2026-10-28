"""
Engine for the diversified_lowturnover family: canonical time-series and cross-sectional momentum on daily futures.
Pure functions, no I/O, no trading. Everything is fixed here; a different value is a NEW trial, not a tweak.

CANONICAL RULES (registry/families.json parameter_rule: canonical only)
  score(t)   = sum of daily log returns over days t-L+1 .. t-21   (L = 21*months; the last ~month is skipped)
  vol(t)     = 60-day std of daily returns * sqrt(252)            (known at t)
  tsmom      : weight = sign(score) * (TARGET_VOL / vol) / n_active, per-asset leverage capped at MAX_LEV
  xsmom      : within each asset class, rank by score; top half long, bottom half short (odd middle = 0), same vol scaling
  rebalance  : last trading day of each month; weights held until the next one
  lag        : weights decided on day t earn the return of day t+1 and later (never day t)
COSTS (family cost model): 1 bp of traded notional + $4.50 per contract traded. Contracts = traded notional / (price * multiplier),
  so commission as a fraction of capital = |dw| * 4.5 / (price * multiplier); capital cancels out.
Roll days: returns come from futures_daily.returns (roll-day return set to 0).
"""
import numpy as np
import pandas as pd

TARGET_VOL = 0.10
VOL_WINDOW = 60
MAX_LEV = 3.0
SKIP_DAYS = 21
SLIPPAGE_BPS = 1.0
COMMISSION = 4.5
ANN = 252

MULTIPLIER = {  # dollars per 1.00 of quoted price
    "ES": 50, "NQ": 20, "YM": 5, "RTY": 50, "ZN": 1000, "ZB": 1000, "ZF": 1000, "CL": 1000, "NG": 10000,
    "GC": 100, "SI": 5000, "HG": 25000, "6E": 125000, "6J": 12500000, "6B": 62500, "6A": 100000,
    "ZC": 50, "ZS": 50, "ZW": 50,   # grain prices are quoted in cents/bushel, 5000 bu contract = $50 per quoted point
}
CLASSES = {
    "equity_index": ["ES", "NQ", "YM", "RTY"], "rates": ["ZN", "ZB", "ZF"], "energy": ["CL", "NG"],
    "metals": ["GC", "SI", "HG"], "fx": ["6E", "6J", "6B", "6A"], "ags": ["ZC", "ZS", "ZW"],
}


def momentum_score(close_or_ret, months, ret_input=True):
    """Sum of daily log returns over days t-L+1..t-SKIP_DAYS. Uses only data up to t."""
    lr = np.log1p(close_or_ret) if ret_input else np.log(close_or_ret).diff()
    L = 21 * months
    return lr.shift(SKIP_DAYS).rolling(L - SKIP_DAYS, min_periods=L - SKIP_DAYS).sum()


def realized_vol(rets):
    return rets.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(ANN)


def month_end_flags(index):
    """True on the last trading day of each calendar month present in the index."""
    s = pd.Series(index, index=index)
    return pd.Series(s.dt.to_period("M").values != s.shift(-1).dt.to_period("M").values, index=index)


def target_weights(rets, months, kind, classes=CLASSES, score=None):
    """Daily DataFrame of the weights DECIDED at each date's close (before any lag). NaN where not tradable.
    kinds: tsmom / xsmom (score = trailing momentum) and tscarry / xscarry (score = the carry panel passed in, positive = long)."""
    if kind in ("tscarry", "xscarry"):
        if score is None:
            raise ValueError("carry kinds need the carry panel as `score`")
        score = score.reindex(index=rets.index, columns=rets.columns)
    else:
        score = momentum_score(rets, months)
    vol = realized_vol(rets)
    scale = (TARGET_VOL / vol).clip(upper=MAX_LEV)
    if kind in ("tsmom", "tscarry"):
        sig = np.sign(score)
    elif kind in ("xsmom", "xscarry"):
        sig = pd.DataFrame(0.0, index=rets.index, columns=rets.columns)
        for cols in classes.values():
            cols = [c for c in cols if c in rets.columns]
            if len(cols) < 2:
                continue
            sc = score[cols]
            rank = sc.rank(axis=1, method="first")
            n = sc.notna().sum(axis=1)
            half = (n // 2)
            long_ = rank.gt(n - half, axis=0)
            short_ = rank.le(half, axis=0)
            part = long_.astype(float) - short_.astype(float)
            part[sc.isna()] = np.nan
            part[n < 2] = np.nan
            sig[cols] = part
        sig = sig.where(score.notna())
    else:
        raise ValueError("kind must be tsmom, xsmom, tscarry or xscarry")
    raw = sig * scale
    n_active = raw.abs().gt(0).sum(axis=1).clip(lower=1)
    return raw.div(n_active, axis=0).where(raw.notna())


def monthly_weights(w_daily):
    """Hold the month-end weights until the next month end; flat (0) until the first valid month end."""
    flags = month_end_flags(w_daily.index)
    held = w_daily.fillna(0.0).copy()          # an asset with no valid signal at a month end is flat, not carried
    held.loc[~flags.values] = np.nan
    return held.ffill().fillna(0.0)


def run_weights(w_decided, rets, prices, slippage_bps=SLIPPAGE_BPS, commission=COMMISSION):
    """Shared by every strategy: weights decided at day t's close earn from t+1 (one-day lag), costs on every weight change."""
    w = w_decided.shift(1).fillna(0.0)
    gross = (w * rets.fillna(0.0)).sum(axis=1)
    dw = w.diff().abs().fillna(w.abs())
    slip = (dw.sum(axis=1)) * slippage_bps / 1e4
    mult = pd.Series({c: MULTIPLIER[c] for c in rets.columns})
    per_contract = prices.reindex_like(rets).ffill() * mult   # dollars of notional per contract
    comm = (dw * (commission / per_contract)).fillna(0.0).sum(axis=1)
    net = gross - slip - comm
    return pd.DataFrame({"gross": gross, "net": net, "turnover": dw.sum(axis=1), "cost": slip + comm}), w


def backtest(rets, prices, months, kind, classes=CLASSES, slippage_bps=SLIPPAGE_BPS, commission=COMMISSION, score=None):
    """Returns a DataFrame of daily gross/net returns plus weights/turnover. Weights decided at t earn from t+1."""
    w_decided = monthly_weights(target_weights(rets.copy(), months, kind, classes, score))
    return run_weights(w_decided, rets, prices, slippage_bps, commission)


def sharpe(r):
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std() * np.sqrt(ANN)) if len(r) > 2 and r.std() > 0 else 0.0


def max_drawdown(r):
    eq = (1 + pd.Series(r).fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())
