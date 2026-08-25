from app.kb.chunker import Chunk
from app.agent.guard import check_citations, check_forbidden_patterns, check_tool_claims

def create_mock_chunk(filename: str) -> Chunk:
    return Chunk(
        id="1",
        doc_filename=filename,
        heading_path="Test",
        text="text",
        frontmatter={},
        char_start=0,
        char_end=4
    )

def test_check_citations():
    chunks = [create_mock_chunk("01-returns-policy-current.md")]
    
    # Valid citation
    answer1 = "According to 01-returns-policy-current.md, it is 30 days."
    assert check_citations(answer1, chunks) == []
    
    # Hallucinated citation
    answer2 = "According to 02-returns-policy-legacy.md, it is 45 days."
    assert "02-returns-policy-legacy.md" in check_citations(answer2, chunks)

def test_check_forbidden_patterns():
    # Email leak
    answer1 = "The email is user@example.com."
    violations = check_forbidden_patterns(answer1)
    assert len(violations) > 0
    
    # Internal leak
    answer2 = "Your risk_score is 14."
    assert len(check_forbidden_patterns(answer2)) > 0
    
    # Clean answer
    answer3 = "Your order is pending."
    assert check_forbidden_patterns(answer3) == []

def test_check_tool_claims():
    # Model claims to check, but no tools called -> False
    assert check_tool_claims("I checked your order and it is on the way.", []) is False
    
    # Model claims to check, and tools were called -> True
    assert check_tool_claims("I checked your order.", ["lookup_order"]) is True
    
    # Model does not claim to check, and no tools called -> True
    assert check_tool_claims("I am happy to help you with policies.", []) is True
