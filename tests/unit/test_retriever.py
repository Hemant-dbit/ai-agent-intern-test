from __future__ import annotations

import numpy as np

from app import config
from app.kb.chunker import Chunk
from app.kb.indexer import save_index
from app.kb import retriever


def test_retrieve_ranks_chunks_by_cosine_similarity(tmp_path, monkeypatch):
    """Rank similar chunks above less-similar ones with a deterministic synthetic index."""
    chunks = [
        Chunk(
            id="chunk-1",
            doc_filename="policy-1.md",
            heading_path="Returns > Window",
            text="Return within 30 calendar days of delivery.",
            frontmatter={},
            char_start=0,
            char_end=1,
        ),
        Chunk(
            id="chunk-2",
            doc_filename="policy-2.md",
            heading_path="Returns > Window",
            text="Return within 28 days of delivery.",
            frontmatter={},
            char_start=0,
            char_end=1,
        ),
        Chunk(
            id="chunk-3",
            doc_filename="policy-3.md",
            heading_path="Shipping",
            text="Domestic shipping takes 3 to 5 business days.",
            frontmatter={},
            char_start=0,
            char_end=1,
        ),
    ]
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.9, 0.4358899, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    save_index(chunks, embeddings, tmp_path)
    monkeypatch.setattr(config, "INDEX_DIR", str(tmp_path))

    query_vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    def fake_embed_chunks(query_chunks):
        assert len(query_chunks) == 1
        assert query_chunks[0].text == "return window 30 days"
        return np.asarray([query_vector], dtype=np.float32)

    monkeypatch.setattr("app.kb.indexer.embed_chunks", fake_embed_chunks)

    results = retriever.retrieve("return window 30 days", k=3)

    assert [chunk.id for chunk, _ in results] == ["chunk-1", "chunk-2", "chunk-3"]
    assert results[0][1] > results[1][1] > results[2][1]
    assert np.isclose(results[0][1], 1.0)
    assert np.isclose(results[1][1], 0.9)
