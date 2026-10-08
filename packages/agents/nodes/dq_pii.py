"""Stage 1 — DQ / PII hash-mask / geocode assist (critical)."""

from __future__ import annotations

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.audit_tools import append_audit
from packages.cat_core.exceptions import ExposureDQError
from packages.cat_core.exposure import validate_and_normalize
from packages.cat_core.types import StageStatus
from packages.security.encryption import hash_token

_PII_COLS = ("owner_name", "email", "phone", "national_id", "policyholder")


def node_dq_pii(state: AgentGraphState) -> AgentGraphState:
    profile = state["profile"]
    frame = state["frame"]
    location_label = state.get("location_label") or "unknown"
    try:
        cleaned, stats, warnings = validate_and_normalize(
            frame,
            profile,
            location_label=location_label,
            source=str(frame["source"].iloc[0]) if "source" in frame.columns else "run",
            force_synthetic=True,
        )
    except ExposureDQError as exc:
        return append_stage(
            state,
            stage="dq_pii",
            status=StageStatus.FAILED,
            message=str(exc),
            critical=True,
        )

    pii_hashed = 0
    for col in _PII_COLS:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].astype(str).map(
                lambda v: hash_token(v) if v and v.lower() not in ("nan", "none") else ""
            )
            pii_hashed += 1
            warnings.append(f"PII column {col} hashed")

    audit = append_audit(
        "dq_pii",
        {
            "run_id": state.get("run_id"),
            "n_rows": int(len(cleaned)),
            "pii_cols_hashed": pii_hashed,
        },
    )
    out = dict(state)
    out["frame"] = cleaned
    out["location_label"] = stats.location_label or location_label
    events = list(state.get("audit_events") or [])
    events.append(audit)
    out["audit_events"] = events
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="dq_pii",
        status=StageStatus.OK,
        message=f"DQ ok; {stats.n_insured_houses} locations; PII hashed={pii_hashed}",
        warnings=warnings,
        data={"ingest_stats": stats.model_dump()},
        critical=True,
    )
