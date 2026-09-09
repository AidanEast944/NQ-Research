from strategy import get_trend_following_atr_signals_from_archive, get_prior_day_fade_signals_from_archive
from analysis_utils import compute_points

print("=" * 60)
print("RISK TRACKING: CORRELATION BETWEEN STRATEGIES")
print("=" * 60)

trend = get_trend_following_atr_signals_from_archive(ma_period=5, atr_multiplier=1.0)
trend = compute_points(trend)
trend = trend.rename(columns={"entry_date": "date", "points": "trend_points"})[["date", "trend_points"]]

fade = get_prior_day_fade_signals_from_archive(stop_points=30, target_points=60)
fade = compute_points(fade, entry_col="Close")
fade = fade.rename(columns={"points": "fade_points"})[["date", "fade_points"]]

merged = trend.merge(fade, on="date", how="inner")

if len(merged) < 3:
    print(f"Only {len(merged)} overlapping trade dates - not enough to compute a meaningful correlation yet.")
else:
    correlation = merged["trend_points"].corr(merged["fade_points"])
    print(f"Overlapping trade dates: {len(merged)}")
    print(f"Correlation between Trend and Fade returns: {correlation:.2f}")
    if correlation > 0.5:
        print("-> Strategies tend to win/lose together - less diversification than it looks.")
    elif correlation < -0.2:
        print("-> Strategies tend to offset each other - genuine diversification benefit.")
    else:
        print("-> Roughly independent - reasonable diversification.")

print("\n" + "=" * 60)
print("POSITION SIZING GUIDANCE (educational - not a recommendation)")
print("=" * 60)
print("""
Common approaches once a strategy is validated:
- Fixed fractional: risk a fixed % (e.g. 1%) of account per trade.
    Position size = (Account x Risk%) / (Stop distance in points x point value)
- Avoid risking more than 1-2% of account per trade during any
  validation/early-live phase.
- Treat a live losing streak that exceeds your worst BACKTESTED
  losing streak as a signal to pause and re-check assumptions,
  not just bad luck.

IMPORTANT: no strategy in this project has reached the validation
threshold (100+ trades, holding up out-of-sample and across markets)
yet. This math is here for when that day comes.
""")