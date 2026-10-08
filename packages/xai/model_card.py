"""Refresh model-card fields from registry TRAINING_CARD + metrics."""

from __future__ import annotations

from typing import Any, Literal, Optional

from packages.ml.registry import ModelRegistry, ModelType


def build_model_card(
    registry: ModelRegistry,
    model_type: ModelType,
    *,
    version: Optional[str] = None,
) -> dict[str, Any]:
    """Assemble an API-ready model card from registry artifacts."""
    ver = version or registry.get_pinned(model_type)
    if ver is None:
        raise FileNotFoundError(f"No pinned {model_type} model")
    if not registry.verify_integrity(model_type, ver):
        raise ValueError(f"Integrity check failed for {model_type}/{ver}")

    _, _, entry = registry.load(model_type, ver)
    card = dict(entry.training_card or {})
    metrics = dict(entry.metrics or {})
    params = dict(entry.params or {})

    return {
        "model_type": model_type,
        "version": entry.version,
        "sha256": entry.sha256,
        "pinned": entry.pinned,
        "feature_schema": entry.feature_schema,
        "metrics": metrics,
        "params": params,
        "purpose": card.get("purpose")
        or f"Predict {'hazard scores' if model_type == 'hazard' else 'damage ratios'} for flood CAT.",
        "intended_use": card.get("intended_use")
        or "Prototype reinsurance underwriting decision support (Nairobi starter / location-flexible).",
        "training_data": card.get("data_manifest") or card.get("training_data") or {},
        "label_meta": card.get("label_meta") or {},
        "limitations": card.get("limitations")
        or [
            "Synthetic / proxy labels — not gauge-validated floods.",
            "SHAP explains the model, not physical flood causation.",
            "Proxy hotspot coverage incomplete (~12/24 named hotspots).",
        ],
        "ethics": card.get("ethics")
        or "Do not use as sole basis for binding reinsurance without actuarial review.",
        "tuning_enabled": bool(card.get("tuning_enabled", params.get("tuning_enabled", False))),
        "feature_schema_version": entry.feature_schema.get("version"),
        "raw_training_card": card,
    }


def list_model_cards(registry: ModelRegistry) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for mtype in ("hazard", "vulnerability"):
        pinned = registry.get_pinned(mtype)  # type: ignore[arg-type]
        if not pinned:
            continue
        try:
            cards.append(build_model_card(registry, mtype, version=pinned))  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            cards.append({"model_type": mtype, "error": str(exc)})
    return cards
