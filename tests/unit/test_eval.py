from app.evaluation import evaluate_assertions
from app.agent.orchestrator import AgentResponse

def test_evaluate_assertions():
    resp1 = AgentResponse(answer="Your order shipped today.", handoff=False)
    
    # Passing assertions
    passed, fails = evaluate_assertions(resp1, [
        {"type": "assert_contains", "value": "shipped"},
        {"type": "assert_not_contains", "value": "delayed"},
        {"type": "assert_handoff", "value": False},
        {"type": "assert_tool_called", "value": "lookup_order"}
    ], tools_called=["lookup_order"])
    
    assert passed is True
    assert len(fails) == 0

    # Failing assertions
    passed, fails = evaluate_assertions(resp1, [
        {"type": "assert_contains", "value": "cancelled"},
        {"type": "assert_handoff", "value": True}
    ], tools_called=[])
    
    assert passed is False
    assert len(fails) == 2
    assert "assert_contains failed" in fails[0]
    assert "assert_handoff failed" in fails[1]
