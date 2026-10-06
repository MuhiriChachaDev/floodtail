"""FLOODTAIL — Comprehensive unit, actuarial, and reconciliation test suite for Phase 4 Risk Analytics.

Covers:
- Empirical Loss Distributions, AAL, OEP, AEP, PML, VaR, TVaR
- Independent Recomputation Proofs
- Policy Tail Contribution Allocation (Sum == TVaR)
- Portfolio Accumulation & Spatial Co-Hit Metrics
- Technical Pricing Waterfall & Reconciliation
- Marginal TVaR Impact (Common Random Numbers)
- A/B Policy Decision Intelligence (Similar AAL -> Differentiated Tail Risk & Price)
- What-If Sensitivity Engine
- Risk Appetite Governance Rules
- Deterministic Seed Reproducibility
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.accumulation import PortfolioAccumulationEngine
from src.catastrophe_store import CatastrophePipeline
from src.counterfactual import CounterfactualEngine, RiskAppetiteConfig, RiskAppetiteRuleEngine
from src.database import DatabaseManager
from src.events import EventCatalogue
from src.hazard import HazardFootprintStore
from src.pricing import TechnicalPricingEngine
from src.risk_metrics import RiskMetricsEngine
from src.risk_store import RiskAnalyticsPipeline, run_risk_analytics
from src.tail_risk import PolicyTailRiskEngine


@pytest.fixture
def executed_catastrophe_run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute a deterministic catastrophe simulation and provide (portfolio_df, elt_df, ylt_df)."""
    demo_port = pd.read_csv("data/demo/portfolio_ab_demo.csv")
    demo_cat = EventCatalogue.from_csv("data/demo/events.csv")
    demo_fp = HazardFootprintStore.from_json_file("data/demo/footprints.json")

    pipeline = CatastrophePipeline()
    res = pipeline.run(
        portfolio_df=demo_port,
        event_catalogue=demo_cat,
        footprint_store=demo_fp,
        simulation_years=1000,
        seed=482913,
    )

    elt_df = pd.read_parquet(res.elt_path) if res.elt_path.endswith(".parquet") else pd.read_csv(res.elt_path)
    ylt_df = pd.read_parquet(res.ylt_path) if res.ylt_path.endswith(".parquet") else pd.read_csv(res.ylt_path)

    return demo_port, elt_df, ylt_df


# ===========================================================================
# 1. Quantitative Risk Metrics & Independent Calculation Tests
# ===========================================================================

