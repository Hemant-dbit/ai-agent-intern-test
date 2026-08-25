"""Knowledge-base conflict detection module."""

from __future__ import annotations
from dataclasses import dataclass
import re

from app.kb.chunker import Chunk
from app.kb.precedence import eligibility_tier

@dataclass
class ConflictResult:
    has_conflict: bool
    conflicting_chunks: list[Chunk]

def extract_day_counts(text: str) -> set[int]:
    """Simple extraction of day counts like '30 days' or '45 calendar days'."""
    matches = re.findall(r'(\d+)\s+(?:calendar\s+)?days', text, flags=re.IGNORECASE)
    return {int(m) for m in matches}

def detect_conflict(ranked_candidates: list[tuple[Chunk, float]]) -> ConflictResult:
    """Detect conflicts between top-tier current/active sources with contradictory claims."""
    if not ranked_candidates:
        return ConflictResult(has_conflict=False, conflicting_chunks=[])

    # Find chunks that have the highest tier (and >= 10, meaning active/official)
    tiers = [eligibility_tier(chunk) for chunk, _ in ranked_candidates]
    
    # If no chunk is eligible (tier < 10), there's no official conflict.
    if not tiers or max(tiers) < 10:
        return ConflictResult(has_conflict=False, conflicting_chunks=[])
        
    top_tier = max(tiers)
    top_chunks = [chunk for chunk, tier in zip(
        [c for c, _ in ranked_candidates], tiers
    ) if tier == top_tier]

    if len(top_chunks) < 2:
        return ConflictResult(has_conflict=False, conflicting_chunks=[])

    # Group chunks by their root heading (e.g. "Returns Policy")
    chunks_by_topic = {}
    for chunk in top_chunks:
        root_topic = chunk.heading_path.split(" > ")[0]
        if root_topic not in chunks_by_topic:
            chunks_by_topic[root_topic] = []
        chunks_by_topic[root_topic].append(chunk)

    # Check for contradictions in numeric day-counts within each topic.
    for topic, topic_chunks in chunks_by_topic.items():
        day_counts_to_chunks = {}
        for chunk in topic_chunks:
            counts = extract_day_counts(chunk.text)
            if counts:
                for count in counts:
                    if count not in day_counts_to_chunks:
                        day_counts_to_chunks[count] = []
                    day_counts_to_chunks[count].append(chunk)

        # If we found multiple different day counts across chunks for THIS topic, it's a conflict
        if len(day_counts_to_chunks) > 1:
            conflicting = []
            for chunks in day_counts_to_chunks.values():
                conflicting.extend(chunks)
            # Deduplicate
            seen_ids = set()
            dedup_conflicting = []
            for c in conflicting:
                if c.id not in seen_ids:
                    seen_ids.add(c.id)
                    dedup_conflicting.append(c)
                    
            return ConflictResult(has_conflict=True, conflicting_chunks=dedup_conflicting)

    return ConflictResult(has_conflict=False, conflicting_chunks=[])
