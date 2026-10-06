"""FLOODTAIL — Catastrophe Pipeline Orchestrator, Output Store & Run Registry.

Orchestrates the complete catastrophe risk pipeline:
    Clean Exposure Portfolio + Stochastic Event Catalogue
    → Monte Carlo Event Simulation
    → Spatial Hazard Intersection (depth_m)
    → Vulnerability Damage Ratios
    → Financial Losses (Ground-up & Net)
    → Event Loss Table (ELT)
    → Year Loss Table (YLT)
    → Multi-Tier Reconciliation
    → SHA-256 Dataset Hashing & SQLite Lineage Persistence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd

from src.config import FLOODTAILConfig, load_config
from src.database import DatabaseManager
from src.events import EventCatalogue, EventSimulator
from src.exceptions import (
    EventSetError,
    HazardModelError,
    LossCalculationError,
    ReconciliationError,
    VulnerabilityModelError,
)
from src.hazard import HazardFootprintStore, SpatialHazardEngine
from src.logging_config import get_logger
from src.loss import CatastropheLossEngine, ReconciliationReport
from src.schemas import RunContext
from src.vulnerability import VulnerabilityEngine

logger = get_logger("catastrophe_store")


@dataclass
class CatastropheRunResult:
    """Standardized envelope containing outputs, paths, hashes, and audit status of a catastrophe run."""

    run_id: str
    simulation_years: int
    event_count: int
    affected_pair_count: int
    portfolio_total_loss: float
    elt_path: str
    ylt_path: str
    hazard_path: str
    event_occurrence_path: str
    elt_hash: str
    ylt_hash: str
    reconciliation_report: ReconciliationReport
    warnings: list[str] = field(default_factory=list)
    status: str = "SUCCESS"  # 'SUCCESS', 'WARNING', 'FAILED'
    metadata: dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CatastrophePipeline:
    """Full-pipeline catastrophe risk calculation and persistence engine."""

    def __init__(
        self,
        output_dir: Union[str, Path] = "data/processed",
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[FLOODTAILConfig] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_manager = db_manager
        self.config = config

    @staticmethod
    def compute_df_sha256(df: pd.DataFrame) -> str:
        """Deterministic SHA-256 hash of a dataframe."""
        serialized = df.to_json(orient="records", date_format="iso").encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _save_table(
        self,
        df: pd.DataFrame,
        run_id: str,
        table_name: str,
    ) -> tuple[Path, str]:
        """Save dataframe to Parquet (or compressed CSV fallback) and compute hash."""
        target_path = self.output_dir / f"{table_name}_{run_id[:8]}.parquet"
        try:
            df.to_parquet(target_path, index=False)
        except Exception:
            target_path = self.output_dir / f"{table_name}_{run_id[:8]}.csv.gz"
            df.to_csv(target_path, index=False, compression="gzip")

        table_hash = self.compute_df_sha256(df)
        return target_path, table_hash

    def run(
        self,
        portfolio_df: pd.DataFrame,
        event_catalogue: Optional[EventCatalogue] = None,
        footprint_store: Optional[HazardFootprintStore] = None,
        vulnerability_engine: Optional[VulnerabilityEngine] = None,
        simulation_years: Optional[int] = None,
        seed: Optional[int] = None,
        run_context: Optional[RunContext] = None,
        deductible: float = 0.0,
        policy_limit: Optional[float] = None,
    ) -> CatastropheRunResult:
        """Execute the end-to-end catastrophe modeling pipeline."""
        start_time = datetime.now(timezone.utc)
        cfg = self.config or load_config()

        # Simulation parameters
        sim_years = simulation_years or (cfg.catastrophe.simulation_years if cfg.catastrophe else cfg.simulation.years)
        sim_seed = seed if seed is not None else (cfg.catastrophe.seed if cfg.catastrophe else cfg.simulation.seed)

        # Run Context
        ctx = run_context or RunContext(
            model_version=cfg.model.model_version,
            random_seed=sim_seed,
            simulation_years=sim_years,
            scenario="baseline",
        )
        run_id = ctx.run_id

        logger.info(
            "=== FLOODTAIL Catastrophe Pipeline Started (run_id=%s, years=%d, seed=%d) ===",
            run_id,
            sim_years,
            sim_seed,
        )

        warnings: list[str] = []

        # 1. Prepare Event Catalogue
        if event_catalogue is None:
            cat_path = Path(cfg.catastrophe.event_catalogue_path if cfg.catastrophe else "data/demo/events.csv")
            event_catalogue = EventCatalogue.from_csv(cat_path)

        # 2. Prepare Footprint Store
        if footprint_store is None:
            fp_path = Path(cfg.catastrophe.footprints_path if cfg.catastrophe else "data/demo/footprints.json")
            footprint_store = HazardFootprintStore.from_json_file(fp_path)

        # 3. Prepare Vulnerability Engine
        if vulnerability_engine is None:
            vulnerability_engine = VulnerabilityEngine()

        loss_engine = CatastropheLossEngine()

        # 4. Stochastic Event Simulation
        logger.info("Simulating stochastic event occurrences...")
        simulator = EventSimulator(
            catalogue=event_catalogue,
            simulation_years=sim_years,
            seed=sim_seed,
        )
        event_occurrences_df = simulator.simulate()

        # 5. Spatial Hazard Intersection
        logger.info("Evaluating spatial flood hazard fields...")
        hazard_engine = SpatialHazardEngine(footprint_store=footprint_store)
        hazard_df, hazard_summary = hazard_engine.evaluate_hazard(
            portfolio_df=portfolio_df,
            event_occurrences_df=event_occurrences_df,
            sparse=True,
        )

        # 6. Vulnerability Evaluation
        logger.info("Applying vulnerability curves...")
        vuln_df = vulnerability_engine.evaluate_vulnerability(
            hazard_df=hazard_df,
            portfolio_df=portfolio_df,
        )

        # 7. Financial Loss Calculation & ELT/YLT Construction
        logger.info("Calculating losses, constructing ELT and YLT, and reconciling...")
        elt_df, ylt_df, recon_report = loss_engine.calculate_losses(
            vulnerability_df=vuln_df,
            simulation_years=sim_years,
            default_deductible=deductible,
            default_limit=policy_limit,
        )

        if not recon_report.passed:
            raise ReconciliationError(
                f"Reconciliation check failed for run {run_id}: ELT total {recon_report.elt_total_loss} != YLT total {recon_report.ylt_total_loss}"
            )

        # 8. Persist Processed Datasets
        occ_path, occ_hash = self._save_table(event_occurrences_df, run_id, "event_occurrences")
        haz_path, haz_hash = self._save_table(hazard_df, run_id, "hazard_results")
        elt_path, elt_hash = self._save_table(elt_df, run_id, "elt")
        ylt_path, ylt_hash = self._save_table(ylt_df, run_id, "ylt")

        # 9. Register in Metadata Database if available
        if self.db_manager:
            try:
                self.db_manager.create_run(
                    run_id=run_id,
                    model_version=ctx.model_version,
                    data_version=ctx.data_version or "v1.0",
                    status="SUCCESS",
                    source_file=str(occ_path.name),
                )
                self.db_manager.update_run(
                    run_id=run_id,
                    row_count=len(portfolio_df),
                    valid_row_count=len(portfolio_df),
                    invalid_row_count=0,
                    quality_score=100.0,
                )
                self.db_manager.record_portfolio_version(
                    run_id=run_id,
                    dataset_path=str(elt_path),
                    dataset_hash=elt_hash,
                    record_count=len(elt_df),
                )
            except Exception as e:
                logger.error("Failed to update database metadata for catastrophe run: %s", e)
                warnings.append(f"Database registration warning: {e}")

        status = "SUCCESS" if recon_report.passed and len(warnings) == 0 else "WARNING"

        logger.info(
            "=== FLOODTAIL Catastrophe Pipeline Finished: Total Portfolio Loss = $%s across %d years (status=%s) ===",
            f"{recon_report.elt_total_loss:,.2f}",
            sim_years,
            status,
        )

        return CatastropheRunResult(
            run_id=run_id,
            simulation_years=sim_years,
            event_count=len(event_occurrences_df),
            affected_pair_count=len(elt_df),
            portfolio_total_loss=recon_report.elt_total_loss,
            elt_path=str(elt_path),
            ylt_path=str(ylt_path),
            hazard_path=str(haz_path),
            event_occurrence_path=str(occ_path),
            elt_hash=elt_hash,
            ylt_hash=ylt_hash,
            reconciliation_report=recon_report,
            warnings=warnings,
            status=status,
            metadata={
                "catalogue_version": event_catalogue.catalogue_version,
                "catalogue_hash": event_catalogue.catalogue_hash,
                "hazard_source": hazard_engine.hazard_source,
                "vulnerability_source": vulnerability_engine.curve_source,
                "exposed_tiv_sum": hazard_summary.total_exposed_tiv,
                "unique_affected_policies": hazard_summary.unique_affected_policies,
                "mean_impacted_depth_m": hazard_summary.mean_impacted_depth_m,
                "max_impacted_depth_m": hazard_summary.max_impacted_depth_m,
            },
            executed_at=start_time,
        )


def run_catastrophe_model(
    portfolio_df: pd.DataFrame,
    simulation_years: Optional[int] = None,
    seed: Optional[int] = None,
    output_dir: Union[str, Path] = "data/processed",
    db_manager: Optional[DatabaseManager] = None,
    config: Optional[FLOODTAILConfig] = None,
) -> CatastropheRunResult:
    """Convenience functional orchestrator for the complete catastrophe pipeline."""
    pipeline = CatastrophePipeline(
        output_dir=output_dir,
        db_manager=db_manager,
        config=config,
    )
    return pipeline.run(
        portfolio_df=portfolio_df,
        simulation_years=simulation_years,
        seed=seed,
    )
