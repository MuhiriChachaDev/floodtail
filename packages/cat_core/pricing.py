"""Technical premium indication from discrete AAL — not a binding quote."""

from __future__ import annotations

from packages.cat_core.assumptions import PricingPolicy
from packages.cat_core.types import PricingIndication


def technical_premium(
    aal_kes: float,
    policy: PricingPolicy,
    *,
    load_factor: float | None = None,
    basis: str = "gross_aal",
) -> PricingIndication:
    """technical = AAL × load_factor (PROTOTYPE). Human approval still required."""
    load = float(load_factor if load_factor is not None else policy.default_load_factor)
    load = max(load, 1.0)
    aal = max(float(aal_kes), 0.0)
    premium = round(aal * load, 2)
    return PricingIndication(
        aal_basis_kes=round(aal, 2),
        load_factor=round(load, 4),
        technical_premium_kes=premium,
        currency=policy.currency,
        formula="technical_premium = AAL × load_factor",
        basis=basis,
        status=policy.status,
        notes=list(policy.notes)
        + [
            "Indication only — not a binding quote; human approval required.",
            f"Default load factor {policy.default_load_factor} (PROTOTYPE).",
        ],
    )
