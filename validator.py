from typing import List, Optional
from backend.app.models.schemas import OrderCreateRequest, OrderSide, RiskValidationResult, RiskReportResponse
from backend.app.risk.rules import risk_config
from backend.app.services.storage import storage
from backend.app.core.logger import logger

class RiskManager:
    def __init__(self, config=risk_config):
        self.config = config

    def validate_order(
        self,
        order: OrderCreateRequest,
        market_price: float,
        current_equity: float,
        initial_cash: float
    ) -> RiskValidationResult:
        """
        Executes strict 5-layer Risk Management validation before any order execution.
        """
        price = order.price or market_price
        open_positions = storage.get_open_positions()
        trade_history = storage.get_trade_history()

        # Rule 1: Maximum Open Positions Limit (Max 3 concurrent)
        if len(open_positions) >= self.config.max_open_positions:
            msg = f"RISK REJECTION: Maximum open positions limit reached ({len(open_positions)}/{self.config.max_open_positions}). Close a position before opening a new one."
            logger.warning(msg)
            return RiskValidationResult(
                is_approved=False,
                rejection_reason=msg,
                risk_metrics={"open_positions": len(open_positions), "limit": self.config.max_open_positions}
            )

        # Rule 2: Daily Loss Limit (Circuit Breaker)
        realized_loss = sum(t.realized_pnl for t in trade_history)
        max_daily_allowed_loss = initial_cash * self.config.daily_loss_limit_pct
        if realized_loss <= -max_daily_allowed_loss:
            msg = f"RISK REJECTION: Daily Loss Limit Circuit Breaker active! Total loss ${abs(realized_loss):,.2f} exceeds threshold ${max_daily_allowed_loss:,.2f} (5%). Trading locked."
            logger.warning(msg)
            return RiskValidationResult(
                is_approved=False,
                rejection_reason=msg,
                risk_metrics={"daily_loss": realized_loss, "allowed_threshold": max_daily_allowed_loss}
            )

        # Rule 3: Mandatory Stop Loss
        if self.config.mandatory_stop_loss:
            if not order.stop_loss or order.stop_loss <= 0:
                msg = "RISK REJECTION: Mandatory Stop Loss is missing or invalid. Every trade must have a defined Stop Loss."
                logger.warning(msg)
                return RiskValidationResult(is_approved=False, rejection_reason=msg)

            if order.side == OrderSide.BUY and order.stop_loss >= price:
                msg = f"RISK REJECTION: For BUY orders, Stop Loss (${order.stop_loss}) must be BELOW entry price (${price})."
                logger.warning(msg)
                return RiskValidationResult(is_approved=False, rejection_reason=msg)

            if order.side == OrderSide.SELL and order.stop_loss <= price:
                msg = f"RISK REJECTION: For SELL orders, Stop Loss (${order.stop_loss}) must be ABOVE entry price (${price})."
                logger.warning(msg)
                return RiskValidationResult(is_approved=False, rejection_reason=msg)

        # Rule 4: Maximum Position Size (Max 10% of equity per position)
        position_value = order.quantity * price
        max_allowed_position_value = current_equity * self.config.max_position_size_pct
        if position_value > max_allowed_position_value:
            msg = (
                f"RISK REJECTION: Position size ${position_value:,.2f} exceeds "
                f"maximum allowed limit ${max_allowed_position_value:,.2f} "
                f"({self.config.max_position_size_pct * 100:.1f}% of current equity ${current_equity:,.2f})."
            )
            logger.warning(msg)
            return RiskValidationResult(
                is_approved=False,
                rejection_reason=msg,
                risk_metrics={
                    "position_value": position_value,
                    "max_allowed": max_allowed_position_value,
                    "equity": current_equity
                }
            )

        # Rule 5: Maximum Risk per Trade (Max 2% of equity at risk)
        per_unit_risk = abs(price - order.stop_loss)
        total_trade_risk = per_unit_risk * order.quantity
        max_allowed_trade_risk = current_equity * self.config.max_risk_per_trade_pct

        if total_trade_risk > max_allowed_trade_risk:
            msg = (
                f"RISK REJECTION: Total capital at risk ${total_trade_risk:,.2f} exceeds "
                f"maximum risk per trade limit ${max_allowed_trade_risk:,.2f} "
                f"({self.config.max_risk_per_trade_pct * 100:.1f}% of current equity ${current_equity:,.2f}). "
                f"Reduce quantity or tighten Stop Loss."
            )
            logger.warning(msg)
            return RiskValidationResult(
                is_approved=False,
                rejection_reason=msg,
                risk_metrics={
                    "total_risk": total_trade_risk,
                    "max_allowed_risk": max_allowed_trade_risk,
                    "equity": current_equity
                }
            )

        # If all 5 checks pass:
        logger.info(f"Risk checks passed for order: {order.symbol} {order.quantity} units. Risk: ${total_trade_risk:,.2f}")
        return RiskValidationResult(
            is_approved=True,
            rejection_reason=None,
            risk_metrics={
                "position_value": position_value,
                "total_risk": total_trade_risk,
                "risk_equity_pct": round((total_trade_risk / current_equity) * 100, 2)
            }
        )

    def generate_risk_report(self, current_equity: float, initial_cash: float) -> RiskReportResponse:
        open_positions = storage.get_open_positions()
        trade_history = storage.get_trade_history()
        realized_loss = sum(t.realized_pnl for t in trade_history)
        daily_loss_limit_amount = initial_cash * self.config.daily_loss_limit_pct
        circuit_breaker = realized_loss <= -daily_loss_limit_amount

        # calculate total risk exposure on open positions
        open_risk = sum(abs(p.entry_price - p.stop_loss) * p.quantity for p in open_positions)

        return RiskReportResponse(
            equity=round(current_equity, 2),
            cash=round(current_equity, 2),
            total_positions=len(open_positions),
            max_positions_allowed=self.config.max_open_positions,
            daily_realized_loss=round(realized_loss, 2),
            daily_loss_limit_amount=round(daily_loss_limit_amount, 2),
            circuit_breaker_active=circuit_breaker,
            risk_per_trade_pct_limit=self.config.max_risk_per_trade_pct * 100,
            max_position_size_pct_limit=self.config.max_position_size_pct * 100,
            open_risk_exposure=round(open_risk, 2)
        )

risk_manager = RiskManager()
