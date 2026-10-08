"""Stage 8 — Actionable Insight Agent (LLM + allowlist validation, template fallback)."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from packages.agents.state import AgentGraphState, append_stage
from packages.agents.tools.audit_tools import append_audit
from packages.agents.tools.math_tools import get_allowlist
from packages.cat_core.insight_template import build_template_insight
from packages.cat_core.types import InsightPackage, Recommendation, StageStatus
from packages.llm.ollama_client import OllamaClient
from packages.security.output_validation import validate_insight_fields
from packages.security.prompt_defence import SAFE_SYSTEM_PROMPT

_JSON_OBJ_RE = re.compile(r"\{[\s\S]*\}")


def _parse_insight_json(text: str) -> Optional[dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    m = _JSON_OBJ_RE.search(text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _recommendation_from_str(value: Any) -> Recommendation:
    try:
        return Recommendation(str(value).upper())
    except ValueError:
        return Recommendation.REVIEW


def build_insight_from_llm(
    metrics,
    allowlist: dict[str, Any],
    draft: dict[str, Any],
) -> InsightPackage:
    template = build_template_insight(metrics)
    band = metrics.capital_band or template.set_aside
    why = [str(x) for x in (draft.get("why") or template.why)][:3]
    next_steps = [str(x) for x in (draft.get("next_steps") or template.next_steps)][:3]
    narrative = str(draft.get("narrative") or template.narrative)
    rec = _recommendation_from_str(draft.get("recommendation") or template.recommendation.value)
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
        numbers_source="tool_allowlist",
        assumptions_version=metrics.assumptions_version,
        data_labels=metrics.data_labels,
        allowlist=allowlist,
    )


def generate_insight(
    metrics,
    *,
    ollama_host: str,
    ollama_model: str,
    force_down: bool = False,
    allowlist: Optional[dict[str, Any]] = None,
) -> tuple[InsightPackage, bool, list[str]]:
    """
    Produce InsightPackage. Returns (insight, used_template, warnings).
    Prefer a pre-built allowlist (e.g. after in-graph XAI) when provided.
    """
    base = get_allowlist(metrics)
    if allowlist:
        merged = dict(allowlist)
        merged.update(base)
        allowlist = merged
    else:
        allowlist = base
    warnings: list[str] = []

    if force_down:
        insight = build_template_insight(metrics)
        insight.allowlist = allowlist
        return insight, True, ["Ollama forced down — template insight"]

    client = OllamaClient(host=ollama_host, model=ollama_model)
    health = client.health()
    if not health.available:
        insight = build_template_insight(metrics)
        insight.allowlist = allowlist
        return insight, True, [f"Ollama down — template insight ({health.detail})"]

    user_prompt = (
        "Using ONLY the allowlisted numbers below, produce a JSON object with keys: "
        "recommendation (ACCEPT|REVIEW|ESCALATE), why (1-3 strings), "
        "next_steps (1-3 strings), narrative (short prose citing allowlisted KES only).\n"
        "If shap_hazard_top_features or shap_vulnerability_top_features are present, "
        "mention them as model drivers (not as invented money figures).\n"
        f"ALLOWLIST:\n{json.dumps(allowlist, default=str)}\n"
        "Do not invent any KES figures not present in the allowlist."
    )
    result = client.chat(
        [{"role": "user", "content": user_prompt}],
        system=SAFE_SYSTEM_PROMPT,
    )
    if result.degraded or not result.content:
        insight = build_template_insight(metrics)
        insight.allowlist = allowlist
        return insight, True, [f"Ollama chat failed — template ({result.error})"]

    draft = _parse_insight_json(result.content)
    if draft is None:
        insight = build_template_insight(metrics)
        insight.allowlist = allowlist
        return insight, True, ["LLM returned non-JSON — template insight"]

    candidate = build_insight_from_llm(metrics, allowlist, draft)
    ok, errors = validate_insight_fields(
        narrative=candidate.narrative,
        why=candidate.why,
        next_steps=candidate.next_steps,
        allowlist=allowlist,
    )
    if not ok:
        append_audit(
            "insight_validation_reject",
            {"run_id": metrics.run_id, "errors": errors},
        )
        insight = build_template_insight(metrics)
        insight.allowlist = allowlist
        return insight, True, [f"Invented KES rejected — template ({errors})"]

    return candidate, False, warnings


def node_insight(state: AgentGraphState) -> AgentGraphState:
    metrics = state.get("metrics")
    if metrics is None:
        return append_stage(
            state,
            stage="insight",
            status=StageStatus.FAILED,
            message="No metrics for insight",
            critical=False,
        )

    insight, used_template, warnings = generate_insight(
        metrics,
        ollama_host=state.get("ollama_host") or "http://localhost:11434",
        ollama_model=state.get("ollama_model") or "qwen2.5:3b-instruct",
        force_down=bool(state.get("force_ollama_down")),
        allowlist=state.get("allowlist"),
    )
    allowlist = insight.allowlist or get_allowlist(metrics)
    audit = append_audit(
        "insight_generated",
        {
            "run_id": state.get("run_id"),
            "numbers_source": insight.numbers_source,
            "recommendation": insight.recommendation.value,
            "template": used_template,
        },
    )
    out = dict(state)
    out["insight"] = insight
    out["allowlist"] = allowlist
    out["narrative"] = insight.narrative
    out["ollama_degraded"] = used_template or bool(state.get("ollama_degraded"))
    out["audit_events"] = list(state.get("audit_events") or []) + [audit]
    return append_stage(
        out,  # type: ignore[arg-type]
        stage="insight",
        status=StageStatus.OK,
        message=(
            f"{'Template' if used_template else 'LLM'} insight: {insight.recommendation.value}"
        ),
        warnings=warnings,
        data={
            "numbers_source": insight.numbers_source,
            "recommendation": insight.recommendation.value,
        },
        critical=False,
    )
