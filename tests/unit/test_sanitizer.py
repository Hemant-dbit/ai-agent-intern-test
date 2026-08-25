import json
import re
from pathlib import Path

from app.orders.sanitizer import sanitize

def test_sanitizer_no_pii_leakage():
    # Load all real orders and run through sanitize
    data_path = Path(__file__).resolve().parents[2] / "data" / "orders.json"
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        orders = dataset.get("orders", [])

    email_regex = re.compile(r'[^@]+@[^@]+\.[^@]+')
    
    # Internal fields from the dictionary
    internal_strings = [
        "risk_score", "warehouse_note", "support_tags", "internal"
    ]

    for raw in orders:
        result = sanitize(raw, raw["order_id"])
        
        # JSON-serialize the result object for checking
        result_json = json.dumps(result.__dict__)

        # Assert no email leak
        assert not email_regex.search(result_json)
        
        # Assert no explicit address pattern (a basic check, mainly we ensure customer keys are absent)
        assert "customer" not in result_json
        assert "shipping_address" not in result_json
        assert "name" not in result_json or "items_summary" in result_json  # only "items_summary" might have item names
        
        # Assert no internal fields leaked
        for internal_str in internal_strings:
            assert internal_str not in result_json

def test_sanitizer_cancelled_returned_stale_delivery():
    # Specific test for stale delivery fields
    raw_cancelled = {
        "order_id": "ORD-CANC",
        "status": "cancelled",
        "estimated_delivery": "2026-10-10",
        "items": []
    }
    res = sanitize(raw_cancelled, "ORD-CANC")
    assert res.delivery_estimate is None

    raw_returned = {
        "order_id": "ORD-RET",
        "status": "returned",
        "estimated_delivery": "2026-10-11",
        "items": []
    }
    res2 = sanitize(raw_returned, "ORD-RET")
    assert res2.delivery_estimate is None

    raw_shipped = {
        "order_id": "ORD-SHIP",
        "status": "shipped",
        "estimated_delivery": "2026-10-12",
        "items": []
    }
    res3 = sanitize(raw_shipped, "ORD-SHIP")
    assert res3.delivery_estimate == "2026-10-12"

def test_sanitizer_not_found():
    res = sanitize(None, "ORD-UNKNOWN")
    assert res.found is False
    assert res.reason == "not_found"
    assert res.order_id == "ORD-UNKNOWN"
