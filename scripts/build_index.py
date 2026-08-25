"""Build the local knowledge-base embedding index."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.config import INDEX_DIR
from app.kb.chunker import chunk_document
from app.kb.indexer import embed_chunks, save_index
from app.kb.loader import load_all


def main() -> None:
    """Load, chunk, embed, and persist the repository knowledge base."""
    documents = load_all(REPOSITORY_ROOT / "knowledge-base")
    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    embeddings = embed_chunks(chunks)
    index_directory = REPOSITORY_ROOT / INDEX_DIR
    save_index(chunks, embeddings, index_directory)
    print(f"Built {len(chunks)} chunks in {index_directory}")


if __name__ == "__main__":
    main()
