"""Tests for heading-bounded knowledge-base chunking."""

from app.kb.chunker import chunk_document
from app.kb.loader import Document, Heading


def _synthetic_policy_document() -> Document:
    raw_text = (
        "# Returns Policy\n\n"
        "## Standard Rule\n"
        "Standard rule: eligible items may be returned within 30 days of delivery.\n\n"
        "## Exceptions\n"
        "Final-sale items are not returnable for a change of mind.\n"
    )
    standard_start = raw_text.index("## Standard Rule")
    exceptions_start = raw_text.index("## Exceptions")
    return Document(
        path="knowledge-base/synthetic.md",
        filename="synthetic.md",
        frontmatter={"status": "active", "policy_authority": "official"},
        raw_text=raw_text,
        headings=[
            Heading("Returns Policy", 1, 0, len(raw_text.encode("utf-8")), None),
            Heading("Standard Rule", 2, standard_start, exceptions_start, 0),
            Heading("Exceptions", 2, exceptions_start, len(raw_text.encode("utf-8")), 0),
        ],
        has_frontmatter=True,
    )


def test_chunks_do_not_cross_h2_policy_rules_and_keep_parent_metadata() -> None:
    """Each H2 policy rule remains isolated with a non-empty path and copied metadata."""
    document = _synthetic_policy_document()
    chunks = chunk_document(document)

    assert len(chunks) == 2
    assert all(chunk.heading_path for chunk in chunks)
    assert all(chunk.frontmatter == document.frontmatter for chunk in chunks)
    assert all(chunk.frontmatter is not document.frontmatter for chunk in chunks)
    assert all(chunk.text == document.raw_text[chunk.char_start : chunk.char_end] for chunk in chunks)
    assert not any(
        "Standard rule:" in chunk.text and "Final-sale items" in chunk.text
        for chunk in chunks
    )
    assert chunks[0].heading_path == "Returns Policy > Standard Rule"
    assert chunks[1].heading_path == "Returns Policy > Exceptions"
