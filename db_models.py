from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class PortfolioState(Base):
    __tablename__ = "portfolio_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    initial_cash = Column(Float, default=100000.0)
    cash = Column(Float, default=100000.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class OrderRecord(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    requested_price = Column(Float, nullable=True)
    filled_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=True)
    status = Column(String, nullable=False) # FILLED, REJECTED, CANCELLED
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PositionRecord(Base):
    __tablename__ = "positions"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=True)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class TradeHistoryRecord(Base):
    __tablename__ = "trade_history"

    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    closed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
