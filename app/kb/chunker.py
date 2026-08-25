"""Create heading-bounded chunks from loaded knowledge-base documents."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.kb.loader import Document, Heading


DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_CHARS = 100
_SENTENCE_END_PATTERN = re.compile(r"[.!?](?=\s|$)")


@dataclass(frozen=True)
class Chunk:
    """A retrieval-ready, heading-bounded slice of a source document."""

    id: str
    doc_filename: str
    heading_path: str
    text: str
    frontmatter: dict[str, Any]
    char_start: int
    char_end: int


def chunk_document(
    doc: Document,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    """Split a document at H2 boundaries and long sections at sentence boundaries."""
    if max_chars < 1:
        raise ValueError("max_chars must be greater than zero")
    if overlap_chars < 0:
        raise ValueError("overlap_chars cannot be negative")
    if not doc.raw_text.strip():
        return []

    sections = _h2_sections(doc)
    chunks: list[Chunk] = []
    for section_start, section_end, heading in sections:
        for start, end in _split_section(doc.raw_text, section_start, section_end, max_chars, overlap_chars):
            heading_path = _heading_path(doc.headings, heading)
            chunks.append(
                Chunk(
                    id=f"{doc.filename}:{len(chunks)}",
                    doc_filename=doc.filename,
                    heading_path=heading_path,
                    text=doc.raw_text[start:end],
                    frontmatter=dict(doc.frontmatter),
                    char_start=start,
                    char_end=end,
                )
            )
    return chunks


def _h2_sections(doc: Document) -> list[tuple[int, int, Heading | None]]:
    """Return non-overlapping source spans, using H2 headings as primary boundaries."""
    h2_headings = [heading for heading in doc.headings if heading.level == 2]
    if not h2_headings:
        first_heading = doc.headings[0] if doc.headings else None
        start, end = _trim_span(doc.raw_text, 0, len(doc.raw_text))
        return [(start, end, first_heading)] if start < end else []

    sections: list[tuple[int, int, Heading]] = []
    for index, heading in enumerate(h2_headings):
        heading_start = _byte_to_char_offset(doc.raw_text, heading.start_byte)
        next_start = (
            _byte_to_char_offset(doc.raw_text, h2_headings[index + 1].start_byte)
            if index + 1 < len(h2_headings)
            else len(doc.raw_text)
        )
        # Keep the document title and any introductory prose with the first H2 section.
        start = 0 if index == 0 else heading_start
        start, end = _trim_span(doc.raw_text, start, next_start)
        if start < end:
            sections.append((start, end, heading))
    return sections


def _split_section(
    raw_text: str,
    start: int,
    end: int,
    max_chars: int,
    overlap_chars: int,
) -> list[tuple[int, int]]:
    """Split a long section at sentence endings while retaining sentence-level overlap."""
    if end - start <= max_chars:
        return [(start, end)]

    section_text = raw_text[start:end]
    sentence_ends = [match.end() for match in _SENTENCE_END_PATTERN.finditer(section_text)]
    if not sentence_ends or sentence_ends[-1] < len(section_text.rstrip()):
        sentence_ends.append(len(section_text))
    sentence_starts = [0]
    for sentence_end in sentence_ends[:-1]:
        next_start = sentence_end
        while next_start < len(section_text) and section_text[next_start].isspace():
            next_start += 1
        if next_start < len(section_text):
            sentence_starts.append(next_start)

    spans: list[tuple[int, int]] = []
    local_start = 0
    while len(section_text) - local_start > max_chars:
        eligible_ends = [sentence_end for sentence_end in sentence_ends if local_start < sentence_end <= local_start + max_chars]
        if not eligible_ends:
            # A single sentence/rule is longer than the target; preserve it intact.
            break
        local_end = eligible_ends[-1]
        absolute_start, absolute_end = _trim_span(raw_text, start + local_start, start + local_end)
        spans.append((absolute_start, absolute_end))

        overlap_start_candidates = [
            sentence_start
            for sentence_start in sentence_starts
            if local_start < sentence_start < local_end and local_end - sentence_start <= overlap_chars
        ]
        local_start = overlap_start_candidates[0] if overlap_start_candidates else local_end

    absolute_start, absolute_end = _trim_span(raw_text, start + local_start, end)
    if absolute_start < absolute_end:
        spans.append((absolute_start, absolute_end))
    return spans


def _heading_path(headings: list[Heading], heading: Heading | None) -> str:
    """Build an ancestor-qualified citation path for a heading."""
    if heading is None:
        return "Document"
    heading_index = headings.index(heading)
    path_parts: list[str] = []
    current_index: int | None = heading_index
    while current_index is not None:
        current = headings[current_index]
        path_parts.append(current.text)
        current_index = current.parent_index
    return " > ".join(reversed(path_parts))


def _byte_to_char_offset(text: str, byte_offset: int) -> int:
    """Convert a known UTF-8 boundary offset to a Python character offset."""
    return len(text.encode("utf-8")[:byte_offset].decode("utf-8"))


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim outer whitespace while keeping offsets aligned with the returned text."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


# TODO: Integrate chunks with indexing in app.kb.indexer.
