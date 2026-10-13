from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class Candle(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_24h_pct: float
    high_24h: float
    low_24h: float
    volume_24h: float
    timestamp: str
    is_stale: bool = False
    is_demo: bool = True
    source: str = "Demo Engine"
    status_message: str = "Demo feed active. Not actual exchange live order."
    candles: List[Candle] = []

class OrderCreateRequest(BaseModel):
    symbol: str = Field(..., json_schema_extra={"example": "BTC/USD"})
    side: OrderSide = Field(..., json_schema_extra={"example": OrderSide.BUY})
    order_type: OrderType = Field(default=OrderType.MARKET)
    quantity: float = Field(..., gt=0, json_schema_extra={"example": 0.5})
    price: Optional[float] = Field(default=None, description="Limit price if LIMIT order, otherwise market price")
    stop_loss: Optional[float] = Field(default=None, description="Stop Loss Price checked by Risk Manager")
    take_profit: Optional[float] = Field(default=None, description="Optional Take Profit Price")

class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    requested_price: Optional[float]
    filled_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: OrderStatus
    rejection_reason: Optional[str] = None
    created_at: str

class PositionResponse(BaseModel):
    id: str
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: Optional[float]
    unrealized_pnl: float
    unrealized_pnl_pct: float
    opened_at: str

class TradeHistoryResponse(BaseModel):
    id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    realized_pnl: float
    fee: float
    closed_at: str

class PortfolioSummary(BaseModel):
    initial_cash: float
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    total_pnl_pct: float
    open_positions_count: int
    max_positions_limit: int
    total_trades_count: int
    winning_trades_count: int
    losing_trades_count: int
    win_rate_pct: float
    circuit_breaker_tripped: bool

class RiskValidationResult(BaseModel):
    is_approved: bool
    rejection_reason: Optional[str] = None
    risk_metrics: Dict[str, Any] = {}

class RiskReportResponse(BaseModel):
    equity: float
    cash: float
    total_positions: int
    max_positions_allowed: int
    daily_realized_loss: float
    daily_loss_limit_amount: float
    circuit_breaker_active: bool
    risk_per_trade_pct_limit: float
    max_position_size_pct_limit: float
    open_risk_exposure: float
