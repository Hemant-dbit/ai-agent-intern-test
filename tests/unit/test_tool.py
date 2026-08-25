from app.orders.tool import normalize_order_id, validate_order_id, lookup_order_raw

def test_normalize_order_id():
    assert normalize_order_id(" ord-1007 ") == "ORD-1007"
    assert normalize_order_id("ORD-1007") == "ORD-1007"
    assert normalize_order_id("ord-1007") == "ORD-1007"

def test_validate_order_id():
    assert validate_order_id("ORD-1007") is True
    assert validate_order_id("ORD-9999") is True
    assert validate_order_id("ord-1007") is False  # Must be normalized first
    assert validate_order_id("ORD-ABCD") is False
    assert validate_order_id("1007") is False
    assert validate_order_id("ORDER-1007") is False

def test_lookup_order_raw_success():
    # Lookup a known real order ID from the fixture data
    order = lookup_order_raw("ORD-1007")
    assert order is not None
    assert order["order_id"] == "ORD-1007"
    assert order["customer"]["name"] == "Ava Morgan"

def test_lookup_order_raw_unknown():
    # Lookup of an unknown ID returns None
    assert lookup_order_raw("ORD-9999") is None

def test_lookup_order_raw_normalization_in_lookup():
    # lookup_order_raw normalizes inside
    order = lookup_order_raw(" ord-1007 ")
    assert order is not None
    assert order["order_id"] == "ORD-1007"
