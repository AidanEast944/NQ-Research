from paper_broker import PaperBroker

# Create a fake account with $10,000 starting balance
broker = PaperBroker(starting_balance=10000)

# Simulate placing one LONG trade
trade = broker.place_order(
    symbol="NQ",
    direction="LONG",
    entry_price=29500,
    stop_price=29470,
    target_price=29560
)

# Simulate that trade later hitting its target
broker.close_position(trade, exit_price=29560, reason="target hit")

# Simulate a second trade that hits its stop instead
trade2 = broker.place_order(
    symbol="NQ",
    direction="SHORT",
    entry_price=29600,
    stop_price=29630,
    target_price=29540
)
broker.close_position(trade2, exit_price=29630, reason="stop hit")

broker.summary()