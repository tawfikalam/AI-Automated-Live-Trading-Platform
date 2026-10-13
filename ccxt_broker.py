import socket
import dns.resolver
from typing import Dict, Any, List, Optional
import ccxt
from backend.config import settings
from backend.app.core.logger import logger
from backend.app.models.schemas import OrderSide, OrderStatus

# DNS Fallback patch
_dns_resolver = dns.resolver.Resolver()
_dns_resolver.nameservers = ['1.1.1.1', '8.8.8.8']
_original_getaddrinfo = socket.getaddrinfo

def _alpaca_dns_patched_getaddrinfo(host, port, *args, **kwargs):
    try:
        return _original_getaddrinfo(host, port, *args, **kwargs)
    except socket.gaierror:
        try:
            answers = _dns_resolver.resolve(str(host), 'A')
            ip = str(answers[0])
            return _original_getaddrinfo(ip, port, *args, **kwargs)
        except Exception:
            return _original_getaddrinfo(host, port, *args, **kwargs)

socket.getaddrinfo = _alpaca_dns_patched_getaddrinfo

class CCXTBrokerAdapter:
    """
    Unified Live/Sandbox Broker Adapter powered by CCXT.
    Supports Alpaca (US Stocks & Crypto), Binance, Bybit, and 100+ exchanges.
    """
    def __init__(self, exchange_id: str = "alpaca"):
        self.exchange_id = exchange_id.lower()
        self.client: Optional[ccxt.Exchange] = None
        self._supported_symbols: Optional[set] = None
        self._init_client()

    def _init_client(self):
        apiKey = getattr(settings, "ALPACA_API_KEY", "") or getattr(settings, "EXCHANGE_API_KEY", "")
        secret = getattr(settings, "ALPACA_SECRET_KEY", "") or getattr(settings, "EXCHANGE_SECRET_KEY", "")

        exchange_class = getattr(ccxt, self.exchange_id, None)
        if not exchange_class:
            logger.error(f"Exchange {self.exchange_id} is not supported by CCXT.")
            return

        config: Dict[str, Any] = {
            "apiKey": apiKey,
            "secret": secret,
            "enableRateLimit": True,
            "timeout": 15000,
        }

        self.client = exchange_class(config)

        is_sandbox = getattr(settings, "BROKER_SANDBOX", True)
        if is_sandbox and hasattr(self.client, "set_sandbox_mode"):
            self.client.set_sandbox_mode(True)
            logger.info(f"Connected to {self.exchange_id.upper()} in SANDBOX/PAPER mode.")
        else:
            logger.warning(f"Connected to {self.exchange_id.upper()} in LIVE mode.")

    def is_configured(self) -> bool:
        if not self.client:
            return False
        return bool(self.client.apiKey and self.client.secret)

    def get_supported_symbols(self) -> set:
        """Returns set of symbols supported by active broker."""
        if not self.is_configured():
            return set()
        if self._supported_symbols is None:
            try:
                markets = self.client.load_markets()
                self._supported_symbols = set(markets.keys())
            except Exception as e:
                logger.warning(f"Failed to load markets for {self.exchange_id}: {e}")
                self._supported_symbols = set()
        return self._supported_symbols

    def is_symbol_supported(self, symbol: str) -> bool:
        """Checks if symbol (e.g. BTC/USDT or BTC/USD) is tradable on active broker."""
        supported = self.get_supported_symbols()
        if not supported:
            # If not loaded, allow attempt
            return True
        norm_usd = symbol.replace("/USDT", "/USD")
        return (symbol in supported) or (norm_usd in supported)

    def get_account_summary(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "configured": False,
                "message": f"{self.exchange_id.upper()} API keys not provided in .env",
                "cash": 0.0,
                "equity": 0.0
            }

        try:
            balance = self.client.fetch_balance()
            total_equity = float(balance.get("total", {}).get("USD", 0.0) or balance.get("total", {}).get("USDT", 0.0))
            free_cash = float(balance.get("free", {}).get("USD", 0.0) or balance.get("free", {}).get("USDT", 0.0))

            return {
                "configured": True,
                "exchange": self.exchange_id,
                "sandbox": getattr(settings, "BROKER_SANDBOX", True),
                "cash": free_cash,
                "equity": total_equity,
                "raw": balance
            }
        except Exception as e:
            logger.error(f"Failed to fetch {self.exchange_id} balance: {str(e)}")
            return {
                "configured": True,
                "error": str(e),
                "cash": 0.0,
                "equity": 0.0
            }

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []

        try:
            if hasattr(self.client, "fetch_positions"):
                raw_positions = self.client.fetch_positions()
                return [
                    {
                        "symbol": p.get("symbol"),
                        "side": p.get("side", "long").upper(),
                        "quantity": float(p.get("contracts") or p.get("amount") or 0.0),
                        "entry_price": float(p.get("entryPrice") or 0.0),
                        "current_price": float(p.get("markPrice") or 0.0),
                        "unrealized_pnl": float(p.get("unrealizedPnl") or 0.0)
                    }
                    for p in raw_positions if float(p.get("contracts") or p.get("amount") or 0.0) > 0
                ]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch positions: {str(e)}")
            return []

    def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_loss: float,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes order on Alpaca broker with automatic USD currency normalization.
        """
        if not self.is_configured():
            raise ValueError(f"Cannot execute live order: {self.exchange_id.upper()} API credentials missing in .env")

        try:
            market_side = side.value.lower()
            params: Dict[str, Any] = {}

            # Alpaca account base currency is USD, not USDT!
            alpaca_symbol = symbol.replace("/USDT", "/USD")

            if stop_loss:
                params["stopLoss"] = {"stopPrice": stop_loss}
            if take_profit:
                params["takeProfit"] = {"limitPrice": take_profit}

            logger.info(f"Submitting {self.exchange_id.upper()} Order: {market_side} {quantity} {alpaca_symbol} (SL: {stop_loss})")
            order = self.client.create_order(
                symbol=alpaca_symbol,
                type="market",
                side=market_side,
                amount=quantity,
                params=params
            )

            logger.info(f"Order filled on {self.exchange_id.upper()}: ID {order.get('id')}")
            return {
                "id": str(order.get("id")),
                "symbol": alpaca_symbol,
                "side": side.value,
                "quantity": quantity,
                "filled_price": float(order.get("price") or order.get("average") or 0.0),
                "status": OrderStatus.FILLED.value,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "broker": self.exchange_id
            }
        except Exception as e:
            logger.error(f"Order submission failed on {self.exchange_id}: {str(e)}")
            raise e

ccxt_broker = CCXTBrokerAdapter(exchange_id="alpaca")
