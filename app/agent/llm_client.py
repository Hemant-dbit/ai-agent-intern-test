"""LLM client wrapper."""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any
import json

from groq import Groq
from app import config

@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]

@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)

def complete(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMResponse:
    """Send a completion request to Groq."""
    # Assuming config defines model name and we use environment variables for Groq API key
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock-key"))
    
    # We use a default fast model unless overridden
    model = os.environ.get("LLM_MODEL", "openai/gpt-oss-20b")
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            tools=tools,
            temperature=0.0
        )
    except Exception as e:
        # In a real app we'd log this; for now return a safe error response
        return LLMResponse(text=f"An error occurred communicating with the LLM: {str(e)}")

    choice = response.choices[0]
    message = choice.message
    
    text = message.content if message.content else ""
    tool_calls = []
    
    if message.tool_calls:
        for tc in message.tool_calls:
            # Groq returns tool calls with function name and arguments string
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(name=tc.function.name, arguments=args))
            
    return LLMResponse(text=text, tool_calls=tool_calls)
