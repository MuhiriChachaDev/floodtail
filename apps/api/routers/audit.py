"""Audit chain routes — Phase E."""

from __future__ import annotations

from fastapi import APIRouter, Query

from apps.api.deps import ContextDep, enforce_permission
from packages.security.audit_log import get_audit_chain

router = APIRouter()


@router.get("/audit")
def get_audit(
    ctx: ContextDep,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    enforce_permission(ctx, "audit:read")
    chain = get_audit_chain()
    events = chain.list_events()
    page = events[offset : offset + limit]
    return {
        "chain_valid": chain.verify(),
        "total": len(events),
        "offset": offset,
        "limit": limit,
        "events": [
            {
                "seq": e.seq,
                "event_type": e.event_type,
                "ts": e.ts,
                "prev_hash": e.prev_hash,
                "event_hash": e.event_hash,
                "payload": e.payload,
            }
            for e in page
        ],
    }
