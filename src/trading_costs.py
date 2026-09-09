SLIPPAGE_POINTS = 1.0
COMMISSION_PER_TRADE = 4.50
POINT_VALUE = 20

def apply_costs(points, point_value=POINT_VALUE, slippage_points=SLIPPAGE_POINTS, commission=COMMISSION_PER_TRADE):
    gross_dollars = points * point_value
    net_dollars = gross_dollars - (slippage_points * point_value) - commission
    return net_dollars