"""Audit append tool for agent stages."""

from __future__ import annotations

from typing import Any, Optional

from packages.security.audit_log import AuditEvent, get_audit_chain


def append_audit(
    event_type: str,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Append an event to the process-wide audit chain."""
    ev: AuditEvent = get_audit_chain().append(event_type, payload)
    return {
        "seq": ev.seq,
        "event_type": ev.event_type,
        "event_hash": ev.event_hash,
        "prev_hash": ev.prev_hash,
        "ts": ev.ts,
        "payload": ev.payload,
    }


try:
    from langchain_core.tools import tool

    @tool
    def append_audit_tool(event_type: str, detail: str = "") -> str:
        """Append a short audit event (event_type + detail string)."""
        ev = append_audit(event_type, {"detail": detail})
        return f"seq={ev['seq']} hash={ev['event_hash'][:12]}"

except ImportError:  # pragma: no cover
    pass
