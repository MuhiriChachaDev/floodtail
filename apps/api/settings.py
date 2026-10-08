"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.cat_core.assumptions import (
    AssumptionsProfile,
    CapitalPolicy,
    PricingPolicy,
    TreatyPolicy,
)
from packages.rag.config import RagSettings

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """FLOODTAIL API settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["prototype", "development", "production"] = "prototype"
    tenant_id: str = "default"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Comma-separated browser origins allowed to call the API (no * in production).
    # Example: https://floodtail.vercel.app,https://floodtail-git-main.vercel.app
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # OpenAPI /docs. None = on in non-prod, off in production.
    # Set ENABLE_DOCS=true|false to override.
    enable_docs: bool | None = None

    # Paths
    project_root: Path = _ROOT
    nairobi_data_dir: Path = _ROOT / "Nairobi_Data"
    models_dir: Path = _ROOT / "models"
    max_upload_mb: int = 50

    # Modelling
    d_max_m: float = 4.0
    return_periods: str = "5,20,50,100,250"
    assumptions_version: str = "nairobi-pluvial-v1"
    capital_floor_rp: int = 100
    capital_ceiling_rp: int = 250
    capital_ceiling_tiv_fraction: float = 1.0
    capital_currency: str = "KES"

    # Prototype single-layer XL (fractions of TIV; absolute overrides via RunConfig)
    treaty_attachment_tiv_fraction: float = 0.05
    treaty_limit_tiv_fraction: float = 0.15
    pricing_default_load_factor: float = 1.25

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_primary_model: str = "qwen2.5:3b-instruct"

    # Predictive ML is a required product stage (hazard + vulnerability).
    # Prior-only is allowed only when allow_prior_only=true (tests / offline debug).
    require_ml: bool = True
    allow_prior_only: bool = False

    # Optional OSM enrichment (Overpass) — off by default; never required for a run
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    use_osm_default: bool = False
    hotspots_filename: str = "nairobi_hotspots_geocoded.csv"

    # JWT / Keycloak (wired in Phase E)
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "floodtail"
    keycloak_client_id: str = "floodtail-api"
    keycloak_client_secret: str = "change_me"
    jwt_secret: str = "dev_jwt_secret_change_me"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 15

    # Security
    aes_key_base64: str = "Zm9vYmFyZm9vYmFyZm9vYmFyZm9vYmFyZm9vYmFyZm9vYmFy"

    # Postgres (compose; portfolio/run store is still in-memory Phase A/B).
    # RAG + long-term agent memory use Postgres + pgvector when reachable.
    postgres_user: str = "floodtail"
    postgres_password: str = "floodtail_dev_change_me"
    postgres_db: str = "floodtail"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # RAG / embeddings
    ollama_embedding_model: str = "nomic-embed-text"
    rag_embedding_dim: int = 768
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_force_memory: bool = False

    def parsed_return_periods(self) -> list[int]:
        parts = [p.strip() for p in self.return_periods.split(",") if p.strip()]
        return [int(p) for p in parts]

    def parsed_cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.env == "production" and ("*" in origins or not origins):
            raise ValueError(
                "CORS_ORIGINS must be an explicit allowlist in production (no '*')"
            )
        return origins

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def docs_enabled(self) -> bool:
        if self.enable_docs is not None:
            return self.enable_docs
        return not self.is_production

    def assumptions_profile(self) -> AssumptionsProfile:
        return AssumptionsProfile(
            assumptions_version=self.assumptions_version,
            d_max_m=self.d_max_m,
            return_periods=self.parsed_return_periods(),
            capital=CapitalPolicy(
                floor_return_period=self.capital_floor_rp,
                ceiling_return_period=self.capital_ceiling_rp,
                ceiling_tiv_fraction=self.capital_ceiling_tiv_fraction,
                currency=self.capital_currency,
            ),
            treaty=TreatyPolicy(
                attachment_tiv_fraction=self.treaty_attachment_tiv_fraction,
                limit_tiv_fraction=self.treaty_limit_tiv_fraction,
                currency=self.capital_currency,
            ),
            pricing=PricingPolicy(
                default_load_factor=self.pricing_default_load_factor,
                currency=self.capital_currency,
            ),
        )

    def rag_settings(self) -> RagSettings:
        return RagSettings(
            postgres_user=self.postgres_user,
            postgres_password=self.postgres_password,
            postgres_db=self.postgres_db,
            postgres_host=self.postgres_host,
            postgres_port=self.postgres_port,
            embedding_dim=self.rag_embedding_dim,
            embedding_model=self.ollama_embedding_model,
            ollama_host=self.ollama_host,
            chunk_size=self.rag_chunk_size,
            chunk_overlap=self.rag_chunk_overlap,
            force_memory=self.rag_force_memory,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
