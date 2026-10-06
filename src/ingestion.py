"""FLOODTAIL — Ingestion engine for diverse reinsurance portfolio file formats.

Supports CSV, Parquet, Excel (.xlsx, .xls), and JSON/NDJSON.
Performs SHA-256 fingerprinting, format detection, size validation,
column mapping integration, and metadata recording.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Union

import pandas as pd

from src.exceptions import IngestionError
from src.logging_config import get_logger
from src.schema_mapper import MappingPlan, SchemaMapper

logger = get_logger("ingestion")

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB default safety ceiling


@dataclass
class IngestionResult:
    """Encapsulates the raw and mapped ingestion results."""

    dataframe: pd.DataFrame
    source_path: Path
    file_type: str
    file_size_bytes: int
    file_hash_sha256: str
    total_rows_read: int
    mapping_plan: MappingPlan
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class IngestionEngine:
    """Engine for reading, inspecting, and standardizing incoming portfolio data files."""

    def __init__(
        self,
        schema_mapper: Optional[SchemaMapper] = None,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        self.schema_mapper = schema_mapper or SchemaMapper()
        self.max_file_size_bytes = max_file_size_bytes

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA-256 hash of a file for provenance and auditability."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def detect_file_type(self, file_path: Path) -> str:
        """Identify file format from extension and signature."""
        suffix = file_path.suffix.lower()
        if suffix in {".csv", ".txt", ".tsv"}:
            return "csv"
        elif suffix in {".parquet", ".pq"}:
            return "parquet"
        elif suffix in {".xlsx", ".xls"}:
            return "excel"
        elif suffix in {".json", ".ndjson", ".jsonl"}:
            return "json"
        else:
            raise IngestionError(
                f"Unsupported file format '{suffix}' for file: {file_path.name}. "
                "Supported formats are CSV, Parquet, Excel (.xlsx, .xls), and JSON/NDJSON."
            )

    def read_raw_dataframe(self, file_path: Path, file_type: Optional[str] = None) -> pd.DataFrame:
        """Read raw file into a pandas DataFrame without column mapping."""
        if not file_path.exists():
            raise IngestionError(f"Input file does not exist: {file_path}")

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise IngestionError(f"Input file is completely empty (0 bytes): {file_path.name}")

        if file_size > self.max_file_size_bytes:
            raise IngestionError(
                f"Input file size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit "
                f"({self.max_file_size_bytes / (1024*1024):.2f} MB)."
            )

        f_type = file_type or self.detect_file_type(file_path)

        try:
            if f_type == "csv":
                try:
                    df = pd.read_csv(file_path, encoding="utf-8", dtype=str)
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding="latin1", dtype=str)
            elif f_type == "parquet":
                df = pd.read_parquet(file_path)
                df = df.astype(str)
            elif f_type == "excel":
                df = pd.read_excel(file_path, dtype=str)
            elif f_type == "json":
                try:
                    df = pd.read_json(file_path, lines=True, dtype=False)
                except Exception:
                    df = pd.read_json(file_path, dtype=False)
                df = df.astype(str)
            else:
                raise IngestionError(f"Unhandled file type: {f_type}")
        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError(f"Failed to read file '{file_path.name}': {exc}") from exc

        if df.empty:
            raise IngestionError(f"Input file contains no data rows: {file_path.name}")

        return df

    def ingest_file(
        self,
        file_path: Union[str, Path],
        apply_mapping: bool = True,
        strict_mapping: bool = False,
    ) -> IngestionResult:
        """Ingest a portfolio file, compute hash, map schema, and return standard IngestionResult.

        Args:
            file_path: Path to the target portfolio file.
            apply_mapping: If True, columns are renamed to canonical schema.
            strict_mapping: If True, raises IngestionError if any required field is missing.

        Returns:
            IngestionResult containing dataframe, mapping plan, and provenance metadata.
        """
        path = Path(file_path)
        if not path.exists():
            raise IngestionError(f"Input file does not exist: {path}")

        file_type = self.detect_file_type(path)
        file_size = path.stat().st_size
        file_hash = self.compute_sha256(path)

        logger.info("Ingesting file: %s (type=%s, size=%d bytes)", path.name, file_type, file_size)

        df = self.read_raw_dataframe(path, file_type=file_type)
        total_rows = len(df)

        mapping_plan = self.schema_mapper.create_mapping_plan(df.columns.tolist())

        if strict_mapping and not mapping_plan.is_valid:
            missing = ", ".join(mapping_plan.missing_required)
            raise IngestionError(
                f"Strict schema mapping failed for '{path.name}'. Missing required fields: {missing}"
            )

        if apply_mapping:
            df = self.schema_mapper.apply_mapping(df, mapping_plan)

        logger.info(
            "Ingestion completed for %s: %d rows, mapped columns: %d",
            path.name,
            total_rows,
            len(mapping_plan.mapped_fields),
        )

        return IngestionResult(
            dataframe=df,
            source_path=path,
            file_type=file_type,
            file_size_bytes=file_size,
            file_hash_sha256=file_hash,
            total_rows_read=total_rows,
            mapping_plan=mapping_plan,
            metadata={
                "unmapped_columns": mapping_plan.unmapped_source_columns,
                "confidence_scores": {
                    col: m.confidence for col, m in mapping_plan.mappings.items()
                },
            },
        )

    def iterate_chunks(
        self,
        file_path: Union[str, Path],
        chunk_size: int = 10000,
    ) -> Iterator[pd.DataFrame]:
        """Iterate over large CSV or tabular files in chunks for memory-efficient processing."""
        path = Path(file_path)
        file_type = self.detect_file_type(path)

        if file_type == "csv":
            for chunk in pd.read_csv(path, chunksize=chunk_size, dtype=str):
                yield chunk
        else:
            full_df = self.read_raw_dataframe(path, file_type=file_type)
            for i in range(0, len(full_df), chunk_size):
                yield full_df.iloc[i : i + chunk_size].copy()
