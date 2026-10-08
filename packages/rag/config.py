"""RAG / memory connection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus


@dataclass(frozen=True)
class RagSettings:
    """Runtime knobs for RAG + long-term memory."""

    postgres_user: str = "floodtail"
    postgres_password: str = "floodtail_dev_change_me"
    postgres_db: str = "floodtail"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    embedding_dim: int = 768
    embedding_model: str = "nomic-embed-text"
    ollama_host: str = "http://localhost:11434"
    chunk_size: int = 800
    chunk_overlap: int = 120
    # When True, never attempt Postgres (tests).
    force_memory: bool = False

    def database_url(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


_settings: Optional[RagSettings] = None


def get_rag_settings() -> RagSettings:
    global _settings
    if _settings is None:
        _settings = RagSettings()
    return _settings


def configure_rag(settings: RagSettings) -> RagSettings:
    global _settings
    _settings = settings
    return _settings


def reset_rag_settings() -> None:
    global _settings
    _settings = None
