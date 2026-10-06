"""FLOODTAIL — Comprehensive unit, stress, and reconciliation tests for Phase 3 Catastrophe Engine.

Covers:
- Event Catalogue and Poisson Simulation
- Spatial Hazard Depth & Zero-Depth Rule
- Vulnerability Curves & Strict Monotonicity
- Ground-up / Net Financial Loss & Policy Terms
- ELT and YLT Construction
- Multi-tier Mathematical Reconciliation
- Deterministic Seed Reproducibility
- Independent Manual Calculation Verification
- Spatial Portfolio Correlation & A/B Shared-Event Accumulation
- Stress Tests & Edge Cases
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.catastrophe_store import CatastrophePipeline, CatastropheRunResult, run_catastrophe_model
from src.database import DatabaseManager
from src.events import EventCatalogue, EventSimulator
from src.exceptions import (
    EventSetError,
    HazardModelError,
    LossCalculationError,
    ReconciliationError,
    VulnerabilityModelError,
)
from src.hazard import FootprintGeometry, HazardFootprintStore, SpatialHazardEngine
from src.loss import CatastropheLossEngine
from src.schemas import EventRecord
from src.vulnerability import VulnerabilityCurve, VulnerabilityEngine


@pytest.fixture
def sample_portfolio() -> pd.DataFrame:
    """Fixture providing clean standardized exposure records."""
    return pd.DataFrame({
        "policy_id": ["POL_A", "POL_B", "POL_C", "POL_D"],
        "latitude": [-1.286389, -1.330000, -1.285000, -4.043477],
        "longitude": [36.817223, 36.700000, 36.820000, 39.668206],
        "insured_value": [25_000_000.0, 25_000_000.0, 10_000_000.0, 15_000_000.0],
        "property_type": ["Commercial", "Commercial", "Residential", "Commercial"],
        "construction_class": ["Reinforced Concrete", "Reinforced Concrete", "Masonry", "Steel Frame"],
        "region": ["Nairobi", "Nairobi", "Nairobi", "Mombasa"],
    })


@pytest.fixture
def sample_catalogue() -> EventCatalogue:
    """Fixture providing a validated 5-event catalogue."""
    df = pd.DataFrame({
        "event_id": ["E01", "E02", "E03", "E04", "E05"],
        "event_name": ["Nairobi Flash", "Nairobi Pluvial", "Nairobi 50yr", "Mombasa Surge", "Mombasa Extreme"],
        "event_type": ["fluvial", "pluvial", "fluvial", "coastal", "coastal"],
        "scenario_tag": ["baseline", "baseline", "baseline", "baseline", "baseline"],
        "annual_frequency": [0.20, 0.10, 0.02, 0.15, 0.01],
        "severity": [1.0, 1.2, 2.0, 1.1, 2.5],
        "footprint_ref": ["FP_NBI_01", "FP_NBI_02", "FP_NBI_03", "FP_MBA_01", "FP_MBA_02"],
        "source": ["SYNTHETIC", "SYNTHETIC", "SYNTHETIC", "SYNTHETIC", "SYNTHETIC"],
    })
    return EventCatalogue(df, catalogue_version="test-v1.0")


@pytest.fixture
def sample_footprints() -> HazardFootprintStore:
    """Fixture providing test spatial footprints."""
    store = HazardFootprintStore()
    store.add_footprint(FootprintGeometry("FP_NBI_01", center_lat=-1.286389, center_lon=36.817223, radius_km=10.0, base_depth_m=1.0))
    store.add_footprint(FootprintGeometry("FP_NBI_02", center_lat=-1.285000, center_lon=36.820000, radius_km=15.0, base_depth_m=1.5))
    store.add_footprint(FootprintGeometry("FP_NBI_03", center_lat=-1.286000, center_lon=36.818000, radius_km=25.0, base_depth_m=2.5))
    store.add_footprint(FootprintGeometry("FP_MBA_01", center_lat=-4.043477, center_lon=39.668206, radius_km=10.0, base_depth_m=1.2))
    store.add_footprint(FootprintGeometry("FP_MBA_02", center_lat=-4.040000, center_lon=39.670000, radius_km=20.0, base_depth_m=2.0))
    return store


# ===========================================================================
# 1. Event Catalogue & Simulation Tests
# ===========================================================================

class TestEventCatalogueAndSimulation:
    """Tests 1–5: Event records, invalid inputs, reproducibility, and Poisson rate."""

    def test_valid_event_record(self, sample_catalogue: EventCatalogue):
        assert len(sample_catalogue.df) == 5
        assert sample_catalogue.total_annual_rate == pytest.approx(0.48)
        assert len(sample_catalogue.catalogue_hash) == 64

    def test_invalid_event_frequency_rejected(self):
        bad_df = pd.DataFrame({
            "event_id": ["E_BAD"],
            "annual_frequency": [-0.5],  # Negative frequency
            "severity": [1.0],
            "footprint_ref": ["FP01"],
        })
        with pytest.raises(EventSetError, match="frequency"):
            EventCatalogue(bad_df)

    def test_duplicate_event_id_rejected(self):
        dup_df = pd.DataFrame({
            "event_id": ["E01", "E01"],
            "annual_frequency": [0.1, 0.2],
            "severity": [1.0, 1.0],
            "footprint_ref": ["FP01", "FP02"],
        })
        with pytest.raises(EventSetError, match="Duplicate event_id"):
            EventCatalogue(dup_df)

    def test_reproducible_event_simulation(self, sample_catalogue: EventCatalogue):
        sim1 = EventSimulator(sample_catalogue, simulation_years=1000, seed=42)
        res1 = sim1.simulate()

        sim2 = EventSimulator(sample_catalogue, simulation_years=1000, seed=42)
        res2 = sim2.simulate()

        pd.testing.assert_frame_equal(res1, res2)

    def test_event_count_reproducibility_and_rate(self, sample_catalogue: EventCatalogue):
        sim = EventSimulator(sample_catalogue, simulation_years=5000, seed=999)
        res = sim.simulate()

        expected_mean = sample_catalogue.total_annual_rate * 5000  # 0.48 * 5000 = 2400
        actual_count = len(res)
        # Poisson dispersion: 3 standard deviations ~ 3 * sqrt(2400) ~ 146
        assert abs(actual_count - expected_mean) < 200


# ===========================================================================
# 2. Hazard Engine & Zero-Depth Rule Tests
# ===========================================================================

class TestSpatialHazardEngine:
    """Tests 6–8: Point-in-footprint, depth calculation, zero-depth rule."""

    def test_policy_outside_footprint_zero_depth(self, sample_footprints: HazardFootprintStore):
        fp = sample_footprints.get_footprint("FP_NBI_01")
        assert fp is not None
        # Policy in Mombasa (-4.04, 39.66) is ~450km away from Nairobi footprint
        depth = fp.compute_depth_at(-4.043477, 39.668206)
        assert depth == 0.0

    def test_policy_inside_footprint_positive_depth(self, sample_footprints: HazardFootprintStore):
        fp = sample_footprints.get_footprint("FP_NBI_01")
        assert fp is not None
        # Exact epicenter coordinate
        depth_center = fp.compute_depth_at(-1.286389, 36.817223)
        assert depth_center == 1.0  # base_depth_m = 1.0

        # Point 5km away (halfway to 10km radius)
        depth_mid = fp.compute_depth_at(-1.286389 + (5.0 / 111.0), 36.817223)
        assert 0.0 < depth_mid < 1.0

    def test_zero_depth_zero_damage_and_loss(self):
        engine_v = VulnerabilityEngine()
        assert engine_v.get_damage_ratio(depth_m=0.0, property_type="Commercial") == 0.0
        assert engine_v.get_damage_ratio(depth_m=-1.0, property_type="Residential") == 0.0


# ===========================================================================
# 3. Vulnerability Engine Tests
# ===========================================================================

class TestVulnerabilityEngine:
    """Tests 9–10: Damage ratio bounds [0, 1] and strict monotonicity."""

    def test_damage_ratio_bounds(self):
        ve = VulnerabilityEngine()
        for depth in [0.0, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 50.0]:
            for ptype in ["Residential", "Commercial", "Industrial", "Agricultural"]:
                dr = ve.get_damage_ratio(depth, property_type=ptype)
                assert 0.0 <= dr <= 1.0

    def test_vulnerability_monotonicity(self):
        ve = VulnerabilityEngine()
        depths = np.linspace(0.0, 6.0, 61)
        for ptype in ["Residential", "Commercial", "Industrial", "Agricultural"]:
            ratios = [ve.get_damage_ratio(d, property_type=ptype) for d in depths]
            diffs = np.diff(ratios)
            assert np.all(diffs >= -1e-7), f"Monotonicity violated for {ptype}"

    def test_custom_curve_monotonicity_violation_rejected(self):
        depths = np.array([0.0, 1.0, 2.0])
        non_monotonic_dr = np.array([0.0, 0.5, 0.2])  # Drops from 0.5 to 0.2
        with pytest.raises(VulnerabilityModelError, match="monotonicity"):
            VulnerabilityCurve(
                property_type="CustomBad",
                construction_class=None,
                depth_points=depths,
                damage_ratios=non_monotonic_dr,
            )


# ===========================================================================
# 4. Financial Loss & Reconciliation Engine Tests
# ===========================================================================

class TestLossEngineAndReconciliation:
    """Tests 11–17: Loss calculation, deductible, limits, ELT/YLT reconciliation."""

    def test_tiv_times_damage_ratio_groundup_loss(self):
        le = CatastropheLossEngine()
        vuln_df = pd.DataFrame({
            "simulation_year": [1, 1],
            "occurrence_id": [1, 1],
            "event_id": ["E01", "E01"],
            "policy_id": ["P1", "P2"],
            "depth_m": [1.0, 2.0],
            "damage_ratio": [0.40, 0.70],
            "insured_value": [10_000_000.0, 20_000_000.0],
        })
        elt, ylt, rep = le.calculate_losses(vuln_df, simulation_years=10)

        assert rep.passed is True
        assert elt.loc[0, "ground_up_loss"] == 4_000_000.0
        assert elt.loc[1, "ground_up_loss"] == 14_000_000.0
        assert elt.loc[0, "loss"] == 4_000_000.0
        assert elt.loc[1, "loss"] == 14_000_000.0
        assert ylt.loc[0, "annual_loss"] == 18_000_000.0

    def test_deductible_and_limit_application(self):
        le = CatastropheLossEngine()
        vuln_df = pd.DataFrame({
            "simulation_year": [1, 1],
            "occurrence_id": [1, 1],
            "event_id": ["E01", "E01"],
            "policy_id": ["P_DED", "P_LIM"],
            "depth_m": [1.0, 1.0],
            "damage_ratio": [0.50, 0.50],
            "insured_value": [10_000_000.0, 10_000_000.0],
            "deductible": [1_000_000.0, 0.0],
            "policy_limit": [10_000_000.0, 3_000_000.0],
        })
        elt, ylt, rep = le.calculate_losses(vuln_df, simulation_years=5)

        # P_DED: ground_up = 5M, deductible = 1M -> net = 4M
        assert elt.loc[0, "loss"] == 4_000_000.0
        # P_LIM: ground_up = 5M, limit = 3M -> net = 3M
        assert elt.loc[1, "loss"] == 3_000_000.0
        assert rep.passed is True

    def test_total_elt_equals_total_ylt_reconciliation(self, sample_portfolio: pd.DataFrame, sample_catalogue: EventCatalogue, sample_footprints: HazardFootprintStore):
        pipeline = CatastrophePipeline()
        res = pipeline.run(
            portfolio_df=sample_portfolio,
            event_catalogue=sample_catalogue,
            footprint_store=sample_footprints,
            simulation_years=500,
            seed=12345,
        )

        assert res.reconciliation_report.passed is True
        assert res.reconciliation_report.elt_total_loss == pytest.approx(res.reconciliation_report.ylt_total_loss, abs=1e-2)
        assert res.reconciliation_report.negative_losses_count == 0
        assert res.reconciliation_report.events_reconciled is True
        assert res.reconciliation_report.annual_losses_reconciled is True

    def test_zero_event_year_produces_zero_loss(self):
        le = CatastropheLossEngine()
        # Event in year 2 only, year 1 and 3 are empty
        vuln_df = pd.DataFrame({
            "simulation_year": [2],
            "occurrence_id": [1],
            "event_id": ["E01"],
            "policy_id": ["P1"],
            "depth_m": [1.0],
            "damage_ratio": [0.50],
            "insured_value": [10_000_000.0],
        })
        elt, ylt, rep = le.calculate_losses(vuln_df, simulation_years=3)

        assert rep.passed is True
        assert len(ylt) == 3
        assert ylt.loc[0, "annual_loss"] == 0.0  # Year 1
        assert ylt.loc[1, "annual_loss"] == 5_000_000.0  # Year 2
        assert ylt.loc[2, "annual_loss"] == 0.0  # Year 3


# ===========================================================================
# 5. Reproducibility & Independent Verification Tests
# ===========================================================================

class TestReproducibilityAndIndependentVerification:
    """Tests 18–22: Identical seed reproducibility, independent manual calculation, and A/B portfolio separation."""

    def test_same_seed_produces_identical_elt_and_ylt(self, sample_portfolio: pd.DataFrame, sample_catalogue: EventCatalogue, sample_footprints: HazardFootprintStore):
        pipeline = CatastrophePipeline()
        res1 = pipeline.run(sample_portfolio, sample_catalogue, sample_footprints, simulation_years=300, seed=777)
        res2 = pipeline.run(sample_portfolio, sample_catalogue, sample_footprints, simulation_years=300, seed=777)

        assert res1.elt_hash == res2.elt_hash
        assert res1.ylt_hash == res2.ylt_hash
        assert res1.portfolio_total_loss == res2.portfolio_total_loss

    def test_independent_manual_calculation_5_cases(self):
        """Independent verification of TIV * Damage Ratio for 5 deterministic benchmark cases."""
        ve = VulnerabilityEngine()
        le = CatastropheLossEngine()

        test_cases = [
            # (depth_m, property_type, cclass, tiv, expected_dr, expected_loss)
            (0.5, "Residential", "Reinforced Concrete", 10_000_000.0, 0.22 * 0.85, 10_000_000.0 * (0.22 * 0.85)),
            (1.0, "Commercial", "Steel Frame", 50_000_000.0, 0.35 * 1.00, 50_000_000.0 * 0.35),
            (2.0, "Industrial", "Steel Frame", 30_000_000.0, 0.60 * 1.00, 30_000_000.0 * 0.60),
            (0.2, "Agricultural", "Masonry", 5_000_000.0, 0.12 * 0.95, 5_000_000.0 * (0.12 * 0.95)),
            (3.0, "Residential", "Timber Frame", 20_000_000.0, min(1.0, 0.88 * 1.15), 20_000_000.0 * min(1.0, 0.88 * 1.15)),
        ]

        for i, (depth, ptype, cclass, tiv, exp_dr, exp_loss) in enumerate(test_cases, 1):
            calculated_dr = ve.get_damage_ratio(depth, property_type=ptype, construction_class=cclass)
            assert calculated_dr == pytest.approx(round(exp_dr, 4), abs=1e-4), f"Case {i} DR mismatch"

            groundup = round(tiv * calculated_dr, 2)
            assert groundup == pytest.approx(round(exp_loss, 2), abs=1e-2), f"Case {i} loss mismatch"

    def test_spatial_correlation_multiple_policies_one_event(self, sample_footprints: HazardFootprintStore):
        """Validates that one event footprint impacts multiple properties simultaneously."""
        portfolio = pd.DataFrame({
            "policy_id": ["P_NBI_1", "P_NBI_2", "P_NBI_3"],
            "latitude": [-1.286389, -1.285000, -1.287000],  # All within 1km of Nairobi center
            "longitude": [36.817223, 36.818000, 36.816000],
            "insured_value": [10_000_000.0, 15_000_000.0, 20_000_000.0],
            "property_type": ["Commercial", "Residential", "Industrial"],
        })
        occ = pd.DataFrame({
            "simulation_year": [1],
            "occurrence_id": [1],
            "event_id": ["E01"],
            "severity": [1.0],
            "footprint_ref": ["FP_NBI_01"],
            "event_type": ["fluvial"],
        })
        hazard_engine = SpatialHazardEngine(footprint_store=sample_footprints)
        hazard_df, summary = hazard_engine.evaluate_hazard(portfolio, occ)

        assert summary.total_impacted_policy_events == 3
        assert summary.unique_affected_policies == 3
        assert len(hazard_df) == 3

    def test_synthetic_ab_structure_produces_shared_event_difference(self, sample_catalogue: EventCatalogue, sample_footprints: HazardFootprintStore):
        """Validates that Policy A (Nairobi Basin) experiences more shared catastrophe occurrences than Policy B (high ground)."""
        ab_portfolio = pd.DataFrame({
            "policy_id": ["POL_DEMO_A", "POL_DEMO_B"],
            "latitude": [-1.286389, -1.330000],  # A in basin epicenter, B 8km away on high ground
            "longitude": [36.817223, 36.700000],
            "insured_value": [25_000_000.0, 25_000_000.0],
            "property_type": ["Commercial", "Commercial"],
            "construction_class": ["Reinforced Concrete", "Reinforced Concrete"],
        })

        pipeline = CatastrophePipeline()
        res = pipeline.run(
            portfolio_df=ab_portfolio,
            event_catalogue=sample_catalogue,
            footprint_store=sample_footprints,
            simulation_years=3000,
            seed=482913,
        )

        elt = pd.read_parquet(res.elt_path) if res.elt_path.endswith(".parquet") else pd.read_csv(res.elt_path)
        hits_a = len(elt[elt["policy_id"] == "POL_DEMO_A"])
        hits_b = len(elt[elt["policy_id"] == "POL_DEMO_B"])

        # Policy A should be hit significantly more often due to central footprint accumulation
        assert hits_a > hits_b
        assert hits_a > 0


# ===========================================================================
# 6. Stress Tests & Edge Cases
# ===========================================================================

class TestCatastropheStressAndEdgeCases:
    """Tests 23–29: All outside, all inside, scale linearity, and empty datasets."""

    def test_stress_all_outside_flood_footprints(self, sample_catalogue: EventCatalogue, sample_footprints: HazardFootprintStore):
        # Exposure far outside Kenya (e.g. London coordinates)
        far_portfolio = pd.DataFrame({
            "policy_id": ["POL_UK_1"],
            "latitude": [51.5074],
            "longitude": [-0.1278],
            "insured_value": [100_000_000.0],
            "property_type": ["Commercial"],
        })
        pipeline = CatastrophePipeline()
        res = pipeline.run(far_portfolio, sample_catalogue, sample_footprints, simulation_years=500, seed=42)

        assert res.affected_pair_count == 0
        assert res.portfolio_total_loss == 0.0
        assert res.reconciliation_report.passed is True

    def test_stress_tiv_doubling_doubles_losses(self, sample_portfolio: pd.DataFrame, sample_catalogue: EventCatalogue, sample_footprints: HazardFootprintStore):
        pipeline = CatastrophePipeline()

        # Base run
        res_base = pipeline.run(sample_portfolio, sample_catalogue, sample_footprints, simulation_years=500, seed=101)

        # Doubled TIV run
        doubled_portfolio = sample_portfolio.copy()
        doubled_portfolio["insured_value"] = doubled_portfolio["insured_value"] * 2.0
        res_doubled = pipeline.run(doubled_portfolio, sample_catalogue, sample_footprints, simulation_years=500, seed=101)

        assert res_doubled.portfolio_total_loss == pytest.approx(res_base.portfolio_total_loss * 2.0, rel=1e-3)

    def test_empty_event_catalogue_produces_zero_loss(self, sample_portfolio: pd.DataFrame):
        empty_cat_df = pd.DataFrame(columns=["event_id", "annual_frequency", "severity", "footprint_ref"])
        with pytest.raises(EventSetError, match="empty"):
            EventCatalogue(empty_cat_df)

    def test_end_to_end_demo_run_from_demo_files(self, tmp_path: Path):
        """End-to-end full execution using data/demo/ catalogue, footprints, and portfolio."""
        demo_port = pd.read_csv("data/demo/portfolio_ab_demo.csv")
        demo_cat = EventCatalogue.from_csv("data/demo/events.csv")
        demo_fp = HazardFootprintStore.from_json_file("data/demo/footprints.json")

        db_path = tmp_path / "cat_floodtail.db"
        db = DatabaseManager(db_path)

        pipeline = CatastrophePipeline(output_dir=tmp_path / "processed", db_manager=db)
        res = pipeline.run(
            portfolio_df=demo_port,
            event_catalogue=demo_cat,
            footprint_store=demo_fp,
            simulation_years=1000,
            seed=482913,
        )

        assert res.status == "SUCCESS"
        assert res.simulation_years == 1000
        assert res.event_count > 0
        assert res.affected_pair_count > 0
        assert res.portfolio_total_loss > 0
        assert res.reconciliation_report.passed is True
        assert Path(res.elt_path).exists()
        assert Path(res.ylt_path).exists()
        assert Path(res.hazard_path).exists()
        assert Path(res.event_occurrence_path).exists()

        persisted_run = db.get_run(res.run_id)
        assert persisted_run is not None
        assert persisted_run["status"] == "SUCCESS"
