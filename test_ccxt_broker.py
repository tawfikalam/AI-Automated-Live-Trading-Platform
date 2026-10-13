import pytest
from unittest.mock import MagicMock
from backend.app.services.ccxt_broker import CCXTBrokerAdapter
from backend.app.models.schemas import OrderSide

def test_ccxt_broker_initialization():
    adapter = CCXTBrokerAdapter(exchange_id="alpaca")
    assert adapter.exchange_id == "alpaca"
    assert adapter.client is not None
    # With keys configured in .env, is_configured should be True
    assert adapter.is_configured() is True

def test_ccxt_broker_summary():
    adapter = CCXTBrokerAdapter(exchange_id="alpaca")
    summary = adapter.get_account_summary()
    assert summary["configured"] is True
    assert summary["exchange"] == "alpaca"

def test_ccxt_broker_mocked_execution():
    adapter = CCXTBrokerAdapter(exchange_id="alpaca")
    mock_client = MagicMock()
    mock_client.apiKey = "mock_key"
    mock_client.secret = "mock_secret"
    mock_client.create_order.return_value = {
        "id": "12345_alpaca",
        "symbol": "BTC/USD",
        "side": "buy",
        "amount": 0.05,
        "price": 60000.0,
        "average": 60000.0
    }
    adapter.client = mock_client

    assert adapter.is_configured() is True
    res = adapter.execute_order(
        symbol="BTC/USD",
        side=OrderSide.BUY,
        quantity=0.05,
        stop_loss=58000.0,
        take_profit=64000.0
    )
    assert res["id"] == "12345_alpaca"
    assert res["status"] == "FILLED"
    assert mock_client.create_order.called
