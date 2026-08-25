"""Configuration loading for the Aster & Row support agent."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

INDEX_DIR = Path(os.getenv("INDEX_DIR", "index"))
DEBUG = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_groq_api_key() -> str:
    """Return the configured Groq API key when an LLM operation needs it."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is required to use Groq features. "
            "Set it in your environment or in a .env file."
        )
    return api_key


# TODO: Add typed configuration for later application features.
