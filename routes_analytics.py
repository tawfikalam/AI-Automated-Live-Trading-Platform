from fastapi import APIRouter, Query
from typing import List, Dict, Any
from backend.app.models.schemas import PortfolioSummary, RiskReportResponse
from backend.app.services.paper_broker import paper_broker
from backend.app.services.market_data import market_data_service
from backend.app.risk.validator import risk_manager
from backend.app.strategy.strategy_library import ALL_40_STRATEGIES, strategy_evaluator
from backend.app.strategy.base import StrategySignal

router = APIRouter(prefix="/api/analytics", tags=["Analytics, Risk & 40 Strategies"])

@router.get("/portfolio", response_model=PortfolioSummary)
def get_portfolio_summary():
    """Retrieve full portfolio metrics: Balance, Equity, Realized/Unrealized P&L, Win Rate, and Circuit Breaker state."""
    return paper_broker.get_portfolio_summary()

@router.get("/risk-report", response_model=RiskReportResponse)
def get_risk_report():
    """Audit current risk exposure, open positions, daily loss, and circuit breaker metrics."""
    portfolio = paper_broker.get_portfolio_summary()
    return risk_manager.generate_risk_report(portfolio.equity, portfolio.initial_cash)

@router.get("/strategies")
def get_available_strategies() -> List[Dict[str, str]]:
    """Returns metadata for all 40 institutional, SMC, Auction Market, and Algorithmic strategies."""
    return [s.to_dict() for s in ALL_40_STRATEGIES]

@router.get("/strategy-signal", response_model=StrategySignal)
def get_strategy_signal(
    strategy_id: str = Query("ict_unicorn", description="Strategy ID to evaluate"),
    symbol: str = Query("BTC/USDT", description="Symbol to evaluate")
):
    """Run any of the 40 strategies on REAL live candle data and return BUY/SELL/HOLD signal."""
    candles = market_data_service.get_candles(symbol, count=80)
    return strategy_evaluator.evaluate(strategy_id, symbol, candles)
