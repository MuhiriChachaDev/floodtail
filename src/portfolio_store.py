"""FLOODTAIL — Analytical Portfolio Parquet Store & Version Manager.

Stores validated, normalized reinsurance exposures into structured Parquet
datasets (with resilient compressed tabular fallbacks) with cryptographic hashing,
metadata registration, and snapshot retrieval.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from src.database import DatabaseManager
from src.exceptions import DatabaseError, SchemaValidationError
from src.logging_config import get_logger
from src.schemas import PortfolioRecord

logger = get_logger("portfolio_store")


@dataclass
class VersionMetadata:
    """Metadata describing a persisted portfolio version snapshot."""

    version_id: Optional[int]
    run_id: str
    dataset_path: str
    dataset_hash: str
    record_count: int
    created_at: datetime


class PortfolioStore:
    """Manages reading and writing of standardized portfolio datasets."""

    def __init__(
        self,
        base_dir: Union[str, Path] = "data/portfolios",
        db_manager: Optional[DatabaseManager] = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db_manager = db_manager

    @staticmethod
    def compute_df_sha256(df: pd.DataFrame) -> str:
        """Deterministic SHA-256 hash of a normalized dataframe."""
        serialized = df.to_json(orient="records", date_format="iso").encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def validate_schema(self, df: pd.DataFrame) -> None:
        """Validate every row conforms to the PortfolioRecord schema."""
        required = ["policy_id", "latitude", "longitude", "insured_value", "property_type"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise SchemaValidationError(f"DataFrame is missing required portfolio columns: {missing}")

        for idx, row in df.iterrows():
            try:
                PortfolioRecord(
                    policy_id=str(row["policy_id"]),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    insured_value=float(row["insured_value"]),
                    property_type=str(row["property_type"]),
                    construction_class=(
                        str(row["construction_class"])
                        if pd.notna(row.get("construction_class")) and row.get("construction_class")
                        else None
                    ),
                    region=(
                        str(row["region"])
                        if pd.notna(row.get("region")) and row.get("region")
                        else None
                    ),
                )
            except Exception as e:
                raise SchemaValidationError(f"Row {idx} fails PortfolioRecord validation: {e}") from e

    def save_portfolio(
        self,
        df: pd.DataFrame,
        run_id: str,
        validate: bool = True,
        filename_prefix: str = "portfolio",
    ) -> VersionMetadata:
        """Persist portfolio DataFrame to Parquet (or compressed tabular store) and register in SQLite."""
        if validate:
            self.validate_schema(df)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_filename = f"{filename_prefix}_{run_id[:8]}_{timestamp_str}.parquet"
        target_path = self.base_dir / target_filename

        out_df = df.copy()
        out_df["policy_id"] = out_df["policy_id"].astype(str)
        out_df["latitude"] = out_df["latitude"].astype(float)
        out_df["longitude"] = out_df["longitude"].astype(float)
        out_df["insured_value"] = out_df["insured_value"].astype(float)
        out_df["property_type"] = out_df["property_type"].astype(str)

        try:
            out_df.to_parquet(target_path, index=False)
        except Exception:
            # Fallback if pyarrow / fastparquet is not installed
            target_path = self.base_dir / f"{filename_prefix}_{run_id[:8]}_{timestamp_str}.csv.gz"
            out_df.to_csv(target_path, index=False, compression="gzip")

        dataset_hash = self.compute_df_sha256(out_df)
        record_count = len(out_df)
        created_at = datetime.now(timezone.utc)

        logger.info(
            "Saved portfolio version for run %s: %d records -> %s (hash=%s)",
            run_id,
            record_count,
            target_path,
            dataset_hash[:12],
        )

        version_id = None
        if self.db_manager:
            try:
                version_id = self.db_manager.record_portfolio_version(
                    run_id=run_id,
                    dataset_path=str(target_path),
                    dataset_hash=dataset_hash,
                    record_count=record_count,
                    created_at=created_at,
                )
            except Exception as e:
                logger.error("Failed to register portfolio version in SQLite: %s", e)

        return VersionMetadata(
            version_id=version_id,
            run_id=run_id,
            dataset_path=str(target_path),
            dataset_hash=dataset_hash,
            record_count=record_count,
            created_at=created_at,
        )

    def load_portfolio(self, path_or_run_id: Union[str, Path]) -> pd.DataFrame:
        """Load portfolio dataset by file path or run_id."""
        path = Path(path_or_run_id)
        if path.exists() and path.is_file():
            if str(path).endswith(".parquet"):
                try:
                    return pd.read_parquet(path)
                except Exception:
                    pass
            if str(path).endswith(".csv.gz") or str(path).endswith(".csv"):
                return pd.read_csv(path)
            if str(path).endswith(".json") or str(path).endswith(".json.gz"):
                return pd.read_json(path)

        if self.db_manager:
            versions = self.db_manager.get_portfolio_versions(str(path_or_run_id))
            if versions:
                latest = versions[-1]
                ds_path = Path(latest["dataset_path"])
                if ds_path.exists():
                    return self.load_portfolio(ds_path)

        matches = list(self.base_dir.glob(f"*{str(path_or_run_id)[:8]}*"))
        if matches:
            return self.load_portfolio(matches[-1])

        raise FileNotFoundError(f"Could not locate portfolio dataset for: {path_or_run_id}")

    def list_saved_versions(self) -> list[Path]:
        """List all datasets in the store directory."""
        return sorted(
            [p for p in self.base_dir.iterdir() if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
