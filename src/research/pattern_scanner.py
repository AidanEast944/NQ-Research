"""
Bounded pattern scanner - NOT an automated strategy generator. Tests a fixed, enumerable list of
feature/threshold combinations and reports raw statistical results for human review. Never creates
a strategy, never logs a research_log.md entry, never touches live_gate.py automatically - a human
must review each candidate and decide whether it has a plausible economic reason before it becomes
anything real.

Every single combination tested here counts toward num_trials, whether or not it's ever pursued -
see trial_count.py. This scanner itself gets logged as ONE research_log.md entry documenting the
full sweep, with the total combination count explicit in that entry, so a 50-combination scan
adds 50 to the honest trial count, not 1.
"""
import sys
sys.path.insert(0, "src")

import pandas as pd
import glob

def load_15m(folder):
    files = glob.glob(f"{folder}/*.csv")
    all_days = [pd.read_csv(f, index_col="Datetime", parse_dates=True) for f in files]
    hist = pd.concat(all_days)
    hist = hist[~hist.index.duplicated(keep="first")]
    hist = hist.sort_index()
    hist.index = pd.to_datetime(hist.index, utc=True).tz_convert("America/New_York")
    return hist

def scan_volatility_momentum_combos(data_folder="data/raw_nq_extended"):
    """Fixed, enumerable scan: for each (vol_lookback, momentum_lookback, forward_window)
    combination, check if high-volatility + strong-momentum bars predict forward returns."""
    hist = load_15m(data_folder)
    hist["date"] = hist.index.date
    daily = hist.groupby("date").agg(close=("Close", "last"), high=("High", "max"), low=("Low", "min"))
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    daily["range"] = daily["high"] - daily["low"]

    results = []
    combos_tested = 0

    for vol_lb in [5, 10, 20]:
        for mom_lb in [3, 5, 10]:
            for fwd in [1, 3, 5]:
                combos_tested += 1
                daily["vol_avg"] = daily["range"].rolling(vol_lb).mean()
                daily["high_vol"] = daily["range"] > daily["vol_avg"]
                daily["momentum"] = daily["close"].pct_change(mom_lb)
                daily["strong_up_momentum"] = daily["momentum"] > daily["momentum"].rolling(vol_lb).std()
                daily["fwd_return"] = daily["close"].shift(-fwd) / daily["close"] - 1

                condition = daily["high_vol"] & daily["strong_up_momentum"]
                subset = daily[condition]["fwd_return"].dropna()
                baseline = daily["fwd_return"].dropna()

                if len(subset) < 10:
                    continue

                results.append({
                    "vol_lookback": vol_lb, "momentum_lookback": mom_lb, "forward_window": fwd,
                    "n": len(subset), "avg_fwd_return_pct": subset.mean() * 100,
                    "baseline_avg_pct": baseline.mean() * 100,
                    "diff_pct": (subset.mean() - baseline.mean()) * 100
                })

    return pd.DataFrame(results), combos_tested

if __name__ == "__main__":
    results, total_combos = scan_volatility_momentum_combos()
    print(f"Total combinations tested: {total_combos}")
    print(f"Combinations with 10+ observations: {len(results)}\n")
    results_sorted = results.reindex(results["diff_pct"].abs().sort_values(ascending=False).index)
    print(results_sorted.head(10).to_string(index=False))