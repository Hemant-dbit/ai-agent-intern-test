"""Tests for real knowledge-base document loading and structure extraction."""

from pathlib import Path

from app.kb.loader import load_all


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE = REPOSITORY_ROOT / "knowledge-base"


def test_load_all_reads_the_real_knowledge_base_and_frontmatter() -> None:
    """All confirmed Markdown documents load with parsed current-policy metadata."""
    documents = load_all(KNOWLEDGE_BASE)

    assert len(documents) == 14
    current_returns = next(document for document in documents if document.filename == "01-returns-policy-current.md")
    assert current_returns.has_frontmatter is True
    assert current_returns.frontmatter["document_id"] == "RET-2026-01"
    assert current_returns.frontmatter["title"] == "Returns Policy"
    assert current_returns.frontmatter["status"] == "active"
    assert current_returns.frontmatter["effective_date"] == "2026-04-01"
    assert "document_id:" not in current_returns.raw_text


def test_heading_extraction_matches_confirmed_repository_structure() -> None:
    """H1/H2 lists and UTF-8 byte ranges match two Task 0 source documents."""
    documents = {document.filename: document for document in load_all(KNOWLEDGE_BASE)}

    assert [(heading.text, heading.level) for heading in documents["01-returns-policy-current.md"].headings] == [
        ("Returns Policy", 1),
        ("Standard return window", 2),
        ("Item condition", 2),
        ("Return shipping and refunds", 2),
        ("Exclusions and exceptions", 2),
    ]
    assert [(heading.text, heading.level) for heading in documents["12-breeze-tumbler-product-card.md"].headings] == [
        ("Breeze Tumbler — Product Information", 1),
        ("Product details", 2),
        ("Cleaning", 2),
        ("Temperature use", 2),
    ]

    current_returns = documents["01-returns-policy-current.md"]
    standard_window = current_returns.headings[1]
    encoded_text = current_returns.raw_text.encode("utf-8")
    assert encoded_text[standard_window.start_byte :].startswith(b"## Standard return window")
    assert standard_window.parent_index == 0
    assert standard_window.end_byte > standard_window.start_byte
