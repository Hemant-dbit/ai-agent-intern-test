"""Evaluation assertion logic."""

from typing import Any
from app.agent.orchestrator import AgentResponse

def evaluate_assertions(response: AgentResponse, assertions: list[dict[str, Any]], tools_called: list[str]) -> tuple[bool, list[str]]:
    """Evaluate a list of assertions against an AgentResponse and its side effects.
    Returns (passed, list_of_failure_reasons).
    """
    failures = []
    
    for assertion in assertions:
        a_type = assertion.get("type")
        a_value = assertion.get("value")
        
        if a_type == "assert_contains":
            if not a_value or str(a_value).lower() not in response.answer.lower():
                failures.append(f"assert_contains failed: '{a_value}' not found in answer.")
                
        elif a_type == "assert_not_contains":
            if a_value and str(a_value).lower() in response.answer.lower():
                failures.append(f"assert_not_contains failed: '{a_value}' found in answer.")
                
        elif a_type == "assert_handoff":
            expected = bool(a_value)
            if response.handoff != expected:
                failures.append(f"assert_handoff failed: expected {expected}, got {response.handoff}.")
                
        elif a_type == "assert_tool_called":
            if a_value not in tools_called:
                failures.append(f"assert_tool_called failed: '{a_value}' not in {tools_called}.")
                
        else:
            failures.append(f"Unknown assertion type: {a_type}")
            
    return len(failures) == 0, failures
