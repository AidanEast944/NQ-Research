"""
Crowding proxy: checks whether pairs trading's time-to-revert is trending shorter over time -
a real, testable signal that more competition may be arbitraging the effect faster, since
crowded trades typically resolve quicker as more capital chases the same signal.
"""
import sys
sys.path.insert(0, "src")

from strategy import get_generic_pairs_signals_from_archive

configs = [
    ("NQ/ES", "data/raw_nq_extended", "data/raw_es_extended", 20, 50),
    ("NQ/YM", "data/raw_nq_extended", "data/raw_ym_extended", 20, 5),
    ("ES/YM", "data/raw_es_extended", "data/raw_ym_extended", 50, 5),
]

for name, folder_a, folder_b, pv_a, pv_b in configs:
    signals = get_generic_pairs_signals_from_archive(folder_a, folder_b, pv_a, pv_b)
    signals = signals.sort_values("entry_date").reset_index(drop=True)

    if len(signals) < 20:
        print(f"{name}: too few trades for a crowding trend check ({len(signals)})")
        continue

    split = len(signals) // 2
    early_half = signals.iloc[:split]
    late_half = signals.iloc[split:]

    print(f"\n{name}:")
    print(f"  Early half avg days held: {early_half['days_held'].mean():.1f}")
    print(f"  Late half avg days held: {late_half['days_held'].mean():.1f}")
    change = ((late_half['days_held'].mean() - early_half['days_held'].mean()) / early_half['days_held'].mean()) * 100
    print(f"  Change: {change:+.1f}% ({'FASTER (possible crowding)' if change < -15 else 'STABLE' if abs(change) <= 15 else 'SLOWER (possible edge widening/less crowded)'})")