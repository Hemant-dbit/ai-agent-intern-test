"""Tests for local embedding and index persistence."""

import numpy as np

from app.kb.chunker import Chunk
from app.kb import indexer


class _FakeEmbedder:
    """Record local embedding inputs and return deterministic vectors."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, inputs: list[str], *, convert_to_numpy: bool, show_progress_bar: bool) -> np.ndarray:
        self.calls.append(inputs)
        assert convert_to_numpy is True
        assert show_progress_bar is False
        return np.asarray([[float(position), float(position + 1)] for position, _ in enumerate(inputs)])


def test_local_embedding_and_index_round_trip(monkeypatch, tmp_path) -> None:
    """Embed synthetic chunks without network access and preserve row order on disk."""
    chunks = [
        Chunk("first.md:0", "first.md", "First > Rule", "First rule text.", {"status": "active"}, 0, 16),
        Chunk("second.md:0", "second.md", "Second > Rule", "Second rule text.", {"status": "active"}, 0, 17),
    ]
    fake_embedder = _FakeEmbedder()
    monkeypatch.setattr(indexer, "_create_embedder", lambda: fake_embedder)

    embeddings = indexer.embed_chunks(chunks)
    indexer.save_index(chunks, embeddings, tmp_path)
    loaded_chunks, loaded_embeddings = indexer.load_index(tmp_path)

    assert fake_embedder.calls == [
        [
            "first.md — First > Rule\n\nFirst rule text.",
            "second.md — Second > Rule\n\nSecond rule text.",
        ]
    ]
    assert embeddings.dtype == np.float32
    assert loaded_chunks == chunks
    assert loaded_embeddings.dtype == np.float32
    np.testing.assert_array_equal(loaded_embeddings, embeddings)
    assert (tmp_path / "chunks.jsonl").is_file()
    assert (tmp_path / "embeddings.npy").is_file()
