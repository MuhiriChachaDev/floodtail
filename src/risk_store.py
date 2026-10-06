"""FLOODTAIL — Risk Analytics Store, Dataset Persistence & Full Phase 4 Orchestrator.

Orchestrates the entire risk-to-price analytical pipeline:
    YLT + ELT + Portfolio
    → Risk Metrics (AAL, OEP, AEP, PML, VaR, TVaR)
    → Policy Tail Contribution & Reconciliation
    → Accumulation & Spatial Co-Hit Analytics
    → Technical Pricing Waterfall
    → Marginal TVaR Impact & Risk Appetite Recommendations
    → Output Parquet Persistence & SQLite Provenance Registry.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd

from src.accumulation import AccumulationAnalysisResult, PortfolioAccumulationEngine
from src.config import FLOODTAILConfig, load_config
from src.counterfactual import (
    CounterfactualEngine,
    MarginalRiskImpact,
    RiskAppetiteConfig,
    RiskAppetiteRuleEngine,
    RiskRecommendation,
)
from src.database import DatabaseManager
from src.exceptions import ModelCalculationError, ReconciliationError
from src.logging_config import get_logger
from src.pricing import PortfolioPricingResult, TechnicalPricingEngine
from src.risk_metrics import RiskMetricsEngine, RiskMetricsSummary
from src.tail_risk import PolicyTailRiskEngine, TailRiskAllocationResult

logger = get_logger("risk_store")


@dataclass
class RiskAnalyticsResult:
    """Master result envelope aggregating all Phase 4 quantitative risk and pricing outputs."""

    run_id: str
    simulation_years: int
    portfolio_aal: float
    portfolio_tvar_996: float
    pml_100: float
    pml_250: float
    pml_500: float
    metrics_summary: RiskMetricsSummary
    tail_allocation: TailRiskAllocationResult
    accumulation: AccumulationAnalysisResult
    pricing: PortfolioPricingResult
    marginal_impacts: list[MarginalRiskImpact]
    recommendations: list[RiskRecommendation]
    risk_metrics_path: str
    policy_tail_path: str
    accumulation_path: str
    pricing_path: str
    counterfactual_path: str
    output_hashes: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    status: str = "SUCCESS"
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskAnalyticsPipeline:
    """Master orchestrator executing risk metrics, tail risk, accumulation, pricing, and persistence."""

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
        """Compute deterministic SHA-256 hash for a DataFrame."""
        serialized = df.to_json(orient="records", date_format="iso").encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _save_table(self, df: pd.DataFrame, run_id: str, table_name: str) -> tuple[Path, str]:
        """Persist DataFrame to Parquet (or compressed CSV fallback) and return path and SHA-256 hash."""
        target_path = self.output_dir / f"{table_name}_{run_id[:8]}.parquet"
        try:
            df.to_parquet(target_path, index=False)
        except Exception:
            target_path = self.output_dir / f"{table_name}_{run_id[:8]}.csv.gz"
            df.to_csv(target_path, index=False, compression="gzip")
        h = self.compute_df_sha256(df)
        return target_path, h

    def run(
        self,
        ylt_df: pd.DataFrame,
        elt_df: pd.DataFrame,
        portfolio_df: pd.DataFrame,
        run_id: str = "RISK_RUN_001",
        confidence: float = 0.996,
        cost_of_capital_rate: float = 0.10,
        expense_rate: float = 0.10,
        run_bootstrap: bool = False,
    ) -> RiskAnalyticsResult:
        """Run the complete Phase 4 risk analytics and technical pricing pipeline."""
        start_time = datetime.now(timezone.utc)
        logger.info(
            "=== FLOODTAIL Risk Analytics Pipeline Started (run_id=%s, confidence=%.3f) ===",
            run_id,
            confidence,
        )

        warnings: list[str] = []

        # 1. Evaluate Portfolio Risk Metrics
        logger.info("Computing AAL, OEP, AEP, PML, VaR, and TVaR...")
        risk_metrics_engine = RiskMetricsEngine(default_confidence=confidence)
        metrics_summary = risk_metrics_engine.evaluate(ylt_df)

        # 2. Allocate Tail Risk to Individual Policies
        logger.info("Allocating tail risk across policies and reconciling TVaR...")
        tail_risk_engine = PolicyTailRiskEngine()
        tail_allocation = tail_risk_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics_summary.tail_set_996,
            portfolio_tvar=metrics_summary.tvar_996,
            portfolio_aal=metrics_summary.aal,
            run_bootstrap=run_bootstrap,
        )

        # 3. Portfolio Accumulation & Spatial Co-Hit Analytics
        logger.info("Analyzing geographic accumulation and spatial co-hits...")
        accumulation_engine = PortfolioAccumulationEngine()
        accumulation_res = accumulation_engine.evaluate(
            portfolio_df=portfolio_df,
            elt_df=elt_df,
            tail_df=tail_allocation.tail_dataframe,
        )

        # 4. Technical Pricing Waterfall
        logger.info("Computing technical premiums with capital and expense loadings...")
        pricing_engine = TechnicalPricingEngine(
            cost_of_capital_rate=cost_of_capital_rate,
            expense_rate=expense_rate,
        )
        pricing_res = pricing_engine.calculate_pricing(
            tail_df=tail_allocation.tail_dataframe,
            run_id=run_id,
        )

        # 5. Marginal TVaR (Common Random Numbers) & Risk Appetite Rule Engine
        logger.info("Evaluating marginal TVaR impacts and underwriting recommendations...")
        counterfactual_engine = CounterfactualEngine(alpha=confidence)
        marginal_impacts = counterfactual_engine.calculate_marginal_tvars(
            ylt_df=ylt_df,
            pal_matrix=tail_allocation.policy_annual_losses_df,
            tail_df=tail_allocation.tail_dataframe,
        )

        rule_engine = RiskAppetiteRuleEngine()
        recommendations = rule_engine.evaluate_policy_recommendations(
            tail_records=tail_allocation.policy_records,
            marginal_impacts=marginal_impacts,
            co_hit_metrics=accumulation_res.co_hit_metrics,
        )

        # 6. Prepare Datasets for Persistence
        # A) Risk Metrics Summary Table
        metrics_df = pd.DataFrame([{
            "simulation_years": metrics_summary.simulation_years,
            "total_simulated_loss": metrics_summary.total_simulated_loss,
            "aal": metrics_summary.aal,
            "var_99": metrics_summary.var_99,
            "var_996": metrics_summary.var_996,
            "tvar_99": metrics_summary.tvar_99,
            "tvar_996": metrics_summary.tvar_996,
            "pml_100": metrics_summary.pml_100,
            "pml_250": metrics_summary.pml_250,
            "pml_500": metrics_summary.pml_500,
        }])

        # B) Counterfactual Table
        rec_df = pd.DataFrame([
            {
                "policy_id": r.policy_id,
                "recommendation": r.recommendation,
                "risk_appetite_status": r.risk_appetite_status,
                "aal": r.aal,
                "tail_contribution": r.tail_contribution,
                "marginal_tvar": r.marginal_tvar,
                "tail_share_pct": r.tail_share_pct,
                "co_hit_rate": r.co_hit_rate,
                "risk_flags": ";".join(r.risk_flags),
                "reason_codes": ";".join(r.reason_codes),
            }
            for r in recommendations
        ])

        # 7. Persist Output Datasets
        m_path, m_hash = self._save_table(metrics_df, run_id, "risk_metrics")
        t_path, t_hash = self._save_table(tail_allocation.tail_dataframe, run_id, "policy_tail")
        a_path, a_hash = self._save_table(accumulation_res.accumulation_dataframe, run_id, "accumulation")
        p_path, p_hash = self._save_table(pricing_res.pricing_dataframe, run_id, "pricing")
        c_path, c_hash = self._save_table(rec_df, run_id, "counterfactual")

        output_hashes = {
            "risk_metrics": m_hash,
            "policy_tail": t_hash,
            "accumulation": a_hash,
            "pricing": p_hash,
            "counterfactual": c_hash,
        }

        # 8. Register in SQLite Metadata DB
        if self.db_manager:
            try:
                run_entry = self.db_manager.get_run(run_id)
                if run_entry is None:
                    model_v = "v1.0"
                    if self.config is not None:
                        if isinstance(self.config, dict):
                            model_v = self.config.get("model_version", "v1.0")
                        elif hasattr(self.config, "model_version"):
                            model_v = getattr(self.config, "model_version", "v1.0")
                    self.db_manager.create_run(
                        run_id=run_id,
                        model_version=model_v,
                        data_version="v1.0",
                        status="SUCCESS",
                        source_file=str(p_path.name),
                    )
                self.db_manager.record_portfolio_version(
                    run_id=run_id,
                    dataset_path=str(p_path),
                    dataset_hash=p_hash,
                    record_count=len(pricing_res.pricing_dataframe),
                )
            except Exception as e:
                logger.error("Failed to register risk analytics in database: %s", e)
                warnings.append(f"Database registration warning: {e}")

        status = "SUCCESS" if len(warnings) == 0 else "WARNING"

        logger.info(
            "=== FLOODTAIL Risk Analytics Pipeline Finished: Total Premium = $%s (status=%s) ===",
            f"{pricing_res.total_technical_premium:,.2f}",
            status,
        )

        return RiskAnalyticsResult(
            run_id=run_id,
            simulation_years=metrics_summary.simulation_years,
            portfolio_aal=metrics_summary.aal,
            portfolio_tvar_996=metrics_summary.tvar_996,
            pml_100=metrics_summary.pml_100,
            pml_250=metrics_summary.pml_250,
            pml_500=metrics_summary.pml_500,
            metrics_summary=metrics_summary,
            tail_allocation=tail_allocation,
            accumulation=accumulation_res,
            pricing=pricing_res,
            marginal_impacts=marginal_impacts,
            recommendations=recommendations,
            risk_metrics_path=str(m_path),
            policy_tail_path=str(t_path),
            accumulation_path=str(a_path),
            pricing_path=str(p_path),
            counterfactual_path=str(c_path),
            output_hashes=output_hashes,
            warnings=warnings,
            status=status,
            executed_at=start_time,
        )


def run_risk_analytics(
    ylt_df: pd.DataFrame,
    elt_df: pd.DataFrame,
    portfolio_df: pd.DataFrame,
    run_id: str = "RISK_RUN_001",
    confidence: float = 0.996,
    cost_of_capital_rate: float = 0.10,
    expense_rate: float = 0.10,
    output_dir: Union[str, Path] = "data/processed",
    db_manager: Optional[DatabaseManager] = None,
    run_bootstrap: bool = False,
) -> RiskAnalyticsResult:
    """Convenience functional orchestrator for the complete Phase 4 risk analytics pipeline."""
    pipeline = RiskAnalyticsPipeline(
        output_dir=output_dir,
        db_manager=db_manager,
    )
    return pipeline.run(
        ylt_df=ylt_df,
        elt_df=elt_df,
        portfolio_df=portfolio_df,
        run_id=run_id,
        confidence=confidence,
        cost_of_capital_rate=cost_of_capital_rate,
        expense_rate=expense_rate,
        run_bootstrap=run_bootstrap,
    )
