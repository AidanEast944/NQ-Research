"""
General-purpose bounded pattern scanner. Tests systematic combinations of features against
forward returns, always within a FIXED, enumerable search space - never open-ended mutation.
Every combination tested must be counted toward num_trials for any resulting strategy (see
research_log.md Entry 54 for the precedent this follows).

This produces CANDIDATES for human review, never automatically creates a strategy, logs a
research_log.md entry, or touches live_gate.py. A human must independently confirm a plausible
economic reason before any result here becomes real code.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import glob

def load_daily(data_folder="data/raw_nq_extended"):
    files = glob.glob(f"{data_folder}/*.csv")
    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    hist = pd.concat(all_days)
    hist = hist[~hist.index.duplicated(keep="first")]
    hist = hist.sort_index()
    hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
    hist["date"] = hist.index.date
    daily = hist.groupby("date").agg(close=("Close", "last"), high=("High", "max"),
                                       low=("Low", "min"), volume=("Volume", "sum"))
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def build_features(daily, lookback):
    """Each feature is computed for a given lookback - kept in one place so every scan uses
    consistent, well-defined feature logic rather than ad-hoc calculations per scan."""
    daily["range"] = daily["high"] - daily["low"]
    features = {}
    features["high_vol"] = daily["range"] > daily["range"].rolling(lookback).mean()
    features["low_vol"] = daily["range"] < daily["range"].rolling(lookback).mean() * 0.7
    features["momentum_up"] = daily["close"].pct_change(lookback) > daily["close"].pct_change(lookback).rolling(lookback).std()
    features["momentum_down"] = daily["close"].pct_change(lookback) < -daily["close"].pct_change(lookback).rolling(lookback).std()
    features["high_volume"] = daily["volume"] > daily["volume"].rolling(lookback).mean() * 1.3
    features["low_volume"] = daily["volume"] < daily["volume"].rolling(lookback).mean() * 0.7
    return features


def scan(data_folder="data/raw_nq_extended", lookbacks=(5, 10, 20), forward_windows=(1, 3, 5),
          min_observations=15):
    daily = load_daily(data_folder)
    results = []
    combos_tested = 0

    feature_names = ["high_vol", "low_vol", "momentum_up", "momentum_down", "high_volume", "low_volume"]

    for lb in lookbacks:
        features = build_features(daily.copy(), lb)
        for feat_a in feature_names:
            for feat_b in feature_names:
                if feat_a >= feat_b:
                    continue  # each unordered pair once, no self-pairing
                for fwd in forward_windows:
                    combos_tested += 1
                    condition = features[feat_a] & features[feat_b]
                    daily["fwd_return"] = daily["close"].shift(-fwd) / daily["close"] - 1
                    subset = daily[condition]["fwd_return"].dropna()
                    baseline = daily["fwd_return"].dropna()

                    if len(subset) < min_observations:
                        continue

                    results.append({
                        "lookback": lb, "feature_a": feat_a, "feature_b": feat_b, "forward_window": fwd,
                        "n": len(subset), "avg_fwd_pct": subset.mean() * 100,
                        "baseline_pct": baseline.mean() * 100, "diff_pct": (subset.mean() - baseline.mean()) * 100
                    })

    return pd.DataFrame(results), combos_tested


if __name__ == "__main__":
    results, total = scan()
    print(f"Total combinations tested: {total}")
    print(f"Combinations with {results['n'].min() if len(results) else 0}+ observations: {len(results)}\n")
    if len(results) > 0:
        top = results.reindex(results["diff_pct"].abs().sort_values(ascending=False).index)
        print(top.head(15).to_string(index=False))