"""Knowledge-base precedence module."""

from __future__ import annotations

from typing import Iterable

from app.kb.chunker import Chunk


def eligibility_tier(chunk: Chunk) -> int:
    """Higher tier = usable as customer-answer authority. Ties broken by
    embedding similarity within a tier; a lower tier is NEVER outranked by
    similarity alone, per Rule 1."""
    fm = chunk.frontmatter
    status = fm.get("status", "").lower()
    authority = fm.get("policy_authority", "").lower()
    audience = fm.get("audience", "customer").lower()

    if audience == "internal":
        return -100

    if status == "active" and authority == "official":
        return 10
    if status == "superseded":
        return 5
    if authority != "official" or status == "draft":
        return -100

    return 0


def resolve_supersession(candidates: list[Chunk]) -> list[Chunk]:
    """Rule 3: an explicit supersedes/superseded_by link resolves a
    conflict deterministically for the overlapping subject/period —
    this must be applied BEFORE falling back to tier/similarity, and it
    must NOT simply discard the superseded document; it marks it
    historical-only rather than eligible-default."""
    resolved = []
    
    present_doc_ids = {c.frontmatter.get("document_id") for c in candidates if c.frontmatter.get("document_id")}
    superseding_ids = {c.frontmatter.get("supersedes") for c in candidates if c.frontmatter.get("supersedes")}
    
    for c in candidates:
        fm = c.frontmatter
        doc_id = fm.get("document_id")
        superseded_by = fm.get("superseded_by")
        
        is_superseded = False
        if superseded_by and superseded_by in present_doc_ids:
            is_superseded = True
        if doc_id and doc_id in superseding_ids:
            is_superseded = True
            
        if is_superseded and fm.get("status", "").lower() != "superseded":
            new_fm = dict(fm)
            new_fm["status"] = "superseded"
            new_c = Chunk(
                id=c.id,
                doc_filename=c.doc_filename,
                heading_path=c.heading_path,
                text=c.text,
                frontmatter=new_fm,
                char_start=c.char_start,
                char_end=c.char_end,
            )
            resolved.append(new_c)
        else:
            resolved.append(c)
            
    return resolved


def rerank(candidates: Iterable[tuple[Chunk, float]]) -> list[tuple[Chunk, float]]:
    """Sorts by eligibility_tier descending, applies resolve_supersession where a link exists, 
    then breaks ties within the same tier by embedding similarity."""
    candidate_list = list(candidates)
    if not candidate_list:
        return []

    chunks = [c for c, _ in candidate_list]
    scores = [s for _, s in candidate_list]
    
    resolved_chunks = resolve_supersession(chunks)
    resolved_candidates = list(zip(resolved_chunks, scores))
    
    resolved_candidates.sort(key=lambda x: (eligibility_tier(x[0]), x[1]), reverse=True)
    
    # Filter out chunks that are completely ineligible (-100 tier)
    # Actually, the prompt says "a 13-support-escalation.md chunk (audience: internal) never appears in reranked output;
    # a 14-internal-content-migration-notes.md chunk (draft, policy_authority: none) never appears in reranked output"
    return [cand for cand in resolved_candidates if eligibility_tier(cand[0]) > -100]
