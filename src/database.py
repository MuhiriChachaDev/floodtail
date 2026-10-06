"""FLOODTAIL — SQLite metadata database manager.

Handles creation, migration, and access to the governance/metadata
database.  Analytical data lives in Parquet; SQLite stores only
metadata, run registry, ingestion records, quality issues, schema
mappings, and dataset versions.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from src.exceptions import DatabaseError
from src.logging_config import get_logger

logger = get_logger("database")

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id           TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL,
    model_version    TEXT,
    data_version     TEXT,
    status           TEXT NOT NULL DEFAULT 'PENDING',
    source_file      TEXT,
    row_count        INTEGER DEFAULT 0,
    valid_row_count  INTEGER DEFAULT 0,
    invalid_row_count INTEGER DEFAULT 0,
    quality_score    REAL
);

CREATE TABLE IF NOT EXISTS ingestion_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    source_filename  TEXT NOT NULL,
    source_type      TEXT,
    file_size        INTEGER,
    ingested_at      TEXT NOT NULL,
    schema_status    TEXT,
    mapping_status   TEXT,
    record_count     INTEGER DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    policy_id        TEXT,
    issue_type       TEXT NOT NULL,
    severity         TEXT NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR','CRITICAL')),
    field            TEXT,
    value            TEXT,
    message          TEXT,
    detector         TEXT,
    status           TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','REVIEWED','RESOLVED','EXCLUDED')),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS schema_mappings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    source_column    TEXT NOT NULL,
    target_field     TEXT,
    mapping_method   TEXT,
    confidence       REAL,
    status           TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS portfolio_versions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    dataset_path     TEXT NOT NULL,
    dataset_hash     TEXT,
    record_count     INTEGER DEFAULT 0,
    created_at       TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    policy_id        TEXT NOT NULL,
    user             TEXT NOT NULL,
    recommendation   TEXT NOT NULL,
    final_decision   TEXT NOT NULL,
    original_premium REAL NOT NULL,
    new_premium      REAL NOT NULL,
    reason           TEXT,
    model_version    TEXT NOT NULL,
    data_version     TEXT NOT NULL,
    decision_hash    TEXT NOT NULL,
    previous_hash    TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id);
CREATE INDEX IF NOT EXISTS idx_dqi_run_id ON data_quality_issues(run_id);
CREATE INDEX IF NOT EXISTS idx_dqi_policy_id ON data_quality_issues(policy_id);
CREATE INDEX IF NOT EXISTS idx_sm_run_id ON schema_mappings(run_id);
CREATE INDEX IF NOT EXISTS idx_pv_run_id ON portfolio_versions(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_run_id ON audit_log(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_policy_id ON audit_log(policy_id);
"""


# ---------------------------------------------------------------------------
# Database manager
# ---------------------------------------------------------------------------

def _default_db_path() -> Path:
    """Return the default database path."""
    return Path(__file__).resolve().parent.parent / "data" / "floodtail.db"


def initialize_database(db_path: Optional[str | Path] = None) -> Path:
    """Create the database and all tables if they don't exist.

    Args:
        db_path: Explicit path.  Defaults to ``data/floodtail.db``.

    Returns:
        The resolved database path.
    """
    path = Path(db_path) if db_path else _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(str(path)) as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.executescript(_INDEX_SQL)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Failed to initialize database: {exc}") from exc

    logger.info("Database initialized at %s", path)
    return path


@contextmanager
def get_connection(
    db_path: Optional[str | Path] = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection as a context manager.

    Args:
        db_path: Explicit path.  Defaults to ``data/floodtail.db``.

    Yields:
        A ``sqlite3.Connection`` with row_factory set to ``sqlite3.Row``.
    """
    path = Path(db_path) if db_path else _default_db_path()
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Run CRUD
# ---------------------------------------------------------------------------

def create_run(
    db_path: str | Path,
    *,
    run_id: str,
    model_version: str = "",
    data_version: str = "",
    status: str = "PENDING",
    source_file: str = "",
) -> None:
    """Insert a new run record."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO runs
               (run_id, created_at, model_version, data_version, status, source_file)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (run_id, now, model_version, data_version, status, source_file),
        )


def update_run(db_path: str | Path, run_id: str, **fields: Any) -> None:
    """Update selected fields on an existing run."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [run_id]
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE runs SET {set_clause} WHERE run_id = ?",  # noqa: S608
            values,
        )


def get_run(db_path: str | Path, run_id: str) -> Optional[dict]:
    """Retrieve a run record by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Ingestion records
# ---------------------------------------------------------------------------

