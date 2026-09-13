"""
Deflated Sharpe Ratio (DSR) - Bailey & Lopez de Prado (2014).
Corrects a strategy's Sharpe ratio for two sources of performance inflation:
1. Selection bias from testing multiple strategies and picking the best-looking one
2. Non-normal return distributions (skew, fat tails)

Reference: "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting,
and Non-Normality", Journal of Portfolio Management, 40(5), 2014.
"""
import math
from scipy import stats
import numpy as np


def expected_max_sharpe(num_trials, sharpe_variance):
    """Expected maximum Sharpe ratio you'd see by chance alone, given N independent trials
    each with the given variance in their Sharpe estimates."""
    if num_trials <= 1:
        return 0.0
    euler_mascheroni = 0.5772156649
    z_term1 = (1 - euler_mascheroni) * stats.norm.ppf(1 - 1.0 / num_trials)
    z_term2 = euler_mascheroni * stats.norm.ppf(1 - 1.0 / (num_trials * math.e))
    return math.sqrt(sharpe_variance) * (z_term1 + z_term2)


def deflated_sharpe_ratio(observed_sharpe, num_trials, sharpe_variance, num_returns,
                           skewness=0.0, kurtosis=3.0):
    """Returns the probability (0 to 1) that the observed Sharpe ratio reflects genuine skill,
    after correcting for how many trials were run to find it and non-normal returns."""
    sr_benchmark = expected_max_sharpe(num_trials, sharpe_variance)

    numerator = (observed_sharpe - sr_benchmark) * math.sqrt(num_returns - 1)
    denominator = math.sqrt(1 - skewness * observed_sharpe + ((kurtosis - 1) / 4) * observed_sharpe ** 2)

    if denominator == 0:
        return 0.0

    psr = stats.norm.cdf(numerator / denominator)
    return psr


def compute_returns_stats(points_list):
    """Compute skewness, kurtosis, and a simple per-trade Sharpe ratio from a raw list of
    trade returns (points or dollars - just be consistent)."""
    arr = np.array(points_list)
    if len(arr) < 2 or arr.std() == 0:
        return {"sharpe": 0.0, "skewness": 0.0, "kurtosis": 3.0, "n": len(arr)}
    sharpe = arr.mean() / arr.std()
    skewness = stats.skew(arr)
    kurtosis = stats.kurtosis(arr, fisher=False)
    return {"sharpe": sharpe, "skewness": skewness, "kurtosis": kurtosis, "n": len(arr)}