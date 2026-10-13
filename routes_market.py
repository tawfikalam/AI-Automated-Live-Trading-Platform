from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
from backend.app.services.market_data import market_data_service, REAL_100_MARKETS
from backend.app.models.schemas import MarketDataResponse, Candle

router = APIRouter(prefix="/api/market", tags=["Live Real Market Data"])

@router.get("/symbols", response_model=List[str])
def get_symbols():
    """Returns list of 100 Real Live Liquid Crypto & Stock Markets."""
    return REAL_100_MARKETS

@router.get("/ticker", response_model=MarketDataResponse)
def get_ticker(symbol: str = Query("BTC/USDT", description="Real trading pair symbol")):
    """Fetch 100% Real Live ticker price and 24h metrics directly from exchange."""
    try:
        return market_data_service.get_market_data(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candles", response_model=List[Candle])
def get_candles(
    symbol: str = Query("BTC/USDT", description="Trading pair symbol"),
    timeframe: str = Query("1m", description="Timeframe: 1m, 3m, 5m, 15m, 1h, 4h, 1d"),
    count: int = Query(150, ge=10, le=300, description="Number of candles")
):
    """Fetch Real Live OHLCV candlestick data with customizable timeframe and historical depth."""
    try:
        return market_data_service.get_candles(symbol, timeframe=timeframe, count=count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