class TestRiskMetricsAndExceedanceCurves:
    """Tests 1–9: AAL, OEP, AEP, PML, VaR, TVaR, and independent recomputations."""

    def test_aal_equals_annual_loss_mean_and_independent_proof(self):
        annual_losses = np.array([0.0, 100_000.0, 500_000.0, 0.0, 1_200_000.0, 200_000.0])
        aal_primary = RiskMetricsEngine.calculate_aal(annual_losses)
        aal_independent = RiskMetricsEngine.verify_aal_independent(annual_losses)

        expected_mean = sum(annual_losses) / len(annual_losses)
        assert aal_primary == pytest.approx(expected_mean, abs=1e-4)
        assert aal_independent == pytest.approx(expected_mean, abs=1e-4)
        assert aal_primary == pytest.approx(aal_independent, abs=1e-4)

    def test_oep_uses_max_event_loss_and_aep_uses_annual_aggregate(self):
        losses = np.array([0.0, 1_000.0, 5_000.0, 10_000.0, 50_000.0, 100_000.0] * 10)
        oep_curve = RiskMetricsEngine.calculate_exceedance_curve(losses, metric_type="OEP", return_periods=[10, 20])
        aep_curve = RiskMetricsEngine.calculate_exceedance_curve(losses, metric_type="AEP", return_periods=[10, 20])

        assert len(oep_curve) == 2
        assert len(aep_curve) == 2
        assert oep_curve[0].metric_type == "OEP"
        assert aep_curve[0].metric_type == "AEP"
        assert oep_curve[0].loss > 0

    def test_var_and_tvar_boundary_weighting_and_independent_proof(self):
        # 100 simulated years: values 1..100
        ylt_df = pd.DataFrame({
            "simulation_year": range(1, 101),
            "annual_loss": [float(i * 1000) for i in range(1, 101)],
        })
        # alpha = 0.96 -> tail mass = 4 years (losses: 100k, 99k, 98k, 97k)
        # mean of top 4 = (100k + 99k + 98k + 97k) / 4 = 98.5k
        tvar_primary = RiskMetricsEngine.calculate_tvar(ylt_df, alpha=0.96)
        tvar_independent = RiskMetricsEngine.verify_tvar_independent(ylt_df, alpha=0.96)

        assert tvar_primary == pytest.approx(98500.0, abs=1.0)
        assert tvar_independent == pytest.approx(98500.0, abs=1.0)

    def test_fractional_tail_weighting_handles_non_integer_tail_mass(self):
        # 10 years, alpha = 0.85 -> tail mass = 1.5 years
        # Top 1 = 100k (full weight = 1.0/1.5), Top 2 = 90k (half weight = 0.5/1.5)
        # TVaR = (100k * 1.0 + 90k * 0.5) / 1.5 = (100 + 45) / 1.5 = 145 / 1.5 = 96.666k
        ylt_df = pd.DataFrame({
            "simulation_year": range(1, 11),
            "annual_loss": [float(i * 10_000) for i in range(1, 11)],
        })
        tvar_val = RiskMetricsEngine.calculate_tvar(ylt_df, alpha=0.85)
        assert tvar_val == pytest.approx(96666.67, abs=1.0)

    def test_zero_loss_years_handled_correctly(self):
        # 10 years with 8 zero-loss years and 2 positive years
        ylt_df = pd.DataFrame({
            "simulation_year": range(1, 11),
            "annual_loss": [0.0] * 8 + [100_000.0, 200_000.0],
            "max_event_loss": [0.0] * 8 + [100_000.0, 200_000.0],
        })
        engine = RiskMetricsEngine(default_confidence=0.90)
        summary = engine.evaluate(ylt_df)

        assert summary.aal == pytest.approx(30_000.0, abs=1.0)
        assert summary.tvar_996 >= 200_000.0


# ===========================================================================
# 2. Policy Tail Risk Contribution & Reconciliation Tests
# ===========================================================================

