"""LLM Response Guard module."""

from __future__ import annotations
import re

from app.kb.chunker import Chunk

# Simple heuristic trigger phrases indicating the model claims to have checked an order.
TOOL_CLAIM_TRIGGERS = [
    "i checked",
    "i looked up",
    "according to your order",
    "i have pulled up",
    "i found your order"
]

FORBIDDEN_PATTERNS = [
    re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+'),  # Email regex
    re.compile(r'\brisk_score\b', re.IGNORECASE),
    re.compile(r'\bwarehouse_note\b', re.IGNORECASE),
    re.compile(r'\bsupport_tags\b', re.IGNORECASE),
    re.compile(r'\binternal\b', re.IGNORECASE)
]

def check_citations(answer: str, retrieved_chunks: list[Chunk], tool_sources: list[str] = None) -> list[str]:
    """Check if the answer cites any filenames that were not actually retrieved or in tools.
    Returns a list of fabricated citations."""
    # Look for patterns like "01-returns-policy-current.md"
    # Replace non-breaking hyphens (\u2011) with regular hyphens first
    answer_norm = answer.replace('\u2011', '-')
    # The actual kb uses files ending in .md
    cited_files = re.findall(r'[\w\-]+\.md', answer_norm)
    if not cited_files:
        return []
        
    valid_files = {chunk.doc_filename for chunk in retrieved_chunks}
    if tool_sources:
        valid_files.update(tool_sources)
        
    fabricated = []
    
    for cited in cited_files:
        if cited not in valid_files:
            fabricated.append(cited)
            
    return list(set(fabricated))

def check_forbidden_patterns(answer: str) -> list[str]:
    """Check for leaked emails or internal fields.
    Returns a list of matching strings or reasons."""
    violations = []
    
    for pattern in FORBIDDEN_PATTERNS:
        matches = pattern.findall(answer)
        if matches:
            # Add the first match as the violation reason
            violations.append(str(matches[0]))
            
    return violations

def check_tool_claims(answer: str, tools_called_this_turn: list[str]) -> bool:
    """Returns False if the answer implies a lookup happened but no tool was called.
    True if the claim is valid or if no claim was made."""
    if tools_called_this_turn:
        return True
        
    answer_lower = answer.lower()
    for trigger in TOOL_CLAIM_TRIGGERS:
        if trigger in answer_lower:
            return False
            
    return True
