from pydantic import BaseModel
from backend.config import settings

class RiskConfig(BaseModel):
    max_risk_per_trade_pct: float = settings.MAX_RISK_PER_TRADE_PCT  # 0.02 (2%)
    max_position_size_pct: float = settings.MAX_POSITION_SIZE_PCT    # 0.10 (10%)
    daily_loss_limit_pct: float = settings.DAILY_LOSS_LIMIT_PCT      # 0.05 (5%)
    max_open_positions: int = settings.MAX_OPEN_POSITIONS            # 3
    mandatory_stop_loss: bool = settings.MANDATORY_STOP_LOSS         # True

risk_config = RiskConfig()
