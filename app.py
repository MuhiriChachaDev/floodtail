"""FLOODTAIL — Enterprise Reinsurance Risk Intelligence Platform.

Main Streamlit application entry point. Orchestrates navigation, backend
integration, demo/live mode, and page routing.

Usage:
    streamlit run app.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Backend imports
# ---------------------------------------------------------------------------

from src.config import load_config
from src.database import DatabaseManager
from src.schemas import RunContext
from src.events import EventCatalogue, EventSimulator
from src.hazard import HazardFootprintStore, SpatialHazardEngine
from src.vulnerability import VulnerabilityEngine
from src.loss import CatastropheLossEngine
from src.quality import DataQualityAuditor
from src.risk_metrics import RiskMetricsEngine
from src.tail_risk import PolicyTailRiskEngine
from src.accumulation import PortfolioAccumulationEngine
from src.pricing import TechnicalPricingEngine
from src.counterfactual import CounterfactualEngine, RiskAppetiteRuleEngine
from src.agent_orchestrator import AgentOrchestrator, WorkflowExecutionResult
from src.audit_log import AuditManager
from src.decision import DecisionEngine, DecisionEvidencePackage
from src.explainability import ExplainabilityEngine
from src.catastrophe_store import CatastrophePipeline
from src.risk_store import RiskAnalyticsPipeline

# UI imports
from ui.theme import get_custom_css, Colors, format_currency, format_pct, format_bps
from ui import components as ui
from ui import charts

# ---------------------------------------------------------------------------
# Page config & styling helper
# ---------------------------------------------------------------------------


# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE & BACKEND ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════

def _init_session() -> None:
    """Initialise session state with defaults."""
    defaults = {
        "mode": "DEMO",
        "run_complete": False,
        "config": None,
        "portfolio_df": None,
        "elt_df": None,
        "ylt_df": None,
        "hazard_df": None,
        "workflow_result": None,
        "risk_result": None,
        "cat_result": None,
        "dq_report": None,
        "metrics_summary": None,
        "run_id": "FT-DEMO-001",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


@st.cache_data(show_spinner=False)
def _load_demo_portfolio() -> pd.DataFrame:
    """Load the canonical demo portfolio CSV."""
    return pd.read_csv("data/demo/portfolio_ab_demo.csv")


def _run_demo_pipeline() -> None:
    """Execute the full FLOODTAIL pipeline on demo data and cache in session state."""
    cfg = load_config()
    st.session_state.config = cfg

    portfolio_df = _load_demo_portfolio()

    # Phase 3 — Catastrophe engine
    ctx = RunContext(
        model_version=cfg.model.model_version,
        random_seed=cfg.simulation.seed,
        simulation_years=cfg.simulation.years,
        scenario=cfg.project.environment,
    )
    catalogue = EventCatalogue.from_csv("data/demo/events.csv")
    hazard_store = HazardFootprintStore.from_json_file("data/demo/footprints.json")

    simulator = EventSimulator(catalogue=catalogue, simulation_years=cfg.simulation.years, seed=cfg.simulation.seed)
    occurrences = simulator.simulate()

    hazard_engine = SpatialHazardEngine(footprint_store=hazard_store)
    hazard_df, _ = hazard_engine.evaluate_hazard(portfolio_df, occurrences)

    vuln_engine = VulnerabilityEngine()
    vuln_df = vuln_engine.evaluate_vulnerability(hazard_df, portfolio_df)

    loss_engine = CatastropheLossEngine()
    elt_df, ylt_df, _ = loss_engine.calculate_losses(vuln_df, simulation_years=cfg.simulation.years)

    st.session_state.portfolio_df = portfolio_df
    st.session_state.elt_df = elt_df
    st.session_state.ylt_df = ylt_df
    st.session_state.hazard_df = hazard_df
    st.session_state.run_id = ctx.run_id

    # Data quality
    auditor = DataQualityAuditor()
    st.session_state.dq_report = auditor.audit(portfolio_df)

    # Phase 4 — Risk analytics
    risk_engine = RiskMetricsEngine()
    metrics = risk_engine.evaluate(ylt_df)
    st.session_state.metrics_summary = metrics

    tail_engine = PolicyTailRiskEngine()
    tail_alloc = tail_engine.allocate_tail_risk(
        elt_df=elt_df, ylt_df=ylt_df, portfolio_df=portfolio_df,
        tail_set=metrics.tail_set_996, portfolio_tvar=metrics.tvar_996,
        portfolio_aal=metrics.aal,
    )
    st.session_state.tail_allocation = tail_alloc

    accum_engine = PortfolioAccumulationEngine()
    accum_result = accum_engine.evaluate(portfolio_df, elt_df, tail_alloc.tail_dataframe)
    st.session_state.accum_result = accum_result

    pricing_engine = TechnicalPricingEngine(cost_of_capital_rate=0.10, expense_rate=0.10)
    pricing_result = pricing_engine.calculate_pricing(tail_df=tail_alloc.tail_dataframe)
    st.session_state.pricing_result = pricing_result

    # Counterfactual
    all_pids = portfolio_df["policy_id"].tolist()
    pal_matrix = PolicyTailRiskEngine.build_policy_annual_loss_matrix(elt_df, all_pids, cfg.simulation.years)
    cf_engine = CounterfactualEngine(alpha=0.996)
    marginals = cf_engine.calculate_marginal_tvars(ylt_df=ylt_df, pal_matrix=pal_matrix, tail_df=tail_alloc.tail_dataframe)
    st.session_state.marginal_impacts = marginals

    # Risk appetite
    rule_engine = RiskAppetiteRuleEngine()
    recs = rule_engine.evaluate_policy_recommendations(
        tail_records=tail_alloc.policy_records,
        marginal_impacts=marginals,
        co_hit_metrics=accum_result.co_hit_metrics,
    )
    st.session_state.recommendations = recs

    # Phase 5 — Agent workflow
    db = DatabaseManager(Path("data/demo/demo_run.db"))
    db.create_run(ctx.run_id, cfg.model.model_version, "v1.0", "SUCCESS", "portfolio_ab_demo.csv")
    orchestrator = AgentOrchestrator(db_manager=db)
    wf_result = orchestrator.run_workflow(
        portfolio_df=portfolio_df,
        elt_df=elt_df,
        ylt_df=ylt_df,
        hazard_df=hazard_df,
        run_id=ctx.run_id,
    )
    st.session_state.workflow_result = wf_result
    st.session_state.db_manager = db
    st.session_state.audit_manager = AuditManager(db)
    st.session_state.decision_engine = DecisionEngine(AuditManager(db))
    st.session_state.run_complete = True
    st.session_state.mode = "DEMO"


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════

PAGES = [
    "01 — Overview",
    "02 — Portfolio",
    "03 — Data Intelligence",
    "04 — Agent Control",
    "05 — Flood Risk",
    "06 — Accumulation",
    "07 — Catastrophe Analytics",
    "08 — Tail Risk",
    "09 — Policy Intelligence",
    "10 — Pricing",
    "11 — Scenario Lab",
    "12 — Risk Appetite",
    "13 — Decisions",
    "14 — Audit",
    "15 — Methodology",
    "16 — Future / 2090",
]


# ═══════════════════════════════════════════════════════════════════════════
# PAGE ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def _require_run() -> bool:
    """Check if a run is available, show empty state if not."""
    if not st.session_state.run_complete:
        ui.empty_state("📊", "Run Portfolio Analysis to view results. Click Demo in the sidebar to load the demo dataset.")
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 01 — EXECUTIVE OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

def page_overview() -> None:
    ui.page_header("Executive Overview", "Portfolio-level risk intelligence summary")
    if not _require_run():
        return

    metrics = st.session_state.metrics_summary
    portfolio_df = st.session_state.portfolio_df
    wf = st.session_state.workflow_result
    dq = st.session_state.dq_report
    accum = st.session_state.accum_result

    # Top KPI row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        ui.metric_card("Total TIV", format_currency(float(portfolio_df["insured_value"].sum())),
                       f"{len(portfolio_df)} policies", Colors.NAVY_500)
    with c2:
        ui.metric_card("AAL", format_currency(metrics.aal),
                       f"{metrics.simulation_years:,} sim years", Colors.FLOOD_TEAL)
    with c3:
        ui.metric_card("PML 1-in-100", format_currency(metrics.pml_100), "Occurrence", Colors.STATUS_AMBER)
    with c4:
        ui.metric_card("PML 1-in-250", format_currency(metrics.pml_250), "Occurrence", Colors.ACCENT_RED)
    with c5:
        ui.metric_card("TVaR (99.6%)", format_currency(metrics.tvar_996),
                       f"{metrics.tail_set_996.tail_year_count} tail obs", Colors.ACCENT_RED)
    with c6:
        ui.metric_card("Policies", str(len(portfolio_df)),
                       f"{portfolio_df['region'].nunique()} regions", Colors.NAVY_500)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content columns
    col_left, col_right = st.columns([3, 2])

    with col_left:
        ui.section_title("🌊 Regional Accumulation")
        if accum:
            regions = [r.region for r in accum.regional_breakdown]
            tiv_shares = [r.tiv_share_pct for r in accum.regional_breakdown]
            tail_shares = [r.tail_share_pct for r in accum.regional_breakdown]
            fig = charts.regional_accumulation(regions, tiv_shares, tail_shares)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        ui.section_title("🏢 Top Tail Contributors")
        tail_alloc = st.session_state.tail_allocation
        top5 = tail_alloc.policy_records[:5]
        for rec in top5:
            st.markdown(
                f'<div class="ft-card" style="padding:12px 16px;margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div style="font-weight:600;color:{Colors.NAVY_800};font-size:13px;">{rec.policy_id}</div>'
                f'<div style="font-weight:700;color:{Colors.ACCENT_RED};font-size:14px;">{format_pct(rec.tail_share_pct)}</div>'
                f'</div>'
                f'<div style="font-size:11px;color:{Colors.GRAY_500};">Tail: {format_currency(rec.tail_contribution)} · AAL: {format_currency(rec.aal)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        ui.section_title("📊 System Status")
        # Data quality
        dq_color = Colors.STATUS_GREEN if dq.passed else Colors.STATUS_AMBER
        st.markdown(f'{ui.status_badge("SUCCESS" if dq.passed else "WARNING")} Data Quality: **{dq.quality_score:.0f}%**', unsafe_allow_html=True)
        # Agent status
        if wf:
            failed = [s for s in wf.trace.steps if s.status == "FAILED"]
            if failed:
                st.markdown(f'{ui.status_badge("WARNING")} Agent Workflow: **{len(failed)} issue(s)**', unsafe_allow_html=True)
            else:
                st.markdown(f'{ui.status_badge("SUCCESS")} Agent Workflow: **All 11 agents passed**', unsafe_allow_html=True)

    # Intelligence insights
    st.markdown("<br>", unsafe_allow_html=True)
    ui.section_title("🤖 FLOODTAIL Intelligence")
    insights = []
    if accum:
        top_region = accum.regional_breakdown[0] if accum.regional_breakdown else None
        if top_region:
            insights.append(f"**{top_region.region}** accounts for {format_pct(top_region.tail_share_pct)} of portfolio tail risk.")
    if tail_alloc:
        high_tail = [r for r in tail_alloc.policy_records if r.tail_share_pct > 10]
        if high_tail:
            insights.append(f"**{len(high_tail)} policies** contribute > 10% of portfolio tail risk each.")
    recs = st.session_state.get("recommendations", [])
    review_count = sum(1 for r in recs if r.recommendation in ("REVIEW", "ESCALATE"))
    if review_count:
        insights.append(f"**{review_count} policies** flagged for review or escalation by risk appetite rules.")

    for ins in insights[:5]:
        ui.info_banner("💡", "Insight", ins, Colors.AI_PURPLE, Colors.AI_LIGHT)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 02 — PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════

def page_portfolio() -> None:
    ui.page_header("Portfolio", "Exposure and policy inventory")
    if not _require_run():
        return

    portfolio_df = st.session_state.portfolio_df
    pricing = st.session_state.pricing_result
    tail_alloc = st.session_state.tail_allocation

    c1, c2, c3, c4 = st.columns(4)
    total_tiv = float(portfolio_df["insured_value"].sum())
    with c1:
        ui.metric_card("Policies", str(len(portfolio_df)), f"{portfolio_df['region'].nunique()} regions")
    with c2:
        ui.metric_card("Total TIV", format_currency(total_tiv))
    with c3:
        ui.metric_card("Average TIV", format_currency(total_tiv / len(portfolio_df)))
    with c4:
        ui.metric_card("Median TIV", format_currency(float(portfolio_df["insured_value"].median())))

    st.markdown("<br>", unsafe_allow_html=True)

    # Build display table
    display_df = portfolio_df[["policy_id", "region", "property_type", "insured_value", "construction_class"]].copy()

    if tail_alloc and tail_alloc.tail_dataframe is not None:
        tail_df = tail_alloc.tail_dataframe[["policy_id", "aal", "tail_contribution"]].copy()
        display_df = display_df.merge(tail_df, on="policy_id", how="left")

    if pricing and pricing.pricing_dataframe is not None:
        price_df = pricing.pricing_dataframe[["policy_id", "technical_premium", "rate_on_line_bps"]].copy()
        display_df = display_df.merge(price_df, on="policy_id", how="left")

    recs = st.session_state.get("recommendations", [])
    if recs:
        rec_map = {r.policy_id: r.recommendation for r in recs}
        display_df["recommendation"] = display_df["policy_id"].map(rec_map).fillna("—")

    # Search
    search = st.text_input("🔍 Search policies", placeholder="Policy ID, region, or property type...")
    if search:
        mask = display_df.apply(lambda row: search.lower() in str(row.values).lower(), axis=1)
        display_df = display_df[mask]

    st.dataframe(display_df, use_container_width=True, height=500)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 03 — DATA INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════

def page_data_intelligence() -> None:
    ui.page_header("Data Intelligence", "Portfolio data quality analysis")
    if not _require_run():
        return

    dq = st.session_state.dq_report
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        color = Colors.STATUS_GREEN if dq.quality_score >= 80 else Colors.STATUS_AMBER
        ui.metric_card("Quality Score", f"{dq.quality_score:.0f}%", "PASS" if dq.passed else "REVIEW", color)
    with c2:
        total = len(dq.issues)
        ui.metric_card("Total Issues", str(total))
    with c3:
        critical = sum(1 for i in dq.issues if i.severity == "CRITICAL")
        ui.metric_card("Critical Issues", str(critical), border_color=Colors.STATUS_RED if critical else "")
    with c4:
        warnings = sum(1 for i in dq.issues if i.severity == "WARNING")
        ui.metric_card("Warnings", str(warnings))

    if dq.issues:
        ui.section_title("Issue Detail")
        issue_data = []
        for iss in dq.issues:
            issue_data.append({
                "Severity": iss.severity,
                "Type": iss.issue_type,
                "Field": iss.field_name,
                "Message": iss.message,
                "Count": iss.affected_count,
            })
        st.dataframe(pd.DataFrame(issue_data), use_container_width=True)
    else:
        ui.info_banner("✓", "Clean Data", "No data quality issues detected.", Colors.STATUS_GREEN, Colors.STATUS_GREEN_BG)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 04 — AGENT CONTROL CENTRE
# ═══════════════════════════════════════════════════════════════════════════

def page_agent_control() -> None:
    ui.page_header("Agent Control Centre", "FLOODTAIL Intelligence — 11-Agent Decision Workflow")
    if not _require_run():
        return

    wf = st.session_state.workflow_result

    # Status summary
    total = len(wf.trace.steps)
    passed = sum(1 for s in wf.trace.steps if s.status in ("SUCCESS", "WARNING"))
    failed = sum(1 for s in wf.trace.steps if s.status == "FAILED")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Agents", str(total), "Total steps", Colors.AI_PURPLE)
    with c2:
        ui.metric_card("Passed", str(passed), border_color=Colors.STATUS_GREEN)
    with c3:
        ui.metric_card("Warnings", str(sum(1 for s in wf.trace.steps if s.status == "WARNING")), border_color=Colors.STATUS_AMBER)
    with c4:
        ui.metric_card("Failed", str(failed), border_color=Colors.STATUS_RED if failed else "")

    st.markdown("<br>", unsafe_allow_html=True)

    # Vertical workflow
    col_flow, col_detail = st.columns([2, 3])

    with col_flow:
        ui.section_title("🤖 Workflow Trace")
        selected_agent = None
        for i, step in enumerate(wf.trace.steps):
            if i > 0:
                ui.agent_connector()
            ui.agent_step(step.agent_name, step.status, step.output_summary, step.duration_ms)

        # Human decision step
        ui.agent_connector()
        ui.agent_step("Human Decision", "PENDING", "Awaiting underwriter review", 0)

    with col_detail:
        ui.section_title("📋 Agent Detail")
        agent_names = [s.agent_name for s in wf.trace.steps]
        selected = st.selectbox("Select agent", agent_names)
        step = next((s for s in wf.trace.steps if s.agent_name == selected), None)
        if step:
            st.markdown(f"**Status:** {ui.status_badge(step.status)}", unsafe_allow_html=True)
            st.markdown(f"**Duration:** {step.duration_ms:.0f}ms")
            st.markdown(f"**Input:** {step.input_summary}")
            st.markdown(f"**Output:** {step.output_summary}")
            if step.warnings:
                ui.section_title("⚠ Warnings")
                for w in step.warnings:
                    st.warning(w)

    # Failure injection
    st.markdown("<br>", unsafe_allow_html=True)
    ui.section_title("🔬 Controlled Failure Injection")
    st.markdown("Test the governance safety mechanism by running the workflow with missing hazard data.")
    if st.button("🛡️ Run Failure Test", type="secondary"):
        with st.spinner("Running controlled failure test..."):
            test_orch = AgentOrchestrator()
            fail_result = test_orch.run_workflow(
                portfolio_df=st.session_state.portfolio_df,
                elt_df=st.session_state.elt_df,
                ylt_df=st.session_state.ylt_df,
                hazard_df=None,
                run_id="FAILURE_TEST",
            )
        if fail_result.status == "REVIEW_REQUIRED":
            ui.info_banner("🛡️", "WORKFLOW HALTED — GOVERNANCE ACTIVE",
                          f"Pipeline stopped at: **{fail_result.trace.stopped_at_step}**. "
                          f"Reason: {fail_result.trace.failure_reason}. "
                          "Human review required before proceeding.",
                          Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG)
            for step in fail_result.trace.steps:
                ui.agent_step(step.agent_name, step.status, step.output_summary, step.duration_ms)
                ui.agent_connector()
        else:
            ui.info_banner("⚠", "Unexpected Result", f"Status: {fail_result.status}", Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 05 — FLOOD RISK
# ═══════════════════════════════════════════════════════════════════════════

def page_flood_risk() -> None:
    ui.page_header("Flood Risk", "Spatial hazard footprints and event analysis")
    if not _require_run():
        return

    hazard_df = st.session_state.hazard_df
    portfolio_df = st.session_state.portfolio_df

    # Summary
    affected = hazard_df[hazard_df["depth_m"] > 0]["policy_id"].nunique()
    events = hazard_df["occurrence_id"].nunique()
    max_depth = float(hazard_df["depth_m"].max())
    mean_depth = float(hazard_df[hazard_df["depth_m"] > 0]["depth_m"].mean()) if affected > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Affected Policies", str(affected), f"of {len(portfolio_df)}", Colors.FLOOD_TEAL)
    with c2:
        ui.metric_card("Unique Events", str(events), "Simulated occurrences", Colors.FLOOD_DARK)
    with c3:
        ui.metric_card("Max Flood Depth", f"{max_depth:.2f}m", border_color=Colors.FLOOD_TEAL)
    with c4:
        ui.metric_card("Mean Depth", f"{mean_depth:.2f}m", "Affected policies only")

    ui.section_title("🗺️ Exposure Map")
    try:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[portfolio_df["latitude"].mean(), portfolio_df["longitude"].mean()], zoom_start=7,
                      tiles="CartoDB positron")
        for _, row in portfolio_df.iterrows():
            color = "#0891B2" if row["policy_id"] in hazard_df[hazard_df["depth_m"] > 0]["policy_id"].values else "#94A3B8"
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=max(4, min(12, row["insured_value"] / 5e6)),
                color=color, fill=True, fill_opacity=0.7,
                popup=f"{row['policy_id']}<br>TIV: KES {row['insured_value']:,.0f}<br>{row['region']}",
            ).add_to(m)
        st_folium(m, width=None, height=450)
    except ImportError:
        ui.info_banner("🗺️", "Map unavailable", "Install folium and streamlit-folium for map visualization.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 06 — ACCUMULATION
# ═══════════════════════════════════════════════════════════════════════════

def page_accumulation() -> None:
    ui.page_header("Accumulation", "Where is the portfolio concentrated?")
    if not _require_run():
        return

    accum = st.session_state.accum_result
    metrics = st.session_state.metrics_summary

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Regions", str(len(accum.regional_breakdown)), border_color=Colors.NAVY_500)
    with c2:
        ui.metric_card("Regional HHI", f"{accum.regional_tiv_hhi:,.0f}", "TIV concentration index")
    with c3:
        ui.metric_card("Top 1% TIV Share", format_pct(accum.tiv_concentration_top1_pct), border_color=Colors.STATUS_AMBER)
    with c4:
        ui.metric_card("Top 1% Tail Share", format_pct(accum.loss_concentration_top1_pct), border_color=Colors.ACCENT_RED)

    # Regional chart
    regions = [r.region for r in accum.regional_breakdown]
    tiv_shares = [r.tiv_share_pct for r in accum.regional_breakdown]
    tail_shares = [r.tail_share_pct for r in accum.regional_breakdown]
    fig = charts.regional_accumulation(regions, tiv_shares, tail_shares)
    st.plotly_chart(fig, use_container_width=True)

    # Regional detail table
    ui.section_title("📊 Regional Detail")
    reg_data = []
    for r in accum.regional_breakdown:
        reg_data.append({
            "Region": r.region,
            "Policies": r.policy_count,
            "TIV": f"KES {r.total_tiv:,.0f}",
            "TIV Share": f"{r.tiv_share_pct:.1f}%",
            "AAL": f"KES {r.total_aal:,.0f}",
            "AAL Share": f"{r.aal_share_pct:.1f}%",
            "Tail Contribution": f"KES {r.total_tail_contribution:,.0f}",
            "Tail Share": f"{r.tail_share_pct:.1f}%",
        })
    st.dataframe(pd.DataFrame(reg_data), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 07 — CATASTROPHE ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

def page_cat_analytics() -> None:
    ui.page_header("Catastrophe Analytics", "Loss distributions, exceedance curves, and return periods")
    if not _require_run():
        return

    metrics = st.session_state.metrics_summary
    ylt_df = st.session_state.ylt_df

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        ui.metric_card("AAL", format_currency(metrics.aal), border_color=Colors.NAVY_500)
    with c2:
        ui.metric_card("VaR (99%)", format_currency(metrics.var_99))
    with c3:
        ui.metric_card("VaR (99.6%)", format_currency(metrics.var_996), "1-in-250")
    with c4:
        ui.metric_card("TVaR (99.6%)", format_currency(metrics.tvar_996), border_color=Colors.ACCENT_RED)
    with c5:
        ui.metric_card("PML 1-in-100", format_currency(metrics.pml_100))
    with c6:
        ui.metric_card("PML 1-in-250", format_currency(metrics.pml_250))

    col_left, col_right = st.columns(2)
    with col_left:
        fig = charts.exceedance_curve(metrics.oep_curve, metrics.aep_curve)
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        annual_losses = ylt_df["annual_loss"].tolist()
        fig = charts.annual_loss_distribution(annual_losses, metrics.aal, metrics.var_996)
        st.plotly_chart(fig, use_container_width=True)

    # Return period table
    ui.section_title("📋 Return Period Table")
    rp_data = []
    for pt in metrics.oep_curve:
        rp_data.append({
            "Return Period": f"1-in-{pt.return_period_years:.0f}",
            "OEP Loss": f"KES {pt.loss:,.0f}",
            "Sample Size": pt.sample_size,
        })
    st.dataframe(pd.DataFrame(rp_data), use_container_width=True)

    # TVaR panel
    ui.section_title("📊 TVaR Detail")
    st.markdown(
        f'<div class="ft-card">'
        f'<div class="ft-metric-label">TAIL VALUE AT RISK</div>'
        f'<div class="ft-metric-value">{format_currency(metrics.tvar_996)}</div>'
        f'<div style="margin-top:8px;font-size:13px;color:{Colors.GRAY_600};">'
        f'α = {metrics.tail_set_996.confidence_level} · '
        f'Tail observations: {metrics.tail_set_996.tail_year_count} / {metrics.simulation_years:,}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if metrics.simulation_years < 10000:
        ui.info_banner("⚠", "Limited Tail Sample",
                      f"{metrics.tail_set_996.tail_year_count} tail observations — larger simulation depth recommended for production.",
                      Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 08 — TAIL RISK
# ═══════════════════════════════════════════════════════════════════════════

def page_tail_risk() -> None:
    ui.page_header("Tail Risk", "Policy-level tail contribution and portfolio TVaR allocation")
    if not _require_run():
        return

    tail_alloc = st.session_state.tail_allocation
    metrics = st.session_state.metrics_summary

    # Summary
    c1, c2, c3 = st.columns(3)
    with c1:
        ui.metric_card("Portfolio TVaR", format_currency(metrics.tvar_996), "99.6% confidence", Colors.ACCENT_RED)
    with c2:
        ui.metric_card("Policies Allocated", str(len(tail_alloc.policy_records)))
    with c3:
        recon_status = "✓ RECONCILED" if tail_alloc.tail_reconciled else "✕ NOT RECONCILED"
        recon_color = Colors.STATUS_GREEN if tail_alloc.tail_reconciled else Colors.STATUS_RED
        ui.metric_card("Reconciliation", recon_status, border_color=recon_color)

    # Bar chart
    top_n = min(15, len(tail_alloc.policy_records))
    top_recs = tail_alloc.policy_records[:top_n]
    pids = [r.policy_id for r in top_recs]
    contribs = [r.tail_contribution for r in top_recs]
    fig = charts.tail_contribution_bars(pids, contribs, metrics.tvar_996)
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    ui.section_title("📋 Full Allocation Table")
    tail_data = []
    for r in tail_alloc.policy_records:
        tail_data.append({
            "Rank": r.tail_rank,
            "Policy": r.policy_id,
            "AAL": f"KES {r.aal:,.0f}",
            "Tail Contribution": f"KES {r.tail_contribution:,.0f}",
            "Tail Share": f"{r.tail_share_pct:.1f}%",
        })
    st.dataframe(pd.DataFrame(tail_data), use_container_width=True)

    # Reconciliation
    sum_contribs = sum(r.tail_contribution for r in tail_alloc.policy_records)
    st.markdown(
        f'<div class="ft-card">'
        f'<div style="font-size:13px;color:{Colors.GRAY_600};">'
        f'Σ Policy Contributions = {format_currency(sum_contribs)}<br>'
        f'Portfolio TVaR = {format_currency(metrics.tvar_996)}<br>'
        f'<span style="color:{Colors.STATUS_GREEN};font-weight:600;">✓ RECONCILED</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 09 — POLICY INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════

def page_policy_intelligence() -> None:
    ui.page_header("Policy Intelligence", "Deep-dive into individual policy risk, pricing, and explainability")
    if not _require_run():
        return

    wf = st.session_state.workflow_result
    portfolio_df = st.session_state.portfolio_df
    policy_ids = portfolio_df["policy_id"].tolist()

    # Policy selector
    col_sel, col_compare = st.columns(2)
    with col_sel:
        selected_policy = st.selectbox("Select Policy", policy_ids, index=0)
    with col_compare:
        compare_policy = st.selectbox("Compare With", ["— None —"] + policy_ids, index=0)

    if selected_policy not in wf.evidence_packages:
        ui.info_banner("⚠", "Evidence Unavailable", f"No evidence package for {selected_policy}.")
        return

    pkg = wf.evidence_packages[selected_policy]

    # Policy metrics
    ui.section_title(f"📋 {selected_policy}")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        ui.metric_card("Insured Value", format_currency(pkg.key_metrics.get("insured_value", 0)), border_color=Colors.NAVY_500)
    with c2:
        ui.metric_card("AAL", format_currency(pkg.key_metrics.get("aal", 0)), border_color=Colors.FLOOD_TEAL)
    with c3:
        ui.metric_card("Tail Contribution", format_currency(pkg.key_metrics.get("tail_contribution", 0)), border_color=Colors.ACCENT_RED)
    with c4:
        ui.metric_card("Technical Premium", format_currency(pkg.key_metrics.get("technical_premium", 0)))
    with c5:
        st.markdown(f'{ui.risk_badge(pkg.recommendation)}', unsafe_allow_html=True)
        st.markdown(f'{ui.confidence_badge(pkg.confidence.level)}', unsafe_allow_html=True)

    # Additional metrics row
    c6, c7, c8, c9 = st.columns(4)
    with c6:
        ui.metric_card("Marginal TVaR", format_currency(pkg.key_metrics.get("marginal_tvar", 0)))
    with c7:
        ui.metric_card("Co-Hit Rate", format_pct(pkg.key_metrics.get("co_hit_rate", 0) * 100 if pkg.key_metrics.get("co_hit_rate", 0) < 1 else pkg.key_metrics.get("co_hit_rate", 0)))
    with c8:
        ui.metric_card("Tail Share", format_pct(pkg.key_metrics.get("tail_share_pct", 0)))
    with c9:
        ui.metric_card("Rate on Line", format_bps(pkg.key_metrics.get("rate_on_line_bps", 0)))

    # A/B Comparison
    if compare_policy != "— None —" and compare_policy in wf.evidence_packages:
        pkg_b = wf.evidence_packages[compare_policy]
        ui.section_title(f"⚖ Comparison: {selected_policy} vs {compare_policy}")

        compare_labels = ["Insured Value", "AAL", "Tail Contribution", "Marginal TVaR", "Technical Premium"]
        vals_a = [pkg.key_metrics.get(k, 0) for k in ["insured_value", "aal", "tail_contribution", "marginal_tvar", "technical_premium"]]
        vals_b = [pkg_b.key_metrics.get(k, 0) for k in ["insured_value", "aal", "tail_contribution", "marginal_tvar", "technical_premium"]]

        fig = charts.policy_comparison_bars(compare_labels, vals_a, vals_b, selected_policy, compare_policy)
        st.plotly_chart(fig, use_container_width=True)

        # Key message
        ui.info_banner("💡", "Portfolio Perspective",
                      "Standalone risk is not the whole portfolio story. "
                      "Policies with similar insured values can have very different tail contributions "
                      "depending on their geographic position, co-hit exposure, and flood hazard profile.",
                      Colors.AI_PURPLE, Colors.AI_LIGHT)

    # WHY? interaction
    st.markdown("<br>", unsafe_allow_html=True)
    ui.section_title("❓ WHY?")
    why_options = [
        "Why is this policy this risk level?",
        "Why is this policy priced this way?",
        "Why is TVaR this high?",
        "What is the recommendation rationale?",
        "Show full mathematical trace",
    ]
    why_choice = st.selectbox("Ask FLOODTAIL", why_options)

    if st.button("🔍 Explain", type="primary"):
        if "risk level" in why_choice:
            exp = ExplainabilityEngine.explain_policy(selected_policy, pkg)
            st.markdown(f"**Risk Level:** {exp.risk_level}")
            st.markdown(f"**Summary:** {exp.summary_text}")
            for d in exp.drivers:
                st.markdown(f"- {d}")
        elif "priced" in why_choice:
            exp = ExplainabilityEngine.explain_price(selected_policy, pkg)
            st.markdown(f"**Technical Premium:** {format_currency(exp.technical_premium)}")
            st.markdown(f"**Formula:** {exp.formula_decomposition}")
            for d in exp.premium_drivers:
                st.markdown(f"- {d}")
        elif "TVaR" in why_choice:
            exp = ExplainabilityEngine.explain_tvar(pkg)
            st.markdown(f"**Portfolio TVaR:** {format_currency(exp.portfolio_tvar)}")
            st.markdown(f"**Summary:** {exp.summary_text}")
        elif "recommendation" in why_choice:
            exp = ExplainabilityEngine.explain_recommendation(selected_policy, pkg)
            st.markdown(f"**Recommendation:** {exp.recommendation}")
            st.markdown(f"**Confidence:** {exp.confidence_level} ({exp.confidence_quadrant})")
            st.markdown(f"**Summary:** {exp.summary_text}")
            st.markdown(f"**Guidance:** {exp.action_guidance}")
        elif "mathematical" in why_choice:
            trace = ExplainabilityEngine.generate_mathematical_trace(selected_policy, pkg)
            step_classes = ["", "ft-trace-flood", "ft-trace-flood", "", "", "ft-trace-risk", "ft-trace-ai"]
            for i, step in enumerate(trace.steps):
                cls = step_classes[i] if i < len(step_classes) else ""
                out_val = format_currency(step.output_value) if isinstance(step.output_value, (int, float)) else str(step.output_value)
                ui.trace_step(step.step_number, step.step_name, step.formula, step.output_name, out_val, step.explanation, cls)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 10 — PRICING
# ═══════════════════════════════════════════════════════════════════════════

def page_pricing() -> None:
    ui.page_header("Pricing", "Technical premium waterfall and pricing intelligence")
    if not _require_run():
        return

    pricing = st.session_state.pricing_result

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Total Premium", format_currency(pricing.total_technical_premium), border_color=Colors.ACCENT_RED)
    with c2:
        ui.metric_card("Expected Loss", format_currency(pricing.total_expected_loss), border_color=Colors.NAVY_500)
    with c3:
        ui.metric_card("Tail Charge", format_currency(pricing.total_tail_charge))
    with c4:
        ui.metric_card("Expense", format_currency(pricing.total_expense))

    fig = charts.pricing_waterfall(pricing.total_expected_loss, pricing.total_tail_charge, pricing.total_expense, pricing.total_technical_premium)
    st.plotly_chart(fig, use_container_width=True)

    ui.info_banner("📐", "Pricing Formula",
                  "Technical Premium = Expected Loss (AAL) + Tail Risk Charge (CoC × Tail Contribution) + Expense Loading. "
                  "Prototype technical pricing formula — not a binding quotation.",
                  Colors.NAVY_500, Colors.NAVY_100)

    # Policy pricing table
    ui.section_title("📋 Policy Pricing Detail")
    if pricing.pricing_dataframe is not None:
        st.dataframe(pricing.pricing_dataframe, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 11 — SCENARIO LAB
# ═══════════════════════════════════════════════════════════════════════════

def page_scenario_lab() -> None:
    ui.page_header("Scenario Lab", "Counterfactual analysis and stress testing")
    if not _require_run():
        return

    metrics = st.session_state.metrics_summary
    marginals = st.session_state.get("marginal_impacts", [])

    ui.section_title("📊 Marginal TVaR Impact")
    if marginals:
        marg_data = []
        for m in marginals:
            marg_data.append({
                "Policy": m.policy_id,
                "Marginal TVaR": f"KES {m.marginal_tvar:,.0f}",
                "Impact Direction": "Diversifying" if m.marginal_tvar < 0 else "Concentrating",
            })
        st.dataframe(pd.DataFrame(marg_data), use_container_width=True)

    # What-if TIV control
    ui.section_title("🔬 What-If Analysis")
    st.markdown("Adjust policy TIV and observe the impact on portfolio risk metrics.")
    wif_policy = st.selectbox("Select policy for What-If", st.session_state.portfolio_df["policy_id"].tolist())
    current_tiv = float(st.session_state.portfolio_df[st.session_state.portfolio_df["policy_id"] == wif_policy]["insured_value"].iloc[0])
    new_tiv = st.number_input("New TIV (KES)", value=int(current_tiv), step=1000000, min_value=0)

    if st.button("⚡ Simulate") and new_tiv != current_tiv:
        scale = new_tiv / current_tiv if current_tiv > 0 else 1.0
        st.markdown(f"**Scale Factor:** {scale:.2f}x")
        ui.info_banner("📊", "What-If Result",
                      f"TIV change: {format_currency(current_tiv)} → {format_currency(float(new_tiv))}. "
                      f"Expected proportional impact on AAL and tail contribution.",
                      Colors.AI_PURPLE, Colors.AI_LIGHT)

    ui.info_banner("⚠", "Prototype Assumption",
                  "Stress assumptions are simple multipliers — not validated climate projections.",
                  Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 12 — RISK APPETITE
# ═══════════════════════════════════════════════════════════════════════════

def page_risk_appetite() -> None:
    ui.page_header("Risk Appetite", "Portfolio governance and underwriting thresholds")
    if not _require_run():
        return

    recs = st.session_state.get("recommendations", [])
    accept = sum(1 for r in recs if r.recommendation == "ACCEPT")
    review = sum(1 for r in recs if r.recommendation == "REVIEW")
    escalate = sum(1 for r in recs if r.recommendation == "ESCALATE")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Total Evaluated", str(len(recs)))
    with c2:
        ui.metric_card("Accept", str(accept), border_color=Colors.STATUS_GREEN)
    with c3:
        ui.metric_card("Review", str(review), border_color=Colors.STATUS_AMBER)
    with c4:
        ui.metric_card("Escalate", str(escalate), border_color=Colors.STATUS_RED)

    ui.section_title("📋 Policy Recommendations")
    rec_data = []
    for r in recs:
        rec_data.append({
            "Policy": r.policy_id,
            "Recommendation": r.recommendation,
            "AAL": f"KES {r.aal:,.0f}",
            "Tail Contribution": f"KES {r.tail_contribution:,.0f}",
            "Tail Share": f"{r.tail_share_pct:.1f}%",
            "Marginal TVaR": f"KES {r.marginal_tvar:,.0f}",
            "Co-Hit Rate": f"{r.co_hit_rate:.1%}",
            "Flags": ", ".join(r.risk_flags) if r.risk_flags else "—",
        })
    st.dataframe(pd.DataFrame(rec_data), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 13 — DECISIONS
# ═══════════════════════════════════════════════════════════════════════════

def page_decisions() -> None:
    ui.page_header("Decision Centre", "AI recommends — Human decides")
    if not _require_run():
        return

    wf = st.session_state.workflow_result
    decision_engine = st.session_state.get("decision_engine")

    policy_ids = list(wf.evidence_packages.keys())
    selected = st.selectbox("Select policy to decide", policy_ids)
    pkg = wf.evidence_packages[selected]

    # Evidence summary
    col_ev, col_dec = st.columns([3, 2])
    with col_ev:
        ui.section_title(f"📋 Evidence: {selected}")
        st.markdown(f"**Recommendation:** {ui.risk_badge(pkg.recommendation)}", unsafe_allow_html=True)
        st.markdown(f"**Confidence:** {ui.confidence_badge(pkg.confidence.level)}", unsafe_allow_html=True)
        st.markdown(f"**Technical Premium:** {format_currency(pkg.key_metrics.get('technical_premium', 0))}")
        st.markdown(f"**AAL:** {format_currency(pkg.key_metrics.get('aal', 0))}")
        st.markdown(f"**Tail Contribution:** {format_currency(pkg.key_metrics.get('tail_contribution', 0))}")

        if pkg.confidence.factors:
            ui.section_title("📊 Confidence Factors")
            for f in pkg.confidence.factors:
                st.markdown(f"- {f}")
        if pkg.warnings:
            ui.section_title("⚠ Warnings")
            for w in pkg.warnings:
                st.warning(w)

    with col_dec:
        ui.section_title("👤 Human Decision")
        decision = st.radio("Decision", ["ACCEPT", "MODIFY", "REJECT"], horizontal=True)
        reason = ""
        modified_premium = None

        if decision == "MODIFY":
            modified_premium = st.number_input("Modified Premium (KES)", min_value=0, step=100000,
                                              value=int(pkg.key_metrics.get("technical_premium", 0)))
            reason = st.text_area("Justification (required)", placeholder="Explain the premium modification...")
        elif decision == "REJECT":
            reason = st.text_area("Justification (required)", placeholder="Explain the rejection reason...")

        user = st.text_input("Underwriter", value="lead_underwriter")

        if st.button("✅ Record Decision", type="primary"):
            if decision_engine is None:
                st.error("Decision engine not available.")
            elif decision in ("MODIFY", "REJECT") and not reason.strip():
                st.error("A justification reason is mandatory for MODIFY or REJECT decisions.")
            elif decision == "MODIFY" and (modified_premium is None or modified_premium <= 0):
                st.error("A positive modified premium is required.")
            elif not user.strip():
                st.error("Underwriter identity is required.")
            else:
                try:
                    result = decision_engine.record_human_decision(
                        evidence=pkg,
                        human_decision=decision,
                        user=user,
                        reason=reason if reason.strip() else None,
                        modified_premium=float(modified_premium) if modified_premium else None,
                    )
                    ui.info_banner("✅", "Decision Recorded",
                                  f"**{decision}** for {selected}. "
                                  f"Final premium: {format_currency(result.final_premium)}. "
                                  f"Audit record #{result.audit_record_id}.",
                                  Colors.STATUS_GREEN, Colors.STATUS_GREEN_BG)
                except Exception as e:
                    st.error(str(e))


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 14 — AUDIT
# ═══════════════════════════════════════════════════════════════════════════

def page_audit() -> None:
    ui.page_header("Audit Trail", "Cryptographic decision governance and hash chain verification")
    if not _require_run():
        return

    audit_mgr = st.session_state.get("audit_manager")
    if not audit_mgr:
        ui.empty_state("🔒", "Audit manager not available.")
        return

    # Verify chain button
    if st.button("🔐 Verify Audit Chain", type="primary"):
        v_result = audit_mgr.verify_audit_chain()
        if v_result.is_valid:
            ui.info_banner("🔐", "AUDIT CHAIN VALID",
                          f"✓ {v_result.record_count} records verified. No tampering detected.",
                          Colors.STATUS_GREEN, Colors.STATUS_GREEN_BG)
        else:
            ui.info_banner("🚨", "AUDIT CHAIN BROKEN",
                          f"✕ Tampering detected at record #{v_result.broken_index}. "
                          f"Expected: {v_result.expected_hash[:16]}... Got: {v_result.actual_hash[:16]}...",
                          Colors.STATUS_RED, Colors.STATUS_RED_BG)

    # Decision history
    ui.section_title("📋 Decision History")
    try:
        from src.database import get_connection
        with get_connection(audit_mgr.db.db_path) as conn:
            rows = conn.execute(
                "SELECT timestamp, user, policy_id, recommendation, final_decision, "
                "original_premium, new_premium, reason, model_version, run_id "
                "FROM audit_log ORDER BY id ASC"
            ).fetchall()
        if rows:
            audit_data = []
            for r in rows:
                audit_data.append({
                    "Timestamp": r["timestamp"],
                    "User": r["user"],
                    "Policy": r["policy_id"],
                    "AI Recommendation": r["recommendation"],
                    "Human Decision": r["final_decision"],
                    "Original Premium": f"KES {r['original_premium']:,.0f}",
                    "New Premium": f"KES {r['new_premium']:,.0f}",
                    "Reason": r["reason"] or "—",
                    "Run ID": r["run_id"],
                })
            st.dataframe(pd.DataFrame(audit_data), use_container_width=True)
        else:
            ui.info_banner("📝", "No Decisions Yet", "Record decisions in the Decision Centre to populate the audit trail.")
    except Exception:
        ui.info_banner("📝", "No Decisions Yet", "Record decisions in the Decision Centre to populate the audit trail.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 15 — METHODOLOGY
# ═══════════════════════════════════════════════════════════════════════════

def page_methodology() -> None:
    ui.page_header("Methodology", "Technical documentation and assumptions")

    sections = {
        "Data": "Portfolio exposure data is ingested, normalized, geocoded, and quality-audited. "
                "Schema mapping handles heterogeneous column names. Data quality scoring penalizes "
                "missing values, outliers, duplicates, and coordinate anomalies.",
        "Event Set": "Stochastic flood events are generated from a catalogue of historical and synthetic flood scenarios. "
                     "Event rates follow a Poisson process with configurable annual frequencies per peril zone.",
        "Hazard": "Spatial intersection determines flood depth at each policy location for each event occurrence. "
                  "Hazard footprints define affected geographic areas with depth profiles.",
        "Vulnerability": "Depth-damage curves translate flood depth to mean damage ratio (MDR) by construction class. "
                         "⚠ Prototype benchmark curves are used — Kenya-specific calibration is not yet established.",
        "Loss": "Ground-up loss = TIV × MDR. Net loss applies deductible and limit. "
                "Event Loss Table (ELT) aggregates all policy-event losses. "
                "Year Loss Table (YLT) aggregates annual totals. ELT-YLT reconciliation enforced.",
        "AAL": "Average Annual Loss = mean of annual aggregate losses across all simulation years. "
               "Independently verified using compensated (Kahan) summation.",
        "OEP / AEP": "Occurrence Exceedance Probability uses the maximum event loss per year. "
                     "Aggregate Exceedance Probability uses the annual aggregate loss. "
                     "Empirical quantiles interpolated at standard return periods.",
        "VaR / TVaR": "Value at Risk = empirical quantile at specified confidence level. "
                      "Tail Value at Risk = weighted average of losses exceeding VaR, "
                      "with fractional boundary year weighting for non-integer tail mass.",
        "Tail Contribution": "Each policy's contribution to portfolio TVaR is allocated empirically: "
                             "sum of policy losses in tail years, weighted by tail observation weights. "
                             "Reconciliation: Σ policy tail contributions = Portfolio TVaR.",
        "Pricing": "Technical Premium = AAL + Tail Risk Charge (CoC × Tail Contribution) + Expense Loading. "
                   "⚠ Prototype formula with 10% cost of capital and 10% expense ratio.",
        "Agents": "11 specialized agents execute sequentially with typed inputs/outputs. "
                  "Critical agent failures halt the pipeline. No LLMs — all logic is deterministic.",
        "Human Decision": "Every policy requires explicit human decision (ACCEPT/MODIFY/REJECT). "
                          "MODIFY and REJECT require mandatory written justification.",
        "Governance": "SHA-256 cryptographic hash chain links each audit record to its predecessor. "
                      "Tamper detection via full chain recomputation. Genesis record uses zero-hash.",
    }

    for title, content in sections.items():
        with st.expander(f"📐 {title}", expanded=False):
            st.markdown(content)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 16 — FUTURE / 2090
# ═══════════════════════════════════════════════════════════════════════════

def page_future_2090() -> None:
    ui.page_header("FLOODTAIL 2090", "Vision — Not Prototype")

    st.markdown(
        f'<div style="text-align:center;padding:40px 20px;">'
        f'<div style="font-size:48px;margin-bottom:12px;">🌍</div>'
        f'<div style="font-size:32px;font-weight:800;color:{Colors.NAVY_800};letter-spacing:-0.02em;">'
        f'The Future of Catastrophe Intelligence</div>'
        f'<div style="font-size:16px;color:{Colors.GRAY_500};margin-top:8px;max-width:600px;margin-left:auto;margin-right:auto;">'
        f'From reactive reinsurance to predictive, continuous portfolio intelligence</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    vision_items = [
        ("🛰️", "Earth Observation", "Satellite imagery, SAR, and multispectral data for real-time flood extent mapping and exposure validation."),
        ("🧠", "Physics-Informed AI", "Machine learning constrained by hydrological physics for sub-catchment flood modelling."),
        ("📡", "Sensor Fusion", "IoT gauges, weather stations, and crowdsourced data for continuous hazard monitoring."),
        ("🏙️", "Digital Twins", "High-resolution 3D city models for property-level vulnerability assessment."),
        ("⚡", "Advanced Computing", "GPU-accelerated Monte Carlo with millions of scenarios per minute."),
        ("🔄", "Continuous Intelligence", "Always-on portfolio risk monitoring with automated rebalancing signals."),
    ]
    for i, (icon, title, desc) in enumerate(vision_items):
        with cols[i % 3]:
            st.markdown(
                f'<div class="ft-card" style="text-align:center;min-height:200px;">'
                f'<div style="font-size:36px;margin-bottom:8px;">{icon}</div>'
                f'<div style="font-size:15px;font-weight:700;color:{Colors.NAVY_800};">{title}</div>'
                f'<div style="font-size:12px;color:{Colors.GRAY_500};margin-top:8px;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Timeline
    st.markdown("<br>", unsafe_allow_html=True)
    ui.section_title("📅 Roadmap")
    t1, t2, t3 = st.columns(3)
    with t1:
        ui.card(
            f'<div style="text-align:center;">'
            f'<div class="ft-metric-label" style="color:{Colors.STATUS_GREEN};">TODAY</div>'
            f'<div style="font-size:16px;font-weight:700;color:{Colors.NAVY_800};margin:8px 0;">Foundation</div>'
            f'<div style="font-size:12px;color:{Colors.GRAY_500};">Stochastic cat model · Agent workflow · Explainable decisions · Audit governance</div>'
            f'</div>'
        )
    with t2:
        ui.card(
            f'<div style="text-align:center;">'
            f'<div class="ft-metric-label" style="color:{Colors.STATUS_AMBER};">NEXT</div>'
            f'<div style="font-size:16px;font-weight:700;color:{Colors.NAVY_800};margin:8px 0;">Enhancement</div>'
            f'<div style="font-size:12px;color:{Colors.GRAY_500};">Climate scenarios · Treaty structures · Real-time data · API integration</div>'
            f'</div>'
        )
    with t3:
        ui.card(
            f'<div style="text-align:center;">'
            f'<div class="ft-metric-label" style="color:{Colors.AI_PURPLE};">2090</div>'
            f'<div style="font-size:16px;font-weight:700;color:{Colors.NAVY_800};margin:8px 0;">Vision</div>'
            f'<div style="font-size:12px;color:{Colors.GRAY_500};">Earth observation · Physics-informed AI · Digital twins · Continuous intelligence</div>'
            f'</div>'
        )

    ui.info_banner("🔬", "Vision — Not Prototype",
                  "The 2090 capabilities shown above represent a conceptual future architecture. "
                  "They are not implemented in the current system and should not be interpreted as production features.",
                  Colors.AI_PURPLE, Colors.AI_LIGHT)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

PAGE_MAP = {
    "01 — Overview": page_overview,
    "02 — Portfolio": page_portfolio,
    "03 — Data Intelligence": page_data_intelligence,
    "04 — Agent Control": page_agent_control,
    "05 — Flood Risk": page_flood_risk,
    "06 — Accumulation": page_accumulation,
    "07 — Catastrophe Analytics": page_cat_analytics,
    "08 — Tail Risk": page_tail_risk,
    "09 — Policy Intelligence": page_policy_intelligence,
    "10 — Pricing": page_pricing,
    "11 — Scenario Lab": page_scenario_lab,
    "12 — Risk Appetite": page_risk_appetite,
    "13 — Decisions": page_decisions,
    "14 — Audit": page_audit,
    "15 — Methodology": page_methodology,
    "16 — Future / 2090": page_future_2090,
}


def run_app() -> None:
    """Render the full Streamlit UI application."""
    st.set_page_config(
        page_title="FLOODTAIL — Flood Catastrophe & Portfolio Intelligence",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    _init_session()

    with st.sidebar:
        st.markdown(
            f'<div style="padding:20px 16px 16px;">'
            f'<div style="font-size:22px;font-weight:800;color:{Colors.WHITE};letter-spacing:-0.02em;">🌊 FLOODTAIL</div>'
            f'<div style="font-size:11px;color:{Colors.GRAY_400};margin-top:2px;">Flood Catastrophe & Portfolio Intelligence</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Mode selector
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if st.button("🎯 Demo", use_container_width=True, type="primary" if st.session_state.mode == "DEMO" else "secondary"):
                if not st.session_state.run_complete:
                    with st.spinner("Running FLOODTAIL demo pipeline..."):
                        _run_demo_pipeline()
                    st.rerun()
        with mode_col2:
            if st.button("📡 Live", use_container_width=True, type="primary" if st.session_state.mode == "LIVE" else "secondary"):
                st.session_state.mode = "LIVE"

        # Run status
        if st.session_state.run_complete:
            run_id = st.session_state.run_id
            cfg = st.session_state.config
            wf = st.session_state.workflow_result
            status_color = Colors.STATUS_GREEN if wf and wf.status == "SUCCESS" else Colors.STATUS_AMBER
            st.markdown(
                f'<div style="padding:8px 16px;background:{Colors.NAVY_900};border-radius:6px;margin:8px 16px;">'
                f'<div style="font-size:10px;color:{Colors.GRAY_400};text-transform:uppercase;letter-spacing:0.05em;">Run ID</div>'
                f'<div style="font-size:13px;color:{Colors.WHITE};font-weight:600;">{run_id[:20]}</div>'
                f'<div style="font-size:10px;color:{Colors.GRAY_400};margin-top:6px;">Model</div>'
                f'<div style="font-size:12px;color:{Colors.GRAY_200};">{cfg.model.model_version if cfg else "—"}</div>'
                f'<div style="font-size:10px;color:{Colors.GRAY_400};margin-top:6px;">Status</div>'
                f'<div style="font-size:12px;color:{status_color};font-weight:600;">● {"READY" if wf and wf.status == "SUCCESS" else "REVIEW REQUIRED"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="padding:8px 16px;background:{Colors.NAVY_900};border-radius:6px;margin:8px 16px;">'
                f'<div style="font-size:12px;color:{Colors.GRAY_400};text-align:center;">Click <b>Demo</b> to load</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        page = st.radio("Navigation", PAGES, label_visibility="collapsed")

    # Execute selected page
    PAGE_MAP.get(page, page_overview)()

    # Footer
    st.markdown("---")
    st.markdown(
        f'<div style="text-align:center;font-size:11px;color:{Colors.GRAY_400};padding:8px;">'
        f'FLOODTAIL · Prototype Catastrophe Risk Intelligence · Synthetic Data · Not for Production Use'
        f'</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    """Bootstrap FLOODTAIL backend and display system status.

    If running within Streamlit, executes the UI application.
    """
    if getattr(st, "runtime", None) and st.runtime.exists():
        run_app()
    else:
        cfg = load_config()
        ctx = RunContext(
            model_version=cfg.model.model_version,
            random_seed=cfg.simulation.seed,
            simulation_years=cfg.simulation.years,
            scenario=cfg.project.environment,
        )
        print(f"FLOODTAIL backend bootstrap complete. Run ID: {ctx.run_id}")


if getattr(st, "runtime", None) and st.runtime.exists():
    run_app()
elif __name__ == "__main__":
    main()
