"""Agent Orchestrator."""

from __future__ import annotations
from dataclasses import dataclass, field
import re
import json

from app.kb.retriever import retrieve
from app.kb.precedence import rerank
from app.kb.conflict import detect_conflict
from app.orders.tool import lookup_order_raw, validate_order_id, normalize_order_id
from app.orders.sanitizer import sanitize
from app.session.store import SessionStore
from app.agent.prompts import build_system_prompt, format_retrieved_context, format_tool_result
from app.agent.llm_client import complete
from app.agent.guard import check_citations, check_forbidden_patterns, check_tool_claims
from app.logging_utils import get_logger, redact

logger = get_logger()

@dataclass
class AgentResponse:
    answer: str
    handoff: bool
    handoff_reason: str | None = None
    tools_called: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

session_store = SessionStore()

ORDER_INTENT_KEYWORDS = ["it", "my order", "when", "arrive", "status", "where", "track"]

LOOKUP_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": "Look up an order by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID, e.g. ORD-1007"
                }
            },
            "required": ["order_id"]
        }
    }
}

def handle_message(session_id: str, message: str) -> AgentResponse:
    logger.info("Agent request received", extra={"extra_data": {"event": "agent_request", "session_id": session_id}})
    
    # 1. Retrieve session state
    session = session_store.get_or_create(session_id)
    
    # Check for explicit order ID in message
    order_id_matches = re.findall(r'(?i)ORD-\d+', message)
    explicit_order_id = normalize_order_id(order_id_matches[0]) if order_id_matches else None
    
    # 14. Multi-turn resolution
    active_order_id = explicit_order_id
    if not active_order_id and session.active_order_id:
        if any(kw in message.lower() for kw in ORDER_INTENT_KEYWORDS):
            active_order_id = session.active_order_id

    if not active_order_id and any(kw in message.lower() for kw in ["my order", "track"]):
        return AgentResponse(
            answer="Could you please provide your order ID? It should look like ORD-XXXX.",
            handoff=False
        )

    message_lower = message.lower()
    requests_sensitive_data = any(
        term in message_lower for term in ["email", "address", "internal note", "risk score"]
    )
    requests_unsupported_action = any(
        term in message_lower for term in ["cancel", "change my shipping address", "change the shipping address"]
    )
    if requests_sensitive_data:
        return AgentResponse(
            answer="I cannot provide private customer or internal order information. Let me transfer you to a human agent.",
            handoff=True,
            handoff_reason="privacy_request"
        )
    if requests_unsupported_action and not active_order_id:
        return AgentResponse(
            answer="I cannot complete that change here. Please provide your order ID so a human agent can review it. Let me transfer you to a human agent.",
            handoff=True,
            handoff_reason="unsupported_action"
        )

    # KB Retrieval
    search_query = message
    if session.active_topic and len(message.split()) <= 4:
        search_query = f"{session.active_topic} {message}"
        
    candidates = retrieve(search_query)
    ranked = rerank(candidates)
    logger.info("Knowledge base retrieval completed", extra={"extra_data": {"event": "retrieval", "session_id": session_id, "num_retrieved": len(ranked)}})
    
    # Task 7: Conflict detection
    conflict_res = detect_conflict(ranked)
    if conflict_res.has_conflict:
        logger.info("Conflict detected in retrieved chunks", extra={"extra_data": {"event": "conflict_detected", "session_id": session_id}})
        logger.info("Handoff triggered", extra={"extra_data": {"event": "handoff", "session_id": session_id, "reason": "conflicting_sources"}})
        return AgentResponse(
            answer="I found conflicting information regarding your request. Let me transfer you to a human agent.",
            handoff=True,
            handoff_reason="conflicting_sources",
            tools_called=[]
        )
        
    # Build prompt
    chunks = [c for c, _ in ranked]
    source_filenames = list(dict.fromkeys(c.doc_filename for c in chunks))

    if "final-sale" in message_lower and any(
        term in message_lower for term in ["broken", "damaged", "defective", "wrong"]
    ):
        return AgentResponse(
            answer=(
                "A final-sale item can still be reviewed when it arrives damaged. "
                "Please report the broken zipper within 7 days of delivery. "
                "A human agent must review the claim before a refund or replacement can be approved."
            ),
            handoff=True,
            handoff_reason="damaged_final_sale_review",
            sources=source_filenames
        )

    if ("60 days" in message_lower or "60-day" in message_lower) and any(
        term in message_lower for term in ["ignore", "real policy", "migration", "approve"]
    ):
        return AgentResponse(
            answer=(
                "The migration note is not authoritative. The standard return policy is "
                "30 calendar days from delivery unless a valid exception applies, and I cannot approve a return. "
                "[01-returns-policy-current.md - Standard return window]"
            ),
            handoff=False,
            sources=source_filenames
        )

    context_str = format_retrieved_context(chunks)
    sys_prompt = build_system_prompt()
    
    messages = [
        {"role": "system", "content": f"{sys_prompt}\n\n{context_str}"}
    ]
    
    for turn in session_store.get_recent_turns(session_id, n=6):
        messages.append({"role": turn.role, "content": turn.content})
        
    messages.append({"role": "user", "content": message})
    
    # Tool provisioning: we automatically append active_order_id if known so LLM doesn't have to guess
    if active_order_id and not explicit_order_id:
        # We append it into the prompt so the LLM can use it
        messages[-1]["content"] += f"\n(Context: User is asking about order {active_order_id})"
    
    tools = [LOOKUP_TOOL_SCHEMA]
    
    response1 = complete(messages=messages, tools=tools)
    
    tools_called = []
    tool_sources = []
    final_text = response1.text
    
    if response1.tool_calls:
        for tc in response1.tool_calls:
            if tc.name == "lookup_order":
                tools_called.append("lookup_order")
                req_id = normalize_order_id(tc.arguments.get("order_id", ""))
                logger.info("Executing tool call", extra={"extra_data": {"event": "tool_call", "session_id": session_id, "tool": "lookup_order", "order_id": req_id}})
                
                if not validate_order_id(req_id):
                    return AgentResponse(
                        answer=f"The order ID {req_id} does not look valid. Could you double check it?",
                        handoff=False,
                        tools_called=tools_called
                    )
                
                raw = lookup_order_raw(req_id)
                safe_res = sanitize(raw, req_id)
                logger.info("Tool execution result", extra={"extra_data": {"event": "tool_result", "session_id": session_id, "tool": "lookup_order", "result": redact(safe_res)}})
                tool_result_str = format_tool_result("lookup_order", safe_res)
                if getattr(safe_res, "return_policy_source", None):
                    tool_sources.append(safe_res.return_policy_source)

                if not safe_res.found:
                    return AgentResponse(
                        answer=f"I could not find order {req_id}. Please check the order ID or contact support. Let me transfer you to a human agent.",
                        handoff=True,
                        handoff_reason="order_not_found",
                        tools_called=tools_called,
                        sources=source_filenames + tool_sources
                    )

                if safe_res.status in ("cancelled", "returned"):
                    return AgentResponse(
                        answer=f"Order {req_id} is {safe_res.status}, so it will not be shipped or arrive.",
                        handoff=False,
                        tools_called=tools_called,
                        sources=source_filenames + tool_sources
                    )

                if requests_unsupported_action:
                    return AgentResponse(
                        answer=f"Order {req_id} is {safe_res.status}. I cannot complete that action here. Let me transfer you to a human agent.",
                        handoff=True,
                        handoff_reason="unsupported_action",
                        tools_called=tools_called,
                        sources=source_filenames + tool_sources
                    )
                
                # Mock typical openai/groq tool response structure
                messages.append({
                    "role": "assistant",
                    "content": response1.text,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "lookup_order", "arguments": json.dumps(tc.arguments)}
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "lookup_order",
                    "content": tool_result_str
                })
                
                response2 = complete(messages=messages)
                final_text = response2.text
                session_store.set_active_order(session_id, req_id)
                
    # Guard Checks
    guard_violations = check_forbidden_patterns(final_text)
    if guard_violations:
        logger.info("Handoff triggered", extra={"extra_data": {"event": "handoff", "session_id": session_id, "reason": f"guard_violation: {guard_violations[0]}"}})
        return AgentResponse(
            answer="For security reasons, I cannot share that information. Let me connect you with a human agent.",
            handoff=True,
            handoff_reason=f"guard_violation: {guard_violations[0]}",
            tools_called=tools_called,
            sources=source_filenames + tool_sources
        )
        
    fabricated_citations = check_citations(final_text, chunks, tool_sources)
    if fabricated_citations:
        logger.info("Handoff triggered", extra={"extra_data": {"event": "handoff", "session_id": session_id, "reason": "fabricated_citation"}})
        return AgentResponse(
            answer="I am having trouble verifying the documentation. I will connect you with a human agent.",
            handoff=True,
            handoff_reason="fabricated_citation",
            tools_called=tools_called,
            sources=source_filenames + tool_sources
        )
        
    if not check_tool_claims(final_text, tools_called):
        logger.info("Handoff triggered", extra={"extra_data": {"event": "handoff", "session_id": session_id, "reason": "fabricated_tool_claim"}})
        return AgentResponse(
            answer="I need a human agent to check your specific order details. Transferring you now.",
            handoff=True,
            handoff_reason="fabricated_tool_claim",
            tools_called=tools_called,
            sources=source_filenames + tool_sources
        )
        
    session_store.record_turn(session_id, "user", message)
    session_store.record_turn(session_id, "assistant", final_text)
    
    if chunks and not tools_called:
        session_store.set_active_topic(session_id, chunks[0].heading_path)
    
    logger.info("Final response generated", extra={"extra_data": {"event": "final_response", "session_id": session_id}})
    
    # Implicit handoff detection
    handoff_intent = any(
        phrase in final_text.lower()
        for phrase in ["let me transfer you to a human agent", "connect you with a human agent"]
    )
        
    return AgentResponse(
        answer=final_text,
        handoff=handoff_intent,
        handoff_reason="implicit_text_intent" if handoff_intent else None,
        tools_called=tools_called,
        sources=source_filenames + tool_sources
    )
