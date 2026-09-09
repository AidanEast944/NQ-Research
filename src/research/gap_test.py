from strategy import get_gap_signals_from_archive

def points_result(row):
    if row["signal"] == "LONG":
        return row["exit_price"] - row["entry_price"]
    else:
        return row["entry_price"] - row["exit_price"]

for mode_name, fill_mode in [("FILL (bet gap closes)", True), ("CONTINUATION (bet gap extends)", False)]:
    signals = get_gap_signals_from_archive(min_gap_points=30, stop_points=40, target_points=80, fill_mode=fill_mode)
    if len(signals) == 0:
        print(f"{mode_name}: no trades")
        continue
    signals["points"] = signals.apply(points_result, axis=1)
    win_rate = (signals["points"] > 0).mean() * 100
    avg_points = signals["points"].mean()
    total_points = signals["points"].sum()
    print(f"\n--- {mode_name} ---")
    print(f"Trades: {len(signals)}, Win rate: {win_rate:.1f}%, Avg points: {avg_points:.2f}, Total: {total_points:.2f}")