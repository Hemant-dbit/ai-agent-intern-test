from app.agent.prompts import build_system_prompt, format_retrieved_context, format_tool_result
from app.kb.chunker import Chunk
from app.orders.sanitizer import OrderLookupResult

def test_build_system_prompt():
    prompt = build_system_prompt()
    assert "ROLE" in prompt
    assert "APPLICATION RULES" in prompt
    assert "TRUST BOUNDARIES" in prompt

def test_format_retrieved_context():
    chunk = Chunk(
        id="1",
        doc_filename="doc.md",
        heading_path="Topic",
        text="Sample text",
        frontmatter={},
        char_start=0,
        char_end=11
    )
    result = format_retrieved_context([chunk])
    assert '<retrieved_context source="doc.md \u2014 Topic">' in result
    assert "Sample text" in result
    assert '</retrieved_context>' in result

def test_format_tool_result():
    sanitized = OrderLookupResult(
        found=True,
        order_id="ORD-1007",
        status="shipped",
        delivery_estimate="2026-08-22",
        items_summary="Atlas Weekender x1",
        tracking_available=True,
        reason="ok",
        placed_at="2026-08-11T15:05:00Z",
        membership_tier="standard"
    )
    result = format_tool_result("lookup_order", sanitized)
    assert '<tool_result tool="lookup_order">' in result
    assert "ORD-1007" in result
    assert '</tool_result>' in result
    assert "warehouse_note" not in result
