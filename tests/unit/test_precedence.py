from pathlib import Path
import pytest
from app.kb.loader import load_all
from app.kb.chunker import chunk_document
from app.kb.precedence import rerank, eligibility_tier

def get_real_chunk(filename: str) -> "Chunk":
    kb_path = Path(__file__).resolve().parents[2] / "knowledge-base"
    docs = load_all(kb_path)
    for doc in docs:
        if doc.filename == filename:
            chunks = chunk_document(doc)
            if chunks:
                return chunks[0]
    raise ValueError(f"Could not find or chunk {filename}")

def test_rerank_current_outranks_legacy_regardless_of_similarity():
    chunk_01 = get_real_chunk("01-returns-policy-current.md")
    chunk_02 = get_real_chunk("02-returns-policy-legacy.md")
    
    # 02 has higher raw score, but 01 should outrank it due to tiering and supersession
    candidates = [
        (chunk_02, 0.99),
        (chunk_01, 0.50)
    ]
    
    reranked = rerank(candidates)
    
    assert len(reranked) == 2
    assert reranked[0][0].doc_filename == "01-returns-policy-current.md"
    assert reranked[1][0].doc_filename == "02-returns-policy-legacy.md"

def test_internal_audience_never_appears():
    chunk_01 = get_real_chunk("01-returns-policy-current.md")
    chunk_13 = get_real_chunk("13-support-escalation.md")
    
    candidates = [
        (chunk_13, 0.99), # highest score
        (chunk_01, 0.50)
    ]
    
    reranked = rerank(candidates)
    
    assert len(reranked) == 1
    assert reranked[0][0].doc_filename == "01-returns-policy-current.md"

def test_draft_none_authority_never_appears():
    chunk_01 = get_real_chunk("01-returns-policy-current.md")
    chunk_14 = get_real_chunk("14-internal-content-migration-notes.md")
    
    candidates = [
        (chunk_14, 0.99), # highest score
        (chunk_01, 0.50)
    ]
    
    reranked = rerank(candidates)
    
    assert len(reranked) == 1
    assert reranked[0][0].doc_filename == "01-returns-policy-current.md"

def test_eligibility_tier_values():
    assert eligibility_tier(get_real_chunk("01-returns-policy-current.md")) == 10
    assert eligibility_tier(get_real_chunk("02-returns-policy-legacy.md")) == 5
    assert eligibility_tier(get_real_chunk("13-support-escalation.md")) == -100
    assert eligibility_tier(get_real_chunk("14-internal-content-migration-notes.md")) == -100
