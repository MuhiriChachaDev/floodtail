"""Capital / set-aside band for underwriter budgeting guidance."""

from __future__ import annotations

from packages.cat_core.assumptions import AssumptionsProfile, CapitalPolicy
from packages.cat_core.types import CapitalBand, EPPoint, TierLoss


def _loss_at_rp(tier_losses: list[TierLoss], rp: int) -> float:
    for t in tier_losses:
        if t.return_period == rp:
            return float(t.loss_kes)
    # nearest RP at or above requested, else max
    candidates = [t for t in tier_losses if t.return_period >= rp]
    if candidates:
        return float(min(candidates, key=lambda t: t.return_period).loss_kes)
    if tier_losses:
        return float(max(tier_losses, key=lambda t: t.return_period).loss_kes)
    return 0.0


def compute_capital_band(
    tier_losses: list[TierLoss],
    aal_kes: float,
    total_tiv_kes: float,
    policy: CapitalPolicy,
) -> CapitalBand:
    """
    Floor  — avoid under-budgeting (configured RP loss, default RP100).
    Central — discrete AAL (technical view; may be below floor).
    Ceiling — avoid over-budgeting: min(configured RP loss, appetite × TIV).

    Note: central (AAL) may be < floor (PML proxy). That is expected for discrete EP.
    Ordering guarantee: floor_kes <= ceiling_kes.
    """
    notes: list[str] = []
    floor = _loss_at_rp(tier_losses, policy.floor_return_period)
    ceiling_rp_loss = _loss_at_rp(tier_losses, policy.ceiling_return_period)
    tiv_cap = float(policy.ceiling_tiv_fraction) * float(total_tiv_kes)
    ceiling = min(ceiling_rp_loss, tiv_cap)

    if floor > ceiling:
        notes.append(
            f"floor ({floor:.2f}) > ceiling ({ceiling:.2f}); clamping floor to ceiling"
        )
        floor = ceiling

    central = float(aal_kes)
    if central < floor:
        notes.append(
            "central AAL is below floor RP loss — set aside at least floor for severe risk"
        )
    if central > ceiling:
        notes.append(
            "central AAL is above ceiling — review appetite cap / TIV fraction"
        )

    return CapitalBand(
        floor_kes=round(floor, 2),
        central_kes=round(central, 2),
        ceiling_kes=round(ceiling, 2),
        currency=policy.currency,
        method="discrete_ep_aal",
        floor_basis=f"rp{policy.floor_return_period}",
        central_basis="aal",
        ceiling_basis=(
            f"min(rp{policy.ceiling_return_period}, "
            f"{policy.ceiling_tiv_fraction}*tiv)"
        ),
        notes=notes,
    )


def compute_capital_band_from_profile(
    tier_losses: list[TierLoss],
    aal_kes: float,
    total_tiv_kes: float,
    profile: AssumptionsProfile,
) -> CapitalBand:
    return compute_capital_band(tier_losses, aal_kes, total_tiv_kes, profile.capital)


def allowlist_from_band(band: CapitalBand) -> dict[str, float]:
    return {
        "set_aside_floor_kes": band.floor_kes,
        "set_aside_central_kes": band.central_kes,
        "set_aside_ceiling_kes": band.ceiling_kes,
    }


def ep_allowlist(ep_curve: list[EPPoint]) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in ep_curve:
        rp = int(p.return_period)
        out[f"ep_loss_rp{rp}_kes"] = p.loss_kes
        out[f"ep_aep_rp{rp}"] = p.aep
    return out
