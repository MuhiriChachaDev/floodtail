"""Run Q&A with prompt defence + allowlist-grounded answers."""

from __future__ import annotations

from typing import Any

from packages.llm.ollama_client import OllamaClient
from packages.security.output_validation import numbers_in_allowlist, reject_invented_kes
from packages.security.prompt_defence import SAFE_SYSTEM_PROMPT, defend_user_text


def answer_query(
    question: str,
    allowlist: dict[str, Any],
    *,
    ollama_host: str,
    ollama_model: str,
    force_down: bool = False,
) -> dict[str, Any]:
    """
    Answer an underwriter question. Rejects injection; blocks invented KES.
    """
    defence = defend_user_text(question)
    if not defence.safe:
        return {
            "ok": False,
            "blocked": True,
            "reason": "prompt_injection",
            "detail": defence.reasons,
            "answer": "",
        }

    # Deterministic allowlist answers for common questions (works offline)
    q = defence.sanitized.lower()
    if "how many" in q and ("house" in q or "insured" in q or "location" in q):
        n = allowlist.get("n_insured_houses") or allowlist.get("insured_houses")
        return {
            "ok": True,
            "blocked": False,
            "answer": f"There are {n} insured houses/locations in this run.",
            "source": "tool_allowlist",
        }
    if "set aside" in q or "capital" in q or "floor" in q:
        floor = allowlist.get("set_aside_floor_kes")
        central = allowlist.get("set_aside_central_kes")
        ceiling = allowlist.get("set_aside_ceiling_kes")
        return {
            "ok": True,
            "blocked": False,
            "answer": (
                f"Set-aside band: floor KES {floor}, central KES {central}, "
                f"ceiling KES {ceiling}."
            ),
            "source": "tool_allowlist",
        }
    if "aal" in q or "average annual" in q:
        return {
            "ok": True,
            "blocked": False,
            "answer": f"Discrete AAL is KES {allowlist.get('aal_kes')}.",
            "source": "tool_allowlist",
        }
    if "tiv" in q:
        return {
            "ok": True,
            "blocked": False,
            "answer": f"Total TIV is KES {allowlist.get('total_tiv_kes')}.",
            "source": "tool_allowlist",
        }

    if force_down:
        return {
            "ok": True,
            "blocked": False,
            "answer": (
                "Ollama unavailable. Use metrics/insight endpoints for grounded figures. "
                f"Allowlisted keys: {sorted(k for k in allowlist if not isinstance(allowlist[k], (dict, list)))[:12]}"
            ),
            "source": "template",
        }

    client = OllamaClient(host=ollama_host, model=ollama_model)
    if not client.health().available:
        return {
            "ok": True,
            "blocked": False,
            "answer": (
                "Ollama unavailable. Grounded figures remain in /insight and /metrics."
            ),
            "source": "template",
            "degraded": True,
        }

    prompt = (
        f"Answer the underwriter question using ONLY this allowlist: {allowlist}\n"
        f"Question: {defence.sanitized}\n"
        "If the answer needs a number not in the allowlist, say you cannot invent it."
    )
    result = client.chat(
        [{"role": "user", "content": prompt}],
        system=SAFE_SYSTEM_PROMPT,
    )
    if result.degraded or not result.content:
        return {
            "ok": True,
            "blocked": False,
            "answer": "Unable to generate narrative answer; see /insight for grounded figures.",
            "source": "template",
            "degraded": True,
        }

    err = reject_invented_kes(result.content, allowlist)
    if err:
        return {
            "ok": False,
            "blocked": False,
            "reason": "invented_kes",
            "detail": err,
            "answer": "Answer rejected: invented money figures. See /insight allowlist.",
            "source": "rejected",
        }
    ok, _ = numbers_in_allowlist(result.content, allowlist)
    if not ok:
        return {
            "ok": False,
            "blocked": False,
            "reason": "invented_kes",
            "answer": "Answer rejected: invented money figures.",
            "source": "rejected",
        }
    return {
        "ok": True,
        "blocked": False,
        "answer": result.content.strip(),
        "source": "tool_allowlist",
    }
