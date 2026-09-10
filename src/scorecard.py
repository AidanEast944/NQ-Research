from analysis_utils import compute_points, full_stats
import trading_costs

# Fixed, non-negotiable thresholds - the same bar for every strategy, every time
MIN_TRADES = 100
MIN_OUT_OF_SAMPLE_TRADES = 20
MAX_ACCEPTABLE_DRAWDOWN_PCT_OF_ACCOUNT = 30  # won't blow up a reasonably sized account
MIN_PROFIT_FACTOR = 1.3
MAX_OOS_EXPECTANCY_DROP_PCT = 50  # out-of-sample shouldn't be less than half of in-sample
PARTIAL_VERDICT_THRESHOLD_PCT = 60  # need at least this % of checks passed for a PARTIAL verdict

def run_scorecard(signals, strategy_name, entry_col="entry_price", exit_col="exit_price",
                   account_size=10000, point_value=20, date_col="entry_date",
                   slippage_points=None, commission=None):
    """slippage_points/commission override trading_costs.py's defaults for check 6 - leave as
    None to use the shared SLIPPAGE_POINTS/COMMISSION_PER_TRADE constants everyone else uses, so
    every strategy is judged against the same cost assumptions unless there's a specific reason
    to deviate. Always pass the SAME point_value you used for the gross stats (e.g. 2 for MNQ) -
    trading_costs.apply_costs() scales slippage in the same units as your points."""
    print("=" * 60)
    print(f"SCORECARD: {strategy_name}")
    print("=" * 60)

    signals = compute_points(signals, entry_col=entry_col, exit_col=exit_col)
    signals = signals.sort_values(date_col)

    checks_passed = 0
    checks_total = 6

    # Check 1: Sample size
    n = len(signals)
    print(f"\n[1] Sample size: {n} trades (need {MIN_TRADES}+)")
    if n >= MIN_TRADES:
        print("    PASS")
        checks_passed += 1
    else:
        print(f"    FAIL - {MIN_TRADES - n} more trades needed before this is trustworthy")

    if n < 5:
        print("\nNot enough data to run remaining checks meaningfully. Stopping here.")
        print(f"\nOVERALL: {checks_passed}/{checks_total} checks passed. VERDICT: INSUFFICIENT DATA")
        return

    overall_stats = full_stats(signals, point_value=point_value)

    # Check 2: Profit factor (gross)
    pf = overall_stats["profit_factor"]
    print(f"\n[2] Profit factor (gross): {pf:.2f} (need {MIN_PROFIT_FACTOR}+)")
    if pf >= MIN_PROFIT_FACTOR:
        print("    PASS")
        checks_passed += 1
    else:
        print("    FAIL")

    # Check 3: Drawdown vs account size
    dd = overall_stats["max_drawdown_dollars"]
    dd_pct = (dd / account_size) * 100
    print(f"\n[3] Max drawdown: ${dd:,.2f} ({dd_pct:.1f}% of ${account_size:,} account, need under {MAX_ACCEPTABLE_DRAWDOWN_PCT_OF_ACCOUNT}%)")
    if dd_pct <= MAX_ACCEPTABLE_DRAWDOWN_PCT_OF_ACCOUNT:
        print("    PASS")
        checks_passed += 1
    else:
        print("    FAIL - this drawdown would risk ruining the account at this size")

    # Check 4 & 5: Out-of-sample consistency
    split = int(n * 0.7)
    in_sample = signals.iloc[:split]
    out_sample = signals.iloc[split:]
    oos_n = len(out_sample)

    print(f"\n[4] Out-of-sample sample size: {oos_n} trades (need {MIN_OUT_OF_SAMPLE_TRADES}+)")
    if oos_n >= MIN_OUT_OF_SAMPLE_TRADES:
        print("    PASS")
        checks_passed += 1
    else:
        print("    FAIL - too few out-of-sample trades to trust the next check")

    if len(in_sample) > 0 and len(out_sample) > 0:
        in_stats = full_stats(in_sample, point_value=point_value)
        out_stats = full_stats(out_sample, point_value=point_value)
        in_exp = in_stats["expectancy_dollars"]
        out_exp = out_stats["expectancy_dollars"]

        print(f"\n[5] Out-of-sample expectancy: ${out_exp:.2f}/trade vs in-sample ${in_exp:.2f}/trade")
        if out_exp <= 0:
            print("    FAIL - out-of-sample expectancy is negative or zero")
        elif in_exp > 0 and (out_exp / in_exp) < (1 - MAX_OOS_EXPECTANCY_DROP_PCT / 100):
            print(f"    FAIL - dropped more than {MAX_OOS_EXPECTANCY_DROP_PCT}% from in-sample")
        else:
            print("    PASS")
            checks_passed += 1
    else:
        print(f"\n[5] Out-of-sample expectancy: not enough data to check")

    # Check 6: Cost-adjusted (net) profit factor. Added 2026-09-10 - every "PASSES SCORECARD"
    # verdict before this point was gross-only. See research_log.md Entry 21: a strategy can
    # clear checks 1-5 on paper and still not survive real slippage and commission.
    slippage = trading_costs.SLIPPAGE_POINTS if slippage_points is None else slippage_points
    comm = trading_costs.COMMISSION_PER_TRADE if commission is None else commission
    net_dollars = [
        trading_costs.apply_costs(p, point_value=point_value, slippage_points=slippage, commission=comm)
        for p in signals["points"]
    ]
    net_wins = sum(d for d in net_dollars if d > 0)
    net_losses = abs(sum(d for d in net_dollars if d <= 0))
    net_pf = net_wins / net_losses if net_losses > 0 else float("inf")
    net_expectancy = sum(net_dollars) / len(net_dollars)

    print(f"\n[6] Cost-adjusted profit factor: {net_pf:.2f} (need {MIN_PROFIT_FACTOR}+; gross was {pf:.2f})")
    print(f"    Cost model: {slippage}pt slippage + ${comm} commission per trade, at point_value={point_value}")
    print(f"    Net expectancy: ${net_expectancy:.2f}/trade (gross was ${overall_stats['expectancy_dollars']:.2f}/trade)")
    if net_pf >= MIN_PROFIT_FACTOR:
        print("    PASS")
        checks_passed += 1
    else:
        print("    FAIL - the edge doesn't survive realistic trading costs")

    print(f"\n{'='*60}")
    print(f"OVERALL: {checks_passed}/{checks_total} checks passed")
    pct_passed = (checks_passed / checks_total) * 100
    if checks_passed == checks_total:
        print("VERDICT: PASSES SCORECARD - candidate for continued live validation")
    elif pct_passed >= PARTIAL_VERDICT_THRESHOLD_PCT:
        print("VERDICT: PARTIAL - promising but not yet trustworthy, keep watching")
    else:
        print("VERDICT: FAIL - not currently a viable strategy")
    print(f"{'='*60}\n")
