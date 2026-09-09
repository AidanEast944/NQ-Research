from strategy import get_pairs_trading_signals_from_archive

MIN_TRADES = 100
MIN_OUT_OF_SAMPLE_TRADES = 20
MAX_ACCEPTABLE_DRAWDOWN_PCT_OF_ACCOUNT = 30
MIN_PROFIT_FACTOR = 1.3
MAX_OOS_EXPECTANCY_DROP_PCT = 50

signals = get_pairs_trading_signals_from_archive()
signals = signals.sort_values("entry_date").reset_index(drop=True)

print("=" * 60)
print("SCORECARD: NQ/ES Pairs Trading")
print("=" * 60)

n = len(signals)
checks_passed = 0
checks_total = 5

print(f"\n[1] Sample size: {n} trades (need {MIN_TRADES}+)")
if n >= MIN_TRADES:
    print("    PASS")
    checks_passed += 1
else:
    print(f"    FAIL - {MIN_TRADES - n} more trades needed")

wins = signals[signals["pnl_dollars"] > 0]["pnl_dollars"]
losses = signals[signals["pnl_dollars"] <= 0]["pnl_dollars"]
pf = wins.sum() / abs(losses.sum()) if len(losses) > 0 and losses.sum() != 0 else float("inf")
print(f"\n[2] Profit factor: {pf:.2f} (need {MIN_PROFIT_FACTOR}+)")
if pf >= MIN_PROFIT_FACTOR:
    print("    PASS")
    checks_passed += 1
else:
    print("    FAIL")

balance = 0
peak = 0
max_dd = 0
for pnl in signals["pnl_dollars"]:
    balance += pnl
    if balance > peak:
        peak = balance
    dd = peak - balance
    if dd > max_dd:
        max_dd = dd

account_size = 10000
dd_pct = (max_dd / account_size) * 100
print(f"\n[3] Max drawdown: ${max_dd:,.2f} ({dd_pct:.1f}% of ${account_size:,} account, need under {MAX_ACCEPTABLE_DRAWDOWN_PCT_OF_ACCOUNT}%)")
if dd_pct <= MAX_ACCEPTABLE_DRAWDOWN_PCT_OF_ACCOUNT:
    print("    PASS")
    checks_passed += 1
else:
    print("    FAIL - this drawdown would risk ruining the account at this size")

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

in_exp = in_sample["pnl_dollars"].mean() if len(in_sample) > 0 else 0
out_exp = out_sample["pnl_dollars"].mean() if len(out_sample) > 0 else 0
print(f"\n[5] Out-of-sample expectancy: ${out_exp:.2f}/trade vs in-sample ${in_exp:.2f}/trade")
if out_exp <= 0:
    print("    FAIL - out-of-sample expectancy is negative or zero")
elif in_exp > 0 and (out_exp / in_exp) < (1 - MAX_OOS_EXPECTANCY_DROP_PCT / 100):
    print(f"    FAIL - dropped more than {MAX_OOS_EXPECTANCY_DROP_PCT}% from in-sample")
else:
    print("    PASS")
    checks_passed += 1

print(f"\n{'='*60}")
print(f"OVERALL: {checks_passed}/{checks_total} checks passed")
if checks_passed == checks_total:
    print("VERDICT: PASSES SCORECARD")
elif checks_passed >= 3:
    print("VERDICT: PARTIAL - promising but not yet trustworthy, keep watching")
else:
    print("VERDICT: FAIL")
print(f"{'='*60}")