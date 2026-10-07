"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.cat_core.assumptions import AssumptionsProfile, CapitalPolicy

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

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_primary_model: str = "qwen2.5:3b-instruct"

    # Optional OSM enrichment (Overpass) — disabled by default for offline flexibility
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

    # Postgres (compose; store is in-memory in Phase A/B)
    postgres_user: str = "floodtail"
    postgres_password: str = "floodtail_dev_change_me"
    postgres_db: str = "floodtail"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    def parsed_return_periods(self) -> list[int]:
        parts = [p.strip() for p in self.return_periods.split(",") if p.strip()]
        return [int(p) for p in parts]

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
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