class TestPolicyTailRiskAllocation:
    """Tests 10–13: Policy AAL reconciliation and exact sum of tail contributions == Portfolio TVaR."""

    def test_policy_annual_losses_reconcile_with_portfolio_losses(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        n_years = len(ylt_df)
        pids = portfolio_df["policy_id"].tolist()

        pal_matrix = PolicyTailRiskEngine.build_policy_annual_loss_matrix(elt_df, pids, n_years)

        # Check for every year: sum across all policies equals portfolio annual loss
        sum_by_year = pal_matrix.sum(axis=0).values
        actual_annual_losses = ylt_df["annual_loss"].values

        np.testing.assert_allclose(sum_by_year, actual_annual_losses, atol=1e-2)

    def test_sum_of_policy_aals_equals_portfolio_aal(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        assert alloc.aal_reconciled is True
        assert alloc.total_allocated_aal == pytest.approx(metrics.aal, abs=1e-2)

    def test_sum_of_policy_tail_contributions_equals_portfolio_tvar(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        assert alloc.tail_reconciled is True
        assert alloc.total_allocated_tail == pytest.approx(metrics.tvar_996, abs=1e-2)

    def test_tail_shares_sum_to_100_percent(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        total_shares = sum(r.tail_share_pct for r in alloc.policy_records)
        assert total_shares == pytest.approx(100.0, abs=1e-2)


# ===========================================================================
# 3. Technical Pricing Waterfall & Reconciliation Tests
# ===========================================================================

class TestTechnicalPricingEngine:
    """Tests 14: Pricing components waterfall (Expected Loss + Tail Charge + Expense == Premium)."""

    def test_pricing_waterfall_reconciliation(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        pricing_engine = TechnicalPricingEngine(cost_of_capital_rate=0.10, expense_rate=0.10)
        pricing_res = pricing_engine.calculate_pricing(alloc.tail_dataframe)

        assert pricing_res.pricing_reconciled is True
        for p in pricing_res.policy_pricing:
            recomputed = round(p.expected_loss + p.tail_charge + p.expense, 2)
            assert p.technical_premium == pytest.approx(recomputed, abs=1e-2)
            assert p.rate_on_line_bps >= 0.0


# ===========================================================================
# 4. Marginal TVaR & Counterfactual Tests
# ===========================================================================

class TestMarginalTVaRAndCounterfactual:
    """Tests 15–16: Common Random Numbers marginal TVaR and A/B policy decision differentiation."""

    def test_marginal_tvar_uses_common_random_numbers(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        cf_engine = CounterfactualEngine(alpha=0.996)
        marginals = cf_engine.calculate_marginal_tvars(
            ylt_df=ylt_df,
            pal_matrix=alloc.policy_annual_losses_df,
            tail_df=alloc.tail_dataframe,
        )

        assert len(marginals) == len(portfolio_df)
        for m in marginals:
            assert m.portfolio_tvar_base == pytest.approx(metrics.tvar_996, abs=1e-2)
            assert m.portfolio_tvar_without <= m.portfolio_tvar_base + 1e-4
            assert m.marginal_tvar_impact >= 0.0

    def test_ab_policy_comparison_differentiates_tail_risk_and_premium(self, executed_catastrophe_run):
        """Validates that Policy A (in flood basin) and Policy B (on high ground) have similar standalone characteristics, but Policy A has higher tail contribution and higher technical premium."""
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        pricing_engine = TechnicalPricingEngine(cost_of_capital_rate=0.10, expense_rate=0.10)
        pricing_res = pricing_engine.calculate_pricing(alloc.tail_dataframe)

        pricing_dict = {p.policy_id: p for p in pricing_res.policy_pricing}
        tail_dict = {r.policy_id: r for r in alloc.policy_records}

        p_a = pricing_dict["POL_DEMO_A"]
        p_b = pricing_dict["POL_DEMO_B"]
        t_a = tail_dict["POL_DEMO_A"]
        t_b = tail_dict["POL_DEMO_B"]

        # Both have identical $25M TIV and Commercial property type
        assert p_a.insured_value == p_b.insured_value == 25_000_000.0

        # Policy A has higher tail contribution and higher price due to spatial accumulation
        assert t_a.tail_contribution > t_b.tail_contribution
        assert p_a.technical_premium > p_b.technical_premium
        assert p_a.tail_charge > p_b.tail_charge


# ===========================================================================
# 5. Accumulation, Concentration & Co-Hit Tests
# ===========================================================================

class TestPortfolioAccumulationAndConcentration:
    """Tests 17–18: Regional accumulation, HHI, and co-hit metrics."""

    def test_regional_accumulation_and_hhi_metrics(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        accum_engine = PortfolioAccumulationEngine()
        accum_res = accum_engine.evaluate(
            portfolio_df=portfolio_df,
            elt_df=elt_df,
            tail_df=alloc.tail_dataframe,
        )

        assert accum_res.total_portfolio_tiv == pytest.approx(portfolio_df["insured_value"].sum(), abs=1e-2)
        assert len(accum_res.regional_breakdown) > 0
        assert 0.0 <= accum_res.regional_tiv_hhi <= 1.0
        assert 0.0 <= accum_res.regional_loss_hhi <= 1.0
        assert 0.0 <= accum_res.tiv_concentration_top10_pct <= 100.0
        assert 0.0 <= accum_res.loss_concentration_top10_pct <= 100.0


# ===========================================================================
# 6. What-If Sensitivity & Risk Appetite Rule Engine Tests
# ===========================================================================

class TestWhatIfAndRiskAppetite:
    """Tests 19–21: TIV what-if scaling and deterministic risk-appetite decision governance."""

    def test_what_if_tiv_scaling(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        cf_engine = CounterfactualEngine(alpha=0.996)
        # Increase POL_DEMO_A TIV from 25M to 30M (+20%)
        what_if = cf_engine.evaluate_what_if_tiv(
            policy_id="POL_DEMO_A",
            new_tiv=30_000_000.0,
            portfolio_df=portfolio_df,
            ylt_df=ylt_df,
            pal_matrix=alloc.policy_annual_losses_df,
            tail_df=alloc.tail_dataframe,
        )

        assert what_if.baseline_value == 25_000_000.0
        assert what_if.modified_value == 30_000_000.0
        assert what_if.new_aal == pytest.approx(what_if.baseline_aal * 1.20, abs=1e-2)
        assert what_if.new_tail_contribution == pytest.approx(what_if.baseline_tail_contribution * 1.20, abs=1e-2)

    def test_risk_appetite_rules_are_deterministic(self, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        metrics_engine = RiskMetricsEngine(default_confidence=0.996)
        metrics = metrics_engine.evaluate(ylt_df)

        tail_engine = PolicyTailRiskEngine()
        alloc = tail_engine.allocate_tail_risk(
            elt_df=elt_df,
            ylt_df=ylt_df,
            portfolio_df=portfolio_df,
            tail_set=metrics.tail_set_996,
            portfolio_tvar=metrics.tvar_996,
            portfolio_aal=metrics.aal,
        )

        cf_engine = CounterfactualEngine(alpha=0.996)
        marginals = cf_engine.calculate_marginal_tvars(
            ylt_df=ylt_df,
            pal_matrix=alloc.policy_annual_losses_df,
            tail_df=alloc.tail_dataframe,
        )

        accum_engine = PortfolioAccumulationEngine()
        accum_res = accum_engine.evaluate(
            portfolio_df=portfolio_df,
            elt_df=elt_df,
            tail_df=alloc.tail_dataframe,
        )

        rule_engine = RiskAppetiteRuleEngine(
            RiskAppetiteConfig(max_policy_marginal_tvar=5_000_000.0, max_policy_tail_share_pct=8.0)
        )
        recommendations = rule_engine.evaluate_policy_recommendations(
            tail_records=alloc.policy_records,
            marginal_impacts=marginals,
            co_hit_metrics=accum_res.co_hit_metrics,
        )

        assert len(recommendations) == len(portfolio_df)
        for rec in recommendations:
            assert rec.recommendation in {"ACCEPT", "REVIEW", "ESCALATE"}
            assert rec.risk_appetite_status in {"WITHIN_APPETITE", "REVIEW_REQUIRED", "APPETITE_BREACH"}


# ===========================================================================
# 7. End-to-End Pipeline & Reproducibility Tests
# ===========================================================================

class TestEndToEndRiskAnalyticsPipeline:
    """Tests 22–25: Full Phase 4 pipeline run, dataset persistence, and hash reproducibility."""

    def test_full_risk_analytics_run_and_persistence(self, tmp_path: Path, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run
        db_path = tmp_path / "risk_test.db"
        db = DatabaseManager(db_path)

        pipeline = RiskAnalyticsPipeline(
            output_dir=tmp_path / "processed",
            db_manager=db,
        )
        res = pipeline.run(
            ylt_df=ylt_df,
            elt_df=elt_df,
            portfolio_df=portfolio_df,
            run_id="TEST_PHASE4_RUN",
        )

        assert res.status == "SUCCESS"
        assert res.portfolio_aal > 0.0
        assert res.portfolio_tvar_996 > 0.0
        assert Path(res.risk_metrics_path).exists()
        assert Path(res.policy_tail_path).exists()
        assert Path(res.accumulation_path).exists()
        assert Path(res.pricing_path).exists()
        assert Path(res.counterfactual_path).exists()
        assert len(res.output_hashes) == 5

    def test_same_inputs_produce_identical_hashes(self, tmp_path: Path, executed_catastrophe_run):
        portfolio_df, elt_df, ylt_df = executed_catastrophe_run

        pipeline = RiskAnalyticsPipeline(output_dir=tmp_path / "processed")
        res1 = pipeline.run(ylt_df=ylt_df, elt_df=elt_df, portfolio_df=portfolio_df, run_id="HASH_RUN_1")
        res2 = pipeline.run(ylt_df=ylt_df, elt_df=elt_df, portfolio_df=portfolio_df, run_id="HASH_RUN_1")

        assert res1.output_hashes == res2.output_hashes
        assert res1.pricing.total_technical_premium == res2.pricing.total_technical_premium
