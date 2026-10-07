"""Location-agnostic modelling assumptions (config-driven, not city-hardcoded)."""

from __future__ import annotations

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
    capital: CapitalPolicy = Field(default_factory=CapitalPolicy)

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
