"""Order lookup tool."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from app import config

# We cache the loaded orders to avoid reading the file on every lookup.
_ORDERS_CACHE: dict[str, dict[str, Any]] | None = None

def normalize_order_id(raw: str) -> str:
    """Normalize an order ID by stripping whitespace and uppercase."""
    # Example: " ord-1007 " -> "ORD-1007"
    return raw.strip().upper()

def validate_order_id(order_id: str) -> bool:
    """Validate that the given string matches the expected order ID format.
    Format is ORD-#### where #### is numbers."""
    if not order_id.startswith("ORD-"):
        return False
    parts = order_id.split("-")
    if len(parts) != 2:
        return False
    return parts[1].isdigit()

def lookup_order_raw(order_id: str) -> dict[str, Any] | None:
    """Load data/orders.json once and lookup by normalized ID."""
    global _ORDERS_CACHE
    if _ORDERS_CACHE is None:
        # Load the orders from the data directory
        data_path = Path(__file__).resolve().parents[2] / "data" / "orders.json"
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
                _ORDERS_CACHE = {
                    normalize_order_id(order["order_id"]): order
                    for order in dataset.get("orders", [])
                }
        except FileNotFoundError:
            return None

    normalized = normalize_order_id(order_id)
    return _ORDERS_CACHE.get(normalized)
