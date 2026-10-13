from typing import List
from backend.app.models.schemas import Candle
from backend.app.strategy.base import BaseStrategy, StrategySignal, SignalType
from backend.app.core.logger import logger

class SMACrossoverStrategy(BaseStrategy):
    """
    Rule-based Moving Average Crossover Strategy.
    Buys when Fast SMA (e.g. 9) crosses above Slow SMA (e.g. 21).
    Sells when Fast SMA crosses below Slow SMA.
    """
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        super().__init__(name="SMA_Crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def _calculate_sma(self, closes: List[float], period: int) -> List[float]:
        if len(closes) < period:
            return []
        smas = []
        for i in range(period, len(closes) + 1):
            window = closes[i - period:i]
            smas.append(sum(window) / period)
        return smas

    def evaluate(self, symbol: str, candles: List[Candle]) -> StrategySignal:
        if len(candles) < self.slow_period + 2:
            return StrategySignal(
                symbol=symbol,
                signal=SignalType.HOLD,
                entry_price=candles[-1].close if candles else 0.0,
                recommended_stop_loss=0.0,
                reason=f"Insufficient candles for analysis ({len(candles)}/{self.slow_period + 2} required)",
                indicators={},
                timestamp=candles[-1].timestamp if candles else 0
            )

        closes = [c.close for c in candles]
        fast_smas = self._calculate_sma(closes, self.fast_period)
        slow_smas = self._calculate_sma(closes, self.slow_period)

        current_price = closes[-1]
        timestamp = candles[-1].timestamp

        # Align the last two data points
        # slow_smas[-1] corresponds to closes[-1]
        # slow_smas[-2] corresponds to closes[-2]
        slow_curr = slow_smas[-1]
        slow_prev = slow_smas[-2]

        fast_curr = fast_smas[-1]
        fast_prev = fast_smas[-2]

        indicators = {
            "fast_sma": round(fast_curr, 2),
            "slow_sma": round(slow_curr, 2),
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "prev_fast_sma": round(fast_prev, 2),
            "prev_slow_sma": round(slow_prev, 2)
        }

        # Check Golden Cross (Bullish)
        if fast_prev <= slow_prev and fast_curr > slow_curr:
            stop_loss = round(current_price * 0.98, 2) # 2% stop loss
            take_profit = round(current_price * 1.04, 2) # 4% take profit (1:2 R:R)
            reason = f"Bullish Cross: Fast SMA({self.fast_period}) crossed above Slow SMA({self.slow_period})"
            logger.info(f"[{symbol}] {reason} @ {current_price}")
            return StrategySignal(
                symbol=symbol,
                signal=SignalType.BUY,
                entry_price=current_price,
                recommended_stop_loss=stop_loss,
                recommended_take_profit=take_profit,
                reason=reason,
                indicators=indicators,
                timestamp=timestamp
            )

        # Check Death Cross (Bearish)
        elif fast_prev >= slow_prev and fast_curr < slow_curr:
            stop_loss = round(current_price * 1.02, 2) # 2% stop loss for short
            take_profit = round(current_price * 0.96, 2) # 4% take profit
            reason = f"Bearish Cross: Fast SMA({self.fast_period}) crossed below Slow SMA({self.slow_period})"
            logger.info(f"[{symbol}] {reason} @ {current_price}")
            return StrategySignal(
                symbol=symbol,
                signal=SignalType.SELL,
                entry_price=current_price,
                recommended_stop_loss=stop_loss,
                recommended_take_profit=take_profit,
                reason=reason,
                indicators=indicators,
                timestamp=timestamp
            )

        # Neutral / Hold
        trend = "Bullish (Fast > Slow)" if fast_curr > slow_curr else "Bearish (Fast < Slow)"
        return StrategySignal(
            symbol=symbol,
            signal=SignalType.HOLD,
            entry_price=current_price,
            recommended_stop_loss=0.0,
            recommended_take_profit=0.0,
            reason=f"No crossover detected. Current trend: {trend}",
            indicators=indicators,
            timestamp=timestamp
        )

sma_crossover = SMACrossoverStrategy()
