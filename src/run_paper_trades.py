from strategy import get_prior_day_break_signals
from paper_broker import PaperBroker

# Get all historical signals from our strategy
signals = get_prior_day_break_signals()

# Create a fresh fake trading account
broker = PaperBroker(starting_balance=10000)

for _, row in signals.iterrows():
    trade = broker.place_order(
        symbol="NQ",
        direction=row["signal"],
        entry_price=row["Close"],
        stop_price=None,   # not needed for closing, just for record-keeping
        target_price=None
    )

    broker.close_position(
        trade,
        exit_price=row["exit_price"],
        reason=row["exit_reason"]
    )

broker.summary()