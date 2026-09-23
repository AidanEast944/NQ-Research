import sys
sys.path.insert(0, "src")
from generate_morning_brief import opened_this_morning

positions = opened_this_morning()

if not positions:
    print("No new positions opened this morning.")
else:
    print(f"{len(positions)} position(s) opened this morning:\n")
    for p in positions:
        print(f"  {p['strategy']}: {p['direction']} {p['symbol']} @ {p['entry_price']} "
              f"(stop: {p['stop_price']}, target: {p['target_price']})")