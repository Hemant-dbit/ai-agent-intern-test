"""Embed chunks and persist a local, row-aligned knowledge-base index."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import numpy as np

from app.kb.chunker import Chunk


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNKS_FILENAME = "chunks.jsonl"
EMBEDDINGS_FILENAME = "embeddings.npy"


def embed_chunks(chunks: list[Chunk]) -> np.ndarray:
    """Embed chunk citation context and text with a local free embedding model."""
    if not chunks:
        return np.empty((0, 0), dtype=np.float32)

    inputs = [
        f"{chunk.doc_filename} — {chunk.heading_path}\n\n{chunk.text}"
        for chunk in chunks
    ]
    embedder = _create_embedder()
    return np.asarray(
        embedder.encode(inputs, convert_to_numpy=True, show_progress_bar=False),
        dtype=np.float32,
    )


def _create_embedder() -> Any:
    """Load the local embedding provider lazily so imports remain side-effect free."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def save_index(chunks: list[Chunk], embeddings: np.ndarray, index_dir: str | Path) -> None:
    """Write JSONL chunk metadata and a row-aligned float32 embedding matrix."""
    matrix = np.asarray(embeddings, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("embeddings must be a two-dimensional array")
    if matrix.shape[0] != len(chunks):
        raise ValueError("embeddings row count must match the number of chunks")

    destination = Path(index_dir)
    destination.mkdir(parents=True, exist_ok=True)
    chunks_path = destination / CHUNKS_FILENAME
    embeddings_path = destination / EMBEDDINGS_FILENAME

    with chunks_path.open("w", encoding="utf-8", newline="\n") as stream:
        for chunk in chunks:
            stream.write(json.dumps(asdict(chunk), ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    np.save(embeddings_path, matrix)


def load_index(index_dir: str | Path) -> tuple[list[Chunk], np.ndarray]:
    """Load chunks and their corresponding embedding rows from an index directory."""
    source = Path(index_dir)
    chunks_path = source / CHUNKS_FILENAME
    embeddings_path = source / EMBEDDINGS_FILENAME

    with chunks_path.open(encoding="utf-8") as stream:
        chunks = [Chunk(**json.loads(line)) for line in stream if line.strip()]
    embeddings = np.load(embeddings_path).astype(np.float32, copy=False)
    if embeddings.ndim != 2:
        raise ValueError("stored embeddings must be a two-dimensional array")
    if embeddings.shape[0] != len(chunks):
        raise ValueError("stored embeddings row count does not match stored chunks")
    return chunks, embeddings


# TODO: Add retrieval-facing index query operations in app.kb.retriever.
