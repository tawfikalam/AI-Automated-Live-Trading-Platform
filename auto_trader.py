import asyncio
import time
from typing import Dict, Any, List
from backend.config import settings
from backend.app.models.schemas import OrderCreateRequest, OrderSide, OrderType
from backend.app.services.market_data import market_data_service
from backend.app.strategy.strategy_library import strategy_evaluator
from backend.app.services.paper_broker import paper_broker
from backend.app.services.ccxt_broker import ccxt_broker
from backend.app.risk.validator import risk_manager
from backend.app.strategy.base import SignalType
from backend.app.core.logger import logger

class AutoTradingBot:
    """
    24/7 Automated Strategy Engine:
    Continuously monitors market, evaluates active strategy,
    passes signals through 5-Guardrail Risk Manager,
    and automatically executes trades on Alpaca/Paper broker.
    """
    def __init__(self):
        self.is_running: bool = False
        self.active_strategy: str = "ict_unicorn"
        self.active_symbol: str = "BTC/USDT"
        self.trade_quantity: float = 0.01
        self.interval_seconds: int = 5
        self.last_signal_time: float = 0.0
        self.last_action_message: str = "Bot initialized and ready to start."
        self.total_auto_trades: int = 0
        self._task: Optional[asyncio.Task] = None

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "active_strategy": self.active_strategy,
            "active_symbol": self.active_symbol,
            "trade_quantity": self.trade_quantity,
            "interval_seconds": self.interval_seconds,
            "last_action_message": self.last_action_message,
            "total_auto_trades": self.total_auto_trades
        }

    def start(self, strategy_id: str = "ict_unicorn", symbol: str = "BTC/USDT", quantity: float = 0.01):
        self.active_strategy = strategy_id
        self.active_symbol = symbol
        self.trade_quantity = quantity
        self.is_running = True
        self.last_action_message = f"🟢 24/7 Auto-Trader Active! Monitoring {symbol} with strategy {strategy_id.upper()}."
        logger.info(self.last_action_message)

    def stop(self):
        self.is_running = False
        self.last_action_message = "⏸️ 24/7 Auto-Trader paused by user."
        logger.info(self.last_action_message)

    async def run_step(self):
        """Single evaluation step executed in background loop"""
        if not self.is_running:
            return

        try:
            candles = market_data_service.get_candles(self.active_symbol, timeframe="1m", count=80)
            if not candles or len(candles) < 25:
                return

            current_price = candles[-1].close
            signal = strategy_evaluator.evaluate(self.active_strategy, self.active_symbol, candles)

            # Check if BUY or SELL signal was triggered
            if signal.signal in [SignalType.BUY, SignalType.SELL]:
                # Don't repeat on same timestamp
                if signal.timestamp == self.last_signal_time:
                    return

                portfolio_summary = paper_broker.get_portfolio_summary()

                order_req = OrderCreateRequest(
                    symbol=self.active_symbol,
                    side=OrderSide.BUY if signal.signal == SignalType.BUY else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=self.trade_quantity,
                    stop_loss=signal.recommended_stop_loss,
                    take_profit=signal.recommended_take_profit
                )

                # 1. Run Risk Manager validation
                risk_res = risk_manager.validate_order(
                    order=order_req,
                    market_price=current_price,
                    current_equity=portfolio_summary.equity,
                    initial_cash=portfolio_summary.initial_cash
                )

                if not risk_res.is_approved:
                    self.last_action_message = f"⚠️ Auto-Trade Signal ({signal.signal}) blocked by Risk Manager: {risk_res.rejection_reason}"
                    return

                # 2. Execute on Alpaca or Paper Broker
                alpaca_executed = False
                alpaca_id = None
                if getattr(settings, "BROKER_TYPE", "internal_paper") == "alpaca" and ccxt_broker.is_configured():
                    if ccxt_broker.is_symbol_supported(self.active_symbol):
                        try:
                            alpaca_res = ccxt_broker.execute_order(
                                symbol=self.active_symbol,
                                side=order_req.side,
                                quantity=self.trade_quantity,
                                stop_loss=signal.recommended_stop_loss,
                                take_profit=signal.recommended_take_profit
                            )
                            alpaca_executed = True
                            alpaca_id = alpaca_res.get("id")
                        except Exception as e:
                            logger.warning(f"Alpaca auto-trade failed: {str(e)}. Fallback to internal paper broker.")
                    else:
                        logger.info(f"Auto-trade: {self.active_symbol} not listed on Alpaca US broker, executing on Paper Sandbox.")

                order_res = paper_broker.execute_paper_order(order_req, current_price)
                if alpaca_executed and alpaca_id:
                    order_res.id = f"alpaca_{alpaca_id}"

                self.last_signal_time = signal.timestamp
                self.total_auto_trades += 1
                self.last_action_message = f"🚀 Auto-Executed: {signal.signal} {self.trade_quantity} {self.active_symbol} @ ${current_price:,.2f} | Reason: {signal.reason}"
                logger.info(self.last_action_message)
            else:
                self.last_action_message = f"Scanning {self.active_symbol}... Signal: {signal.signal} ({signal.reason[:60]}...)"

        except Exception as e:
            logger.error(f"Error in auto trader loop: {str(e)}")

auto_trading_bot = AutoTradingBot()
