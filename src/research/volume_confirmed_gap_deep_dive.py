"""
Deep-dive scrutiny of Entry 25's volume-confirmed gap continuation result (6/6 scorecard, cost-
adjusted PF 1.39 at a 1.2x volume threshold), following the same "don't trust a good headline
number until it's been stress-tested" standard applied to every other result in this project.

The fixed 40/80-point stop/target already rules out single-trade domination (Entry 21/22's failure
mode) - that's confirmed empirically below (Part 1) but structurally guaranteed either way. The
real open question flagged when this result first came in: the 1.2x threshold was picked from a
3-way sweep where profit factor rose monotonically as the threshold rose and the sample shrank
(1.0x -> 1.2x -> 1.5x, PF 1.40 -> 1.57 -> 1.88, n 175 -> 132 -> 93) - consistent with EITHER a real
"more participation confirms more genuine continuation" effect, or mild selection luck on a
shrinking sample. Four checks aimed at that specific concern:

  Part 1: exit-reason mix at 1.2x (confirms the bounded-risk claim holds for THIS filtered subset,
          not just the unfiltered baseline it's inherited from)
  Part 2: confound check (does the LOW-volume subset show the same "improves over time" pattern as
          the high-volume subset? If so, the volume filter isn't adding real information beyond a
          generic calendar trend - same method as Entry 21)
  Part 3: finer threshold granularity (does the relationship rise smoothly, or jump around?)
  Part 4: lookback-window robustness (does a 10-day or 30-day trailing volume average still work,
          or does the effect only appear at exactly 20 days?)
  Part 5: THE key check - honest out-of-time threshold selection. Rather than judging out-of-sample
          performance of a threshold chosen using the FULL sample (which is what the original test
          did), pick whichever threshold looks best using ONLY the first 70% of trades chronologically,
          then check whether THAT fixed choice still works on the last 30% - the way a live trader
          would actually have to choose, without seeing the future.
"""
from strategy import get_weekday_open_gap_signals_with_volume_from_archive
from analysis_utils import compute_points, full_stats, print_stats
from walk_forward import walk_forward_test

POINT_VALUE = 2  # MNQ

print("=" * 70)
print("PART 1: Exit-reason mix at the chosen 1.2x threshold")
print("=" * 70)
print("Confirms the bounded-risk claim (no single trade can exceed 80pts/-40pts) actually holds")
print("for THIS filtered subset, not just assumed from the unfiltered baseline it's drawn from.\n")

signals = get_weekday_open_gap_signals_with_volume_from_archive()
signals = compute_points(signals, entry_col="entry_price", exit_col="exit_price")
signals = signals.sort_values("date").reset_index(drop=True)
confirmed_12 = signals[signals["volume_ratio"] >= 1.2].copy()
print(f"n={len(confirmed_12)}, exit reasons: {confirmed_12['exit_reason'].value_counts().to_dict()}")
eod_pct = (confirmed_12["exit_reason"] == "eod").mean() * 100
print(f"eod (undefined-size) exits: {eod_pct:.1f}% of trades - should be small for the bounded-risk claim to hold")

print("\n" + "=" * 70)
print("PART 2: Confound check - does UNCONFIRMED (low volume) show the same time trend?")
print("=" * 70)
print("Same method as Entry 21: split into 4 sequential windows and compare. If both the")
print("confirmed and unconfirmed subsets improve similarly over calendar time, the volume filter")
print("isn't adding real information - it's riding a shared trend also present in unfiltered data.\n")

unconfirmed_12 = signals[signals["volume_ratio"] < 1.2].copy()
print(f"--- CONFIRMED (>= 1.2x), n={len(confirmed_12)} ---")
walk_forward_test(confirmed_12, "Confirmed >= 1.2x", num_windows=4, date_col="date", point_value=POINT_VALUE)
print(f"\n--- UNCONFIRMED (< 1.2x), n={len(unconfirmed_12)} ---")
walk_forward_test(unconfirmed_12, "Unconfirmed < 1.2x", num_windows=4, date_col="date", point_value=POINT_VALUE)

