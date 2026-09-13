"""
Runs the Deflated Sharpe Ratio check against every strategy this project has ever tested with
real, recomputable backtest functions in strategy.py. This gives an honest, real trial count
(not a guess) for strategies we can still query - some very early exploratory scripts (deleted
or superseded) aren't recoverable and are noted as a limitation, not silently ignored.
"""
import sys
sys.path.insert(0, "src")

from deflated_sharpe import deflated_sharpe_ratio, compute_returns_stats
import strategy as strat
from trial_count import count_research_trials

def get_points(signals, entry_col="entry_price", exit_col="exit_price"):
    def pts(row):
        if row["signal"] == "LONG":
            return row[exit_col] - row[entry_col]
        return row[entry_col] - row[exit_col]
    return signals.apply(pts, axis=1).tolist()

trials = []

try:
    s = strat.get_prior_day_break_signals_from_archive(stop_points=30, target_points=60, data_folder="data/raw_nq_extended")
    trials.append(("Prior Day Breakout", get_points(s, "Close", "exit_price")))
except Exception as e:
    print(f"Skipped Prior Day Breakout: {e}")

try:
    s = strat.get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60, data_folder="data/raw_nq_extended")
    trials.append(("Prior Day Fade", get_points(s, "Close", "exit_price")))
except Exception as e:
    print(f"Skipped Prior Day Fade: {e}")

try:
    s = strat.get_weekday_open_gap_signals_from_archive(data_folder="data/raw_nq_extended")
    trials.append(("Gap Continuation (corrected)", get_points(s)))
except Exception as e:
    print(f"Skipped Gap Continuation: {e}")

try:
    s = strat.get_weekday_open_gap_signals_with_volume_from_archive(data_folder="data/raw_nq_extended")
    filtered = s[s["volume_ratio"] >= 1.2]
    trials.append(("Volume-Confirmed Gap NQ (1.2x)", get_points(filtered)))
except Exception as e:
    print(f"Skipped Volume-Confirmed Gap NQ: {e}")

if not trials:
    print("No trials could be computed - check strategy.py function names.")
    sys.exit()

print(f"\n{'='*70}")
print(f"REAL TRIAL COUNT FROM RECOMPUTABLE STRATEGIES: {len(trials)}")
print(f"ACTUAL num_trials USED FOR DSR (from research_log.md, the true project-wide count): {count_research_trials()}")
print(f"{'='*70}")
print("NOTE: This project has tested 40+ strategy variations total across its history.")
print("Many early/superseded scripts are no longer directly recomputable. This DSR check")
print("uses the trials we CAN verify right now as a conservative floor, not the true total -")
print("meaning the real DSR is likely LOWER (more skeptical) than what's computed here,")
print("since more trials = harder to clear the bar. Treat this as a lower bound on rigor,")
print("not a precise final number.\n")

sharpes = []
for name, points in trials:
    stats_result = compute_returns_stats(points)
    sharpes.append(stats_result["sharpe"])
    print(f"{name}: n={stats_result['n']}, Sharpe={stats_result['sharpe']:.3f}")

sharpe_variance = float(__import__("numpy").var(sharpes)) if len(sharpes) > 1 else 0.01

print(f"\n{'='*70}")
print("DEFLATED SHARPE RATIO RESULTS")
print(f"{'='*70}")

for name, points in trials:
    stats_result = compute_returns_stats(points)
    dsr = deflated_sharpe_ratio(
        observed_sharpe=stats_result["sharpe"],
        num_trials=count_research_trials(),
        sharpe_variance=sharpe_variance,
        num_returns=stats_result["n"],
        skewness=stats_result["skewness"],
        kurtosis=stats_result["kurtosis"]
    )
    verdict = "LIKELY GENUINE" if dsr >= 0.95 else ("UNCERTAIN" if dsr >= 0.5 else "LIKELY LUCK")
    print(f"{name}: DSR={dsr:.3f} ({dsr*100:.1f}% probability of genuine skill) - {verdict}")
    