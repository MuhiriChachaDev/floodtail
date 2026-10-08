"""Portfolio ingest routes."""

from __future__ import annotations

import io
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from apps.api.deps import (
    ContextDep,
    SettingsDep,
    StoreDep,
    enforce_permission,
    enforce_tenant,
)
from packages.agents.tools.audit_tools import append_audit
from packages.agents.tools.portfolio_tools import schema_map
from packages.cat_core.exceptions import ExposureDQError
from packages.cat_core.exposure import (
    builtin_nairobi_path,
    default_data_labels,
    load_exposure_csv,
    validate_and_normalize,
)
from packages.cat_core.raster_hazard import fill_hazard_from_data_dir
from packages.cat_core.types import Portfolio

router = APIRouter()


@router.post("/portfolios")
async def create_portfolio(
    settings: SettingsDep,
    store: StoreDep,
    ctx: ContextDep,
    source: str = Form(default="builtin_nairobi"),
    location_label: Optional[str] = Form(default=None),
    name: Optional[str] = Form(default=None),
    sample_rasters: Optional[bool] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
) -> dict:
    """
    Create a portfolio from the built-in Nairobi starter kit or an uploaded CSV.

    Form fields:
    - source: `builtin_nairobi` | `upload`
    - location_label: optional label (default Nairobi / upload)
    - name: optional display name
    - sample_rasters: when true (default from settings), fill missing hazard_score_*
      from GeoTIFFs under Nairobi_Data (requires rasterio)
    - file: CSV when source=upload

    Upload CSVs are schema-mapped (lat/longitude/tiv/occupancy aliases accepted).
    """
    enforce_permission(ctx, "portfolio:write")
    profile = settings.assumptions_profile()
    pid = store.create_portfolio_id()
    column_mapping: dict = {}

    try:
        if source == "builtin_nairobi":
            path = builtin_nairobi_path(settings.nairobi_data_dir)
            raw = load_exposure_csv(path)
            loc = location_label or "Nairobi County"
            src = "builtin_nairobi"
            display = name or "Nairobi built-in (synthetic)"
        elif source == "upload":
            if file is None:
                raise HTTPException(status_code=400, detail="file required when source=upload")
            max_bytes = settings.max_upload_mb * 1024 * 1024
            data = await file.read()
            if len(data) > max_bytes:
                raise HTTPException(status_code=400, detail=f"Upload exceeds {settings.max_upload_mb} MB")
            raw = pd.read_csv(io.BytesIO(data))
            loc = location_label or "uploaded"
            src = f"upload:{file.filename or 'portfolio.csv'}"
            display = name or (file.filename or "uploaded portfolio")
        else:
            raise HTTPException(
                status_code=400,
                detail="source must be builtin_nairobi or upload",
            )

        # Always schema-map so foreign CSVs (latitude/tiv_usd/occupancy) work
        mapped, column_mapping, map_warnings = schema_map(raw)
        frame, stats, warnings = validate_and_normalize(
            mapped,
            profile,
            location_label=loc,
            source=src,
            force_synthetic=True,
        )
        warnings = list(map_warnings) + list(warnings)

        do_sample = (
            settings.sample_rasters_on_upload
            if sample_rasters is None
            else bool(sample_rasters)
        )
        if do_sample and any("HAZARD_ZERO_FILL" in w for w in warnings):
            frame, raster_warns = fill_hazard_from_data_dir(
                frame,
                settings.nairobi_data_dir,
                list(profile.tier_names),
                only_missing_or_zero=True,
            )
            warnings.extend(raster_warns)
            # Recompute stats after scores change
            from packages.cat_core.exposure import compute_ingest_stats

            stats = compute_ingest_stats(frame, location_label=loc, source=src)
    except ExposureDQError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to load portfolio: {exc}") from exc

    labels = default_data_labels(profile, synthetic=stats.synthetic, notes=warnings)
    portfolio = Portfolio(
        id=pid,
        tenant_id=ctx.tenant_id,
        name=display,
        location_label=loc,
        source=src,
        synthetic=stats.synthetic,
        n_rows=stats.n_insured_houses,
        ingest_stats=stats,
        assumptions_version=profile.assumptions_version,
        data_labels=labels,
        extra={"warnings": warnings, "column_mapping": column_mapping},
    )
    store.save_portfolio(portfolio, frame)
    append_audit(
        "portfolio_ingest",
        {
            "portfolio_id": pid,
            "source": src,
            "n_rows": stats.n_insured_houses,
            "actor": ctx.actor,
            "role": ctx.role,
            "tenant_id": ctx.tenant_id,
            "column_mapping": column_mapping,
        },
    )
    return {
        "portfolio": portfolio.model_dump(mode="json"),
        "warnings": warnings,
        "column_mapping": column_mapping,
    }


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str, store: StoreDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "portfolio:read")
    portfolio = store.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="portfolio not found")
    enforce_tenant(portfolio, ctx)
    return {"portfolio": portfolio.model_dump(mode="json")}


@router.get("/portfolios/{portfolio_id}/properties")
def get_portfolio_properties(
    portfolio_id: str,
    store: StoreDep,
    ctx: ContextDep,
    limit: int = Query(default=600, ge=1, le=600),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Raw exposure rows (lat/lon/TIV/hazard) for map & DQ — works before a run."""
    enforce_permission(ctx, "portfolio:read")
    portfolio = store.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="portfolio not found")
    enforce_tenant(portfolio, ctx)
    frame = store.get_portfolio_frame(portfolio_id)
    if frame is None or frame.empty:
        raise HTTPException(status_code=404, detail="portfolio rows not available")

    total = len(frame)
    page = frame.iloc[offset : offset + limit]
    cols = [
        c
        for c in [
            "loc_id",
            "lat",
            "lon",
            "housing_class",
            "tiv_kes",
            "synthetic",
            "hazard_score_common",
            "hazard_score_occasional",
            "hazard_score_moderate",
            "hazard_score_severe",
            "hazard_score_extreme",
        ]
        if c in page.columns
    ]
    return {
        "portfolio_id": portfolio_id,
        "location_label": portfolio.location_label,
        "total": total,
        "offset": offset,
        "limit": limit,
        "bbox": portfolio.ingest_stats.bbox if portfolio.ingest_stats else None,
        "properties": page[cols].to_dict(orient="records"),
    }


@router.get("/portfolios")
def list_portfolios(store: StoreDep, ctx: ContextDep) -> dict:
    enforce_permission(ctx, "portfolio:read")
    items = store.list_portfolios(tenant_id=ctx.tenant_id)
    return {"portfolios": [p.model_dump(mode="json") for p in items]}
