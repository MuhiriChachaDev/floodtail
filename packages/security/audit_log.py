"""Lightweight SHA-256 append-only audit chain (full RBAC in Phase E)."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_event_payload(payload: dict[str, Any], prev_hash: str) -> str:
    blob = json.dumps({"prev": prev_hash, "payload": payload}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class AuditEvent:
    seq: int
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str
    ts: str = field(default_factory=_utc_iso)


class AuditChain:
    """In-process append-only chain; API store may wrap this."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: list[AuditEvent] = []

    def append(self, event_type: str, payload: Optional[dict[str, Any]] = None) -> AuditEvent:
        with self._lock:
            prev = self._events[-1].event_hash if self._events else self.GENESIS
            body = dict(payload or {})
            body.setdefault("event_type", event_type)
            body.setdefault("ts", _utc_iso())
            digest = hash_event_payload(body, prev)
            ev = AuditEvent(
                seq=len(self._events) + 1,
                event_type=event_type,
                payload=body,
                prev_hash=prev,
                event_hash=digest,
                ts=body["ts"],
            )
            self._events.append(ev)
            return ev

    def verify(self) -> bool:
        with self._lock:
            prev = self.GENESIS
            for ev in self._events:
                expected = hash_event_payload(ev.payload, prev)
                if expected != ev.event_hash or ev.prev_hash != prev:
                    return False
                prev = ev.event_hash
            return True

    def list_events(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


_chain: Optional[AuditChain] = None
_chain_lock = threading.Lock()


def get_audit_chain() -> AuditChain:
    global _chain
    with _chain_lock:
        if _chain is None:
            _chain = AuditChain()
        return _chain


def reset_audit_chain() -> AuditChain:
    global _chain
    with _chain_lock:
        _chain = AuditChain()
        return _chain
