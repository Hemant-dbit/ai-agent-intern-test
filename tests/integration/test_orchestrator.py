from unittest.mock import patch, MagicMock

from app.agent.orchestrator import handle_message, session_store
from app.agent.llm_client import LLMResponse, ToolCall
from app.kb.chunker import Chunk

def setup_function():
    # Clear session store before each test
    session_store._sessions = {}

@patch('app.agent.orchestrator.complete')
def test_policy_question_no_tool_call(mock_complete):
    # Setup mock to return a normal answer
    mock_complete.return_value = LLMResponse(text="It's 30 days.", tool_calls=[])
    
    response = handle_message("sess1", "Do you ship internationally?")
    
    assert response.handoff is False
    assert response.answer == "It's 30 days."
    assert len(session_store.get_or_create("sess1").turns) == 2

@patch('app.agent.orchestrator.complete')
def test_order_question_with_explicit_id(mock_complete):
    # First call returns a tool call
    mock_complete.side_effect = [
        LLMResponse(text="", tool_calls=[ToolCall(name="lookup_order", arguments={"order_id": "ORD-1007"})]),
        LLMResponse(text="Your order shipped.", tool_calls=[])
    ]
    
    response = handle_message("sess2", "Where is my order ORD-1007?")
    
    assert response.handoff is False
    assert response.answer == "Your order shipped."
    assert session_store.get_or_create("sess2").active_order_id == "ORD-1007"

@patch('app.agent.orchestrator.complete')
def test_order_question_no_id_no_session(mock_complete):
    # Missing ID should short-circuit and ask for clarification, never calling LLM
    response = handle_message("sess3", "Where is my order?")
    
    assert response.handoff is False
    assert "Could you please provide your order ID" in response.answer
    assert mock_complete.call_count == 0

@patch('app.agent.orchestrator.complete')
@patch('app.agent.orchestrator.detect_conflict')
def test_conflict_detection_triggers_handoff(mock_conflict, mock_complete):
    mock_conflict.return_value = MagicMock(has_conflict=True)
    
    response = handle_message("sess4", "What is the return window?")
    
    assert response.handoff is True
    assert response.handoff_reason == "conflicting_sources"

@patch('app.agent.orchestrator.complete')
def test_fabricated_tool_claim_triggers_handoff(mock_complete):
    # LLM claims it checked an order but didn't make a tool call
    mock_complete.return_value = LLMResponse(text="I checked your order, it's pending.", tool_calls=[])
    
    response = handle_message("sess5", "Where is my order ORD-1007? I am a customer.")
    
    assert response.handoff is True
    assert response.handoff_reason == "fabricated_tool_claim"

@patch('app.agent.orchestrator.complete')
def test_multiturn_order_resolution(mock_complete):
    session_store.set_active_order("sess6", "ORD-1007")
    
    mock_complete.side_effect = [
        LLMResponse(text="", tool_calls=[ToolCall(name="lookup_order", arguments={"order_id": "ORD-1007"})]),
        LLMResponse(text="It will arrive on August 22.", tool_calls=[])
    ]
    
    # Message doesn't contain the order ID, but has implicit context and active_order_id is set
    response = handle_message("sess6", "When will it arrive?")
    
    assert response.handoff is False
    assert "August 22" in response.answer
    assert mock_complete.call_count == 2
    
@patch('app.agent.orchestrator.complete')
def test_multiturn_topic_resolution(mock_complete):
    session_store.set_active_topic("sess7", "International Shipping")
    
    mock_complete.return_value = LLMResponse(text="Yes, Canada works.", tool_calls=[])
    
    # Message is short and we have an active topic. We assert retrieve gets called with the topic context.
    # To test this purely via side-effect, we can mock retrieve or just assert the final state.
    # Since we can't easily mock retrieve here without patch, we'll just check that it runs without errors.
    with patch('app.agent.orchestrator.retrieve') as mock_retrieve:
        mock_retrieve.return_value = []
        handle_message("sess7", "What about Canada?")
        
        # Verify retrieve was called with the topic appended
        mock_retrieve.assert_called_once_with("International Shipping What about Canada?")
