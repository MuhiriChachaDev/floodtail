"""In-memory portfolio / run store (Phase A). Swap for Postgres later."""

from __future__ import annotations

import threading
from typing import Any, Optional
from uuid import uuid4

import pandas as pd

from packages.cat_core.types import Portfolio, RunConfig, RunRecord, utc_now


class InMemoryStore:
    """Thread-safe dict store with a stable get/save interface."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._portfolios: dict[str, Portfolio] = {}
        self._frames: dict[str, pd.DataFrame] = {}
        self._runs: dict[str, RunRecord] = {}
        self._run_properties: dict[str, pd.DataFrame] = {}

    # --- portfolios ---------------------------------------------------------

    def create_portfolio_id(self) -> str:
        return str(uuid4())

    def save_portfolio(
        self,
        portfolio: Portfolio,
        frame: Optional[pd.DataFrame] = None,
    ) -> Portfolio:
        with self._lock:
            self._portfolios[portfolio.id] = portfolio.model_copy(deep=True)
            if frame is not None:
                self._frames[portfolio.id] = frame.copy()
            return self._portfolios[portfolio.id]

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        with self._lock:
            p = self._portfolios.get(portfolio_id)
            return p.model_copy(deep=True) if p else None

    def get_portfolio_frame(self, portfolio_id: str) -> Optional[pd.DataFrame]:
        with self._lock:
            frame = self._frames.get(portfolio_id)
            return frame.copy() if frame is not None else None

    def list_portfolios(self, tenant_id: Optional[str] = None) -> list[Portfolio]:
        with self._lock:
            items = list(self._portfolios.values())
            if tenant_id is not None:
                items = [p for p in items if p.tenant_id == tenant_id]
            return [p.model_copy(deep=True) for p in items]

    def delete_portfolio(self, portfolio_id: str) -> bool:
        with self._lock:
            existed = portfolio_id in self._portfolios
            self._portfolios.pop(portfolio_id, None)
            self._frames.pop(portfolio_id, None)
            return existed

    # --- runs ---------------------------------------------------------------

    def create_run_id(self) -> str:
        return str(uuid4())

    def save_run(self, run: RunRecord) -> RunRecord:
        with self._lock:
            run.updated_at = utc_now()
            self._runs[run.id] = run.model_copy(deep=True)
            return self._runs[run.id]

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            r = self._runs.get(run_id)
            return r.model_copy(deep=True) if r else None

    def list_runs(
        self,
        *,
        portfolio_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[RunRecord]:
        with self._lock:
            items = list(self._runs.values())
            if portfolio_id is not None:
                items = [r for r in items if r.portfolio_id == portfolio_id]
            if tenant_id is not None:
                items = [r for r in items if r.tenant_id == tenant_id]
            return [r.model_copy(deep=True) for r in items]

    def create_run(self, config: RunConfig, run_id: Optional[str] = None) -> RunRecord:
        rid = run_id or self.create_run_id()
        record = RunRecord(
            id=rid,
            portfolio_id=config.portfolio_id,
            tenant_id=config.tenant_id,
            status="PENDING",
            config=config,
        )
        return self.save_run(record)

    def save_run_properties(self, run_id: str, frame: pd.DataFrame) -> None:
        with self._lock:
            self._run_properties[run_id] = frame.copy()

    def get_run_properties(self, run_id: str) -> Optional[pd.DataFrame]:
        with self._lock:
            frame = self._run_properties.get(run_id)
            return frame.copy() if frame is not None else None

    def clear(self) -> None:
        """Test helper — wipe all state."""
        with self._lock:
            self._portfolios.clear()
            self._frames.clear()
            self._runs.clear()
            self._run_properties.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "portfolios": len(self._portfolios),
                "frames": len(self._frames),
                "runs": len(self._runs),
                "run_properties": len(self._run_properties),
            }


_store: Optional[InMemoryStore] = None
_store_lock = threading.Lock()


def get_store() -> InMemoryStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = InMemoryStore()
        return _store


def reset_store() -> InMemoryStore:
    """Replace the process-wide store (tests)."""
    global _store
    with _store_lock:
        _store = InMemoryStore()
        return _store
