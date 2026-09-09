def fixed_fractional_size(account_balance, risk_percent, stop_points, point_value):
    """Risk a fixed % of account on this trade. Returns number of contracts (can be fractional -
    round down for real trading, since you can't buy partial futures contracts)."""
    risk_dollars = account_balance * (risk_percent / 100)
    risk_per_contract = stop_points * point_value
    if risk_per_contract == 0:
        return 0
    return risk_dollars / risk_per_contract


def kelly_fraction(win_rate, avg_win, avg_loss):
    """Classic Kelly formula: what fraction of your account to risk, given a strategy's
    historical win rate and average win/loss size. avg_loss should be a POSITIVE number
    (magnitude of a typical loss), not negative.

    IMPORTANT: full Kelly is historically known to be too aggressive in practice (based on
    perfect knowledge of true win rate/sizes, which you never actually have). Most practitioners
    use "half Kelly" or less. This function returns full Kelly - apply your own safety
    multiplier (like 0.5) when actually using it."""
    if avg_loss == 0:
        return 0
    win_loss_ratio = avg_win / avg_loss
    kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
    return max(kelly, 0)  # never suggest a negative position size


def recommended_contracts(account_balance, win_rate, avg_win, avg_loss, stop_points, point_value, kelly_safety_multiplier=0.5):
    """Combines Kelly sizing (scaled down for safety) with a hard cap based on fixed-fractional
    risk, so you never risk more than a sane amount regardless of what Kelly suggests."""
    kelly_pct = kelly_fraction(win_rate, avg_win, avg_loss) * kelly_safety_multiplier * 100
    kelly_pct = min(kelly_pct, 2.0)  # hard cap: never risk more than 2% per trade, no matter what

    contracts = fixed_fractional_size(account_balance, kelly_pct, stop_points, point_value)
    return contracts, kelly_pct