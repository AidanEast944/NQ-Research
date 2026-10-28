"""
Carry (roll yield) from the front and second futures contracts. Pure functions; no trading.

carry_t = ln(P_front / P_second) * 365 / spacing_t     (annualized; positive = backwardation = long earns the roll yield)
spacing_t = days between the previous two front-contract rolls, i.e. the cycle gap between consecutive contracts, read ONLY from
  past instrument_id changes, so it is known at t (an exact expiry calendar would need extra data; this proxy is documented, not hidden).
signal   = mean of carry over the last 5 trading days (fixed, one value, reduces single-day noise at roll days).
Rolls use the calendar-roll continuous series (.c.0 / .c.1) so both legs always roll together.
"""
import numpy as np
import pandas as pd

SMOOTH_DAYS = 5
MIN_SPACING, MAX_SPACING = 20, 200       # sanity band; outside it the spacing is treated as unknown (carry NaN)


def spacing_days(front):
    """Days between the previous two instrument_id changes of the front series, known at each date. NaN until two rolls have happened."""
    roll = front["instrument_id"] != front["instrument_id"].shift(1)
    roll.iloc[0] = False
    dates = pd.Series(front.index, index=front.index)
    # the gap between the two most recent rolls: at a roll date, (this roll - previous roll); then carried until the next roll
    roll_dates = dates[roll]
    gap = (roll_dates - roll_dates.shift(1)).dt.days
    sp = pd.Series(np.nan, index=front.index)
    sp[roll_dates.index] = gap.values
    sp = sp.ffill()
    return sp.where((sp >= MIN_SPACING) & (sp <= MAX_SPACING))


def carry_series(front, second, smooth=SMOOTH_DAYS):
    """front, second: daily frames with 'close' (front also 'instrument_id'). Returns the smoothed annualized carry, indexed like front."""
    p1 = second["close"].reindex(front.index).ffill(limit=5)
    ratio = np.log(front["close"] / p1)
    ratio = ratio.where((front["close"] > 0) & (p1 > 0))
    ann = ratio * 365.0 / spacing_days(front)
    return ann.rolling(smooth, min_periods=smooth).mean()


def carry_panel(fronts, seconds, index=None):
    """dict symbol -> frame, for both legs. Returns a DataFrame (one column per symbol) on the union calendar; NaN where unknown."""
    cols = {s: carry_series(fronts[s], seconds[s]) for s in fronts}
    df = pd.DataFrame(cols).sort_index()
    return df.reindex(index) if index is not None else df