print("\n" + "=" * 70)
print("PART 3: Finer threshold granularity - smooth trend or noisy jumps?")
print("=" * 70)
for threshold in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]:
    subset = signals[signals["volume_ratio"] >= threshold]
    stats = full_stats(subset, point_value=POINT_VALUE)
    if stats:
        print(f"  threshold={threshold:.1f}x: n={stats['trades']:>4}, win_rate={stats['win_rate']:.1f}%, "
              f"PF={stats['profit_factor']:.2f}, expectancy=${stats['expectancy_dollars']:.2f}/trade")
    else:
        print(f"  threshold={threshold:.1f}x: no trades")

print("\n" + "=" * 70)
print("PART 4: Lookback-window robustness (10-day / 20-day / 30-day trailing volume average)")
print("=" * 70)
for lookback in [10, 20, 30]:
    lb_signals = get_weekday_open_gap_signals_with_volume_from_archive(volume_lookback=lookback)
    lb_signals = compute_points(lb_signals, entry_col="entry_price", exit_col="exit_price")
    confirmed_lb = lb_signals[lb_signals["volume_ratio"] >= 1.2]
    stats = full_stats(confirmed_lb, point_value=POINT_VALUE)
    if stats:
        print(f"  volume_lookback={lookback}d, threshold=1.2x: n={stats['trades']:>4}, "
              f"win_rate={stats['win_rate']:.1f}%, PF={stats['profit_factor']:.2f}, "
              f"expectancy=${stats['expectancy_dollars']:.2f}/trade")
    else:
        print(f"  volume_lookback={lookback}d: no trades")

print("\n" + "=" * 70)
print("PART 5: Honest out-of-time threshold selection (the key check)")
print("=" * 70)
print("The original sweep picked 1.2x using ALL 460 trades - including the 'out-of-sample' 30%")
print("used to judge it later. That's not how a live trader would actually choose: they'd only")
print("have the earlier data available. Splitting chronologically at 70% BEFORE choosing a")
print("threshold, picking whichever looks best using ONLY the first 70%, then checking whether")
print("that fixed choice - decided without seeing the future - still works on the real last 30%.\n")

split_idx = int(len(signals) * 0.7)
in_sample = signals.iloc[:split_idx]
out_sample = signals.iloc[split_idx:]
print(f"In-sample (first 70%): {len(in_sample)} trades, {in_sample['date'].min()} to {in_sample['date'].max()}")
print(f"Out-of-sample (last 30%): {len(out_sample)} trades, {out_sample['date'].min()} to {out_sample['date'].max()}\n")

print("Threshold performance using ONLY in-sample data (this is what a live trader could have seen):")
best_threshold, best_pf = None, -999
for threshold in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]:
    subset = in_sample[in_sample["volume_ratio"] >= threshold]
    stats = full_stats(subset, point_value=POINT_VALUE)
    if stats and stats["trades"] >= 20:  # need a minimally trustworthy sample to even consider it
        print(f"  threshold={threshold:.1f}x: n={stats['trades']:>4}, PF={stats['profit_factor']:.2f}, "
              f"expectancy=${stats['expectancy_dollars']:.2f}/trade")
        if stats["profit_factor"] > best_pf:
            best_pf, best_threshold = stats["profit_factor"], threshold
    else:
        n = stats["trades"] if stats else 0
        print(f"  threshold={threshold:.1f}x: n={n:>4} (too few in-sample trades to trust)")

print(f"\nBest in-sample-only threshold: {best_threshold}x (PF {best_pf:.2f} in-sample)")
print(f"Applying that SAME fixed threshold to the real, unseen-at-the-time out-of-sample 30%:")
honest_oos = out_sample[out_sample["volume_ratio"] >= best_threshold]
honest_stats = full_stats(honest_oos, point_value=POINT_VALUE)
if honest_stats:
    print_stats(honest_stats)
else:
    print("  No qualifying trades in the out-of-sample period at this threshold.")

print("\nFor comparison, the ORIGINAL out-of-sample slice at 1.2x (chosen with full-sample hindsight):")
hindsight_oos = out_sample[out_sample["volume_ratio"] >= 1.2]
print_stats(full_stats(hindsight_oos, point_value=POINT_VALUE))
