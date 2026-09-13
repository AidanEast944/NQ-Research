"""
Rolling edge-decay check: compares a strategy's expectancy on its most recent trades against
its full historical expectancy, to catch a currently-passing strategy that's quietly weakening
as the market competes the edge away - distinct from the one-time walk-forward/out-of-sample
splits already in scorecard.py, which only look at historical data once.

Meant to be re-run periodically (monthly, alongside the regular scorecard check-in) as new real
trades accumulate - the whole point is watching the TREND over repeated checks, not a single
snapshot.
"""
import pandas as pd

def check_edge_decay(signals, entry_col="entry_price", exit_col="exit_price",
                       date_col="date", recent_n=30, point_value=1):
    """recent_n: how many of the MOST RECENT trades count as "recent" for this check.
    30 is a reasonable default - enough trades to not be noise-dominated, recent enough to
    catch a real, ongoing shift rather than ancient history."""
    signals = signals.copy()
    signals = signals.sort_values(date_col).reset_index(drop=True)

    def pts(row):
        if row["signal"] == "LONG":
            return row[exit_col] - row[entry_col]
        return row[entry_col] - row[exit_col]

    signals["points"] = signals.apply(pts, axis=1)
    signals["dollars"] = signals["points"] * point_value

    if len(signals) < recent_n + 20:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": f"Need at least {recent_n + 20} trades for a meaningful decay check, "
                       f"have {len(signals)}."
        }

    full_history = signals.iloc[:-recent_n]
    recent = signals.iloc[-recent_n:]

    full_expectancy = full_history["dollars"].mean()
    recent_expectancy = recent["dollars"].mean()

    full_win_rate = (full_history["dollars"] > 0).mean() * 100
    recent_win_rate = (recent["dollars"] > 0).mean() * 100

    if full_expectancy == 0:
        pct_change = float("nan")
    else:
        pct_change = ((recent_expectancy - full_expectancy) / abs(full_expectancy)) * 100

    if recent_expectancy <= 0 and full_expectancy > 0:
        status = "WARNING_TURNED_NEGATIVE"
    elif pct_change < -50:
        status = "WARNING_SIGNIFICANT_DECAY"
    elif pct_change < -20:
        status = "WATCH_MILD_DECAY"
    else:
        status = "STABLE_OR_IMPROVING"

    return {
        "status": status,
        "full_history_trades": len(full_history),
        "full_history_expectancy": full_expectancy,
        "full_history_win_rate": full_win_rate,
        "recent_n_trades": len(recent),
        "recent_expectancy": recent_expectancy,
        "recent_win_rate": recent_win_rate,
        "pct_change": pct_change,
    }


def print_decay_report(result, strategy_name):
    print(f"\n--- Edge Decay Check: {strategy_name} ---")
    if result["status"] == "INSUFFICIENT_DATA":
        print(result["message"])
        return

    print(f"Full history ({result['full_history_trades']} trades): "
          f"${result['full_history_expectancy']:.2f}/trade avg, {result['full_history_win_rate']:.1f}% win rate")
    print(f"Most recent {result['recent_n_trades']} trades: "
          f"${result['recent_expectancy']:.2f}/trade avg, {result['recent_win_rate']:.1f}% win rate")
    print(f"Change: {result['pct_change']:+.1f}%")

    if result["status"] == "WARNING_TURNED_NEGATIVE":
        print("STATUS: WARNING - expectancy has turned negative in recent trades despite a "
              "positive full history. This is the exact signature of a decaying, arbitraged-away edge.")
    elif result["status"] == "WARNING_SIGNIFICANT_DECAY":
        print("STATUS: WARNING - recent performance is more than 50% worse than full history. "
              "Worth investigating before continuing to trust this strategy's current status.")
    elif result["status"] == "WATCH_MILD_DECAY":
        print("STATUS: WATCH - some weakening visible, not yet alarming. Keep monitoring.")
    else:
        print("STATUS: STABLE - no meaningful decay detected. Recent performance consistent "
              "with or better than full history.")