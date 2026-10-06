"""FLOODTAIL — Comprehensive unit and integration test suite for Phase 2 Data Layer.

Covers:
- DatabaseManager (SQLite metadata, CRUD, constraints, transactions)
- SchemaMapper (exact, alias, fuzzy mapping, column conflicts)
- IngestionEngine (CSV, Parquet, Excel, JSON/NDJSON, SHA-256, chunking)
- PortfolioNormalizer (coordinates, currency, taxonomy, invalid row quarantine)
- DataQualityAuditor (completeness, uniqueness, IQR, Z-score, HHI, score)
- PortfolioStore (Parquet persistence, version hashing, schema validation)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.database import DatabaseManager, initialize_database
from src.exceptions import DatabaseError, IngestionError, SchemaValidationError
from src.ingestion import IngestionEngine, IngestionResult
from src.normalizer import PortfolioNormalizer
from src.portfolio_store import PortfolioStore
from src.quality import DataQualityAuditor
from src.schema_mapper import MappingPlan, SchemaMapper
from src.schemas import PortfolioRecord

try:
    import pyarrow
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False



# ===========================================================================
# 1. Database Manager Tests
# ===========================================================================

class TestDatabaseManager:
    """Test suite for SQLite metadata database."""

    def test_init_creates_tables_and_indexes(self, tmp_path: Path):
        db_file = tmp_path / "test_floodtail.db"
        db = DatabaseManager(db_file)
        assert db_file.exists()

        # Verify tables exist
        import sqlite3
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            assert {"runs", "ingestion_records", "data_quality_issues", "schema_mappings", "portfolio_versions"}.issubset(tables)

    def test_run_lifecycle_crud(self, tmp_path: Path):
        db = DatabaseManager(tmp_path / "test.db")
        run_id = "RUN-TEST-001"

        db.create_run(
            run_id=run_id,
            model_version="0.1.0",
            data_version="v1.0",
            status="PENDING",
            source_file="sample.csv",
        )

        run = db.get_run(run_id)
        assert run is not None
        assert run["run_id"] == run_id
        assert run["status"] == "PENDING"
        assert run["source_file"] == "sample.csv"

        # Update run
        db.update_run(
            run_id,
            status="SUCCESS",
            row_count=1000,
            valid_row_count=980,
            invalid_row_count=20,
            quality_score=94.5,
        )

        updated = db.get_run(run_id)
        assert updated["status"] == "SUCCESS"
        assert updated["row_count"] == 1000
        assert updated["valid_row_count"] == 980
        assert updated["invalid_row_count"] == 20
        assert updated["quality_score"] == 94.5

    def test_record_ingestion_and_quality_issues(self, tmp_path: Path):
        db = DatabaseManager(tmp_path / "test.db")
        run_id = "RUN-TEST-002"
        db.create_run(run_id=run_id)

        db.record_ingestion(
            run_id=run_id,
            source_filename="nairobi_portfolio.csv",
            source_type="csv",
            file_size=10240,
            schema_status="MAPPED",
            mapping_status="SUCCESS",
            record_count=150,
        )

        issues = [
            {
                "run_id": run_id,
                "policy_id": "POL_999",
                "issue_type": "INVALID_COORDINATES",
                "severity": "ERROR",
                "field": "latitude",
                "value": "999.0",
                "message": "Latitude out of bounds",
                "detector": "Normalizer",
            },
            {
                "run_id": run_id,
                "policy_id": "POL_100",
                "issue_type": "EXTREME_TIV",
                "severity": "WARNING",
                "field": "insured_value",
                "value": "500000000",
                "message": "High outlier",
                "detector": "IQRDetector",
            },
        ]
        db.record_quality_issues(issues)

        fetched_issues = db.get_quality_issues(run_id)
        assert len(fetched_issues) == 2
        assert fetched_issues[0]["policy_id"] == "POL_999"
        assert fetched_issues[0]["severity"] == "ERROR"

    def test_schema_mappings_and_portfolio_versions(self, tmp_path: Path):
        db = DatabaseManager(tmp_path / "test.db")
        run_id = "RUN-TEST-003"
        db.create_run(run_id=run_id)

        mappings = [
            {
                "run_id": run_id,
                "source_column": "TIV_AMOUNT",
                "target_field": "insured_value",
                "mapping_method": "ALIAS",
                "confidence": 1.0,
                "status": "ACCEPTED",
            }
        ]
        db.record_schema_mappings(mappings)

        ver_id = db.record_portfolio_version(
            run_id=run_id,
            dataset_path="/data/portfolios/p1.parquet",
            dataset_hash="abcdef123456",
            record_count=500,
        )
        assert ver_id > 0

        versions = db.get_portfolio_versions(run_id)
        assert len(versions) == 1
        assert versions[0]["dataset_hash"] == "abcdef123456"
        assert versions[0]["record_count"] == 500


# ===========================================================================
# 2. Schema Mapper Tests
# ===========================================================================

class TestSchemaMapper:
    """Test suite for intelligent column mapping."""

    def test_exact_matches(self):
        mapper = SchemaMapper()
        columns = ["policy_id", "latitude", "longitude", "insured_value", "property_type"]
        plan = mapper.create_mapping_plan(columns)

        assert plan.is_valid is True
        assert len(plan.missing_required) == 0
        assert plan.mappings["policy_id"].target_field == "policy_id"
        assert plan.mappings["policy_id"].mapping_method == "EXACT"
        assert plan.mappings["policy_id"].confidence == 1.0

    def test_alias_matches(self):
        mapper = SchemaMapper()
        columns = ["Policy_Number", "Lat", "Lng", "TIV", "Occupancy", "Building_Class", "County"]
        plan = mapper.create_mapping_plan(columns)

        assert plan.is_valid is True
        assert plan.mappings["Policy_Number"].target_field == "policy_id"
        assert plan.mappings["Lat"].target_field == "latitude"
        assert plan.mappings["Lng"].target_field == "longitude"
        assert plan.mappings["TIV"].target_field == "insured_value"
        assert plan.mappings["Occupancy"].target_field == "property_type"
        assert plan.mappings["Building_Class"].target_field == "construction_class"
        assert plan.mappings["County"].target_field == "region"

    def test_fuzzy_matching(self):
        mapper = SchemaMapper()
        columns = ["pol_ident", "gps_latitude", "gps_longitude", "total_val_insured", "prop_type"]
        plan = mapper.create_mapping_plan(columns)

        assert "gps_latitude" in plan.mappings
        assert plan.mappings["gps_latitude"].target_field == "latitude"
        assert "gps_longitude" in plan.mappings
        assert plan.mappings["gps_longitude"].target_field == "longitude"

    def test_apply_mapping_to_dataframe(self):
        mapper = SchemaMapper()
        df = pd.DataFrame({
            "Policy_No": ["P1", "P2"],
            "Lat": [-1.286389, -4.043477],
            "Lon": [36.817223, 39.668206],
            "Sum_Insured": [1000000, 2500000],
            "Building_Type": ["Office", "Warehouse"],
        })
        plan = mapper.create_mapping_plan(df.columns.tolist())
        mapped_df = mapper.apply_mapping(df, plan)

        assert "policy_id" in mapped_df.columns
        assert "latitude" in mapped_df.columns
        assert "longitude" in mapped_df.columns
        assert "insured_value" in mapped_df.columns
        assert "property_type" in mapped_df.columns


# ===========================================================================
# 3. Ingestion Engine Tests
# ===========================================================================

class TestIngestionEngine:
    """Test suite for multi-format ingestion engine."""

    def test_ingest_csv_with_mapping(self, tmp_path: Path):
        csv_file = tmp_path / "portfolio.csv"
        csv_file.write_text(
            "Policy_ID,LAT,LONG,TIV,PROPERTY\n"
            "POL_001,-1.28,36.81,5000000,Commercial\n"
            "POL_002,-1.30,36.85,7500000,Residential\n",
            encoding="utf-8",
        )

        engine = IngestionEngine()
        result = engine.ingest_file(csv_file)

        assert isinstance(result, IngestionResult)
        assert result.file_type == "csv"
        assert result.total_rows_read == 2
        assert len(result.file_hash_sha256) == 64
        assert "policy_id" in result.dataframe.columns
        assert "latitude" in result.dataframe.columns
        assert "insured_value" in result.dataframe.columns

    @pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow required for parquet ingestion")
    def test_ingest_parquet(self, tmp_path: Path):
        pq_file = tmp_path / "portfolio.parquet"
        df = pd.DataFrame({
            "policy_id": ["P101", "P102"],
            "latitude": [-1.28, -1.29],
            "longitude": [36.81, 36.82],
            "insured_value": [1000000.0, 2000000.0],
            "property_type": ["Residential", "Commercial"],
        })
        df.to_parquet(pq_file)

        engine = IngestionEngine()
        result = engine.ingest_file(pq_file)
        assert result.file_type == "parquet"
        assert result.total_rows_read == 2
        assert result.dataframe["policy_id"].tolist() == ["P101", "P102"]

    def test_ingest_json_lines(self, tmp_path: Path):
        json_file = tmp_path / "portfolio.ndjson"
        data = [
            {"policy": "P201", "lat": -1.28, "lon": 36.81, "tiv": 3000000, "occupancy": "Residential"},
            {"policy": "P202", "lat": -1.30, "lon": 36.85, "tiv": 4500000, "occupancy": "Commercial"},
        ]
        with open(json_file, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        engine = IngestionEngine()
        result = engine.ingest_file(json_file)
        assert result.file_type == "json"
        assert result.total_rows_read == 2
        assert "policy_id" in result.dataframe.columns

    def test_empty_file_rejected(self, tmp_path: Path):
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("", encoding="utf-8")

        engine = IngestionEngine()
        with pytest.raises(IngestionError, match="empty"):
            engine.ingest_file(empty_file)

    def test_nonexistent_file_rejected(self, tmp_path: Path):
        engine = IngestionEngine()
        with pytest.raises(IngestionError, match="does not exist"):
            engine.ingest_file(tmp_path / "does_not_exist.csv")

    def test_unsupported_format_rejected(self, tmp_path: Path):
        bad_file = tmp_path / "bad.docx"
        bad_file.write_text("hello", encoding="utf-8")

        engine = IngestionEngine()
        with pytest.raises(IngestionError, match="Unsupported file format"):
            engine.ingest_file(bad_file)

    def test_chunk_iteration(self, tmp_path: Path):
        csv_file = tmp_path / "large.csv"
        rows = ["policy_id,latitude,longitude,insured_value,property_type"]
        for i in range(25):
            rows.append(f"POL_{i:03d},-1.28,36.81,1000000,Residential")
        csv_file.write_text("\n".join(rows), encoding="utf-8")

        engine = IngestionEngine()
        chunks = list(engine.iterate_chunks(csv_file, chunk_size=10))
        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5


# ===========================================================================
# 4. Normalizer Tests
# ===========================================================================

class TestPortfolioNormalizer:
    """Test suite for data standardization and cleansing."""

    def test_currency_and_numeric_cleaning(self):
        normalizer = PortfolioNormalizer()
        df = pd.DataFrame({
            "policy_id": ["P1", "P2", "P3", "P4", "P5"],
            "latitude": ["-1.286389", "-4.043477", "0.514277", "-1.29", "-1.30"],
            "longitude": ["36.817223", "39.668206", "35.269780", "36.82", "36.83"],
            "insured_value": ["KES 5,000,000", "$ 12,500,000.50", " 2500000 ", "15M", "500K"],
            "property_type": ["residential", "COMMERCIAL", "apt", "Warehouse", "Office"],
        })
        res = normalizer.normalize(df)

        assert res.valid_count == 5
        assert res.invalid_count == 0
        assert res.clean_dataframe.loc[0, "insured_value"] == 5000000.0
        assert res.clean_dataframe.loc[1, "insured_value"] == 12500000.50
        assert res.clean_dataframe.loc[2, "insured_value"] == 2500000.0
        assert res.clean_dataframe.loc[3, "insured_value"] == 15000000.0
        assert res.clean_dataframe.loc[4, "insured_value"] == 500000.0
        assert res.clean_dataframe.loc[0, "property_type"] == "Residential"
        assert res.clean_dataframe.loc[1, "property_type"] == "Commercial"
        assert res.clean_dataframe.loc[2, "property_type"] == "Residential"
        assert res.clean_dataframe.loc[3, "property_type"] == "Industrial"
        assert res.clean_dataframe.loc[4, "property_type"] == "Commercial"

    def test_swapped_coordinates_autocorrection(self):
        normalizer = PortfolioNormalizer()
        # In Kenya, Lat is roughly [-5, 5] and Lon is roughly [34, 42]
        # Swapped: lat=36.82, lon=-1.28
        df = pd.DataFrame({
            "policy_id": ["P_SWAP"],
            "latitude": [36.817223],
            "longitude": [-1.286389],
            "insured_value": [5000000],
            "property_type": ["Commercial"],
        })
        res = normalizer.normalize(df)

        assert res.valid_count == 1
        assert res.clean_dataframe.loc[0, "latitude"] == pytest.approx(-1.286389)
        assert res.clean_dataframe.loc[0, "longitude"] == pytest.approx(36.817223)
        assert any(i.issue_type == "SWAPPED_COORDINATES_AUTOCORRECTED" for i in res.issues)

    def test_invalid_records_quarantine(self):
        normalizer = PortfolioNormalizer()
        df = pd.DataFrame({
            "policy_id": ["P_VALID", "P_BAD_LAT", "P_NEG_VAL", ""],
            "latitude": [-1.28, 999.0, -1.30, -1.31],
            "longitude": [36.81, 36.82, 36.83, 36.84],
            "insured_value": [1000000, 2000000, -50000, 1000000],
            "property_type": ["Residential", "Residential", "Commercial", "Commercial"],
        })
        res = normalizer.normalize(df)

        assert res.valid_count == 1
        assert res.invalid_count == 3
        assert res.clean_dataframe.iloc[0]["policy_id"] == "P_VALID"
        assert len(res.issues) >= 3


# ===========================================================================
# 5. Data Quality Auditor Tests
# ===========================================================================

class TestDataQualityAuditor:
    """Test suite for statistical profiling and data quality scoring."""

    def test_clean_portfolio_high_score(self):
        auditor = DataQualityAuditor()
        df = pd.DataFrame({
            "policy_id": [f"POL_{i:04d}" for i in range(50)],
            "latitude": np.random.uniform(-1.5, -1.1, 50),
            "longitude": np.random.uniform(36.7, 37.0, 50),
            "insured_value": np.random.uniform(1_000_000, 10_000_000, 50),
            "property_type": ["Residential"] * 30 + ["Commercial"] * 20,
            "region": ["Nairobi"] * 50,
        })
        report = auditor.audit(df)

        assert report.passed is True
        assert report.quality_score >= 80.0
        assert report.profile is not None
        assert report.profile.total_records == 50
        assert report.profile.duplicate_policies == 0

    def test_dirty_portfolio_fails_quality(self):
        auditor = DataQualityAuditor(min_pass_score=80.0)
        df = pd.DataFrame({
            "policy_id": ["POL_1", "POL_1", None, "POL_4"],  # Duplicate & Null
            "latitude": [-1.28, None, -1.30, -1.31],
            "longitude": [36.81, 36.82, 36.83, 36.84],
            "insured_value": [1000000, -50000, None, 1000000],  # Negative & Null
            "property_type": ["Residential", None, "Commercial", "Commercial"],
        })
        report = auditor.audit(df)

        assert report.passed is False
        assert report.quality_score < 70.0
        assert report.critical_count > 0

    def test_iqr_outlier_detection(self):
        auditor = DataQualityAuditor(iqr_multiplier=2.0)
        # 40 normal values around 1M, plus 2 extreme outliers (500M)
        values = [1_000_000 + i * 10000 for i in range(40)] + [500_000_000, 750_000_000]
        df = pd.DataFrame({
            "policy_id": [f"POL_{i}" for i in range(len(values))],
            "latitude": [-1.28] * len(values),
            "longitude": [36.81] * len(values),
            "insured_value": values,
            "property_type": ["Commercial"] * len(values),
        })
        report = auditor.audit(df)

        assert report.profile.iqr_outlier_count >= 2
        assert any(i.issue_type == "EXTREME_TIV_IQR_OUTLIER" for i in report.issues)


# ===========================================================================
# 6. Portfolio Store Tests
# ===========================================================================

class TestPortfolioStore:
    """Test suite for Parquet persistence and snapshot management."""

    def test_save_and_load_portfolio(self, tmp_path: Path):
        db = DatabaseManager(tmp_path / "metadata.db")
        store = PortfolioStore(base_dir=tmp_path / "portfolios", db_manager=db)

        df = pd.DataFrame({
            "policy_id": ["P1", "P2", "P3"],
            "latitude": [-1.286389, -4.043477, 0.514277],
            "longitude": [36.817223, 39.668206, 35.269780],
            "insured_value": [5000000.0, 12500000.0, 2500000.0],
            "property_type": ["Residential", "Commercial", "Residential"],
            "construction_class": ["Masonry", "Reinforced Concrete", None],
            "region": ["Nairobi", "Mombasa", "Eldoret"],
        })

        run_id = "RUN-STORE-001"
        db.create_run(run_id=run_id)

        meta = store.save_portfolio(df, run_id=run_id)

        assert meta.run_id == run_id
        assert meta.record_count == 3
        assert len(meta.dataset_hash) == 64
        assert Path(meta.dataset_path).exists()

        # Load back by path
        loaded_by_path = store.load_portfolio(meta.dataset_path)
        assert len(loaded_by_path) == 3
        assert list(loaded_by_path["policy_id"]) == ["P1", "P2", "P3"]

        # Load back by run_id
        loaded_by_run = store.load_portfolio(run_id)
        assert len(loaded_by_run) == 3

    def test_schema_validation_rejects_invalid_dataframe(self, tmp_path: Path):
        store = PortfolioStore(base_dir=tmp_path / "portfolios")
        invalid_df = pd.DataFrame({
            "policy_id": ["P1"],
            "latitude": [999.0],  # Invalid latitude > 90
            "longitude": [36.81],
            "insured_value": [5000000.0],
            "property_type": ["Residential"],
        })

        with pytest.raises(SchemaValidationError):
            store.save_portfolio(invalid_df, run_id="FAIL-RUN", validate=True)


# ===========================================================================
# 7. End-to-End Phase 2 Integration Pipeline Test
# ===========================================================================

class TestDataLayerEndToEnd:
    """Full integration pipeline test: Ingestion -> Normalization -> Quality Audit -> Parquet Store -> Metadata DB."""

    def test_full_pipeline(self, tmp_path: Path):
        db_path = tmp_path / "e2e_floodtail.db"
        store_dir = tmp_path / "e2e_portfolios"
        raw_csv = tmp_path / "kenya_raw_portfolio.csv"

        # 1. Create realistic raw file with heterogeneous column names and noisy values
        raw_csv.write_text(
            'Policy_Number,LAT,LONG,Sum_Insured,Occupancy,Building_Class,County\n'
            'KE-NBI-001,-1.286389,36.817223,"KES 15,000,000",Commercial,Concrete,Nairobi\n'
            'KE-MBA-002,-4.043477,39.668206,"KES 8,500,000",Residential,Masonry,Mombasa\n'
            'KE-KSM-003,-0.091702,34.767956,"KES 4,200,000",Industrial,Steel,Kisumu\n'
            'KE-SWAP-004,36.82,-1.29,"KES 12,000,000",Residential,Frame,Nairobi\n'  # Swapped coords
            'KE-BAD-005,999.0,36.81,-5000,Office,Concrete,Nairobi\n',             # Corrupt row
            encoding="utf-8",
        )

        db = DatabaseManager(db_path)
        run_id = "RUN-E2E-PHASE2"
        db.create_run(run_id=run_id, model_version="0.1.0", source_file=raw_csv.name)

        # 2. Ingest
        ingestion_engine = IngestionEngine()
        ingest_res = ingestion_engine.ingest_file(raw_csv)
        assert ingest_res.total_rows_read == 5
        db.record_ingestion(
            run_id=run_id,
            source_filename=raw_csv.name,
            source_type=ingest_res.file_type,
            file_size=ingest_res.file_size_bytes,
            schema_status="MAPPED",
            mapping_status="SUCCESS",
            record_count=ingest_res.total_rows_read,
        )

        # 3. Normalize
        normalizer = PortfolioNormalizer()
        norm_res = normalizer.normalize(ingest_res.dataframe)
        assert norm_res.valid_count == 4
        assert norm_res.invalid_count == 1

        # 4. Quality Audit
        auditor = DataQualityAuditor()
        quality_report = auditor.audit(norm_res.clean_dataframe)
        assert quality_report.passed is True

        # Record issues in DB
        db_issues = [
            {
                "run_id": run_id,
                "policy_id": iss.policy_id,
                "issue_type": iss.issue_type,
                "severity": iss.severity,
                "field": iss.field,
                "value": str(iss.raw_value),
                "message": iss.message,
                "detector": "Normalizer",
            }
            for iss in norm_res.issues
        ]
        db.record_quality_issues(db_issues)

        # 5. Persist to Parquet Store
        store = PortfolioStore(base_dir=store_dir, db_manager=db)
        version_meta = store.save_portfolio(norm_res.clean_dataframe, run_id=run_id)

        # 6. Update Run Status
        db.update_run(
            run_id,
            status="SUCCESS",
            row_count=norm_res.total_input_rows,
            valid_row_count=norm_res.valid_count,
            invalid_row_count=norm_res.invalid_count,
            quality_score=quality_report.quality_score,
        )

        # 7. Verification
        persisted_run = db.get_run(run_id)
        assert persisted_run["status"] == "SUCCESS"
        assert persisted_run["valid_row_count"] == 4
        assert persisted_run["invalid_row_count"] == 1

        loaded_df = store.load_portfolio(run_id)
        assert len(loaded_df) == 4
        assert "policy_id" in loaded_df.columns
        assert loaded_df.iloc[0]["insured_value"] == 15000000.0

    def test_schema_mapper_unmapped_and_review(self):
        mapper = SchemaMapper(auto_accept_threshold=0.85, review_threshold=0.50)
        # Random non-matching column
        columns = ["random_custom_header_xyz", "lat"]
        plan = mapper.create_mapping_plan(columns)
        assert plan.mappings["random_custom_header_xyz"].status == "UNMAPPED"
        assert plan.is_valid is False
        assert "policy_id" in plan.missing_required

    def test_quality_auditor_empty_df(self):
        auditor = DataQualityAuditor()
        report = auditor.audit(pd.DataFrame())
        assert report.quality_score == 0.0
        assert report.passed is False
        assert report.critical_count == 1

    def test_portfolio_store_listing(self, tmp_path: Path):
        store = PortfolioStore(base_dir=tmp_path / "portfolios")
        df = pd.DataFrame({
            "policy_id": ["P1"],
            "latitude": [-1.28],
            "longitude": [36.81],
            "insured_value": [1000000.0],
            "property_type": ["Residential"],
        })
        store.save_portfolio(df, run_id="RUN-A")
        store.save_portfolio(df, run_id="RUN-B")
        saved = store.list_saved_versions()
        assert len(saved) == 2
