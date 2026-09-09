from strategy import check_cointegration

pairs = [
    ("NQ/ES", "data/raw_nq_extended", "data/raw_es_extended"),
    ("NQ/YM", "data/raw_nq_extended", "data/raw_ym_extended"),
    ("ES/YM", "data/raw_es_extended", "data/raw_ym_extended"),
]

print("=" * 60)
print("COINTEGRATION CHECK - Tier 1 live pairs")
print("=" * 60)
print("Testing whether these pairs show real statistical evidence of a long-run")
print("equilibrium relationship (Engle-Granger), not just a rolling z-score that")
print("looks mean-reverting by construction. In-sample only (first 70%) to avoid")
print("look-ahead bias.\n")

for label, folder_a, folder_b in pairs:
    check_cointegration(folder_a, folder_b, label=label)
    print()

# Confirmatory check: pairs already rejected out-of-sample (Entry 14, research_log.md).
# If research_log.md's finding holds, these should show weaker/no cointegration evidence
# than the Tier-1 pairs above - independent statistical support for "the edge is specific
# to large-cap correlation structure, not universal."
print("=" * 60)
print("CONFIRMATORY CHECK - pairs already rejected out-of-sample (Entry 14)")
print("=" * 60)
print()

rejected_pairs = [
    ("NQ/RTY", "data/raw_nq_extended", "data/raw_rty_extended"),
    ("ES/RTY", "data/raw_es_extended", "data/raw_rty_extended"),
    ("YM/RTY", "data/raw_ym_extended", "data/raw_rty_extended"),
]
for label, folder_a, folder_b in rejected_pairs:
    check_cointegration(folder_a, folder_b, label=label)
    print()
