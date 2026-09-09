from strategy import get_trend_following_atr_signals_from_archive, get_prior_day_fade_signals_from_archive
from analysis_utils import compute_points, full_stats, print_stats

print("=" * 60)
print("DEEP DIVE: NQ 5-DAY TREND (ATR-based stop)")
print("=" * 60)

print("\n--- Q1: Sample size check ---")
print("Archive currently spans ~4 months. Multi-day trend trades produce")
print("far fewer signals than intraday setups. Honest ceiling right now")
print("is likely 15-30 trades depending on parameters - NOT the 50-100+")
print("needed for real confidence. Everything below is early evidence.\n")

print("--- Q2: Which ATR multiplier is best? ---")
best = None
for mult in [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]:
    signals = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=mult)
    if len(signals) == 0:
        print(f"\nATR x{mult}: no trades")
        continue
    signals = compute_points(signals)
    stats = full_stats(signals, label=f"ATR x{mult}")
    print(f"\nATR multiplier {mult}:")
    print_stats(stats)
    if best is None or stats["expectancy_dollars"] > best["expectancy_dollars"]:
        best = stats

if best:
    print(f"\n>>> Best by expectancy: {best['label']} (${best['expectancy_dollars']:.2f}/trade)")

print("\n" + "=" * 60)
print("Q6: PERFORMANCE ACROSS ARCHIVE PERIODS (early vs late half)")
print("=" * 60)
signals = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0)
signals = compute_points(signals)
signals = signals.sort_values("entry_date")
split = len(signals) // 2
early = signals.iloc[:split]
late = signals.iloc[split:]
print("\nEarly period:")
print_stats(full_stats(early, label="early"))
print("\nLate period:")
print_stats(full_stats(late, label="late"))
print("\nNote: this is a rough proxy for 'different market conditions' -")
print("only 2 chunks of the same 4-month window, not truly different regimes.")

print("\n" + "=" * 60)
print("Q7: OUT-OF-SAMPLE CHECK (ATR x1.0, 70/30 split)")
print("=" * 60)
split70 = int(len(signals) * 0.7)
in_s = signals.iloc[:split70]
out_s = signals.iloc[split70:]
print("\nIn-sample:")
print_stats(full_stats(in_s, label="in-sample"))
print("\nOut-of-sample:")
print_stats(full_stats(out_s, label="out-of-sample"))

print("\n" + "=" * 60)
print("FADE STRATEGY - SAME METRICS, FOR COMPARISON")
print("=" * 60)
fade_signals = get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60)
fade_signals = compute_points(fade_signals, entry_col="Close")
print_stats(full_stats(fade_signals, label="fade"))