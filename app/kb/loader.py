"""Load Markdown knowledge-base documents and their citation structure."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


_HEADING_PATTERN = re.compile(r"^(#{1,3})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_FRONTMATTER_KEY_PATTERN = re.compile(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$")


@dataclass(frozen=True)
class Heading:
    """A Markdown heading and its UTF-8 byte range in a document's raw text."""

    text: str
    level: int
    start_byte: int
    end_byte: int
    parent_index: int | None


@dataclass(frozen=True)
class Document:
    """A loaded Markdown knowledge-base document."""

    path: str
    filename: str
    frontmatter: dict[str, Any]
    raw_text: str
    headings: list[Heading]
    has_frontmatter: bool = False


def load_all(kb_dir: str | Path) -> list[Document]:
    """Load every Markdown document in ``kb_dir`` in filename order."""
    directory = Path(kb_dir)
    return [_load_document(path) for path in sorted(directory.glob("*.md"))]


def _load_document(path: Path) -> Document:
    content = path.read_text(encoding="utf-8")
    frontmatter, raw_text, has_frontmatter = _split_frontmatter(content)
    return Document(
        path=path.as_posix(),
        filename=path.name,
        frontmatter=frontmatter,
        raw_text=raw_text,
        headings=_extract_headings(raw_text),
        has_frontmatter=has_frontmatter,
    )


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str, bool]:
    """Separate a leading YAML-like front-matter block without extra dependencies."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, content, False

    for end_index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter_lines = lines[1:end_index]
            return _parse_frontmatter(frontmatter_lines), "".join(lines[end_index + 1 :]), True

    return {}, content, False


def _parse_frontmatter(lines: list[str]) -> dict[str, Any]:
    """Parse the repository's scalar key/value front-matter schema."""
    parsed: dict[str, Any] = {}
    for line in lines:
        match = _FRONTMATTER_KEY_PATTERN.match(line.rstrip("\r\n"))
        if not match:
            continue
        key, value = match.groups()
        parsed[key] = _parse_scalar(value.strip())
    return parsed


def _parse_scalar(value: str) -> Any:
    """Parse common scalar values while leaving dates and unquoted text intact."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\d*\.\d+)", value):
        return float(value)
    return value


def _extract_headings(raw_text: str) -> list[Heading]:
    """Extract H1-H3 headings with UTF-8 byte ranges and parent relationships."""
    provisional: list[tuple[str, int, int, int | None]] = []
    open_parents: dict[int, int] = {}

    for match in _HEADING_PATTERN.finditer(raw_text):
        level = len(match.group(1))
        text = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(2)).strip()
        start_byte = len(raw_text[: match.start()].encode("utf-8"))
        parent_index = next(
            (open_parents[parent_level] for parent_level in range(level - 1, 0, -1) if parent_level in open_parents),
            None,
        )
        provisional.append((text, level, start_byte, parent_index))
        open_parents[level] = len(provisional) - 1
        for deeper_level in range(level + 1, 4):
            open_parents.pop(deeper_level, None)

    raw_text_length = len(raw_text.encode("utf-8"))
    headings: list[Heading] = []
    for index, (text, level, start_byte, parent_index) in enumerate(provisional):
        end_byte = next(
            (
                following_start
                for _, following_level, following_start, _ in provisional[index + 1 :]
                if following_level <= level
            ),
            raw_text_length,
        )
        headings.append(
            Heading(
                text=text,
                level=level,
                start_byte=start_byte,
                end_byte=end_byte,
                parent_index=parent_index,
            )
        )
    return headings


# TODO: Add heading-bounded chunking in app.kb.chunker.
