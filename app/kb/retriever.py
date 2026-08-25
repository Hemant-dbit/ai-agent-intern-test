"""Knowledge-base retrieval module."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app import config
from app.kb.chunker import Chunk
from app.kb.indexer import load_index
import app.kb.indexer as indexer


def retrieve(query: str, k: int = 8) -> list[tuple[Chunk, float]]:
    """Return the closest matching chunks to a query using cosine similarity."""
    if not query or k <= 0:
        return []

    chunks, embeddings = load_index(Path(config.INDEX_DIR))
    if not chunks or embeddings.size == 0:
        return []

    query_chunk = Chunk(
        id="query",
        doc_filename="query",
        heading_path="Query",
        text=query,
        frontmatter={},
        char_start=0,
        char_end=len(query),
    )
    query_vector = np.asarray(indexer.embed_chunks([query_chunk]), dtype=np.float32)
    query_vector = query_vector.reshape(1, -1)

    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim != 2:
        raise ValueError("stored embeddings must be a two-dimensional array")

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    query_norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
    safe_norms = np.where(norms == 0, 1.0, norms)
    safe_query_norm = np.where(query_norm == 0, 1.0, query_norm)

    normalized_embeddings = embeddings / safe_norms
    normalized_query = query_vector / safe_query_norm
    scores = (normalized_embeddings @ normalized_query.T).reshape(-1)

    top_indices = np.argsort(scores)[::-1][:k]
    return [(chunks[index], float(scores[index])) for index in top_indices]
