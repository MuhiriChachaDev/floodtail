"""FLOODTAIL — Data Quality, Statistical Profiling & Anomaly Audit Engine.

Evaluates incoming reinsurance portfolio data across completeness, validity,
uniqueness, distribution outliers, and spatial concentration.
Computes a composite Data Quality Score (0-100) and produces structured audit records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.logging_config import get_logger

logger = get_logger("quality")


@dataclass
class QualityIssue:
    """Individual data quality defect identified during audit."""

    policy_id: Optional[str]
    issue_type: str
    severity: str  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    field: Optional[str]
    value: Optional[str]
    message: str
    detector: str
    status: str = "OPEN"


@dataclass
class QualityProfile:
    """Statistical summary and distributional metrics of the dataset."""

    total_records: int
    unique_policies: int
    duplicate_policies: int
    total_insured_value: float
    mean_insured_value: float
    median_insured_value: float
    std_insured_value: float
    min_insured_value: float
    max_insured_value: float
    q25_insured_value: float
    q75_insured_value: float
    q99_insured_value: float
    iqr_outlier_count: int
    zscore_outlier_count: int
    property_type_breakdown: dict[str, int]
    region_breakdown: dict[str, int]
    spatial_hhi_concentration: float


@dataclass
class QualityReport:
    """Comprehensive evaluation report for an ingested portfolio."""

    quality_score: float  # 0.0 to 100.0
    passed: bool
    issues: list[QualityIssue] = field(default_factory=list)
    profile: Optional[QualityProfile] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")


class DataQualityAuditor:
    """Audits portfolio datasets using rule-based metrics, statistical profiling, and anomaly detection."""

    def __init__(
        self,
        min_pass_score: float = 75.0,
        z_score_threshold: float = 3.5,
        iqr_multiplier: float = 3.0,
        enable_ml_anomaly: bool = True,
    ) -> None:
        self.min_pass_score = min_pass_score
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.enable_ml_anomaly = enable_ml_anomaly

    def audit(self, df: pd.DataFrame) -> QualityReport:
        """Run comprehensive audit on a portfolio DataFrame."""
        if df.empty:
            logger.warning("Empty dataframe provided to DataQualityAuditor")
            return QualityReport(
                quality_score=0.0,
                passed=False,
                issues=[
                    QualityIssue(
                        policy_id=None,
                        issue_type="EMPTY_DATASET",
                        severity="CRITICAL",
                        field=None,
                        value="0 rows",
                        message="Portfolio dataset is completely empty.",
                        detector="RuleEngine",
                    )
                ],
            )

        issues: list[QualityIssue] = []
        n_rows = len(df)

        # 1. Uniqueness / Duplication
        if "policy_id" in df.columns:
            duplicates = df[df.duplicated(subset=["policy_id"], keep=False)]
            dup_count = len(duplicates)
            if dup_count > 0:
                for pid in duplicates["policy_id"].unique()[:20]:  # Cap individual issue reports
                    issues.append(
                        QualityIssue(
                            policy_id=str(pid),
                            issue_type="DUPLICATE_POLICY",
                            severity="WARNING",
                            field="policy_id",
                            value=str(pid),
                            message=f"Duplicate policy_id '{pid}' detected",
                            detector="UniquenessRule",
                        )
                    )
        else:
            dup_count = 0
            issues.append(
                QualityIssue(
                    policy_id=None,
                    issue_type="MISSING_KEY_COLUMN",
                    severity="CRITICAL",
                    field="policy_id",
                    value=None,
                    message="Missing required 'policy_id' column.",
                    detector="SchemaRule",
                )
            )

        # 2. Completeness Check
        required_cols = ["policy_id", "latitude", "longitude", "insured_value", "property_type"]
        null_counts = {}
        for col in required_cols:
            if col in df.columns:
                nulls = int(df[col].isna().sum())
                null_counts[col] = nulls
                if nulls > 0:
                    severity = "CRITICAL" if col in {"policy_id", "insured_value"} else "ERROR"
                    issues.append(
                        QualityIssue(
                            policy_id=None,
                            issue_type="NULL_FIELD_VALUES",
                            severity=severity,
                            field=col,
                            value=f"{nulls}/{n_rows} nulls",
                            message=f"Column '{col}' has {nulls} missing/null values ({nulls/n_rows*100:.1f}%).",
                            detector="CompletenessRule",
                        )
                    )
            else:
                null_counts[col] = n_rows
                issues.append(
                    QualityIssue(
                        policy_id=None,
                        issue_type="MISSING_COLUMN",
                        severity="CRITICAL",
                        field=col,
                        value=None,
                        message=f"Required column '{col}' is entirely absent.",
                        detector="SchemaRule",
                    )
                )

        # 3. Statistical Distribution & Outliers (Insured Value)
        tiv_series = pd.to_numeric(df.get("insured_value", pd.Series()), errors="coerce").dropna()
        iqr_outliers = 0
        z_outliers = 0

        if not tiv_series.empty and len(tiv_series) > 0:
            tot_tiv = float(tiv_series.sum())
            mean_tiv = float(tiv_series.mean())
            median_tiv = float(tiv_series.median())
            std_tiv = float(tiv_series.std()) if len(tiv_series) > 1 else 0.0
            min_tiv = float(tiv_series.min())
            max_tiv = float(tiv_series.max())
            q25 = float(tiv_series.quantile(0.25))
            q75 = float(tiv_series.quantile(0.75))
            q99 = float(tiv_series.quantile(0.99))
            iqr = q75 - q25

            # Negative or zero check
            invalid_tivs = tiv_series[tiv_series <= 0]
            if len(invalid_tivs) > 0:
                issues.append(
                    QualityIssue(
                        policy_id=None,
                        issue_type="NON_POSITIVE_TIV",
                        severity="CRITICAL",
                        field="insured_value",
                        value=f"{len(invalid_tivs)} non-positive",
                        message=f"{len(invalid_tivs)} records have non-positive insured value (<= 0).",
                        detector="ValidityRule",
                    )
                )

            # Statistical Outliers: IQR Method
            if iqr > 0:
                iqr_upper_bound = q75 + (self.iqr_multiplier * iqr)
                extreme_iqr = df[pd.to_numeric(df.get("insured_value"), errors="coerce") > iqr_upper_bound]
                iqr_outliers = len(extreme_iqr)
                if iqr_outliers > 0:
                    for _, row in extreme_iqr.head(10).iterrows():
                        issues.append(
                            QualityIssue(
                                policy_id=str(row.get("policy_id", "")),
                                issue_type="EXTREME_TIV_IQR_OUTLIER",
                                severity="WARNING",
                                field="insured_value",
                                value=str(row.get("insured_value")),
                                message=f"Insured value exceeds 3x IQR threshold ({iqr_upper_bound:,.2f})",
                                detector="IQRStatisticalProfiler",
                            )
                        )

            # Statistical Outliers: Z-Score
            if std_tiv > 0:
                z_scores = np.abs((tiv_series - mean_tiv) / std_tiv)
                z_outliers = int((z_scores > self.z_score_threshold).sum())

            # ML Anomaly Detection: Isolation Forest (optional)
            if self.enable_ml_anomaly and len(df) >= 30:
                try:
                    from sklearn.ensemble import IsolationForest

                    coords_and_val = df[["latitude", "longitude", "insured_value"]].apply(
                        pd.to_numeric, errors="coerce"
                    ).dropna()
                    if len(coords_and_val) >= 30:
                        iso = IsolationForest(contamination=0.01, random_state=42)
                        preds = iso.fit_predict(coords_and_val)
                        ml_anomalies = int((preds == -1).sum())
                        if ml_anomalies > 0:
                            issues.append(
                                QualityIssue(
                                    policy_id=None,
                                    issue_type="ML_MULTIVARIATE_ANOMALY",
                                    severity="INFO",
                                    field="multivariate",
                                    value=f"{ml_anomalies} anomalies",
                                    message=f"Isolation Forest identified {ml_anomalies} multivariate spatial-exposure anomalies (1% tail).",
                                    detector="IsolationForestDetector",
                                )
                            )
                except Exception as e:
                    logger.debug("ML anomaly detection skipped: %s", e)

        else:
            tot_tiv = mean_tiv = median_tiv = std_tiv = min_tiv = max_tiv = q25 = q75 = q99 = 0.0

        # 4. Spatial Concentration (HHI by 0.1 degree grid bin or region)
        spatial_hhi = 0.0
        if "latitude" in df.columns and "longitude" in df.columns and not tiv_series.empty:
            valid_geo = df[["latitude", "longitude", "insured_value"]].apply(
                pd.to_numeric, errors="coerce"
            ).dropna()
            if not valid_geo.empty and tot_tiv > 0:
                # Bin into ~10km grid cells (0.1 deg)
                grid_lat = (valid_geo["latitude"] * 10).round() / 10
                grid_lon = (valid_geo["longitude"] * 10).round() / 10
                valid_geo["grid"] = grid_lat.astype(str) + "_" + grid_lon.astype(str)
                grid_shares = valid_geo.groupby("grid")["insured_value"].sum() / tot_tiv
                spatial_hhi = float((grid_shares**2).sum())

                if spatial_hhi > 0.35:
                    issues.append(
                        QualityIssue(
                            policy_id=None,
                            issue_type="HIGH_SPATIAL_CONCENTRATION",
                            severity="WARNING",
                            field="coordinates",
                            value=f"HHI = {spatial_hhi:.3f}",
                            message=f"High spatial concentration detected (HHI={spatial_hhi:.3f} > 0.35). Heavy peril accumulation.",
                            detector="SpatialConcentrationEngine",
                        )
                    )

        # 5. Taxonomy Breakdowns
        prop_breakdown = (
            df["property_type"].value_counts().to_dict()
            if "property_type" in df.columns
            else {}
        )
        region_breakdown = (
            df["region"].value_counts().to_dict()
            if "region" in df.columns
            else {}
        )

        profile = QualityProfile(
            total_records=n_rows,
            unique_policies=len(df["policy_id"].unique()) if "policy_id" in df.columns else 0,
            duplicate_policies=dup_count,
            total_insured_value=tot_tiv,
            mean_insured_value=mean_tiv,
            median_insured_value=median_tiv,
            std_insured_value=std_tiv,
            min_insured_value=min_tiv,
            max_insured_value=max_tiv,
            q25_insured_value=q25,
            q75_insured_value=q75,
            q99_insured_value=q99,
            iqr_outlier_count=iqr_outliers,
            zscore_outlier_count=z_outliers,
            property_type_breakdown=prop_breakdown,
            region_breakdown=region_breakdown,
            spatial_hhi_concentration=spatial_hhi,
        )

        # 6. Composite Score Calculation (0.0 to 100.0)
        # Weights: Completeness (40%), Validity (30%), Uniqueness (20%), Consistency/Distribution (10%)
        total_cells = n_rows * len(required_cols)
        missing_cells = sum(null_counts.values())
        completeness_pct = max(0.0, 1.0 - (missing_cells / total_cells)) if total_cells > 0 else 0.0

        uniqueness_pct = max(0.0, 1.0 - (dup_count / n_rows)) if n_rows > 0 else 1.0

        crit_count = sum(1 for i in issues if i.severity == "CRITICAL")
        err_count = sum(1 for i in issues if i.severity == "ERROR")
        warn_count = sum(1 for i in issues if i.severity == "WARNING")

        validity_pct = max(0.0, 1.0 - ((crit_count * 5 + err_count * 2) / (n_rows + 10)))
        consistency_pct = max(0.0, 1.0 - (warn_count / (n_rows + 20)))

        composite_score = (
            (completeness_pct * 40.0)
            + (validity_pct * 30.0)
            + (uniqueness_pct * 20.0)
            + (consistency_pct * 10.0)
        )
        composite_score = round(max(0.0, min(100.0, composite_score)), 2)

        passed = (composite_score >= self.min_pass_score) and (crit_count == 0)

        logger.info(
            "Quality audit finished: score=%.2f/100, passed=%s, issues=%d (crit=%d, err=%d, warn=%d)",
            composite_score,
            passed,
            len(issues),
            crit_count,
            err_count,
            warn_count,
        )

        return QualityReport(
            quality_score=composite_score,
            passed=passed,
            issues=issues,
            profile=profile,
            metrics={
                "completeness_rate": completeness_pct,
                "uniqueness_rate": uniqueness_pct,
                "validity_rate": validity_pct,
                "spatial_hhi": spatial_hhi,
            },
        )
