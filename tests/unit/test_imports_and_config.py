"""Scaffolding tests for module imports and deferred Groq key validation."""

import importlib

import pytest


MODULES = (
    "app.config",
    "app.kb.loader",
    "app.kb.chunker",
    "app.kb.indexer",
    "app.kb.retriever",
    "app.kb.precedence",
    "app.kb.conflict",
    "app.orders.tool",
    "app.orders.sanitizer",
    "app.session.store",
    "app.agent.orchestrator",
    "app.agent.prompts",
    "app.agent.llm_client",
    "app.agent.guard",
    "app.logging_utils",
    "app.cli",
)


def test_application_modules_import_and_groq_key_is_deferred(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import modules and validate API-key presence only on request."""
    imported_modules = [importlib.import_module(module_name) for module_name in MODULES]
    assert len(imported_modules) == len(MODULES)

    config = importlib.import_module("app.config")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is required"):
        config.get_groq_api_key()

    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    assert config.get_groq_api_key() == "fake-key-for-test"
