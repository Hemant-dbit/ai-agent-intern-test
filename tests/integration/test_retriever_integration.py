from __future__ import annotations

from app.kb.retriever import retrieve


def test_retrieve_returns_current_returns_policy_for_return_window_query():
    """Check that the real embedding index surfaces the active returns policy for a clear policy query."""
    results = retrieve("how long do I have to return a bag", k=8)

    assert results
    assert any(chunk.doc_filename == "01-returns-policy-current.md" for chunk, _ in results)
    assert all(isinstance(score, float) for _, score in results)
