import math

def compute_points(signals, entry_col="entry_price", exit_col="exit_price"):
    def pr(row):
        if row["signal"] == "LONG":
            return row[exit_col] - row[entry_col]
        else:
            return row[entry_col] - row[exit_col]
    signals = signals.copy()
    signals["points"] = signals.apply(pr, axis=1)
    return signals

def full_stats(signals, point_value=20, label=""):
    if len(signals) == 0:
        return None
    points = signals["points"].tolist()
    wins = [p for p in points if p > 0]
    losses = [p for p in points if p <= 0]
    win_rate = len(wins) / len(points) * 100
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    gross_win = sum(wins) * point_value
    gross_loss = abs(sum(losses)) * point_value
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
    expectancy = sum(points) / len(points)
    expectancy_dollars = expectancy * point_value

    balance = 0
    peak = 0
    max_dd = 0
    cur_streak = 0
    streak_type = None
    worst_loss_streak = 0
    worst_win_streak = 0
    for p in points:
        balance += p * point_value
        if balance > peak:
            peak = balance
        dd = peak - balance
        if dd > max_dd:
            max_dd = dd
        is_win = p > 0
        if streak_type == is_win:
            cur_streak += 1
        else:
            cur_streak = 1
            streak_type = is_win
        if is_win:
            worst_win_streak = max(worst_win_streak, cur_streak)
        else:
            worst_loss_streak = max(worst_loss_streak, cur_streak)

    return {
        "label": label,
        "trades": len(points),
        "win_rate": win_rate,
        "avg_win_pts": avg_win,
        "avg_loss_pts": avg_loss,
        "profit_factor": profit_factor,
        "expectancy_pts": expectancy,
        "expectancy_dollars": expectancy_dollars,
        "max_drawdown_dollars": max_dd,
        "worst_losing_streak": worst_loss_streak,
        "worst_winning_streak": worst_win_streak,
        "total_pnl_dollars": balance,
        "sharpe": sharpe_ratio(points),
        "sortino": sortino_ratio(points),
        "calmar": calmar_ratio(balance, max_dd),
    }

def print_stats(stats):
    if stats is None:
        print("  No trades.")
        return
    print(f"  Trades: {stats['trades']}")
    print(f"  Win rate: {stats['win_rate']:.1f}%")
    print(f"  Avg win: {stats['avg_win_pts']:.2f} pts | Avg loss: {stats['avg_loss_pts']:.2f} pts")
    print(f"  Profit factor: {stats['profit_factor']:.2f}")
    print(f"  Expectancy: {stats['expectancy_pts']:.2f} pts (${stats['expectancy_dollars']:.2f}) per trade")
    print(f"  Max drawdown: ${stats['max_drawdown_dollars']:,.2f}")
    print(f"  Worst losing streak: {stats['worst_losing_streak']} | Worst winning streak: {stats['worst_winning_streak']}")
    print(f"  Total P&L: ${stats['total_pnl_dollars']:,.2f}")

    sharpe_str = f"{stats['sharpe']:.2f}" if stats['sharpe'] is not None else "N/A"
    sortino_str = f"{stats['sortino']:.2f}" if stats['sortino'] is not None else "N/A"
    calmar_str = f"{stats['calmar']:.2f}" if stats['calmar'] is not None else "N/A"
    print(f"  Sharpe (per-trade, non-annualized): {sharpe_str}")
    print(f"  Sortino (per-trade, non-annualized): {sortino_str}")
    print(f"  Calmar (return/max drawdown): {calmar_str}")
    

    

def sharpe_ratio(points_list):
    if len(points_list) < 2:
        return None
    mean_r = sum(points_list) / len(points_list)
    variance = sum((p - mean_r) ** 2 for p in points_list) / (len(points_list) - 1)
    std_r = math.sqrt(variance)
    if std_r == 0:
        return None
    return mean_r / std_r

def sortino_ratio(points_list):
    if len(points_list) < 2:
        return None
    mean_r = sum(points_list) / len(points_list)
    downside = [p for p in points_list if p < 0]
    if len(downside) < 2:
        return None
    downside_variance = sum((p - 0) ** 2 for p in downside) / len(downside)
    downside_std = math.sqrt(downside_variance)
    if downside_std == 0:
        return None
    return mean_r / downside_std

def calmar_ratio(total_pnl_dollars, max_drawdown_dollars):
    if max_drawdown_dollars == 0:
        return None
    return total_pnl_dollars / max_drawdown_dollars