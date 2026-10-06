"""FLOODTAIL — Data normalizer, cleaner, and standardizer.

Standardizes raw portfolio records into clean, validated data ready for
catastrophe modeling and Pydantic validation.
Handles coordinate validation, currency / numeric parsing, occupancy &
construction taxonomy mapping, and row-level issue extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.logging_config import get_logger

logger = get_logger("normalizer")

# Canonical occupancy taxonomy
OCCUPANCY_MAPPING: dict[str, str] = {
    "residential": "Residential",
    "res": "Residential",
    "dwelling": "Residential",
    "single family": "Residential",
    "apartment": "Residential",
    "apt": "Residential",
    "condo": "Residential",
    "house": "Residential",
    "commercial": "Commercial",
    "comm": "Commercial",
    "office": "Commercial",
    "retail": "Commercial",
    "shop": "Commercial",
    "hotel": "Commercial",
    "hospital": "Commercial",
    "school": "Commercial",
    "industrial": "Industrial",
    "ind": "Industrial",
    "factory": "Industrial",
    "warehouse": "Industrial",
    "manufacturing": "Industrial",
    "agricultural": "Agricultural",
    "agri": "Agricultural",
    "farm": "Agricultural",
}

# Canonical construction taxonomy
CONSTRUCTION_MAPPING: dict[str, str] = {
    "concrete": "Reinforced Concrete",
    "reinforced concrete": "Reinforced Concrete",
    "rc": "Reinforced Concrete",
    "masonry": "Masonry",
    "brick": "Masonry",
    "stone": "Masonry",
    "block": "Masonry",
    "steel": "Steel Frame",
    "steel frame": "Steel Frame",
    "metal": "Steel Frame",
    "timber": "Timber Frame",
    "wood": "Timber Frame",
    "frame": "Timber Frame",
}

# Approximate geographic bounds for Kenya (used for sanity flagging)
KENYA_LAT_MIN, KENYA_LAT_MAX = -5.05, 5.50
KENYA_LON_MIN, KENYA_LON_MAX = 33.80, 42.00


@dataclass
class NormalizationIssue:
    """Represents a row-level data cleaning or validation problem."""

    row_index: int
    policy_id: Optional[str]
    field: str
    issue_type: str
    severity: str  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    raw_value: Any
    message: str


@dataclass
class NormalizationResult:
    """Output envelope containing cleaned dataset and audit trail of issues."""

    clean_dataframe: pd.DataFrame
    invalid_dataframe: pd.DataFrame
    issues: list[NormalizationIssue] = field(default_factory=list)
    total_input_rows: int = 0
    valid_count: int = 0
    invalid_count: int = 0

    @property
    def validity_rate(self) -> float:
        if self.total_input_rows == 0:
            return 1.0
        return self.valid_count / self.total_input_rows


class PortfolioNormalizer:
    """Transforms raw portfolio tabular data into canonical schema format."""

    def __init__(
        self,
        default_currency: str = "KES",
        exchange_rates: Optional[dict[str, float]] = None,
        flag_non_kenya: bool = True,
    ) -> None:
        self.default_currency = default_currency
        # Exchange rate to standard currency (e.g., KES base: USD = 0.0077, EUR = 0.0071, etc.)
        self.exchange_rates = exchange_rates or {
            "KES": 1.0,
            "KSH": 1.0,
            "USD": 130.0,
            "EUR": 140.0,
            "GBP": 165.0,
        }
        self.flag_non_kenya = flag_non_kenya

    @staticmethod
    def clean_numeric_value(raw: Any) -> Optional[float]:
        """Strip currency signs, commas, whitespace, and parse float."""
        if raw is None or pd.isna(raw):
            return None
        if isinstance(raw, (int, float)):
            if np.isnan(raw) or np.isinf(raw):
                return None
            return float(raw)

        s = str(raw).strip()
        if not s or s.lower() in {"nan", "none", "null", "n/a", "-"}:
            return None

        # Check for multiplier suffixes
        s_upper = s.upper()
        multiplier = 1.0
        if s_upper.endswith("M") or " M" in s_upper or " MILLION" in s_upper:
            multiplier = 1_000_000.0
            s = re.sub(r"(?i)\s*(million|m)\b", "", s)
        elif s_upper.endswith("K") or " K" in s_upper or " THOUSAND" in s_upper:
            multiplier = 1_000.0
            s = re.sub(r"(?i)\s*(thousand|k)\b", "", s)
        elif s_upper.endswith("B") or " B" in s_upper or " BILLION" in s_upper:
            multiplier = 1_000_000_000.0
            s = re.sub(r"(?i)\s*(billion|b)\b", "", s)

        # Remove currency symbols, commas, spaces
        s_clean = re.sub(r"[^\d.-]", "", s)
        try:
            val = float(s_clean) * multiplier
            return val if not (np.isnan(val) or np.isinf(val)) else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def standardize_property_type(raw: Any) -> str:
        """Map raw property / occupancy type to canonical taxonomy."""
        if raw is None or pd.isna(raw):
            return "Other / Unknown"
        norm = str(raw).strip().lower()
        if not norm:
            return "Other / Unknown"
        if norm in OCCUPANCY_MAPPING:
            return OCCUPANCY_MAPPING[norm]
        for key in sorted(OCCUPANCY_MAPPING.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(key) + r"\b", norm):
                return OCCUPANCY_MAPPING[key]
        for key in sorted(OCCUPANCY_MAPPING.keys(), key=len, reverse=True):
            if key in norm and len(key) >= 4:
                return OCCUPANCY_MAPPING[key]
        return str(raw).strip().title()

    @staticmethod
    def standardize_construction_class(raw: Any) -> Optional[str]:
        """Map raw construction type to canonical taxonomy."""
        if raw is None or pd.isna(raw):
            return None
        norm = str(raw).strip().lower()
        if not norm or norm in {"none", "nan", "null", "n/a", "-"}:
            return None
        if norm in CONSTRUCTION_MAPPING:
            return CONSTRUCTION_MAPPING[norm]
        for key in sorted(CONSTRUCTION_MAPPING.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(key) + r"\b", norm):
                return CONSTRUCTION_MAPPING[key]
        for key in sorted(CONSTRUCTION_MAPPING.keys(), key=len, reverse=True):
            if key in norm and len(key) >= 4:
                return CONSTRUCTION_MAPPING[key]
        return str(raw).strip().title()

    def normalize(self, df: pd.DataFrame) -> NormalizationResult:
        """Execute full normalization pipeline on DataFrame.

        Steps:
            1. Validate required columns existence.
            2. Policy ID cleanup & deduplication.
            3. Coordinate parsing, validation, and swap detection.
            4. Insured value cleaning & positive check.
            5. Taxonomy harmonization.
            6. Partition into valid vs invalid records with issue logs.
        """
        total_rows = len(df)
        issues: list[NormalizationIssue] = []
        valid_rows: list[dict[str, Any]] = []
        invalid_rows: list[dict[str, Any]] = []

        seen_policy_ids: set[str] = set()

        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            row_idx = int(idx) if isinstance(idx, int) else 0
            row_has_error = False

            # 1. Policy ID
            raw_pid = row_dict.get("policy_id")
            if raw_pid is None or pd.isna(raw_pid) or not str(raw_pid).strip():
                issues.append(
                    NormalizationIssue(
                        row_index=row_idx,
                        policy_id=None,
                        field="policy_id",
                        issue_type="MISSING_POLICY_ID",
                        severity="ERROR",
                        raw_value=raw_pid,
                        message="Missing or empty policy_id",
                    )
                )
                row_has_error = True
                clean_pid = f"INVALID_ROW_{row_idx}"
            else:
                clean_pid = str(raw_pid).strip()
                if clean_pid in seen_policy_ids:
                    issues.append(
                        NormalizationIssue(
                            row_index=row_idx,
                            policy_id=clean_pid,
                            field="policy_id",
                            issue_type="DUPLICATE_POLICY_ID",
                            severity="WARNING",
                            raw_value=raw_pid,
                            message=f"Duplicate policy_id '{clean_pid}' encountered",
                        )
                    )
                seen_policy_ids.add(clean_pid)

            # 2. Coordinates
            raw_lat = row_dict.get("latitude")
            raw_lon = row_dict.get("longitude")

            clean_lat = self.clean_numeric_value(raw_lat)
            clean_lon = self.clean_numeric_value(raw_lon)

            if clean_lat is None or clean_lon is None:
                issues.append(
                    NormalizationIssue(
                        row_index=row_idx,
                        policy_id=clean_pid,
                        field="coordinates",
                        issue_type="INVALID_COORDINATES",
                        severity="ERROR",
                        raw_value=f"lat={raw_lat}, lon={raw_lon}",
                        message="Latitude or Longitude is null or unparseable",
                    )
                )
                row_has_error = True
            else:
                # Coordinate swap check: If lat looks like Kenya lon (33-42) and lon looks like Kenya lat (-5 to 5)
                if (
                    KENYA_LON_MIN <= clean_lat <= KENYA_LON_MAX
                    and KENYA_LAT_MIN <= clean_lon <= KENYA_LAT_MAX
                ):
                    issues.append(
                        NormalizationIssue(
                            row_index=row_idx,
                            policy_id=clean_pid,
                            field="coordinates",
                            issue_type="SWAPPED_COORDINATES_AUTOCORRECTED",
                            severity="WARNING",
                            raw_value=f"lat={clean_lat}, lon={clean_lon}",
                            message="Detected swapped latitude/longitude coordinates; auto-corrected.",
                        )
                    )
                    clean_lat, clean_lon = clean_lon, clean_lat

                # Bounds check
                if not (-90.0 <= clean_lat <= 90.0):
                    issues.append(
                        NormalizationIssue(
                            row_index=row_idx,
                            policy_id=clean_pid,
                            field="latitude",
                            issue_type="LATITUDE_OUT_OF_BOUNDS",
                            severity="ERROR",
                            raw_value=clean_lat,
                            message=f"Latitude {clean_lat} is outside WGS-84 valid range [-90, 90]",
                        )
                    )
                    row_has_error = True

                if not (-180.0 <= clean_lon <= 180.0):
                    issues.append(
                        NormalizationIssue(
                            row_index=row_idx,
                            policy_id=clean_pid,
                            field="longitude",
                            issue_type="LONGITUDE_OUT_OF_BOUNDS",
                            severity="ERROR",
                            raw_value=clean_lon,
                            message=f"Longitude {clean_lon} is outside WGS-84 valid range [-180, 180]",
                        )
                    )
                    row_has_error = True

                # Kenya boundary warning
                if self.flag_non_kenya and not row_has_error:
                    if not (
                        KENYA_LAT_MIN <= clean_lat <= KENYA_LAT_MAX
                        and KENYA_LON_MIN <= clean_lon <= KENYA_LON_MAX
                    ):
                        issues.append(
                            NormalizationIssue(
                                row_index=row_idx,
                                policy_id=clean_pid,
                                field="coordinates",
                                issue_type="OUTSIDE_PRIMARY_PERIL_REGION",
                                severity="INFO",
                                raw_value=f"lat={clean_lat}, lon={clean_lon}",
                                message=f"Location ({clean_lat:.4f}, {clean_lon:.4f}) is outside Kenya regional peril bounding box",
                            )
                        )

            # 3. Insured Value
            raw_val = row_dict.get("insured_value")
            clean_val = self.clean_numeric_value(raw_val)

            if clean_val is None or clean_val <= 0:
                issues.append(
                    NormalizationIssue(
                        row_index=row_idx,
                        policy_id=clean_pid,
                        field="insured_value",
                        issue_type="INVALID_INSURED_VALUE",
                        severity="ERROR",
                        raw_value=raw_val,
                        message=f"Insured value must be a strictly positive number (> 0), got: {raw_val}",
                    )
                )
                row_has_error = True

            # 4. Property type
            raw_ptype = row_dict.get("property_type")
            clean_ptype = self.standardize_property_type(raw_ptype)

            # 5. Construction class
            raw_cclass = row_dict.get("construction_class")
            clean_cclass = self.standardize_construction_class(raw_cclass)

            # 6. Region
            raw_region = row_dict.get("region")
            clean_region = (
                str(raw_region).strip().title()
                if (raw_region is not None and not pd.isna(raw_region) and str(raw_region).strip())
                else None
            )

            # Assemble normalized row record
            record = {
                "policy_id": clean_pid,
                "latitude": clean_lat,
                "longitude": clean_lon,
                "insured_value": clean_val,
                "property_type": clean_ptype,
                "construction_class": clean_cclass,
                "region": clean_region,
            }

            if row_has_error:
                invalid_rows.append(record)
            else:
                valid_rows.append(record)

        clean_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=[
            "policy_id", "latitude", "longitude", "insured_value", "property_type", "construction_class", "region"
        ])
        invalid_df = pd.DataFrame(invalid_rows) if invalid_rows else pd.DataFrame(columns=[
            "policy_id", "latitude", "longitude", "insured_value", "property_type", "construction_class", "region"
        ])

        logger.info(
            "Normalization complete: %d total, %d valid (%.1f%%), %d invalid, %d issues logged",
            total_rows,
            len(clean_df),
            (len(clean_df) / total_rows * 100) if total_rows > 0 else 100.0,
            len(invalid_df),
            len(issues),
        )

        return NormalizationResult(
            clean_dataframe=clean_df,
            invalid_dataframe=invalid_df,
            issues=issues,
            total_input_rows=total_rows,
            valid_count=len(clean_df),
            invalid_count=len(invalid_df),
        )
