"""Deterministic policy applicability rules for orders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


class OrderLookupResult(Protocol):
    """Protocol defining the required fields from a sanitized order."""
    placed_at: str
    membership_tier: str


@dataclass
class ReturnWindowResult:
    window_days: int
    source: str
    note: str | None


def resolve_return_window(order: OrderLookupResult) -> ReturnWindowResult:
    """Resolve the applicable return window for a specific order deterministically.
    
    Rules:
    - Orders placed before 2026-04-01: 45 days (legacy policy).
    - TrailPlus members at time of placement: 45 days.
    - Standard: 30 days.
    - Never uses 14-internal-content-migration-notes.md.
    """
    placed_at = getattr(order, "placed_at", "")
    membership = getattr(order, "membership_tier", "")

    if placed_at and placed_at < "2026-04-01":
        return ReturnWindowResult(
            window_days=45,
            source="02-returns-policy-legacy.md",
            note=None
        )
    elif membership.lower() == "trailplus":
        return ReturnWindowResult(
            window_days=45,
            source="09-trailplus-membership.md",
            note=None
        )
    else:
        return ReturnWindowResult(
            window_days=30,
            source="01-returns-policy-current.md",
            note=None
        )
