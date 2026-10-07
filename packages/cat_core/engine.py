"""CAT run engine — prior-only or ML-backed (Phase B/C)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from packages.cat_core.accumulation import build_accumulation_summary
from packages.cat_core.assumptions import AssumptionsProfile
from packages.cat_core.capital import compute_capital_band_from_profile
from packages.cat_core.depth import add_depth_columns
from packages.cat_core.ep import build_ep_curve, build_tier_losses, discrete_aal
from packages.cat_core.exposure import default_data_labels
from packages.cat_core.financial import add_loss_columns, reconcile_location_losses
from packages.cat_core.insight_template import build_template_insight
from packages.cat_core.types import (
    AgentResult,
    DataLabels,
    InsightPackage,
    MetricsPayload,
    StageStatus,
)
from packages.cat_core.vulnerability_prior import add_damage_ratio_columns
from packages.ml.enrich import enrich_frame
from packages.ml.registry import ModelRegistry


@dataclass
class EngineResult:
    metrics: MetricsPayload
    insight: InsightPackage
    properties: pd.DataFrame
    stages: list[AgentResult]


def run_prior_only(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    run_id: str,
    portfolio_id: str,
    location_label: str,
    data_labels: Optional[DataLabels] = None,
    hotspots: Optional[pd.DataFrame] = None,
    use_osm: bool = False,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
) -> EngineResult:
    return run_cat(
        frame,
        profile,
        run_id=run_id,
        portfolio_id=portfolio_id,
        location_label=location_label,
        data_labels=data_labels,
        hotspots=hotspots,
        use_osm=use_osm,
        overpass_url=overpass_url,
    )


def run_cat(
    frame: pd.DataFrame,
    profile: AssumptionsProfile,
    *,
    run_id: str,
    portfolio_id: str,
    location_label: str,
    data_labels: Optional[DataLabels] = None,
    hotspots: Optional[pd.DataFrame] = None,
    use_osm: bool = False,
    overpass_url: str = "https://overpass-api.de/api/interpreter",
    registry: Optional[ModelRegistry] = None,
    hazard_model_version: Optional[str] = None,
    vuln_model_version: Optional[str] = None,
    use_ml: bool = False,
) -> EngineResult:
    """
    Flexible CAT run:
    enrich → optional hazard ML → depth → vuln prior or ML → loss → EP → capital → insight.
    """
    stages: list[AgentResult] = []
    warnings: list[str] = []
    labels = data_labels or default_data_labels(profile)
    baseline_delta: dict = {}

    work = enrich_frame(
        frame,
        hotspots=hotspots,
        use_osm=use_osm,
        overpass_url=overpass_url,
    )
    stages.append(
        AgentResult(
            stage="enrich",
            status=StageStatus.OK,
            message="Geo enrichment (hotspot haversine; optional OSM)",
            data={
                "has_hotspot_layer": int(work.get("has_hotspot_layer", pd.Series([0])).iloc[0])
                if "has_hotspot_layer" in work.columns
                else 0,
                "has_osm_waterway": int(work["has_osm_waterway"].max())
                if "has_osm_waterway" in work.columns
                else 0,
            },
            critical=False,
        )
    )

    hazard_ver = None
    vuln_ver = None
    use_hazard_ml = bool(use_ml or hazard_model_version)
    use_vuln_ml = bool(use_ml or vuln_model_version)

    # Baseline prior-path scores for delta (copy before ML overwrites)
    baseline_scores = {
        tier: work[f"hazard_score_{tier}"].astype(float).copy()
        if f"hazard_score_{tier}" in work.columns
        else pd.Series(0.0, index=work.index)
        for tier in profile.tier_names
    }

    if use_hazard_ml:
        if registry is None:
            raise ValueError("registry required when use_ml / hazard_model_version set")
        from packages.ml.hazard.infer import predict_hazard

        work, haz_lineage = predict_hazard(
            work, profile, registry, version=hazard_model_version
        )
        hazard_ver = haz_lineage["hazard_model_version"]
        stages.append(
            AgentResult(
                stage="predict_hazard",
                status=StageStatus.OK,
                message=f"Hazard ML version={hazard_ver}",
                data=haz_lineage,
                critical=True,
            )
        )
    else:
        stages.append(
            AgentResult(
                stage="predict_hazard",
                status=StageStatus.SKIPPED,
                message="Using ingested / proxy hazard scores (no ML)",
                critical=False,
            )
        )

    work = add_depth_columns(work, profile)
    stages.append(
        AgentResult(
            stage="depth_map",
            status=StageStatus.OK,
            message=f"Mapped scores → depth with D_max={profile.d_max_m}",
            critical=True,
        )
    )

    if use_vuln_ml:
        if registry is None:
            raise ValueError("registry required when use_ml / vuln_model_version set")
        from packages.ml.vulnerability.infer import predict_vulnerability_for_tiers

        # Keep prior damage for delta
        prior_work = add_damage_ratio_columns(work, profile.tier_names)
        for tier in profile.tier_names:
            work[f"damage_ratio_prior_{tier}"] = prior_work[f"damage_ratio_{tier}"]
        work, vuln_lineage = predict_vulnerability_for_tiers(
            work, profile, registry, version=vuln_model_version
        )
        vuln_ver = vuln_lineage["vuln_model_version"]
        stages.append(
            AgentResult(
                stage="predict_vulnerability",
                status=StageStatus.OK,
                message=f"Vulnerability ML version={vuln_ver}",
                data=vuln_lineage,
                critical=True,
            )
        )
    else:
        work = add_damage_ratio_columns(work, profile.tier_names)
        stages.append(
            AgentResult(
                stage="predict_vulnerability",
                status=StageStatus.SKIPPED,
                message="Using JRC-adapted vulnerability priors (no ML)",
                critical=False,
            )
        )

    work = add_loss_columns(work, profile.tier_names)
    tier_totals = reconcile_location_losses(work, profile.tier_names)
    stages.append(
        AgentResult(
            stage="financial",
            status=StageStatus.OK,
            message="Ground-up losses reconciled",
            data={"tier_totals": tier_totals},
            critical=True,
        )
    )

    # Baseline EP from pre-ML scores + prior vuln (for delta)
    if use_hazard_ml or use_vuln_ml:
        base = frame.copy()
        for tier in profile.tier_names:
            base[f"hazard_score_{tier}"] = baseline_scores[tier]
        base = enrich_frame(base, hotspots=hotspots, use_osm=False)
        base = add_depth_columns(base, profile)
        base = add_damage_ratio_columns(base, profile.tier_names)
        base = add_loss_columns(base, profile.tier_names)
        base_totals = reconcile_location_losses(base, profile.tier_names)
        base_tiers = build_tier_losses(base_totals, profile)
        base_aal = discrete_aal(base_tiers)
        baseline_delta = {
            "baseline_aal_kes": round(base_aal, 2),
            "tier_loss_delta_kes": {
                t: round(float(tier_totals[t] - base_totals[t]), 2) for t in profile.tier_names
            },
        }

    mean_dmg = {tier: float(work[f"damage_ratio_{tier}"].mean()) for tier in profile.tier_names}
    tier_losses = build_tier_losses(tier_totals, profile, mean_damage_by_tier=mean_dmg)
    ep_curve = build_ep_curve(tier_losses)
    aal = discrete_aal(tier_losses)
    if baseline_delta:
        baseline_delta["aal_delta_kes"] = round(aal - float(baseline_delta["baseline_aal_kes"]), 2)

    capital = compute_capital_band_from_profile(
        tier_losses, aal, float(work["tiv_kes"].sum()), profile
    )
    accum = build_accumulation_summary(work, profile.tier_names)
    stages.append(
        AgentResult(
            stage="ep_capital",
            status=StageStatus.OK,
            message="EP curve + capital band computed",
            critical=True,
        )
    )

    metrics = MetricsPayload(
        run_id=run_id,
        portfolio_id=portfolio_id,
        assumptions_version=profile.assumptions_version,
        data_labels=labels,
        n_insured_houses=int(len(work)),
        total_tiv_kes=float(work["tiv_kes"].sum()),
        location_label=location_label,
        tier_losses=tier_losses,
        ep_curve=ep_curve,
        aal_kes=round(aal, 2),
        capital_band=capital,
        hazard_model_version=hazard_ver,
        vuln_model_version=vuln_ver,
        baseline_delta=baseline_delta,
        accumulation_summary=accum,
        warnings=warnings,
    )
    insight = build_template_insight(metrics)
    stages.append(
        AgentResult(
            stage="insight_template",
            status=StageStatus.OK,
            message=f"Template insight: {insight.recommendation.value}",
            critical=False,
        )
    )
    return EngineResult(metrics=metrics, insight=insight, properties=work, stages=stages)


def default_hotspots_frame(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    hs = pd.read_csv(path)
    if "lat" not in hs.columns or "lon" not in hs.columns:
        return None
    return hs
