"""LangChain tools wrapping grounded CAT math (EP / capital / accumulation)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ValidationError

from packages.cat_core.accumulation import build_accumulation_summary
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.capital import (
    allowlist_from_band,
    compute_capital_band_from_profile,
    ep_allowlist,
)
from packages.cat_core.ep import (
    AAL_CAVEAT,
    AAL_METHOD,
    build_ep_curve,
    build_tier_losses,
    discrete_aal,
    light_mc_aal_band,
)
from packages.cat_core.financial import add_loss_columns, reconcile_location_losses
from packages.cat_core.pricing import technical_premium
from packages.cat_core.reinsurance import build_financial_view
from packages.cat_core.types import CapitalBand, MetricsPayload, TierLoss


def compute_ep_capital(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    run_id: str,
    portfolio_id: str,
    location_label: str,
    data_labels: Any,
    hazard_model_version: str | None = None,
    vuln_model_version: str | None = None,
    baseline_delta: dict | None = None,
    warnings: list[str] | None = None,
    treaty_attachment_kes: float | None = None,
    treaty_limit_kes: float | None = None,
    pricing_load_factor: float | None = None,
) -> tuple[pd.DataFrame, MetricsPayload, list[TierLoss], CapitalBand]:
    """Compute losses → EP → AAL → XL financial → capital → technical premium."""
    work = add_loss_columns(frame, profile.tier_names)
    tier_totals = reconcile_location_losses(work, profile.tier_names)
    mean_dmg = {
        tier: float(work[f"damage_ratio_{tier}"].mean()) for tier in profile.tier_names
    }
    tier_losses = build_tier_losses(tier_totals, profile, mean_damage_by_tier=mean_dmg)
    ep_curve = build_ep_curve(tier_losses)
    aal = discrete_aal(tier_losses)
    warn_list = list(warnings or [])
    aal_uncertainty = None
    mc = profile.monte_carlo
    if mc.enabled:
        aal_uncertainty = light_mc_aal_band(
            work,
            profile,
            n_sims=mc.n_sims,
            noise_sigma=mc.noise_sigma,
            seed=mc.seed,
        )
        warn_list.append(
            f"Light MC AAL band enabled (n={mc.n_sims}, sigma={mc.noise_sigma})"
        )
    total_tiv = float(work["tiv_kes"].sum())
    capital = compute_capital_band_from_profile(
        tier_losses, aal, total_tiv, profile
    )
    treaty_policy = profile.treaty.model_copy(deep=True)
    if treaty_attachment_kes is not None:
        treaty_policy.attachment_kes = float(treaty_attachment_kes)
    if treaty_limit_kes is not None:
        treaty_policy.limit_kes = float(treaty_limit_kes)
    financial = build_financial_view(
        tier_losses, treaty_policy, total_tiv, reference_tier="severe"
    )
    pricing = technical_premium(
        aal,
        profile.pricing,
        load_factor=pricing_load_factor,
        basis="gross_aal",
    )
    # Stamp honesty notes onto data_labels when it supports notes
    if hasattr(data_labels, "notes"):
        extra = [
            AAL_CAVEAT,
            f"Treaty {financial.treaty.name} ({financial.treaty.status})",
            f"Pricing {pricing.status}: load×{pricing.load_factor}",
        ]
        notes = list(getattr(data_labels, "notes", []) or [])
        for note in extra:
            if note not in notes:
                notes.append(note)
        data_labels.notes = notes
    if hasattr(data_labels, "aal_method"):
        data_labels.aal_method = AAL_METHOD
    if hasattr(data_labels, "aal_caveat"):
        data_labels.aal_caveat = AAL_CAVEAT
    accum = build_accumulation_summary(work, profile.tier_names)
    from packages.cat_core.depth_damage import build_depth_damage_summary

    depth_damage = build_depth_damage_summary(work, profile)
    metrics = MetricsPayload(
        run_id=run_id,
        portfolio_id=portfolio_id,
        assumptions_version=profile.assumptions_version,
        data_labels=data_labels,
        n_insured_houses=int(len(work)),
        total_tiv_kes=total_tiv,
        location_label=location_label,
        tier_losses=tier_losses,
        ep_curve=ep_curve,
        aal_kes=round(aal, 2),
        aal_method=AAL_METHOD,
        aal_caveat=AAL_CAVEAT,
        aal_uncertainty=aal_uncertainty,
        capital_band=capital,
        financial=financial,
        pricing=pricing,
        hazard_model_version=hazard_model_version,
        vuln_model_version=vuln_model_version,
        baseline_delta=dict(baseline_delta or {}),
        accumulation_summary=accum,
        depth_damage_summary=depth_damage,
        warnings=warn_list,
    )
    return work, metrics, tier_losses, capital


def compute_accumulation(frame: pd.DataFrame, profile: AssumptionsProfile) -> dict[str, Any]:
    return build_accumulation_summary(frame, profile.tier_names)


def get_allowlist(metrics: MetricsPayload) -> dict[str, Any]:
    """Frozen numbers the Insight Agent / LLM may present."""
    band = metrics.capital_band
    allow: dict[str, Any] = {
        "n_insured_houses": metrics.n_insured_houses,
        "insured_houses": metrics.n_insured_houses,
        "total_tiv_kes": metrics.total_tiv_kes,
        "location_label": metrics.location_label,
        "aal_kes": metrics.aal_kes,
        "assumptions_version": metrics.assumptions_version,
    }
    if band is not None:
        allow.update(allowlist_from_band(band))
        allow["set_aside"] = {
            "floor": band.floor_kes,
            "central": band.central_kes,
            "ceiling": band.ceiling_kes,
            "currency": band.currency,
        }
    allow.update(ep_allowlist(metrics.ep_curve))
    for t in metrics.tier_losses:
        allow[f"tier_loss_{t.tier}_kes"] = t.loss_kes
        allow[f"ep_loss_rp{t.return_period}_kes"] = t.loss_kes

    fin = metrics.financial
    if fin is not None:
        allow["aal_gross_kes"] = fin.aal_gross_kes
        allow["aal_net_kes"] = fin.aal_net_kes
        allow["aal_ceded_kes"] = fin.aal_ceded_kes
        allow["treaty_name"] = fin.treaty.name
        allow["treaty_attachment_kes"] = fin.treaty.attachment_kes
        allow["treaty_limit_kes"] = fin.treaty.limit_kes
        allow["treaty_retention_kes"] = fin.treaty.retention_kes
        for layer in fin.layered_by_tier:
            allow[f"net_loss_{layer.tier}_kes"] = layer.net_kes
            allow[f"recovery_{layer.tier}_kes"] = layer.recovery_kes
    if metrics.pricing is not None:
        allow["technical_premium_kes"] = metrics.pricing.technical_premium_kes
        allow["pricing_load_factor"] = metrics.pricing.load_factor

    by_class = (metrics.accumulation_summary or {}).get("by_housing_class") or []
    if by_class:
        top = by_class[0]
        allow["top_class"] = top.get("housing_class")
        allow["top_class_loss_share_pct"] = top.get("loss_share_pct")
        allow["top_concentration_drivers"] = [
            {
                "housing_class": c.get("housing_class"),
                "loss_share_pct": c.get("loss_share_pct"),
            }
            for c in by_class[:3]
        ]

    if metrics.hazard_model_version:
        allow["hazard_model_version"] = metrics.hazard_model_version
    if metrics.vuln_model_version:
        allow["vuln_model_version"] = metrics.vuln_model_version
    if metrics.baseline_delta:
        allow["baseline_delta"] = metrics.baseline_delta
        if "aal_delta_kes" in metrics.baseline_delta:
            allow["aal_delta_kes"] = metrics.baseline_delta["aal_delta_kes"]
        if "baseline_aal_kes" in metrics.baseline_delta:
            allow["baseline_aal_kes"] = metrics.baseline_delta["baseline_aal_kes"]
    enrich = (metrics.accumulation_summary or {}).get("enrichment") or {}
    if enrich:
        allow["enrichment"] = enrich
    xai = metrics.xai_summary or {}
    if xai:
        allow["xai_disclaimer"] = xai.get("disclaimer")
        haz = xai.get("hazard_global") or {}
        vuln = xai.get("vulnerability_global") or {}
        if haz.get("top_features"):
            allow["shap_hazard_top_features"] = haz["top_features"]
        if vuln.get("top_features"):
            allow["shap_vulnerability_top_features"] = vuln["top_features"]
        sample = xai.get("sample_local") or {}
        if sample.get("loc_id"):
            allow["shap_sample_loc_id"] = sample["loc_id"]
            allow["shap_sample_prediction"] = sample.get("prediction")
            feats = sample.get("top_features") or []
            allow["shap_sample_top_features"] = [
                f.get("feature") for f in feats if isinstance(f, dict) and f.get("feature")
            ]
    return allow


def allowlist_from_client_metrics(raw: dict[str, Any] | None) -> dict[str, Any]:
    """
    Build a grounded allowlist from metrics JSON cached in the browser.

    Used when the API store no longer has the run (in-memory restart) but the UI
    still holds frozen metrics from the last portfolio test.
    """
    if not raw:
        return {}
    try:
        metrics = MetricsPayload.model_validate(raw)
        return get_allowlist(metrics)
    except ValidationError:
        allow: dict[str, Any] = {}
        n = raw.get("n_insured_houses")
        if n is not None:
            allow["n_insured_houses"] = int(n)
            allow["insured_houses"] = int(n)
        for key in ("total_tiv_kes", "aal_kes", "location_label", "assumptions_version"):
            if raw.get(key) is not None:
                allow[key] = raw[key]
        band = raw.get("capital_band")
        if isinstance(band, dict):
            try:
                cb = CapitalBand.model_validate(band)
                allow.update(allowlist_from_band(cb))
            except ValidationError:
                pass
        return allow


try:
    from langchain_core.tools import tool

    @tool
    def describe_math_tools() -> str:
        """List grounded math tools (EP, capital, accumulation, allowlist)."""
        return "compute_ep_capital, compute_accumulation, get_allowlist"

except ImportError:  # pragma: no cover
    pass
