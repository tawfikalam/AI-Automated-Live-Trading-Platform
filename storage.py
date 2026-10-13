import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings
from backend.app.models.db_models import Base, PortfolioState, OrderRecord, PositionRecord, TradeHistoryRecord
from backend.app.models.schemas import OrderSide, OrderStatus, PositionSide
from backend.app.core.logger import logger

class StorageService:
    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._init_db()

    def _init_db(self):
        Base.metadata.create_all(bind=self.engine)
        # Initialize default portfolio state if not exists
        with self.get_session() as session:
            portfolio = session.query(PortfolioState).first()
            if not portfolio:
                portfolio = PortfolioState(
                    initial_cash=settings.INITIAL_CASH,
                    cash=settings.INITIAL_CASH
                )
                session.add(portfolio)
                session.commit()
                logger.info(f"Initialized new portfolio with ${settings.INITIAL_CASH:,.2f}")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def get_portfolio(self) -> Tuple[float, float]:
        """Returns (initial_cash, current_cash)"""
        with self.get_session() as session:
            portfolio = session.query(PortfolioState).first()
            if portfolio:
                return portfolio.initial_cash, portfolio.cash
            return settings.INITIAL_CASH, settings.INITIAL_CASH

    def update_cash(self, delta: float) -> float:
        """Adds or deducts cash and returns new cash balance"""
        with self.get_session() as session:
            portfolio = session.query(PortfolioState).first()
            if not portfolio:
                portfolio = PortfolioState(initial_cash=settings.INITIAL_CASH, cash=settings.INITIAL_CASH)
                session.add(portfolio)
            portfolio.cash += delta
            session.commit()
            return portfolio.cash

    def reset_portfolio(self, initial_cash: float = settings.INITIAL_CASH):
        """Resets paper trading account to pristine initial state"""
        with self.get_session() as session:
            session.query(PositionRecord).delete()
            session.query(TradeHistoryRecord).delete()
            session.query(OrderRecord).delete()
            portfolio = session.query(PortfolioState).first()
            if portfolio:
                portfolio.initial_cash = initial_cash
                portfolio.cash = initial_cash
            else:
                session.add(PortfolioState(initial_cash=initial_cash, cash=initial_cash))
            session.commit()
            logger.info(f"Reset portfolio to ${initial_cash:,.2f}")

    def save_order(self, order_dict: dict) -> OrderRecord:
        with self.get_session() as session:
            order = OrderRecord(**order_dict)
            session.add(order)
            session.commit()
            session.refresh(order)
            return order

    def get_orders(self, limit: int = 50) -> List[OrderRecord]:
        with self.get_session() as session:
            return session.query(OrderRecord).order_by(OrderRecord.created_at.desc()).limit(limit).all()

    def get_open_positions(self) -> List[PositionRecord]:
        with self.get_session() as session:
            return session.query(PositionRecord).all()

    def open_position(self, position_dict: dict) -> PositionRecord:
        with self.get_session() as session:
            position = PositionRecord(**position_dict)
            session.add(position)
            session.commit()
            session.refresh(position)
            return position

    def close_position(self, position_id: str, exit_price: float, fee: float = 0.0) -> Optional[TradeHistoryRecord]:
        with self.get_session() as session:
            pos = session.query(PositionRecord).filter(PositionRecord.id == position_id).first()
            if not pos:
                return None
            
            # Calculate realized P&L
            if pos.side == PositionSide.LONG.value:
                pnl = (exit_price - pos.entry_price) * pos.quantity - fee
            else: # SHORT
                pnl = (pos.entry_price - exit_price) * pos.quantity - fee

            # Return capital + P&L to cash balance
            returned_capital = (pos.entry_price * pos.quantity) + pnl
            portfolio = session.query(PortfolioState).first()
            if portfolio:
                portfolio.cash += returned_capital

            # Create trade history record
            history_record = TradeHistoryRecord(
                id=f"trade_{uuid.uuid4().hex[:8]}",
                order_id=pos.id,
                symbol=pos.symbol,
                side=pos.side,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                realized_pnl=round(pnl, 2),
                fee=round(fee, 2),
                closed_at=datetime.now(timezone.utc)
            )
            session.add(history_record)
            session.delete(pos)
            session.commit()
            session.refresh(history_record)
            logger.info(f"Closed position {pos.symbol} {pos.quantity} @ {exit_price}. P&L: ${pnl:,.2f}")
            return history_record

    def get_trade_history(self, limit: int = 50) -> List[TradeHistoryRecord]:
        with self.get_session() as session:
            return session.query(TradeHistoryRecord).order_by(TradeHistoryRecord.closed_at.desc()).limit(limit).all()

storage = StorageService()
