import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.services.storage import storage

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    storage.reset_portfolio(initial_cash=100000.0)
    yield
    storage.reset_portfolio(initial_cash=100000.0)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["paper_trading"] is True
    assert data["live_trading_enabled"] is False

def test_market_ticker():
    res = client.get("/api/market/ticker?symbol=BTC/USDT")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "BTC/USDT"
    assert data["price"] > 0
    assert data["is_demo"] is False

def test_market_candles():
    res = client.get("/api/market/candles?symbol=BTC/USD&count=20")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 20
    assert "close" in data[0]

def test_portfolio_summary():
    res = client.get("/api/analytics/portfolio")
    assert res.status_code == 200
    data = res.json()
    assert data["cash"] == 100000.0
    assert data["open_positions_count"] == 0

def test_submit_valid_paper_order():
    payload = {
        "symbol": "BTC/USD",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.05,
        "stop_loss": 50000.0,
        "take_profit": 75000.0
    }
    res = client.post("/api/trade/order", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "FILLED"
    assert data["symbol"] == "BTC/USD"

def test_submit_order_rejected_by_risk():
    # Attempt oversized position ($60,000 > 10% limit of $10,000)
    payload = {
        "symbol": "BTC/USD",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 1.0,
        "stop_loss": 59000.0
    }
    res = client.post("/api/trade/order", json=payload)
    assert res.status_code == 422
    assert "exceeds maximum allowed limit" in res.json()["detail"]

def test_strategy_signal():
    res = client.get("/api/analytics/strategy-signal?symbol=BTC/USD")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "BTC/USD"
    assert data["signal"] in ["BUY", "SELL", "HOLD"]
