"""Location-agnostic modelling assumptions (config-driven, not city-hardcoded)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CapitalPolicy(BaseModel):
    """Config-driven set-aside band rules (floor / central / ceiling)."""

    floor_return_period: int = Field(
        default=100,
        description="RP used for capital floor (avoid under-budgeting).",
    )
    ceiling_return_period: int = Field(
        default=250,
        description="RP used as ceiling candidate (avoid over-budgeting).",
    )
    ceiling_tiv_fraction: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Ceiling also capped at this fraction of total TIV.",
    )
    currency: str = Field(default="KES")


class TreatyPolicy(BaseModel):
    """Prototype single-layer XL terms (absolute KES overrides or TIV fractions)."""

    name: str = "prototype_xl_v1"
    status: str = "PROTOTYPE"
    currency: str = "KES"
    # Absolute overrides win when set; otherwise fractions of portfolio TIV apply.
    attachment_kes: Optional[float] = Field(default=None, ge=0.0)
    limit_kes: Optional[float] = Field(default=None, ge=0.0)
    retention_kes: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Cedent retention display; defaults to attachment when unset.",
    )
    attachment_tiv_fraction: float = Field(default=0.05, ge=0.0, le=1.0)
    limit_tiv_fraction: float = Field(default=0.15, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class PricingPolicy(BaseModel):
    """Technical premium indication defaults (not a binding quote)."""

    status: str = "PROTOTYPE"
    currency: str = "KES"
    default_load_factor: float = Field(default=1.25, ge=1.0, le=3.0)
    notes: list[str] = Field(default_factory=list)


class MonteCarloPolicy(BaseModel):
    """Optional light damage-ratio noise MC around discrete AAL."""

    enabled: bool = False
    n_sims: int = Field(default=200, ge=1, le=5000)
    noise_sigma: float = Field(default=0.08, ge=0.0, le=0.5)
    seed: int = 42


class AssumptionsProfile(BaseModel):
    """Run-level modelling assumptions."""

    assumptions_version: str = "nairobi-pluvial-v1"
    d_max_m: float = Field(default=4.0, gt=0.0)
    return_periods: list[int] = Field(default_factory=lambda: [5, 20, 50, 100, 250])
    tier_names: list[str] = Field(
        default_factory=lambda: [
            "common",
            "occasional",
            "moderate",
            "severe",
            "extreme",
        ]
    )
    housing_classes: list[str] = Field(
        default_factory=lambda: [
            "informal_iron_sheet",
            "semi_permanent",
            "permanent_masonry",
            "concrete_rcc",
        ]
    )
    # Optional depth–damage overrides / extensions: {class: [[depth_m, ratio], ...]}
    # Merged on top of JRC_ADAPTED_CURVES so new classes can be added without code edits.
    vulnerability_curves: dict[str, list[list[float]]] = Field(default_factory=dict)
    capital: CapitalPolicy = Field(default_factory=CapitalPolicy)
    treaty: TreatyPolicy = Field(default_factory=TreatyPolicy)
    pricing: PricingPolicy = Field(default_factory=PricingPolicy)
    monte_carlo: MonteCarloPolicy = Field(default_factory=MonteCarloPolicy)

    @field_validator("return_periods")
    @classmethod
    def _sorted_positive(cls, v: list[int]) -> list[int]:
        if not v or any(rp <= 0 for rp in v):
            raise ValueError("return_periods must be non-empty positive integers")
        return sorted(v)

    def tier_rp_map(self) -> dict[str, int]:
        """Map tier name → assumed return period (zip order)."""
        n = min(len(self.tier_names), len(self.return_periods))
        return {self.tier_names[i]: self.return_periods[i] for i in range(n)}

    def aep_for_rp(self, rp: int) -> float:
        return 1.0 / float(rp)

    def resolved_vulnerability_curves(self) -> dict[str, list[tuple[float, float]]]:
        from packages.cat_core.vulnerability_prior import resolve_curves

        return resolve_curves(self.vulnerability_curves or None)
