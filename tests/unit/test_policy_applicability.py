from dataclasses import dataclass
from app.orders.policy_applicability import resolve_return_window

@dataclass
class MockOrder:
    placed_at: str
    membership_tier: str

def test_legacy_policy_applies_before_cutover():
    # an order placed 2026-03-15 (before the cutover) returns 45 days from the legacy source 
    # regardless of current membership status
    order = MockOrder(placed_at="2026-03-15T12:00:00Z", membership_tier="Standard")
    result = resolve_return_window(order)
    assert result.window_days == 45
    assert result.source == "02-returns-policy-legacy.md"

    # Even if they were TrailPlus, legacy policy still applies and is 45 days (source is legacy)
    order2 = MockOrder(placed_at="2026-03-15T12:00:00Z", membership_tier="TrailPlus")
    result2 = resolve_return_window(order2)
    assert result2.window_days == 45
    assert result2.source == "02-returns-policy-legacy.md"

def test_trailplus_after_placement_does_not_apply():
    # an order placed 2026-05-01 by a customer who became TrailPlus AFTER that order was placed 
    # returns 30 days, not 45 (no retroactive extension)
    # The order's snapshotted membership_tier is what matters.
    order = MockOrder(placed_at="2026-05-01T10:00:00Z", membership_tier="Standard")
    result = resolve_return_window(order)
    assert result.window_days == 30
    assert result.source == "01-returns-policy-current.md"

def test_trailplus_at_placement_applies():
    # an order placed 2026-05-01 by a customer who WAS TrailPlus at that time 
    # returns 45 days from the trailplus source
    order = MockOrder(placed_at="2026-05-01T10:00:00Z", membership_tier="TrailPlus")
    result = resolve_return_window(order)
    assert result.window_days == 45
    assert result.source == "09-trailplus-membership.md"

def test_standard_plan_after_cutover_applies():
    # an order placed 2026-05-01 by a standard-plan customer 
    # returns 30 days from the current-policy source
    order = MockOrder(placed_at="2026-05-01T14:30:00Z", membership_tier="Standard")
    result = resolve_return_window(order)
    assert result.window_days == 30
    assert result.source == "01-returns-policy-current.md"
