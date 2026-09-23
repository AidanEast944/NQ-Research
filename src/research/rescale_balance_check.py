import sys
sys.path.insert(0, 'src')
from paper_broker import PaperBroker

accounts = [
    ("Gap Continuation (NQ)", "data/gap_paper_account.json"),
    ("Volume Gap 1.2x (NQ)", "data/volume_gap_1_2x_paper_account.json"),
    ("Volume Gap 1.5x (NQ)", "data/volume_gap_1_5x_paper_account.json"),
    ("Volume Gap 1.2x (YM)", "data/volume_gap_ym_1_2x_paper_account.json"),
    ("Volume Gap 1.5x (YM)", "data/volume_gap_ym_1_5x_paper_account.json"),
]

for hypothetical_start in [500, 1000, 2500, 5000]:
    print(f"\n=== Hypothetical starting balance: ${hypothetical_start:,} ===")
    for name, filepath in accounts:
        broker = PaperBroker(starting_balance=10000, state_file=filepath)
        actual_dollar_change = broker.balance - 10000
        rescaled_balance = hypothetical_start + actual_dollar_change
        pct_change = (actual_dollar_change / hypothetical_start) * 100
        print(f"{name}: ${rescaled_balance:,.2f} ({pct_change:+.1f}%)")