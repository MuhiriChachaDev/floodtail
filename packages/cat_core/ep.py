"""Exceedance probability curve and discrete AAL from tier losses."""

from __future__ import annotations

import numpy as np
import pandas as pd

from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.types import (
    AAL_CAVEAT_DISCRETE,
    AAL_METHOD_DISCRETE,
    AALUncertaintyBand,
    EPPoint,
    TierLoss,
)

# Re-export for callers / docs
AAL_METHOD = AAL_METHOD_DISCRETE
AAL_CAVEAT = AAL_CAVEAT_DISCRETE


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
    """AAL ≈ Σ (AEP_tier × tier_portfolio_loss) — prototype discrete approximation.

    Not equivalent to the mean of a stochastic year-loss catalogue.
    See AAL_CAVEAT / MetricsPayload.aal_caveat.
    """
    return float(sum(t.aep * t.loss_kes for t in tier_losses))


def light_mc_aal_band(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    n_sims: int = 200,
    noise_sigma: float = 0.08,
    seed: int = 42,
    damage_prefix: str = "damage_ratio_",
    tiv_col: str = "tiv_kes",
) -> AALUncertaintyBand:
    """
    Optional uncertainty band: perturb per-location damage ratios with
    multiplicative log-noise, recompute discrete AAL each sim.

    PROTOTYPE — illustrates sensitivity only; not a hydrological catalogue.
    """
    n_sims = max(1, int(n_sims))
    rng = np.random.default_rng(int(seed))
    tiv = frame[tiv_col].astype(float).to_numpy()
    aeps = {tier: profile.aep_for_rp(rp) for tier, rp in profile.tier_rp_map().items()}
    base_dmg = {
        tier: frame[f"{damage_prefix}{tier}"].astype(float).clip(0.0, 1.0).to_numpy()
        for tier in profile.tier_names
        if f"{damage_prefix}{tier}" in frame.columns
    }
    aals: list[float] = []
    for _ in range(n_sims):
        aal = 0.0
        for tier, dmg in base_dmg.items():
            noise = rng.normal(0.0, noise_sigma, size=dmg.shape)
            perturbed = np.clip(dmg * (1.0 + noise), 0.0, 1.0)
            tier_loss = float((perturbed * tiv).sum())
            aal += aeps[tier] * tier_loss
        aals.append(aal)
    arr = np.asarray(aals, dtype=float)
    return AALUncertaintyBand(
        method="damage_ratio_noise_mc",
        n_sims=n_sims,
        seed=int(seed),
        aal_mean_kes=round(float(arr.mean()), 2),
        aal_p05_kes=round(float(np.percentile(arr, 5)), 2),
        aal_p50_kes=round(float(np.percentile(arr, 50)), 2),
        aal_p95_kes=round(float(np.percentile(arr, 95)), 2),
        noise_sigma=float(noise_sigma),
        notes=[
            "Light MC on damage ratios — not a stochastic flood catalogue.",
            AAL_CAVEAT,
        ],
    )