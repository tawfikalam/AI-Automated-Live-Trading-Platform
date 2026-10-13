import pytest
from backend.app.models.schemas import OrderCreateRequest, OrderSide, OrderType
from backend.app.risk.validator import RiskManager
from backend.app.risk.rules import RiskConfig
from backend.app.services.storage import storage

@pytest.fixture(autouse=True)
def clean_storage():
    storage.reset_portfolio(initial_cash=100000.0)
    yield
    storage.reset_portfolio(initial_cash=100000.0)

def test_risk_rule_mandatory_stop_loss_missing():
    rm = RiskManager()
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        stop_loss=None # Missing stop loss
    )
    res = rm.validate_order(order, market_price=60000.0, current_equity=100000.0, initial_cash=100000.0)
    assert not res.is_approved
    assert "Stop Loss is missing" in res.rejection_reason

def test_risk_rule_buy_stop_loss_above_entry():
    rm = RiskManager()
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        stop_loss=65000.0 # Stop loss above entry for BUY is invalid
    )
    res = rm.validate_order(order, market_price=60000.0, current_equity=100000.0, initial_cash=100000.0)
    assert not res.is_approved
    assert "must be BELOW entry price" in res.rejection_reason

def test_risk_rule_position_size_exceeded():
    rm = RiskManager() # max 10% position size
    # Equity = $100,000 -> Max allowed position = $10,000
    # Try opening $15,000 position
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=0.25, # 0.25 * 60,000 = $15,000
        stop_loss=59000.0
    )
    res = rm.validate_order(order, market_price=60000.0, current_equity=100000.0, initial_cash=100000.0)
    assert not res.is_approved
    assert "exceeds maximum allowed limit" in res.rejection_reason

def test_risk_rule_max_risk_per_trade_exceeded():
    rm = RiskManager() # max 2% risk of equity = $2,000
    # Entry = 60,000, Stop Loss = 50,000 (diff = 10,000). Qty = 0.25 -> Risk = $2,500 > $2,000
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=0.15, # 0.15 * 60,000 = $9,000 (under 10% position size)
        stop_loss=40000.0 # Risk = (60k - 40k) * 0.15 = $3,000 > $2,000
    )
    res = rm.validate_order(order, market_price=60000.0, current_equity=100000.0, initial_cash=100000.0)
    assert not res.is_approved
    assert "Total capital at risk" in res.rejection_reason

def test_risk_rule_max_open_positions_limit():
    rm = RiskManager() # max 3 positions
    # Manually insert 3 positions into storage
    for i in range(3):
        storage.open_position({
            "id": f"pos_dummy_{i}",
            "symbol": f"SYM_{i}",
            "side": "LONG",
            "quantity": 1.0,
            "entry_price": 100.0,
            "stop_loss": 90.0
        })

    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=0.05,
        stop_loss=59000.0
    )
    res = rm.validate_order(order, market_price=60000.0, current_equity=100000.0, initial_cash=100000.0)
    assert not res.is_approved
    assert "Maximum open positions limit reached" in res.rejection_reason

def test_risk_approval_when_all_rules_met():
    rm = RiskManager()
    # Equity = $100,000
    # Position: 0.1 BTC @ 60,000 = $6,000 (6% of equity, <= 10%)
    # Stop loss: 59,000 -> Risk = (60,000 - 59,000) * 0.1 = $100 (0.1% of equity, <= 2%)
    order = OrderCreateRequest(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=0.1,
        stop_loss=59000.0
    )
    res = rm.validate_order(order, market_price=60000.0, current_equity=100000.0, initial_cash=100000.0)
    assert res.is_approved
    assert res.rejection_reason is None
