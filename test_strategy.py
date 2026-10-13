import pytest
from backend.app.models.schemas import Candle
from backend.app.strategy.sma_crossover import SMACrossoverStrategy
from backend.app.strategy.base import SignalType

def make_candle(t: int, close: float) -> Candle:
    return Candle(
        timestamp=t,
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        volume=10.0
    )

def test_insufficient_candles():
    strat = SMACrossoverStrategy(fast_period=9, slow_period=21)
    candles = [make_candle(i, 100.0) for i in range(10)]
    signal = strat.evaluate("BTC/USD", candles)
    assert signal.signal == SignalType.HOLD
    assert "Insufficient candles" in signal.reason

def test_bullish_sma_crossover():
    strat = SMACrossoverStrategy(fast_period=3, slow_period=5)
    # Downtrend then sharp uptrend crossing exactly on last candle
    prices = [100.0, 98.0, 96.0, 94.0, 92.0, 90.0, 95.0, 105.0]
    candles = [make_candle(i * 60000, p) for i, p in enumerate(prices)]
    signal = strat.evaluate("BTC/USD", candles)
    
    assert signal.signal == SignalType.BUY
    assert signal.recommended_stop_loss < signal.entry_price
    assert signal.recommended_take_profit > signal.entry_price
    assert "Bullish Cross" in signal.reason

def test_bearish_sma_crossover():
    strat = SMACrossoverStrategy(fast_period=3, slow_period=5)
    # Uptrend then sharp downtrend crossing exactly on last candle
    prices = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 105.0, 95.0]
    candles = [make_candle(i * 60000, p) for i, p in enumerate(prices)]
    signal = strat.evaluate("BTC/USD", candles)

    assert signal.signal == SignalType.SELL
    assert signal.recommended_stop_loss > signal.entry_price
    assert signal.recommended_take_profit < signal.entry_price
    assert "Bearish Cross" in signal.reason
