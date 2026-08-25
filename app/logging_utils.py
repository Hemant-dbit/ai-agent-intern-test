"""Structured JSON logging utilities."""

import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.orders.sanitizer import OrderLookupResult

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        
        # Add any extra fields passed in the 'extra' kwarg
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)  # type: ignore
            
        return json.dumps(log_obj)

def get_logger(name: str = "aster_row") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    return logger

def redact(data: Any) -> Any:
    """Redact sensitive information from order data for logging.
    If given an OrderLookupResult, it's already safe but we convert it to dict.
    If given raw data, we strictly only log the ID and status."""
    if isinstance(data, OrderLookupResult):
        return asdict(data)
    if isinstance(data, dict):
        return {
            "order_id": data.get("order_id", "unknown"),
            "status": data.get("status", "unknown")
        }
    return str(data)
