"""Exceedance probability curve and discrete AAL from tier losses."""

from __future__ import annotations

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.types import EPPoint, TierLoss


def build_tier_losses(
    tier_totals: dict[str, float],
    profile: AssumptionsProfile,
    *,
    mean_damage_by_tier: dict[str, float] | None = None,
) -> list[TierLoss]:
    mean_damage_by_tier = mean_damage_by_tier or {}
    rows: list[TierLoss] = []
    for tier, rp in profile.tier_rp_map().items():
        rows.append(
            TierLoss(
                tier=tier,
                return_period=rp,
                aep=profile.aep_for_rp(rp),
                loss_kes=float(tier_totals.get(tier, 0.0)),
                mean_damage_ratio=mean_damage_by_tier.get(tier),
            )
        )
    # Sort by increasing return period (rarer / typically larger)
    rows.sort(key=lambda r: r.return_period)
    return rows


def build_ep_curve(tier_losses: list[TierLoss]) -> list[EPPoint]:
    return [
        EPPoint(
            return_period=float(t.return_period),
            aep=t.aep,
            loss_kes=t.loss_kes,
        )
        for t in tier_losses
    ]


def discrete_aal(tier_losses: list[TierLoss]) -> float:
    """AAL ≈ Σ (AEP_tier × tier_portfolio_loss) — prototype discrete approximation."""
    return float(sum(t.aep * t.loss_kes for t in tier_losses))
