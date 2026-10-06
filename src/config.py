"""FLOODTAIL — Configuration loader.

Loads ``config.yaml``, validates required sections, and exposes a fully
typed ``FLOODTAILConfig`` Pydantic model.  Fails loudly with
``ConfigurationError`` when anything is wrong.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from src.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Typed configuration models
# ---------------------------------------------------------------------------

class ProjectConfig(BaseModel):
    """Project-level metadata."""
    name: str
    version: str
    environment: str = "development"


class SimulationConfig(BaseModel):
    """Monte-Carlo simulation parameters."""
    years: int = Field(..., ge=1)
    seed: int


class RiskConfig(BaseModel):
    """Risk metric thresholds."""
    tail_confidence: float = Field(..., gt=0, lt=1)


class PricingConfig(BaseModel):
    """Pricing assumptions (prototype — not production calibration)."""
    cost_of_capital_rate: float = Field(..., ge=0)
    expense_rate: float = Field(..., ge=0)


class ModelConfig(BaseModel):
    """Model version identifiers."""
    hazard_version: str
    vulnerability_version: str
    model_version: str


class GovernanceConfig(BaseModel):
    """Governance and audit flags."""
    require_human_decision: bool = True
    audit_enabled: bool = True


class DataConfig(BaseModel):
    """Portfolio data expectations."""
    portfolio_required_fields: list[str]


class FLOODTAILConfig(BaseModel):
    """Top-level configuration aggregating all sections."""
    project: ProjectConfig
    simulation: SimulationConfig
    risk: RiskConfig
    pricing: PricingConfig
    model: ModelConfig
    governance: GovernanceConfig
    data: DataConfig


# ---------------------------------------------------------------------------
# Required top-level sections
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS = [
    "project",
    "simulation",
    "risk",
    "pricing",
    "model",
    "governance",
    "data",
]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: Optional[str | Path] = None) -> FLOODTAILConfig:
    """Load and validate the FLOODTAIL configuration.

    Args:
        path: Explicit path to a YAML file.  When *None* the loader looks
              for ``config.yaml`` in the project root (the directory
              containing this package's parent).

    Returns:
        A validated ``FLOODTAILConfig`` instance.

    Raises:
        ConfigurationError: If the file is missing, unparseable, or fails
            validation.
    """
    config_path = Path(path) if path else _default_config_path()

    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Cannot read configuration file: {exc}") from exc

    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML parse error: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration file must contain a YAML mapping")

    # Check required sections
    missing = [s for s in _REQUIRED_SECTIONS if s not in raw]
    if missing:
        raise ConfigurationError(
            f"Missing required configuration sections: {', '.join(missing)}"
        )

    try:
        return FLOODTAILConfig(**raw)
    except Exception as exc:
        raise ConfigurationError(f"Configuration validation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_config_path() -> Path:
    """Return the default ``config.yaml`` location (project root)."""
    return Path(__file__).resolve().parent.parent / "config.yaml"
