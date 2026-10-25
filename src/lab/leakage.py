"""Deterministic look-ahead detection.

truncation_test: a feature computed at time t may only use data up to t. Compute the feature on the
full series, then recompute on the series truncated at several cut points; every value at or before
the cut must be identical. Any difference means the feature peeked at the future.
"""
import numpy as np
import pandas as pd


def truncation_test(feature_fn, df, n_cuts=5, min_rows=30):
    """feature_fn(df) -> Series aligned to df.index. Returns (passed, details)."""
    full = feature_fn(df)
    n = len(df)
    if n < min_rows * 2:
        return False, "not enough rows to test"
    cuts = np.linspace(min_rows, n - 1, n_cuts).astype(int)
    for c in cuts:
        part = feature_fn(df.iloc[:c])
        a = full.iloc[:c]
        b = part.iloc[:c]
        both = pd.concat([a, b], axis=1).dropna()
        if len(both) and not np.allclose(both.iloc[:, 0].values, both.iloc[:, 1].values, equal_nan=True):
            first = both.index[(both.iloc[:, 0] - both.iloc[:, 1]).abs().values > 1e-9][0]
            return False, f"feature changed at {first} when data after row {c} was removed (look-ahead)"
        # NaN-vs-value mismatch also leaks
        mism = (a.isna() != b.isna()).any()
        if mism and len(a) == len(b):
            nan_a, nan_b = a.isna().values, b.isna().values
            # a value present in truncated but NaN in full (or vice versa) is a leak signal
            if (nan_a != nan_b).any():
                return False, f"feature availability changed when data after row {c} was removed (look-ahead)"
    return True, f"identical across {len(cuts)} truncation points"
