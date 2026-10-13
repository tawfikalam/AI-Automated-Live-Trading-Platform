from fastapi import APIRouter, HTTPException, Path, Query
from typing import List, Dict, Any
from backend.config import settings
from backend.app.models.schemas import (
    OrderCreateRequest, OrderResponse, PositionResponse,
    TradeHistoryResponse, OrderStatus
)
from backend.app.services.paper_broker import paper_broker
from backend.app.services.ccxt_broker import ccxt_broker
from backend.app.services.market_data import market_data_service
from backend.app.services.storage import storage
from backend.app.services.auto_trader import auto_trading_bot
from backend.app.risk.validator import risk_manager
from backend.app.core.logger import logger

router = APIRouter(prefix="/api/trade", tags=["Paper Trading & Broker Execution"])

@router.get("/broker-status")
def get_broker_status() -> Dict[str, Any]:
    """Check active broker connection type (internal_paper vs Alpaca/CCXT) and sandbox mode."""
    supported = list(ccxt_broker.get_supported_symbols()) if ccxt_broker.is_configured() else []
    return {
        "active_broker": settings.BROKER_TYPE,
        "is_sandbox": settings.BROKER_SANDBOX,
        "alpaca_configured": ccxt_broker.is_configured(),
        "exchange": ccxt_broker.exchange_id,
        "supported_symbols_count": len(supported),
        "supported_symbols": supported,
        "mode_description": (
            "Alpaca Paper Sandbox (via CCXT)" if settings.BROKER_TYPE == "alpaca" and settings.BROKER_SANDBOX
            else "Alpaca Live Real Money" if settings.BROKER_TYPE == "alpaca"
            else "Internal Simulated Paper Sandbox"
        )
    }

# 24/7 Auto-Trader Bot Controls
@router.get("/bot-status")
def get_bot_status() -> Dict[str, Any]:
    """Get 24/7 automated strategy bot execution status."""
    return auto_trading_bot.get_status()

@router.post("/bot-toggle")
def toggle_bot(
    enable: bool = Query(..., description="Enable or disable 24/7 auto trader"),
    strategy_id: str = Query("ict_unicorn", description="Strategy to run"),
    symbol: str = Query("BTC/USDT", description="Symbol to trade"),
    quantity: float = Query(0.01, description="Quantity per trade")
) -> Dict[str, Any]:
    """Turn 24/7 automated strategy bot ON or OFF."""
    if enable:
        auto_trading_bot.start(strategy_id=strategy_id, symbol=symbol, quantity=quantity)
    else:
        auto_trading_bot.stop()
    return auto_trading_bot.get_status()

@router.post("/order", response_model=OrderResponse)
def submit_paper_order(order_req: OrderCreateRequest):
    """
    Validates order with 5-rule Risk Manager, then executes on Alpaca Sandbox or Paper Broker.
    Symbols not listed on US Alpaca broker (e.g. BNB) are seamlessly executed on the Paper Engine.
    """
    market_data = market_data_service.get_market_data(order_req.symbol)
    current_price = market_data.price
    portfolio_summary = paper_broker.get_portfolio_summary()

    # 1. Strict Risk Manager Pre-Trade Evaluation
    risk_result = risk_manager.validate_order(
        order=order_req,
        market_price=current_price,
        current_equity=portfolio_summary.equity,
        initial_cash=portfolio_summary.initial_cash
    )

    if not risk_result.is_approved:
        logger.warning(f"Order rejected by Risk Manager: {risk_result.rejection_reason}")
        raise HTTPException(
            status_code=422,
            detail=risk_result.rejection_reason
        )

    # 2. Broker Routing: Alpaca via CCXT or Internal Paper Broker
    routed_alpaca = False
    alpaca_id = None
    if settings.BROKER_TYPE == "alpaca" and ccxt_broker.is_configured():
        if ccxt_broker.is_symbol_supported(order_req.symbol):
            try:
                alpaca_res = ccxt_broker.execute_order(
                    symbol=order_req.symbol,
                    side=order_req.side,
                    quantity=order_req.quantity,
                    stop_loss=order_req.stop_loss,
                    take_profit=order_req.take_profit
                )
                routed_alpaca = True
                alpaca_id = alpaca_res.get("id")
            except Exception as e:
                logger.warning(f"Alpaca order execution failed ({str(e)}). Routing through internal paper engine.")
        else:
            logger.info(f"{order_req.symbol} is not listed on US broker Alpaca. Seamlessly executed on Paper Sandbox Engine.")

    order_res = paper_broker.execute_paper_order(order_req, current_price)
    if routed_alpaca and alpaca_id:
        order_res.id = f"alpaca_{alpaca_id}"
    return order_res

@router.get("/orders", response_model=List[OrderResponse])
def get_orders():
    """Retrieve recent orders permanently stored in SQLite database."""
    db_orders = storage.get_orders(limit=100)
    return [
        OrderResponse(
            id=o.id,
            symbol=o.symbol,
            side=o.side,
            order_type=o.order_type,
            quantity=o.quantity,
            requested_price=o.requested_price,
            filled_price=o.filled_price,
            stop_loss=o.stop_loss,
            take_profit=o.take_profit,
            status=OrderStatus(o.status),
            rejection_reason=o.rejection_reason,
            created_at=o.created_at.isoformat() if hasattr(o.created_at, "isoformat") else str(o.created_at)
        )
        for o in db_orders
    ]

@router.get("/positions", response_model=List[PositionResponse])
def get_open_positions():
    """Get active open positions permanently stored in SQLite database."""
    return paper_broker.get_positions()

@router.post("/positions/{position_id}/close", response_model=TradeHistoryResponse)
def close_position(position_id: str = Path(..., description="Position ID to close")):
    """Manually close an open position and permanently write to SQLite Trade History."""
    trade = paper_broker.close_paper_position(position_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Position not found or already closed")
    return trade

@router.get("/history", response_model=List[TradeHistoryResponse])
def get_trade_history():
    """Get completed trade history permanently stored in SQLite database."""
    db_trades = storage.get_trade_history(limit=100)
    return [
        TradeHistoryResponse(
            id=t.id,
            order_id=t.order_id,
            symbol=t.symbol,
            side=t.side,
            quantity=t.quantity,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            realized_pnl=t.realized_pnl,
            fee=t.fee,
            closed_at=t.closed_at.isoformat() if hasattr(t.closed_at, "isoformat") else str(t.closed_at)
        )
        for t in db_trades
    ]

@router.post("/reset")
def reset_account():
    """Reset paper account back to initial $100,000 cash balance."""
    storage.reset_portfolio()
    return {"status": "success", "message": "Paper account reset to $100,000.00"}
