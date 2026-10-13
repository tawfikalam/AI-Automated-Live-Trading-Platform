from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from backend.app.models.schemas import Candle

class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class StrategySignal(BaseModel):
    symbol: str
    signal: SignalType
    entry_price: float
    recommended_stop_loss: float
    recommended_take_profit: Optional[float] = None
    reason: str
    indicators: Dict[str, Any] = {}
    timestamp: int

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(self, symbol: str, candles: List[Candle]) -> StrategySignal:
        """Evaluates candlestick series and produces a trade signal"""
        pass
