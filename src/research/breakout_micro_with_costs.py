from strategy import get_prior_day_break_signals_from_archive
from analysis_utils import compute_points, full_stats, print_stats

FOLDER = "data/raw_nq_extended"
MICRO_POINT_VALUE = 2
SLIPPAGE_POINTS = 1.0
COMMISSION_PER_TRADE = 2.00  # realistic round-turn micro commission

signals = get_prior_day_break_signals_from_archive(stop_points=30, target_points=60, data_folder=FOLDER)
signals = compute_points(signals, entry_col="Close")

print("=" * 60)
print("BREAKOUT (30/60), MNQ SIZING - COST IMPACT")
print("=" * 60)

gross_total = (signals["points"] * MICRO_POINT_VALUE).sum()
print(f"\nGross P&L (no costs): ${gross_total:,.2f}")

net_points = signals["points"] - SLIPPAGE_POINTS
net_dollars_per_trade = (net_points * MICRO_POINT_VALUE) - COMMISSION_PER_TRADE
net_total = net_dollars_per_trade.sum()

print(f"Net P&L (with ${SLIPPAGE_POINTS}pt slippage + ${COMMISSION_PER_TRADE} commission per trade): ${net_total:,.2f}")
print(f"Cost impact: ${gross_total - net_total:,.2f}")
print(f"Trades: {len(signals)}")

wins = (net_dollars_per_trade > 0).sum()
losses = (net_dollars_per_trade <= 0).sum()
net_win_rate = wins / len(signals) * 100
gross_win = net_dollars_per_trade[net_dollars_per_trade > 0].sum()
gross_loss = abs(net_dollars_per_trade[net_dollars_per_trade <= 0].sum())
net_profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

print(f"\nNet win rate: {net_win_rate:.1f}%")
print(f"Net profit factor (after costs): {net_profit_factor:.2f}")
print(f"Net expectancy per trade: ${net_dollars_per_trade.mean():.2f}")