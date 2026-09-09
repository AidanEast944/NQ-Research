from strategy import get_trend_following_signals_from_archive
from trading_costs import apply_costs

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

signals = get_trend_following_signals_from_archive(ma_period=5, stop_points=200)
signals["points"] = signals.apply(points_result, axis=1)
signals["net_dollars"] = signals["points"].apply(apply_costs)

gross_total = (signals["points"] * 20).sum()
net_total = signals["net_dollars"].sum()

print(f"Trades: {len(signals)}")
print(f"Gross P&L (no costs): ${gross_total:,.2f}")
print(f"Net P&L (with slippage + commission): ${net_total:,.2f}")
print(f"Cost impact: ${gross_total - net_total:,.2f}")