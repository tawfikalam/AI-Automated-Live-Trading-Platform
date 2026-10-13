from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    APP_NAME: str = "AI Paper Trading Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Paper Trading initial cash
    INITIAL_CASH: float = 100000.0
    BASE_CURRENCY: str = "USD"

    # Risk Management Guardrails
    MAX_RISK_PER_TRADE_PCT: float = 0.02   # 2% max risk per trade
    MAX_POSITION_SIZE_PCT: float = 0.10    # 10% max allocation per position
    DAILY_LOSS_LIMIT_PCT: float = 0.05     # 5% max daily drawdown circuit breaker
    MAX_OPEN_POSITIONS: int = 3            # Max 3 open positions simultaneously
    MANDATORY_STOP_LOSS: bool = True

    # Broker Integration (Internal Paper vs CCXT/Alpaca)
    BROKER_TYPE: str = "internal_paper"    # "internal_paper", "alpaca", "binance"
    BROKER_SANDBOX: bool = True            # True = Alpaca Paper Sandbox, False = Live Money
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    EXCHANGE_API_KEY: str = ""
    EXCHANGE_SECRET_KEY: str = ""

    # Market Data
    MARKET_DATA_PROVIDER: str = "fallback"
    MARKET_STALE_THRESHOLD_SECONDS: int = 300 # 5 min

    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'trading.db'}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
