"""Stage 2 — optional FreeTextExposure (non-critical; schema-validated)."""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.audit_tools import append_audit
from packages.agents.tools.portfolio_tools import build_freetext_candidates
from packages.cat_core.exceptions import ExposureDQError
from packages.cat_core.types import StageStatus
from packages.llm.ollama_client import OllamaClient
from packages.security.prompt_defence import SAFE_SYSTEM_PROMPT, defend_user_text

_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def _parse_rows_from_llm(text: str) -> list[dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        if isinstance(data, dict) and "rows" in data:
            return [r for r in data["rows"] if isinstance(r, dict)]
    except json.JSONDecodeError:
        pass
    m = _JSON_ARRAY_RE.search(text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
        except json.JSONDecodeError:
            return []
    return []


def _heuristic_rows_from_text(text: str, profile) -> list[dict[str, Any]]:
    """
    Minimal non-LLM parse for demo when Ollama is down but text has structured hints.
    Expects lines like: loc_id,lat,lon,housing_class,tiv_kes
    """
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            rows.append(
                {
                    "loc_id": parts[0],
                    "lat": float(parts[1]),
                    "lon": float(parts[2]),
                    "housing_class": parts[3],
                    "tiv_kes": float(parts[4]),
                }
            )
        except ValueError:
            continue
    return rows


def node_freetext(state: AgentGraphState) -> AgentGraphState:
    if not state.get("enable_freetext"):
        return append_stage(
            state,
            stage="freetext_exposure",
            status=StageStatus.SKIPPED,
            message="Free-text exposure disabled",
            critical=False,
        )

    raw_text = state.get("freetext") or ""
    defence = defend_user_text(raw_text)
    if not defence.safe:
        audit = append_audit(
            "freetext_injection_blocked",
            {"run_id": state.get("run_id"), "reasons": defence.reasons},
        )
        out = dict(state)
        out["audit_events"] = list(state.get("audit_events") or []) + [audit]
        return append_stage(
            out,  # type: ignore[arg-type]
            stage="freetext_exposure",
            status=StageStatus.FAILED,
            message=f"Prompt injection blocked: {defence.reasons}",
            warnings=["Free-text rejected by prompt defence"],
            critical=False,
        )

    profile = state["profile"]
    rows: list[dict[str, Any]] = []
    ollama_degraded = bool(state.get("force_ollama_down") or state.get("ollama_degraded"))

    if not ollama_degraded:
        client = OllamaClient(
            host=state.get("ollama_host") or "http://localhost:11434",
            model=state.get("ollama_model") or "qwen2.5:3b-instruct",
        )
        status = client.health()
        if not status.available:
            ollama_degraded = True
        else:
            prompt = (
                "Extract flood exposure locations as a JSON array of objects with keys: "
                "loc_id, lat, lon, housing_class, tiv_kes. "
                f"Allowed housing_class values: {profile.housing_classes}. "
                "Return ONLY JSON. User description:\n"
                f"{defence.sanitized}"
            )
            result = client.chat(
                [{"role": "user", "content": prompt}],
                system=SAFE_SYSTEM_PROMPT + " Output JSON only.",
            )
            if result.degraded:
                ollama_degraded = True
            else:
                rows = _parse_rows_from_llm(result.content)

    if ollama_degraded or not rows:
        rows = _heuristic_rows_from_text(defence.sanitized, profile)

    if not rows:
        out = dict(state)
        out["ollama_degraded"] = ollama_degraded or out.get("ollama_degraded", False)
        return append_stage(
            out,  # type: ignore[arg-type]
            stage="freetext_exposure",
            status=StageStatus.WARN,
            message="No structured rows from free-text; continuing with existing portfolio",
            warnings=["freetext produced no rows"],
            critical=False,
        )

    try:
        candidates, warnings = build_freetext_candidates(rows, profile)
    except ExposureDQError as exc:
        # Schema fail rejects bad rows — do not mutate portfolio
        audit = append_audit(
            "freetext_schema_reject",
            {"run_id": state.get("run_id"), "error": str(exc), "n_candidates": len(rows)},
        )
        out = dict(state)
        out["audit_events"] = list(state.get("audit_events") or []) + [audit]
        return append_stage(
            out,  # type: ignore[arg-type]
            stage="freetext_exposure",
            status=StageStatus.FAILED,
            message=f"Free-text schema validation failed: {exc}",
            warnings=[str(exc)],
            data={"rejected": True},
            critical=False,
        )

    base = state["frame"]
    merged = pd.concat([base, candidates], ignore_index=True)
    out = dict(state)
    out["frame"] = merged
    out["ollama_degraded"] = ollama_degraded or bool(state.get("ollama_degraded"))
    audit = append_audit(
        "freetext_append",
        {"run_id": state.get("run_id"), "appended": int(len(candidates))},
    )
    out["audit_events"] = list(state.get("audit_events") or []) + [audit]
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="freetext_exposure",
        status=StageStatus.OK,
        message=f"Appended {len(candidates)} synthetic free-text rows",
        warnings=warnings,
        data={"appended": int(len(candidates)), "synthetic": True},
        critical=False,
    )
