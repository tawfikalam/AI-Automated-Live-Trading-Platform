import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from backend.config import settings
from backend.app.models.schemas import (
    OrderCreateRequest, OrderResponse, PositionResponse,
    TradeHistoryResponse, PortfolioSummary, OrderStatus,
    OrderSide, PositionSide
)
from backend.app.services.storage import storage
from backend.app.services.market_data import market_data_service
from backend.app.core.logger import logger

class PaperBroker:
    def __init__(self):
        self.storage = storage
        self.slippage_pct = 0.0005 # 0.05% slippage simulation
        self.fee_pct = 0.0005      # 0.05% maker/taker fee

    def get_portfolio_summary(self) -> PortfolioSummary:
        initial_cash, cash = self.storage.get_portfolio()
        open_positions = self.storage.get_open_positions()
        trade_history = self.storage.get_trade_history()

        unrealized_pnl = 0.0
        total_position_value = 0.0

        for pos in open_positions:
            # fetch current price
            m_data = market_data_service.get_market_data(pos.symbol)
            curr_price = m_data.price
            if pos.side == PositionSide.LONG.value:
                pnl = (curr_price - pos.entry_price) * pos.quantity
            else:
                pnl = (pos.entry_price - curr_price) * pos.quantity
            unrealized_pnl += pnl
            total_position_value += (pos.entry_price * pos.quantity)

        equity = cash + total_position_value + unrealized_pnl
        realized_pnl = sum(t.realized_pnl for t in trade_history)
        total_pnl = round(realized_pnl + unrealized_pnl, 2)
        total_pnl_pct = round((total_pnl / initial_cash) * 100, 2) if initial_cash > 0 else 0.0

        winning_trades = [t for t in trade_history if t.realized_pnl > 0]
        losing_trades = [t for t in trade_history if t.realized_pnl <= 0]
        win_rate = round((len(winning_trades) / len(trade_history) * 100), 1) if trade_history else 0.0

        # Check circuit breaker: daily loss limit
        daily_loss_limit_amount = initial_cash * settings.DAILY_LOSS_LIMIT_PCT
        circuit_breaker = (realized_pnl + unrealized_pnl) <= -daily_loss_limit_amount

        return PortfolioSummary(
            initial_cash=round(initial_cash, 2),
            cash=round(cash, 2),
            equity=round(equity, 2),
            realized_pnl=round(realized_pnl, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            open_positions_count=len(open_positions),
            max_positions_limit=settings.MAX_OPEN_POSITIONS,
            total_trades_count=len(trade_history),
            winning_trades_count=len(winning_trades),
            losing_trades_count=len(losing_trades),
            win_rate_pct=win_rate,
            circuit_breaker_tripped=circuit_breaker
        )

    def get_positions(self) -> List[PositionResponse]:
        raw_positions = self.storage.get_open_positions()
        results: List[PositionResponse] = []

        for p in raw_positions:
            m_data = market_data_service.get_market_data(p.symbol)
            curr_price = m_data.price
            if p.side == PositionSide.LONG.value:
                pnl = (curr_price - p.entry_price) * p.quantity
                pnl_pct = ((curr_price - p.entry_price) / p.entry_price) * 100
            else:
                pnl = (p.entry_price - curr_price) * p.quantity
                pnl_pct = ((p.entry_price - curr_price) / p.entry_price) * 100

            results.append(PositionResponse(
                id=p.id,
                symbol=p.symbol,
                side=PositionSide(p.side),
                quantity=p.quantity,
                entry_price=round(p.entry_price, 2),
                current_price=round(curr_price, 2),
                stop_loss=round(p.stop_loss, 2),
                take_profit=round(p.take_profit, 2) if p.take_profit else None,
                unrealized_pnl=round(p.unrealized_pnl if hasattr(p, 'unrealized_pnl') else pnl, 2),
                unrealized_pnl_pct=round(pnl_pct, 2),
                opened_at=p.opened_at.isoformat() if hasattr(p.opened_at, "isoformat") else str(p.opened_at)
            ))
        return results

    def execute_paper_order(self, order_req: OrderCreateRequest, market_price: float) -> OrderResponse:
        order_id = f"ord_{uuid.uuid4().hex[:8]}"

        # Calculate slippage
        if order_req.side == OrderSide.BUY:
            fill_price = market_price * (1.0 + self.slippage_pct)
        else:
            fill_price = market_price * (1.0 - self.slippage_pct)

        order_cost = fill_price * order_req.quantity
        fee = order_cost * self.fee_pct
        total_deduction = order_cost + fee

        initial_cash, current_cash = self.storage.get_portfolio()

        if current_cash < total_deduction:
            # Insufficient virtual funds
            rejected_order = {
                "id": order_id,
                "symbol": order_req.symbol,
                "side": order_req.side.value,
                "order_type": order_req.order_type.value,
                "quantity": order_req.quantity,
                "requested_price": order_req.price or market_price,
                "filled_price": None,
                "stop_loss": order_req.stop_loss,
                "take_profit": order_req.take_profit,
                "status": OrderStatus.REJECTED.value,
                "rejection_reason": f"Insufficient paper trading funds. Required: ${total_deduction:,.2f}, Available: ${current_cash:,.2f}",
                "created_at": datetime.now(timezone.utc)
            }
            self.storage.save_order(rejected_order)
            logger.warning(f"Order {order_id} rejected: insufficient funds")
            return OrderResponse(
                id=order_id,
                symbol=order_req.symbol,
                side=order_req.side,
                order_type=order_req.order_type,
                quantity=order_req.quantity,
                requested_price=order_req.price or market_price,
                filled_price=None,
                stop_loss=order_req.stop_loss,
                take_profit=order_req.take_profit,
                status=OrderStatus.REJECTED,
                rejection_reason=rejected_order["rejection_reason"],
                created_at=rejected_order["created_at"].isoformat()
            )

        # Deduct virtual cash
        self.storage.update_cash(-total_deduction)

        # Record order
        now = datetime.now(timezone.utc)
        order_record = {
            "id": order_id,
            "symbol": order_req.symbol,
            "side": order_req.side.value,
            "order_type": order_req.order_type.value,
            "quantity": order_req.quantity,
            "requested_price": order_req.price or market_price,
            "filled_price": round(fill_price, 2),
            "stop_loss": order_req.stop_loss,
            "take_profit": order_req.take_profit,
            "status": OrderStatus.FILLED.value,
            "rejection_reason": None,
            "created_at": now
        }
        self.storage.save_order(order_record)

        # Open Position
        pos_id = f"pos_{uuid.uuid4().hex[:8]}"
        pos_record = {
            "id": pos_id,
            "symbol": order_req.symbol,
            "side": PositionSide.LONG.value if order_req.side == OrderSide.BUY else PositionSide.SHORT.value,
            "quantity": order_req.quantity,
            "entry_price": round(fill_price, 2),
            "stop_loss": order_req.stop_loss,
            "take_profit": order_req.take_profit,
            "opened_at": now
        }
        self.storage.open_position(pos_record)

        logger.info(f"Simulated Paper Order FILLED: {order_req.side.value} {order_req.quantity} {order_req.symbol} @ ${fill_price:,.2f}")

        return OrderResponse(
            id=order_id,
            symbol=order_req.symbol,
            side=order_req.side,
            order_type=order_req.order_type,
            quantity=order_req.quantity,
            requested_price=order_req.price or market_price,
            filled_price=round(fill_price, 2),
            stop_loss=order_req.stop_loss,
            take_profit=order_req.take_profit,
            status=OrderStatus.FILLED,
            rejection_reason=None,
            created_at=now.isoformat()
        )

    def close_paper_position(self, position_id: str) -> Optional[TradeHistoryResponse]:
        # Find position to get symbol
        positions = self.storage.get_open_positions()
        target_pos = next((p for p in positions if p.id == position_id), None)
        if not target_pos:
            return None

        m_data = market_data_service.get_market_data(target_pos.symbol)
        exit_price = m_data.price
        fee = exit_price * target_pos.quantity * self.fee_pct

        trade = self.storage.close_position(position_id, exit_price, fee)
        if trade:
            return TradeHistoryResponse(
                id=trade.id,
                order_id=trade.order_id,
                symbol=trade.symbol,
                side=trade.side,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                realized_pnl=trade.realized_pnl,
                fee=trade.fee,
                closed_at=trade.closed_at.isoformat() if hasattr(trade.closed_at, "isoformat") else str(trade.closed_at)
            )
        return None

paper_broker = PaperBroker()
