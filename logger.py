import logging
import sys
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        log_obj = {
            "timestamp": timestamp,
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return f"[{timestamp}] [{record.levelname:<8}] {record.name} - {record.getMessage()}"

def setup_logger(name: str = "trading") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
    return logger

logger = setup_logger()
