"""Portfolio / run store — in-memory with optional durable disk backend."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable
from uuid import uuid4

import pandas as pd

from packages.cat_core.types import Portfolio, RunConfig, RunRecord, utc_now


@runtime_checkable
class StoreProtocol(Protocol):
    def create_portfolio_id(self) -> str: ...
    def save_portfolio(
        self, portfolio: Portfolio, frame: Optional[pd.DataFrame] = None
    ) -> Portfolio: ...
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]: ...
    def get_portfolio_frame(self, portfolio_id: str) -> Optional[pd.DataFrame]: ...
    def list_portfolios(self, tenant_id: Optional[str] = None) -> list[Portfolio]: ...
    def delete_portfolio(self, portfolio_id: str) -> bool: ...
    def create_run_id(self) -> str: ...
    def save_run(self, run: RunRecord) -> RunRecord: ...
    def get_run(self, run_id: str) -> Optional[RunRecord]: ...
    def list_runs(
        self,
        *,
        portfolio_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[RunRecord]: ...
    def create_run(
        self, config: RunConfig, run_id: Optional[str] = None
    ) -> RunRecord: ...
    def save_run_properties(self, run_id: str, frame: pd.DataFrame) -> None: ...
    def get_run_properties(self, run_id: str) -> Optional[pd.DataFrame]: ...
    def clear(self) -> None: ...
    def stats(self) -> dict[str, Any]: ...


class InMemoryStore:
    """Thread-safe dict store with a stable get/save interface."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._portfolios: dict[str, Portfolio] = {}
        self._frames: dict[str, pd.DataFrame] = {}
        self._runs: dict[str, RunRecord] = {}
        self._run_properties: dict[str, pd.DataFrame] = {}
        self.backend: str = "memory"

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
                "backend": self.backend,
                "portfolios": len(self._portfolios),
                "frames": len(self._frames),
                "runs": len(self._runs),
                "run_properties": len(self._run_properties),
            }


class FileStore(InMemoryStore):
    """
    Durable JSON + parquet/CSV store under a root directory.

    Survives process restart. Same API as InMemoryStore.
    """

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.backend = "file"
        self.root = Path(root)
        self._portfolios_dir = self.root / "portfolios"
        self._runs_dir = self.root / "runs"
        self._portfolios_dir.mkdir(parents=True, exist_ok=True)
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    def _portfolio_meta_path(self, pid: str) -> Path:
        return self._portfolios_dir / f"{pid}.json"

    def _portfolio_frame_path(self, pid: str) -> Path:
        return self._portfolios_dir / f"{pid}.parquet"

    def _portfolio_frame_csv(self, pid: str) -> Path:
        return self._portfolios_dir / f"{pid}.csv"

    def _run_meta_path(self, rid: str) -> Path:
        return self._runs_dir / f"{rid}.json"

    def _run_props_path(self, rid: str) -> Path:
        return self._runs_dir / f"{rid}_properties.parquet"

    def _run_props_csv(self, rid: str) -> Path:
        return self._runs_dir / f"{rid}_properties.csv"

    def _write_frame(self, path_parquet: Path, path_csv: Path, frame: pd.DataFrame) -> None:
        try:
            frame.to_parquet(path_parquet, index=False)
            if path_csv.exists():
                path_csv.unlink()
        except Exception:  # noqa: BLE001 — pyarrow optional
            frame.to_csv(path_csv, index=False)

    def _read_frame(self, path_parquet: Path, path_csv: Path) -> Optional[pd.DataFrame]:
        if path_parquet.exists():
            try:
                return pd.read_parquet(path_parquet)
            except Exception:  # noqa: BLE001
                pass
        if path_csv.exists():
            return pd.read_csv(path_csv)
        return None

    def _load_from_disk(self) -> None:
        for meta in self._portfolios_dir.glob("*.json"):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                portfolio = Portfolio.model_validate(data)
                frame = self._read_frame(
                    self._portfolio_frame_path(portfolio.id),
                    self._portfolio_frame_csv(portfolio.id),
                )
                self._portfolios[portfolio.id] = portfolio
                if frame is not None:
                    self._frames[portfolio.id] = frame
            except Exception:  # noqa: BLE001
                continue
        for meta in self._runs_dir.glob("*.json"):
            if meta.name.endswith("_properties.json"):
                continue
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                run = RunRecord.model_validate(data)
                self._runs[run.id] = run
                props = self._read_frame(
                    self._run_props_path(run.id),
                    self._run_props_csv(run.id),
                )
                if props is not None:
                    self._run_properties[run.id] = props
            except Exception:  # noqa: BLE001
                continue

    def save_portfolio(
        self,
        portfolio: Portfolio,
        frame: Optional[pd.DataFrame] = None,
    ) -> Portfolio:
        saved = super().save_portfolio(portfolio, frame)
        with self._lock:
            self._portfolio_meta_path(saved.id).write_text(
                saved.model_dump_json(),
                encoding="utf-8",
            )
            if frame is not None or saved.id in self._frames:
                fr = frame if frame is not None else self._frames[saved.id]
                self._write_frame(
                    self._portfolio_frame_path(saved.id),
                    self._portfolio_frame_csv(saved.id),
                    fr,
                )
        return saved

    def delete_portfolio(self, portfolio_id: str) -> bool:
        existed = super().delete_portfolio(portfolio_id)
        for path in (
            self._portfolio_meta_path(portfolio_id),
            self._portfolio_frame_path(portfolio_id),
            self._portfolio_frame_csv(portfolio_id),
        ):
            if path.exists():
                path.unlink()
        return existed

    def save_run(self, run: RunRecord) -> RunRecord:
        saved = super().save_run(run)
        with self._lock:
            self._run_meta_path(saved.id).write_text(
                saved.model_dump_json(),
                encoding="utf-8",
            )
        return saved

    def save_run_properties(self, run_id: str, frame: pd.DataFrame) -> None:
        super().save_run_properties(run_id, frame)
        with self._lock:
            self._write_frame(
                self._run_props_path(run_id),
                self._run_props_csv(run_id),
                frame,
            )

    def clear(self) -> None:
        super().clear()
        for path in list(self._portfolios_dir.glob("*")) + list(self._runs_dir.glob("*")):
            if path.is_file():
                path.unlink()

    def stats(self) -> dict[str, Any]:
        base = super().stats()
        base["root"] = str(self.root)
        return base


_store: Optional[InMemoryStore] = None
_store_lock = threading.Lock()


def get_store() -> InMemoryStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = InMemoryStore()
        return _store


def init_store(*, backend: str = "memory", root: Optional[Path] = None) -> InMemoryStore:
    """Create / replace the process-wide store (called from app lifespan)."""
    global _store
    with _store_lock:
        if backend == "file":
            if root is None:
                raise ValueError("root required for file store backend")
            _store = FileStore(Path(root))
        else:
            _store = InMemoryStore()
        return _store


def reset_store(*, backend: str = "memory", root: Optional[Path] = None) -> InMemoryStore:
    """Replace the process-wide store (tests default to memory)."""
    return init_store(backend=backend, root=root)
