"""Deterministic XL reinsurance layering: gross → retention/attachment → recovery → net.

Prototype single-layer excess-of-loss (XL). Not a full treaty programme.
"""

from __future__ import annotations

from packages.cat_core.assumptions import TreatyPolicy
from packages.cat_core.ep import discrete_aal
from packages.cat_core.types import (
    EPPoint,
    FinancialView,
    LayeredLoss,
    TierLoss,
    TreatyTerms,
)


def resolve_treaty_terms(
    policy: TreatyPolicy,
    total_tiv_kes: float,
) -> TreatyTerms:
    """Resolve absolute KES terms from fixed overrides or TIV fractions."""
    tiv = max(float(total_tiv_kes), 0.0)
    if policy.attachment_kes is not None:
        attachment = float(policy.attachment_kes)
    else:
        attachment = round(tiv * float(policy.attachment_tiv_fraction), 2)

    if policy.limit_kes is not None:
        limit = float(policy.limit_kes)
    else:
        limit = round(tiv * float(policy.limit_tiv_fraction), 2)

    attachment = max(attachment, 0.0)
    limit = max(limit, 0.0)
    retention = (
        float(policy.retention_kes)
        if policy.retention_kes is not None
        else attachment
    )
    retention = max(retention, 0.0)

    notes = list(policy.notes)
    if policy.attachment_kes is None:
        notes.append(
            f"Attachment = {policy.attachment_tiv_fraction:.0%} × TIV (PROTOTYPE)"
        )
    if policy.limit_kes is None:
        notes.append(f"Limit = {policy.limit_tiv_fraction:.0%} × TIV (PROTOTYPE)")
    notes.append(
        "Single-layer XL: recovery = min(limit, max(0, gross − attachment)); "
        "net = gross − recovery. Not a multi-layer programme."
    )

    return TreatyTerms(
        name=policy.name,
        status=policy.status,
        currency=policy.currency,
        attachment_kes=round(attachment, 2),
        limit_kes=round(limit, 2),
        retention_kes=round(retention, 2),
        notes=notes,
    )


def apply_xl(gross_kes: float, treaty: TreatyTerms) -> tuple[float, float, float]:
    """Return (retained_below_attachment, recovery, net) for one gross loss."""
    g = max(float(gross_kes), 0.0)
    attachment = float(treaty.attachment_kes)
    limit = float(treaty.limit_kes)
    recovery = min(limit, max(0.0, g - attachment))
    net = g - recovery
    retained = min(g, attachment)
    return round(retained, 2), round(recovery, 2), round(net, 2)


def layer_tier_losses(
    tier_losses: list[TierLoss],
    treaty: TreatyTerms,
) -> list[LayeredLoss]:
    rows: list[LayeredLoss] = []
    for t in tier_losses:
        retained, recovery, net = apply_xl(t.loss_kes, treaty)
        rows.append(
            LayeredLoss(
                tier=t.tier,
                return_period=t.return_period,
                aep=t.aep,
                gross_kes=round(float(t.loss_kes), 2),
                retained_kes=retained,
                recovery_kes=recovery,
                net_kes=net,
            )
        )
    rows.sort(key=lambda r: r.return_period)
    return rows


def build_financial_view(
    tier_losses: list[TierLoss],
    policy: TreatyPolicy,
    total_tiv_kes: float,
    *,
    reference_tier: str = "severe",
) -> FinancialView:
    treaty = resolve_treaty_terms(policy, total_tiv_kes)
    layered = layer_tier_losses(tier_losses, treaty)
    ep_gross = [
        EPPoint(return_period=float(t.return_period), aep=t.aep, loss_kes=t.gross_kes)
        for t in layered
    ]
    ep_net = [
        EPPoint(return_period=float(t.return_period), aep=t.aep, loss_kes=t.net_kes)
        for t in layered
    ]
    # Reuse discrete AAL formula on synthetic TierLoss shapes
    aal_gross = discrete_aal(
        [
            TierLoss(
                tier=t.tier,
                return_period=t.return_period,
                aep=t.aep,
                loss_kes=t.gross_kes,
            )
            for t in layered
        ]
    )
    aal_net = discrete_aal(
        [
            TierLoss(
                tier=t.tier,
                return_period=t.return_period,
                aep=t.aep,
                loss_kes=t.net_kes,
            )
            for t in layered
        ]
    )
    aal_ceded = max(0.0, aal_gross - aal_net)
    return FinancialView(
        treaty=treaty,
        layered_by_tier=layered,
        ep_curve_gross=ep_gross,
        ep_curve_net=ep_net,
        aal_gross_kes=round(aal_gross, 2),
        aal_net_kes=round(aal_net, 2),
        aal_ceded_kes=round(aal_ceded, 2),
        reference_tier=reference_tier,
    )
