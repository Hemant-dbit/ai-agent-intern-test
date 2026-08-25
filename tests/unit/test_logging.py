import json
import io
import logging
from unittest.mock import patch

from app.agent.orchestrator import handle_message
from app.logging_utils import get_logger
from app.agent.llm_client import LLMResponse, ToolCall

def test_logging_no_pii_leak():
    logger = get_logger()
    
    # Capture standard out/logger output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    from app.logging_utils import JSONFormatter
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # We will trigger a full orchestrator turn involving a real order lookup
    with patch('app.agent.orchestrator.complete') as mock_complete:
        # Mock LLM to invoke tool
        mock_complete.side_effect = [
            LLMResponse(text="", tool_calls=[ToolCall(name="lookup_order", arguments={"order_id": "ORD-1001"})]),
            LLMResponse(text="It is pending.", tool_calls=[])
        ]
        
        handle_message("log-sess-1", "Where is ORD-1001?")
        
    logger.removeHandler(handler)
    logs = log_capture.getvalue()
    
    # Assert logs do not contain the email or internal fields
    assert "maya.reed@example.test" not in logs
    assert "risk_score" not in logs
    assert "warehouse_note" not in logs
    assert "ORD-1001" in logs  # ID should be present
    
    # Verify it logged structured json
    parsed_count = 0
    for line in logs.strip().split("\n"):
        try:
            log_obj = json.loads(line)
            assert "timestamp" in log_obj
            assert "level" in log_obj
            parsed_count += 1
        except json.JSONDecodeError:
            pass
    assert parsed_count > 0, "No structured logs were captured."
