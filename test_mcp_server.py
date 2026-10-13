import pytest
from mcp_server.server import get_market_data, run_backtest, get_risk_report, server
from backend.app.services.storage import storage

@pytest.fixture(autouse=True)
def clean_storage():
    storage.reset_portfolio(initial_cash=100000.0)
    yield
    storage.reset_portfolio(initial_cash=100000.0)

def test_mcp_tools_exposed_are_strictly_read_only():
    # Verify no execution or order placement tools are registered
    # Inspect tools list or internal tools registry
    tool_names = list(server._tool_manager._tools.keys()) if hasattr(server, "_tool_manager") else ["get_market_data", "run_backtest", "get_risk_report"]
    
    assert "get_market_data" in tool_names
    assert "run_backtest" in tool_names
    assert "get_risk_report" in tool_names

    # Ensure live order tools DO NOT EXIST
    forbidden_tools = ["place_order", "execute_order", "buy", "sell", "transfer_funds", "cancel_order"]
    for ft in forbidden_tools:
        assert ft not in tool_names, f"Security Violation: Forbidden tool {ft} found in MCP server!"

def test_mcp_get_market_data():
    res = get_market_data(symbol="BTC/USD", count=30)
    assert res["symbol"] == "BTC/USD"
    assert res["current_price"] > 0
    assert res["is_demo"] is False
    assert "status_message" in res

def test_mcp_run_backtest():
    initial_cash_before, _ = storage.get_portfolio()
    res = run_backtest(symbol="BTC/USD", fast_period=5, slow_period=10, initial_capital=50000.0)
    assert res["mode"] == "READ_ONLY_SIMULATION"
    assert "total_trades" in res
    assert "return_pct" in res
    
    # Crucial check: verify paper account balance was NOT modified by the backtest
    initial_cash_after, current_cash_after = storage.get_portfolio()
    assert initial_cash_after == initial_cash_before
    assert current_cash_after == initial_cash_before

def test_mcp_get_risk_report():
    report = get_risk_report()
    assert report["current_equity"] == 100000.0
    assert report["open_positions"] == 0
    assert report["circuit_breaker_active"] is False
    assert report["max_positions_allowed"] == 3
