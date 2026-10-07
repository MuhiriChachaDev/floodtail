"""Template underwriter insight (no LLM) — Phase B."""

from __future__ import annotations

from typing import Any

from packages.cat_core.types import (
    CapitalBand,
    DataLabels,
    InsightPackage,
    MetricsPayload,
    Recommendation,
)


def _recommendation(metrics: MetricsPayload) -> Recommendation:
    band = metrics.capital_band
    if band is None:
        return Recommendation.REVIEW
    accum = metrics.accumulation_summary or {}
    by_class = accum.get("by_housing_class") or []
    top_share = float(by_class[0]["loss_share_pct"]) if by_class else 0.0
    # Heuristic appetite: escalate if extreme loss > 25% of TIV or one class > 50% loss
    extreme_loss = 0.0
    for t in metrics.tier_losses:
        if t.tier == "extreme" or t.return_period >= 250:
            extreme_loss = t.loss_kes
            break
    if metrics.total_tiv_kes > 0 and extreme_loss / metrics.total_tiv_kes > 0.25:
        return Recommendation.ESCALATE
    if top_share >= 50.0:
        return Recommendation.REVIEW
    if band.floor_kes <= 0.05 * metrics.total_tiv_kes:
        return Recommendation.ACCEPT
    return Recommendation.REVIEW


def build_template_insight(metrics: MetricsPayload) -> InsightPackage:
    band = metrics.capital_band or CapitalBand(
        floor_kes=0.0, central_kes=metrics.aal_kes, ceiling_kes=0.0
    )
    rec = _recommendation(metrics)
    by_class = (metrics.accumulation_summary or {}).get("by_housing_class") or []
    top_class = by_class[0]["housing_class"] if by_class else "n/a"
    top_share = by_class[0]["loss_share_pct"] if by_class else 0.0

    why = [
        (
            f"{metrics.n_insured_houses} insured locations in "
            f"{metrics.location_label}; total TIV KES {metrics.total_tiv_kes:,.0f}."
        ),
        (
            f"Set aside at least KES {band.floor_kes:,.0f} (floor) and not more than "
            f"KES {band.ceiling_kes:,.0f} (ceiling); technical AAL "
            f"KES {band.central_kes:,.0f}."
        ),
    ]
    if by_class:
        why.append(
            f"Top loss concentration: {top_class} at {top_share:.1f}% of reference-tier loss."
        )

    next_steps: list[str]
    if rec == Recommendation.ACCEPT:
        next_steps = [
            "Document assumptions_version and data_labels on the binding note.",
            "Monitor hotspot / class mix on the next renewal.",
        ]
    elif rec == Recommendation.ESCALATE:
        next_steps = [
            "Escalate to actuary: extreme-tier loss is high vs TIV.",
            "Review concentration and consider capacity limits before accepting.",
        ]
    else:
        next_steps = [
            "Review housing-class concentration before accepting more writings.",
            "Compare set-aside floor vs current capital allocation.",
            "Optional: train/pin ML models (Phase C) and re-run for delta.",
        ]

    allowlist: dict[str, Any] = {
        "insured_houses": metrics.n_insured_houses,
        "total_tiv_kes": metrics.total_tiv_kes,
        "aal_kes": metrics.aal_kes,
        "set_aside_floor_kes": band.floor_kes,
        "set_aside_central_kes": band.central_kes,
        "set_aside_ceiling_kes": band.ceiling_kes,
        "location_label": metrics.location_label,
    }
    for t in metrics.tier_losses:
        allowlist[f"tier_loss_{t.tier}_kes"] = t.loss_kes

    narrative = (
        f"For {metrics.location_label}, the book has {metrics.n_insured_houses} insured houses "
        f"with TIV KES {metrics.total_tiv_kes:,.0f}. "
        f"Recommended set-aside band: KES {band.floor_kes:,.0f} – {band.ceiling_kes:,.0f} "
        f"(central AAL KES {band.central_kes:,.0f}). "
        f"Recommendation: {rec.value}."
    )

    return InsightPackage(
        run_id=metrics.run_id,
        recommendation=rec,
        insured_houses=metrics.n_insured_houses,
        total_tiv_kes=metrics.total_tiv_kes,
        location_label=metrics.location_label,
        set_aside=band,
        why=why,
        next_steps=next_steps,
        narrative=narrative,
        numbers_source="template",
        assumptions_version=metrics.assumptions_version,
        data_labels=metrics.data_labels or DataLabels(),
        allowlist=allowlist,
    )
