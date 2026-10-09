"""Run Q&A with prompt defence + allowlist-grounded answers + RAG/memory context."""

from __future__ import annotations

from typing import Any, Optional

from packages.agents.tools.memory_tools import tool_append_chat, tool_recall, tool_remember
from packages.agents.tools.rag_tools import tool_search_knowledge
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
    tenant_id: str = "default",
    session_id: Optional[str] = None,
    use_rag: bool = True,
    use_memory: bool = True,
) -> dict[str, Any]:
    """
    Answer an underwriter question. Rejects injection; blocks invented KES.

    Optionally retrieves RAG document passages and long-term memories to ground
    qualitative context. Numeric CAT figures still come only from the allowlist.
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

    q_norm = defence.sanitized.strip().lower()
    if q_norm in {"hi", "hello", "hey", "hiya"} or q_norm.startswith(
        ("hi ", "hello ", "hey ")
    ):
        answer = (
            "Hello. I can help with Nairobi flood risk, run metrics (insured count, "
            "AAL, TIV, capital set-aside), and knowledge-base documents. "
            "Run a portfolio test first to ground money figures on your book."
        )
        sid = session_id or "default"
        _persist_turn(tenant_id, sid, defence.sanitized, answer, False)
        return {
            "ok": True,
            "blocked": False,
            "answer": answer,
            "source": "template_greeting",
            "rag_used": False,
            "memory_used": False,
        }

    sid = session_id or "default"
    rag_context = ""
    memory_context = ""
    if use_rag:
        try:
            rag = tool_search_knowledge(
                defence.sanitized, tenant_id=tenant_id, k=4
            )
            rag_context = rag.get("context") or ""
        except Exception:  # noqa: BLE001
            rag_context = ""
    if use_memory:
        try:
            mem = tool_recall(
                defence.sanitized, tenant_id=tenant_id, session_id=sid, k=4
            )
            memory_context = mem.get("context") or ""
        except Exception:  # noqa: BLE001
            memory_context = ""

    # Deterministic allowlist answers for common questions (works offline)
    q = defence.sanitized.lower()
    if "how many" in q and ("house" in q or "insured" in q or "location" in q):
        n = allowlist.get("n_insured_houses") or allowlist.get("insured_houses")
        if n is not None:
            answer = f"There are {n} insured houses/locations in this run."
            _persist_turn(tenant_id, sid, defence.sanitized, answer, use_memory)
            return {
                "ok": True,
                "blocked": False,
                "answer": answer,
                "source": "tool_allowlist",
                "rag_used": bool(rag_context),
                "memory_used": bool(memory_context),
            }
    if "set aside" in q or "capital" in q or "floor" in q:
        floor = allowlist.get("set_aside_floor_kes")
        central = allowlist.get("set_aside_central_kes")
        ceiling = allowlist.get("set_aside_ceiling_kes")
        if floor is not None and central is not None and ceiling is not None:
            answer = (
                f"Set-aside band: floor KES {floor}, central KES {central}, "
                f"ceiling KES {ceiling}."
            )
            _persist_turn(tenant_id, sid, defence.sanitized, answer, use_memory)
            return {
                "ok": True,
                "blocked": False,
                "answer": answer,
                "source": "tool_allowlist",
                "rag_used": bool(rag_context),
                "memory_used": bool(memory_context),
            }
    if ("aal" in q or "average annual" in q) and allowlist.get("aal_kes") is not None:
        answer = f"Discrete AAL is KES {allowlist.get('aal_kes')}."
        _persist_turn(tenant_id, sid, defence.sanitized, answer, use_memory)
        return {
            "ok": True,
            "blocked": False,
            "answer": answer,
            "source": "tool_allowlist",
            "rag_used": bool(rag_context),
            "memory_used": bool(memory_context),
        }
    if "tiv" in q and "document" not in q and allowlist.get("total_tiv_kes") is not None:
        answer = f"Total TIV is KES {allowlist.get('total_tiv_kes')}."
        _persist_turn(tenant_id, sid, defence.sanitized, answer, use_memory)
        return {
            "ok": True,
            "blocked": False,
            "answer": answer,
            "source": "tool_allowlist",
            "rag_used": bool(rag_context),
            "memory_used": bool(memory_context),
        }

    if force_down:
        # Still return RAG/memory qualitative context when LLM is down
        if rag_context or memory_context:
            parts = [
                "Ollama unavailable. Grounded run figures remain in /insight.",
            ]
            if rag_context:
                parts.append("Document context:\n" + rag_context[:2000])
            if memory_context:
                parts.append("Prior memory:\n" + memory_context[:1000])
            answer = "\n\n".join(parts)
            _persist_turn(tenant_id, sid, defence.sanitized, answer, use_memory)
            return {
                "ok": True,
                "blocked": False,
                "answer": answer,
                "source": "rag_memory_template",
                "rag_used": bool(rag_context),
                "memory_used": bool(memory_context),
            }
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
        "Answer the underwriter question.\n"
        "NUMERIC RULES: Money / EP / AAL / capital / TIV figures MUST come ONLY "
        f"from this allowlist: {allowlist}\n"
        "If a number is not in the allowlist, say you cannot invent it.\n"
        "You MAY use the document and memory passages below for qualitative "
        "context (cover terms, assumptions stated in files, underwriting notes). "
        "Do not treat document numbers as allowlisted CAT metrics unless they "
        "also appear in the allowlist.\n\n"
    )
    if rag_context:
        prompt += f"Retrieved document passages:\n{rag_context}\n\n"
    if memory_context:
        prompt += f"Prior session memories:\n{memory_context}\n\n"
    prompt += f"Question: {defence.sanitized}"

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
    answer = result.content.strip()
    _persist_turn(tenant_id, sid, defence.sanitized, answer, use_memory)
    # Store a short summary memory of what was asked (qualitative only)
    if use_memory:
        try:
            tool_remember(
                f"User asked about: {defence.sanitized[:200]}",
                tenant_id=tenant_id,
                session_id=sid,
                memory_type="interaction",
            )
        except Exception:  # noqa: BLE001
            pass
    return {
        "ok": True,
        "blocked": False,
        "answer": answer,
        "source": "tool_allowlist_rag" if rag_context else "tool_allowlist",
        "rag_used": bool(rag_context),
        "memory_used": bool(memory_context),
    }


def _persist_turn(
    tenant_id: str,
    session_id: str,
    question: str,
    answer: str,
    use_memory: bool,
) -> None:
    if not use_memory:
        return
    try:
        tool_append_chat(
            tenant_id=tenant_id,
            session_id=session_id,
            role="user",
            content=question,
        )
        tool_append_chat(
            tenant_id=tenant_id,
            session_id=session_id,
            role="assistant",
            content=answer,
        )
    except Exception:  # noqa: BLE001
        pass