def save_ingestion_record(
    db_path: str | Path,
    *,
    run_id: str,
    source_filename: str,
    source_type: str,
    file_size: int,
    schema_status: str = "",
    mapping_status: str = "",
    record_count: int = 0,
) -> None:
    """Insert an ingestion-record row."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO ingestion_records
               (run_id, source_filename, source_type, file_size,
                ingested_at, schema_status, mapping_status, record_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, source_filename, source_type, file_size,
             now, schema_status, mapping_status, record_count),
        )


# ---------------------------------------------------------------------------
# Quality issues
# ---------------------------------------------------------------------------

def save_quality_issues(
    db_path: str | Path,
    issues: list[dict],
) -> None:
    """Batch-insert quality-issue rows.

    Each dict must contain: run_id, policy_id, issue_type, severity,
    field, value, message, detector, status.
    """
    if not issues:
        return
    with get_connection(db_path) as conn:
        conn.executemany(
            """INSERT INTO data_quality_issues
               (run_id, policy_id, issue_type, severity, field, value,
                message, detector, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    i["run_id"], i.get("policy_id", ""),
                    i["issue_type"], i["severity"],
                    i.get("field", ""), i.get("value", ""),
                    i.get("message", ""), i.get("detector", ""),
                    i.get("status", "OPEN"),
                )
                for i in issues
            ],
        )


def get_quality_issues(
    db_path: str | Path,
    run_id: str,
) -> list[dict]:
    """Retrieve all quality issues for a run."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM data_quality_issues WHERE run_id = ?", (run_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Schema mappings
# ---------------------------------------------------------------------------

def save_schema_mappings(
    db_path: str | Path,
    mappings: list[dict],
) -> None:
    """Batch-insert schema-mapping rows."""
    if not mappings:
        return
    with get_connection(db_path) as conn:
        conn.executemany(
            """INSERT INTO schema_mappings
               (run_id, source_column, target_field, mapping_method,
                confidence, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    m["run_id"], m["source_column"],
                    m.get("target_field", ""), m.get("mapping_method", ""),
                    m.get("confidence", 0.0), m.get("status", ""),
                )
                for m in mappings
            ],
        )


# ---------------------------------------------------------------------------
# Portfolio versions
# ---------------------------------------------------------------------------

def save_portfolio_version(
    db_path: str | Path,
    *,
    run_id: str,
    dataset_path: str,
    dataset_hash: str,
    record_count: int,
    created_at: Optional[datetime] = None,
) -> int:
    """Register a produced portfolio dataset and return inserted ID."""
    now = (created_at or datetime.now(timezone.utc)).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO portfolio_versions
               (run_id, dataset_path, dataset_hash, record_count, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, str(dataset_path), dataset_hash, record_count, now),
        )
        return cursor.lastrowid or 0


def get_portfolio_versions(
    db_path: str | Path,
    run_id: Optional[str] = None,
) -> list[dict]:
    """Retrieve portfolio version records, optionally filtered by run_id."""
    with get_connection(db_path) as conn:
        if run_id:
            rows = conn.execute(
                "SELECT * FROM portfolio_versions WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM portfolio_versions ORDER BY id DESC"
            ).fetchall()
    return [dict(r) for r in rows]


class DatabaseManager:
    """Object-oriented interface to the FLOODTAIL metadata SQLite database."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = initialize_database(db_path)

    def create_run(
        self,
        run_id: str,
        model_version: str = "",
        data_version: str = "",
        status: str = "PENDING",
        source_file: str = "",
    ) -> None:
        create_run(
            self.db_path,
            run_id=run_id,
            model_version=model_version,
            data_version=data_version,
            status=status,
            source_file=source_file,
        )

    def update_run(self, run_id: str, **fields: Any) -> None:
        update_run(self.db_path, run_id, **fields)

    def get_run(self, run_id: str) -> Optional[dict]:
        return get_run(self.db_path, run_id)

    def record_ingestion(
        self,
        run_id: str,
        source_filename: str,
        source_type: str,
        file_size: int,
        schema_status: str = "",
        mapping_status: str = "",
        record_count: int = 0,
    ) -> None:
        save_ingestion_record(
            self.db_path,
            run_id=run_id,
            source_filename=source_filename,
            source_type=source_type,
            file_size=file_size,
            schema_status=schema_status,
            mapping_status=mapping_status,
            record_count=record_count,
        )

    def record_quality_issues(self, issues: list[dict]) -> None:
        save_quality_issues(self.db_path, issues)

    def get_quality_issues(self, run_id: str) -> list[dict]:
        return get_quality_issues(self.db_path, run_id)

    def record_schema_mappings(self, mappings: list[dict]) -> None:
        save_schema_mappings(self.db_path, mappings)

    def record_portfolio_version(
        self,
        run_id: str,
        dataset_path: str,
        dataset_hash: str,
        record_count: int,
        created_at: Optional[datetime] = None,
    ) -> int:
        return save_portfolio_version(
            self.db_path,
            run_id=run_id,
            dataset_path=dataset_path,
            dataset_hash=dataset_hash,
            record_count=record_count,
            created_at=created_at,
        )

    def get_portfolio_versions(self, run_id: Optional[str] = None) -> list[dict]:
        return get_portfolio_versions(self.db_path, run_id)

