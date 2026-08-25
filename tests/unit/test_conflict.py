from app.kb.chunker import Chunk
from app.kb.conflict import detect_conflict

def create_chunk(id_val: str, text: str, status: str = "active", authority: str = "official") -> Chunk:
    return Chunk(
        id=id_val,
        doc_filename="test.md",
        heading_path="Test",
        text=text,
        frontmatter={"status": status, "policy_authority": authority, "audience": "customer"},
        char_start=0,
        char_end=len(text)
    )

def test_detect_conflict_same_topic_different_days():
    chunk1 = create_chunk("1", "You have 30 days to return this item.")
    chunk2 = create_chunk("2", "You have 45 calendar days to return this item.")
    
    candidates = [(chunk1, 0.9), (chunk2, 0.8)]
    result = detect_conflict(candidates)
    
    assert result.has_conflict is True
    assert len(result.conflicting_chunks) == 2

def test_detect_conflict_current_vs_legacy():
    # Legacy chunk should not conflict because it's not top-tier
    chunk1 = create_chunk("1", "You have 30 days to return this item.", status="active")
    chunk2 = create_chunk("2", "You have 45 calendar days to return this item.", status="superseded")
    
    candidates = [(chunk1, 0.9), (chunk2, 0.8)]
    result = detect_conflict(candidates)
    
    assert result.has_conflict is False

def test_detect_conflict_unrelated_current_chunks():
    chunk1 = create_chunk("1", "You have 30 days to return this item.")
    chunk2 = create_chunk("2", "We ship to Canada.")
    
    candidates = [(chunk1, 0.9), (chunk2, 0.8)]
    result = detect_conflict(candidates)
    
    assert result.has_conflict is False

def test_no_candidates():
    result = detect_conflict([])
    assert result.has_conflict is False
