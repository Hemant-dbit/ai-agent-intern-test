"""Order-data sanitization module."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal
from app.orders.policy_applicability import resolve_return_window

@dataclass
class OrderLookupResult:
    found: bool
    order_id: str | None
    status: str | None
    delivery_estimate: str | None
    items_summary: str | None
    tracking_available: bool
    reason: Literal["ok", "not_found", "malformed_id"]
    placed_at: str | None
    membership_tier: str | None
    return_window_days: int | None
    return_policy_source: str | None
    carrier: str | None


def sanitize(raw: dict[str, Any] | None, requested_id: str) -> OrderLookupResult:
    """Sanitize raw order data to ensure customer-safe fields only (allow-list)."""
    if raw is None:
        return OrderLookupResult(
            found=False,
            order_id=requested_id,
            status=None,
            delivery_estimate=None,
            items_summary=None,
            tracking_available=False,
            reason="not_found",
            placed_at=None,
            membership_tier=None,
            return_window_days=None,
            return_policy_source=None,
            carrier=None
        )

    # Use allowlist explicitly.
    status = raw.get("status")
    
    # Format items_summary
    items = raw.get("items", [])
    item_strings = []
    for item in items:
        name = item.get("name", "Unknown Item")
        quantity = item.get("quantity", 1)
        item_strings.append(f"{name} x{quantity}")
    items_summary = ", ".join(item_strings) if item_strings else None

    # Handle stale delivery estimate for cancelled/returned orders.
    delivery_estimate = raw.get("estimated_delivery")
    if status in ("cancelled", "returned"):
        delivery_estimate = None

    tracking_number = raw.get("tracking_number")
    tracking_available = bool(tracking_number)

    res = OrderLookupResult(
        found=True,
        order_id=raw.get("order_id"),
        status=status,
        delivery_estimate=delivery_estimate,
        items_summary=items_summary,
        tracking_available=tracking_available,
        reason="ok",
        placed_at=raw.get("placed_at"),
        membership_tier=raw.get("membership_tier"),
        return_window_days=None,  # placeholder before resolution
        return_policy_source=None, # placeholder
        carrier=raw.get("carrier")
    )
    
    window = resolve_return_window(res)
    res.return_window_days = window.window_days
    res.return_policy_source = window.source
    
    return res
