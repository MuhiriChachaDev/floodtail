"""Briefing / narrative helpers (validated against allowlist)."""

from __future__ import annotations

from typing import Any

from packages.cat_core.insight_template import build_template_insight
from packages.cat_core.types import MetricsPayload
from packages.llm.ollama_client import OllamaClient
from packages.security.output_validation import numbers_in_allowlist
from packages.security.prompt_defence import SAFE_SYSTEM_PROMPT


def generate_narrative(
    metrics: MetricsPayload,
    allowlist: dict[str, Any],
    *,
    ollama_host: str,
    ollama_model: str,
    force_down: bool = False,
) -> tuple[str, str]:
    """
    Return (narrative, source) where source is tool_allowlist|template.
    """
    template = build_template_insight(metrics).narrative
    if force_down:
        return template, "template"

    client = OllamaClient(host=ollama_host, model=ollama_model)
    if not client.health().available:
        return template, "template"

    prompt = (
        "Write a 3-sentence underwriter briefing using ONLY these allowlisted numbers. "
        "Cite KES figures exactly as given. No invented figures.\n"
        f"ALLOWLIST: {allowlist}"
    )
    result = client.chat(
        [{"role": "user", "content": prompt}],
        system=SAFE_SYSTEM_PROMPT,
    )
    if result.degraded or not result.content:
        return template, "template"

    ok, _ = numbers_in_allowlist(result.content, allowlist)
    if not ok:
        return template, "template"
    return result.content.strip(), "tool_allowlist"
