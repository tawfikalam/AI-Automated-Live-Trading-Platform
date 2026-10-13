import pytest
from backend.app.models.schemas import OrderCreateRequest, OrderSide, OrderType, OrderStatus
from backend.app.services.paper_broker import paper_broker
from backend.app.services.storage import storage

@pytest.fixture(autouse=True)
def clean_storage():
    storage.reset_portfolio(initial_cash=100000.0)
    yield
    storage.reset_portfolio(initial_cash=100000.0)

def test_paper_order_execution():
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        stop_loss=58000.0,
        take_profit=64000.0
    )
    res = paper_broker.execute_paper_order(order, market_price=60000.0)
    assert res.status == OrderStatus.FILLED
    assert res.filled_price > 60000.0 # reflects simulated slippage
    
    # Check open positions
    positions = paper_broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "BTC/USD"
    assert positions[0].quantity == 0.1

def test_paper_position_close_and_pnl():
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=0.1,
        stop_loss=58000.0
    )
    fill = paper_broker.execute_paper_order(order, market_price=60000.0)
    positions = paper_broker.get_positions()
    pos_id = positions[0].id

    # Close position
    trade = paper_broker.close_paper_position(pos_id)
    assert trade is not None
    assert trade.quantity == 0.1
    assert len(paper_broker.get_positions()) == 0
    assert len(storage.get_trade_history()) == 1

def test_insufficient_funds_rejection():
    # Set cash to $100
    storage.reset_portfolio(initial_cash=100.0)
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=1.0, # Requires ~$60,000
        stop_loss=50000.0
    )
    res = paper_broker.execute_paper_order(order, market_price=60000.0)
    assert res.status == OrderStatus.REJECTED
    assert "Insufficient paper trading funds" in res.rejection_reason
