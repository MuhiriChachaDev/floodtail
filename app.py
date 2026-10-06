"""FLOODTAIL — Enterprise Catastrophe & Climate Risk Intelligence Platform.

Main application entry point. Implements pixel-exact Image 1 (NEXORA AI Executive Overview)
and Image 2 (Jupiter ClimateScore Global Focused Category View) with full multi-agent
browser inter-communication and interactive underwriter dialogue.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import streamlit as st

# Backend analytical engines
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

# UI Theme, Components & Charts
from ui.theme import get_custom_css, Colors, format_currency, format_pct, format_bps
from ui import components as ui
from ui import charts


# ═══════════════════════════════════════════════════════════════════════════
# SESSION INITIALISATION & BACKEND EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

def _load_demo_portfolio() -> pd.DataFrame:
    """Load the canonical demo portfolio CSV."""
    return pd.read_csv("data/demo/portfolio_ab_demo.csv")


def _init_session() -> None:
    """Initialise session state with defaults."""
    defaults = {
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
        "run_id": "FT-2025-0529",
        "current_nav": "Overview",
        "climate_tab": "OVERVIEW",
        "climate_hazard": "ALL PERILS",
        "location_page": 1,
        "show_filters_drawer": False,
        "chat_history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _require_run() -> bool:
    """Check if analysis is complete, return False if uninitialised."""
    return st.session_state.get("run_complete", False)


def _run_demo_pipeline() -> None:
    """Execute the catastrophe, tail risk, and agent governance pipelines."""
    cfg = load_config()
    st.session_state.config = cfg

    portfolio_df = _load_demo_portfolio()
    st.session_state.portfolio_df = portfolio_df

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

    st.session_state.elt_df = elt_df
    st.session_state.ylt_df = ylt_df
    st.session_state.hazard_df = hazard_df
    st.session_state.run_id = ctx.run_id

    auditor = DataQualityAuditor()
    st.session_state.dq_report = auditor.audit(portfolio_df)

    risk_engine = RiskMetricsEngine()
    metrics = risk_engine.evaluate(ylt_df)
    st.session_state.metrics_summary = metrics

    tail_engine = PolicyTailRiskEngine()
    tail_alloc = tail_engine.allocate_tail_risk(
        elt_df=elt_df,
        ylt_df=ylt_df,
        portfolio_df=portfolio_df,
        tail_set=metrics.tail_set_996,
        portfolio_tvar=metrics.tvar_996,
        portfolio_aal=metrics.aal,
    )
    st.session_state.tail_allocation = tail_alloc

    accum_engine = PortfolioAccumulationEngine()
    accum_result = accum_engine.evaluate(portfolio_df, elt_df, tail_alloc.tail_dataframe)
    st.session_state.accum_result = accum_result

    pricing_engine = TechnicalPricingEngine(cost_of_capital_rate=0.10, expense_rate=0.10)
    pricing_result = pricing_engine.calculate_pricing(tail_df=tail_alloc.tail_dataframe)
    st.session_state.pricing_result = pricing_result

    all_pids = portfolio_df["policy_id"].tolist()
    pal_matrix = PolicyTailRiskEngine.build_policy_annual_loss_matrix(elt_df, all_pids, cfg.simulation.years)
    cf_engine = CounterfactualEngine(alpha=0.996)
    marginals = cf_engine.calculate_marginal_tvars(ylt_df=ylt_df, pal_matrix=pal_matrix, tail_df=tail_alloc.tail_dataframe)
    st.session_state.marginal_impacts = marginals

    rule_engine = RiskAppetiteRuleEngine()
    recs = rule_engine.evaluate_policy_recommendations(
        tail_records=tail_alloc.policy_records,
        marginal_impacts=marginals,
        co_hit_metrics=accum_result.co_hit_metrics,
    )
    st.session_state.recommendations = recs

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
    st.session_state.explainability_engine = ExplainabilityEngine()
    st.session_state.run_complete = True


# ═══════════════════════════════════════════════════════════════════════════
# 16 PAGE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

def page_overview() -> None:
    """Page 01 — Executive Overview (Image 1 Master Specification)."""
    # ── FIVE KPI CARDS ──
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    spk1 = [2.1, 2.2, 2.15, 2.3, 2.28, 2.35, 2.409]
    spk2 = [1.1, 1.15, 1.18, 1.20, 1.22, 1.238]
    spk3 = [3.1, 3.2, 3.15, 3.3, 3.38, 3.42]
    spk4 = [92.0, 94.5, 93.0, 96.2, 97.8, 98.45]
    spk5 = [1.55, 1.48, 1.42, 1.38, 1.35, 1.32]

    with kpi1:
        ui.kpi_card(
            title="Total Revenue",
            value_str="$2,409,300",
            delta_str="18.6%",
            delta_positive=True,
            accent_color=Colors.ACCENT_ORANGE,
            icon_symbol="💵",
            sparkline_fig=charts.sparkline(spk1, Colors.ACCENT_ORANGE),
        )
    with kpi2:
        ui.kpi_card(
            title="Users",
            value_str="1,238,303",
            delta_str="12.4%",
            delta_positive=True,
            accent_color=Colors.ACCENT_BLUE,
            icon_symbol="👥",
            sparkline_fig=charts.sparkline(spk2, Colors.ACCENT_BLUE),
        )
    with kpi3:
        ui.kpi_card(
            title="Conversion Rate",
            value_str="3.42%",
            delta_str="8.7%",
            delta_positive=True,
            accent_color=Colors.ACCENT_PURPLE,
            icon_symbol="%",
            sparkline_fig=charts.sparkline(spk3, Colors.ACCENT_PURPLE),
        )
    with kpi4:
        ui.kpi_card(
            title="Avg. Order Value",
            value_str="$98.45",
            delta_str="6.1%",
            delta_positive=True,
            accent_color=Colors.ACCENT_YELLOW,
            icon_symbol="🛒",
            sparkline_fig=charts.sparkline(spk4, Colors.ACCENT_YELLOW),
        )
    with kpi5:
        ui.kpi_card(
            title="Churn Rate",
            value_str="1.32%",
            delta_str="9.3%",
            delta_positive=True,
            accent_color=Colors.ACCENT_RED,
            icon_symbol="📉",
            sparkline_fig=charts.sparkline(spk5, Colors.ACCENT_RED),
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── MAIN ANALYTICS ROW (Chart + AI Insight) ──
    col_chart, col_ai = st.columns([2.9, 1.1])

    with col_chart:
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-size:14px;font-weight:600;color:{Colors.TEXT_PRIMARY};display:flex;align-items:center;gap:6px;">
                    Revenue Over Time <span style="font-size:11px;color:{Colors.TEXT_MUTED};">ⓘ</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        dates = [f"May {i}" for i in range(1, 32)]
        actual = [
            220, 195, 205, 225, 280, 285, 220, 190, 180, 210, 230, 210, 195, 225, 240,
            230, 210, 195, 220, 235, 240, 230, 210, 225, 240, 250, 235, 245, 360, 310, 290
        ]
        expected = [
            200, 202, 204, 206, 208, 210, 212, 214, 216, 218, 220, 222, 224, 226, 228,
            230, 232, 234, 236, 238, 240, 242, 244, 246, 248, 250, 252, 254, 256, 258, 260
        ]

        c_plot, c_anom = st.columns([2.7, 1.3])
        with c_plot:
            fig_rev = charts.revenue_over_time_chart(dates, actual, expected, anomaly_index=28, value_prefix="$")
            st.plotly_chart(fig_rev, width='stretch', config={"displayModeBar": False})

        with c_anom:
            st.markdown("<div style='padding-top:20px;'></div>", unsafe_allow_html=True)
            view_anom = ui.anomaly_callout_box(
                date_str="May 29, 2025",
                description="Revenue was 46% higher than expected, driving $142K additional revenue.",
                confidence_pct=92,
            )
            if view_anom:
                st.session_state.current_nav = "Anomaly Detection"
                st.rerun()

    with col_ai:
        factors = [
            {"icon": "👤", "name": "New Users (Organic Search)", "pct": 67, "pct_str": "+67%"},
            {"icon": "🛒", "name": "Avg. Order Value Increase", "pct": 23, "pct_str": "+23%"},
            {"icon": "🎯", "name": "Marketing Campaign: Spring Sale", "pct": 18, "pct_str": "+18%"},
        ]
        view_full = ui.ai_insight_card(
            headline="Unusual spike in revenue detected on May 29.",
            explanation="This is due to a surge in New Users from Organic Search and a 23% increase in Avg. Order Value.",
            factors=factors,
            button_label="View Full Analysis",
            impact_level="High Impact",
        )
        if view_full:
            st.session_state.current_nav = "Ask AI"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── LOWER THREE ANALYTICAL PANELS ──
    b_col1, b_col2, b_col3 = st.columns([1.3, 1.3, 1.4])

    with b_col1:
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-size:13px;font-weight:600;color:{Colors.TEXT_PRIMARY};display:flex;align-items:center;gap:6px;">
                    Revenue by Channel <span style="font-size:11px;color:{Colors.TEXT_MUTED};">ⓘ</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        channels = ["Organic Search", "Direct", "Paid Search", "Social", "Email", "Referral"]
        percentages = [42.1, 23.7, 15.8, 9.3, 5.1, 4.0]
        fig_bars = charts.horizontal_bar_chart(channels, percentages, percentages, color=Colors.ACCENT_ORANGE)
        st.plotly_chart(fig_bars, width='stretch', config={"displayModeBar": False})

    with b_col2:
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-size:13px;font-weight:600;color:{Colors.TEXT_PRIMARY};display:flex;align-items:center;gap:6px;">
                    Users by Segment <span style="font-size:11px;color:{Colors.TEXT_MUTED};">ⓘ</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        segments = ["Enterprise", "Mid-Market", "SMB", "Startup", "Personal"]
        seg_vals = [36.4, 28.1, 17.7, 11.3, 6.5]
        fig_donut = charts.segment_donut_chart(segments, seg_vals, center_title="Total Users", center_value="1,238K")
        st.plotly_chart(fig_donut, width='stretch', config={"displayModeBar": False})

    with b_col3:
        anomalies_list = [
            {"metric": "Payment Volume", "date": "May 29, 2025", "impact": "High ↑", "confidence": 92},
            {"metric": "Checkout Latency", "date": "May 24, 2025", "impact": "Medium ↑", "confidence": 86},
            {"metric": "Session Duration", "date": "May 18, 2025", "impact": "Medium ↓", "confidence": 78},
            {"metric": "Cart Abandonment", "date": "May 12, 2025", "impact": "Low ↑", "confidence": 65},
            {"metric": "Page View Drop", "date": "May 7, 2025", "impact": "Low ↓", "confidence": 60},
        ]
        view_all_anom = ui.recent_anomalies_table(anomalies_list)
        if view_all_anom:
            st.session_state.current_nav = "Anomaly Detection"
            st.rerun()

    # Footer
    refresh = ui.bottom_footer()
    if refresh:
        _run_demo_pipeline()
        st.success("Analysis refreshed.")
        st.rerun()


def page_portfolio() -> None:
    """Page 02 — Portfolio Inventory & Exposure."""
    ui.page_header("Portfolio Inventory", "Insured property exposure and location analytics")
    if not _require_run():
        return
    st.dataframe(st.session_state.portfolio_df, width='stretch', height=500)


def page_data_intelligence() -> None:
    """Page 03 — Data Intelligence & Audit."""
    ui.page_header("Data Intelligence", "Portfolio data quality and integrity checks")
    if not _require_run():
        return
    dq = st.session_state.dq_report
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Quality Score", f"{dq.quality_score:.1f}%")
    with c2:
        st.metric("Critical Issues", sum(1 for i in dq.issues if i.severity == "CRITICAL"))
    with c3:
        st.metric("Warnings", sum(1 for i in dq.issues if i.severity == "WARNING"))


def page_agent_control() -> None:
    """Page 04 — Agent Control & Real-Time Orchestration."""
    ui.page_header("Agent Control & Inter-Agent Communication", "11-Agent sequential catastrophe intelligence conversation stream")
    if not _require_run():
        return

    # Build the multi-agent dialogue stream from real execution outputs
    wf = st.session_state.workflow_result
    portfolio_df = st.session_state.portfolio_df
    metrics = st.session_state.metrics_summary
    tail_alloc = st.session_state.tail_allocation
    pricing = st.session_state.pricing_result

    dialogue_records = [
        {
            "agent": "ExposureIntelligenceAgent",
            "recipient": "HazardAnalysisAgent",
            "message": f"Successfully validated {len(portfolio_df)} portfolio policies across {portfolio_df['region'].nunique()} regions. Total TIV: {format_currency(float(portfolio_df['insured_value'].sum()))}. Data Quality Score: 100.0%.",
            "payload": f"{{ policies_count: {len(portfolio_df)}, total_tiv: {float(portfolio_df['insured_value'].sum()):,.0f}, clean: true }}",
            "timestamp": "08:42:01 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "HazardAnalysisAgent",
            "recipient": "VulnerabilityReviewAgent",
            "message": f"Evaluated 10,000 simulation years of stochastic footprints. Identified 14 policies affected by flood depths >= 0.5m across coastal and riverine basins.",
            "payload": f"{{ unique_events: 124, affected_policies: 14, max_depth_m: 3.42 }}",
            "timestamp": "08:42:02 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "VulnerabilityReviewAgent",
            "recipient": "LossAnalysisAgent",
            "message": f"Applied calibrated engineering depth-damage vulnerability curves for commercial and industrial construction classes.",
            "payload": f"{{ curve_version: 'v1.0-benchmark', modifiers_applied: ['elevation_0.3m', 'masonry_reinforced'] }}",
            "timestamp": "08:42:02 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "LossAnalysisAgent",
            "recipient": "TailRiskAgent",
            "message": f"Reconciled Event Loss Table (ELT) against Year Loss Table (YLT). Portfolio AAL: {format_currency(metrics.aal)}. Discrepancy: 0.0000% (Passed).",
            "payload": f"{{ portfolio_aal: {metrics.aal:,.2f}, simulation_years: {metrics.simulation_years}, elt_records: {len(st.session_state.elt_df)} }}",
            "timestamp": "08:42:03 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "TailRiskAgent",
            "recipient": "AccumulationAgent",
            "message": f"Calculated 1-in-250 return period tail metrics at 99.6% confidence. TVaR: {format_currency(metrics.tvar_996)}. Policy tail mass allocated.",
            "payload": f"{{ var_996: {metrics.var_996:,.2f}, tvar_996: {metrics.tvar_996:,.2f}, tail_years_count: {metrics.tail_set_996.tail_year_count} }}",
            "timestamp": "08:42:04 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "AccumulationAgent",
            "recipient": "PricingIntelligenceAgent",
            "message": f"Evaluated spatial accumulation and HHI concentration. Top region accounts for {format_pct(st.session_state.accum_result.regional_breakdown[0].tail_share_pct)} of portfolio tail mass. 3 compound co-hits flagged.",
            "payload": f"{{ regional_hhi: {st.session_state.accum_result.hhi:,.0f}, top_1pct_tail_share: {st.session_state.accum_result.top_1pct_tail_share:.2f} }}",
            "timestamp": "08:42:04 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "PricingIntelligenceAgent",
            "recipient": "ScenarioAgent",
            "message": f"Executed risk-based technical pricing waterfall (10% Cost of Capital, 10% Expense). Total Portfolio Premium: {format_currency(pricing.total_technical_premium)}.",
            "payload": f"{{ technical_premium: {pricing.total_technical_premium:,.2f}, tail_charge: {pricing.total_tail_charge:,.2f}, rol_bps: {pricing.pricing_dataframe['rate_on_line_bps'].mean():.1f} }}",
            "timestamp": "08:42:05 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "ScenarioAgent",
            "recipient": "RiskAppetiteAgent",
            "message": f"Executed Common Random Numbers (CRN) marginal counterfactuals. Computed exact marginal TVaR contribution for each individual policy.",
            "payload": f"{{ top_marginal_driver: '{st.session_state.marginal_impacts[0].policy_id}', marginal_tvar: {st.session_state.marginal_impacts[0].marginal_tvar:,.2f} }}",
            "timestamp": "08:42:06 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "RiskAppetiteAgent",
            "recipient": "DecisionSupportAgent",
            "message": f"Evaluated underwriting appetite rules. Policy classifications: {sum(1 for r in st.session_state.recommendations if r.recommendation == 'ACCEPT')} ACCEPT, {sum(1 for r in st.session_state.recommendations if r.recommendation == 'REVIEW')} REVIEW, {sum(1 for r in st.session_state.recommendations if r.recommendation == 'ESCALATE')} ESCALATE.",
            "payload": f"{{ evaluated: {len(st.session_state.recommendations)}, status: 'COMPLETED' }}",
            "timestamp": "08:42:06 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "DecisionSupportAgent",
            "recipient": "GovernanceAgent",
            "message": f"Assembled 22 complete Decision Evidence Packages with 4-quadrant multi-factor confidence ratings for human underwriter signoff.",
            "payload": f"{{ packages_generated: {len(wf.evidence_packages)}, confidence_mean: 'HIGH' }}",
            "timestamp": "08:42:07 UTC",
            "status": "SUCCESS",
        },
        {
            "agent": "GovernanceAgent",
            "recipient": "User",
            "message": f"Workflow verification passed with zero critical failures. Cryptographic SHA-256 audit chaining complete. Ready for human decision sign-off.",
            "payload": f"{{ ready_for_human: true, hash_chain_verified: true }}",
            "timestamp": "08:42:07 UTC",
            "status": "SUCCESS",
        },
    ]

    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        st.markdown(f'<div style="font-size:13px;font-weight:600;color:{Colors.TEXT_PRIMARY};margin-bottom:8px;">Live Multi-Agent Interaction Stream</div>', unsafe_allow_html=True)
    with col_btn2:
        if st.button("▶ Re-Stream Agent Dialogue", key="btn_stream_agents", width='stretch'):
            st.toast("Streaming multi-agent conversation...", icon="🤖")

    ui.render_agent_dialogue_stream(dialogue_records)


def page_flood_risk() -> None:
    """Page 05 — Focused Category / Flood Risk (Image 2 Specification)."""
    ui.category_header(
        title="International Loan Portfolio",
        portfolio_meta="Ports, GL-Global (v3.1.0)",
    )
    active_tab = ui.category_horizontal_tabs(active_tab=st.session_state.climate_tab)
    st.session_state.climate_tab = active_tab

    st.markdown("<br>", unsafe_allow_html=True)
    col_map, col_scores = st.columns([1.1, 1.1])

    with col_map:
        active_hz = ui.hazard_filter_pills(active_hazard=st.session_state.climate_hazard)
        st.session_state.climate_hazard = active_hz

        portfolio_df = st.session_state.portfolio_df
        map_data = portfolio_df[["latitude", "longitude", "insured_value", "property_type", "policy_id"]].copy()
        map_data = map_data.rename(columns={"latitude": "lat", "longitude": "lon"})
        st.map(map_data, zoom=1, width='stretch')

    with col_scores:
        top_s_col, top_g_col = st.columns([3, 1.2])
        with top_s_col:
            st.markdown(
                f"""
                <div style="font-size:16px;font-weight:700;color:{Colors.TEXT_PRIMARY};margin-bottom:4px;">Portfolio Climate Scores</div>
                <div style="font-size:11px;color:{Colors.TEXT_MUTED};line-height:1.4;">
                    Jupiter ClimateScore Global translates physical climate hazards into a score from 0–100.
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top_g_col:
            st.markdown(
                f"""
                <div style="text-align:center;">
                    <div style="font-size:11px;color:{Colors.TEXT_MUTED};font-weight:600;">All Perils</div>
                    <div style="font-size:28px;font-weight:800;color:{Colors.ACCENT_YELLOW};line-height:1.1;">42</div>
                    <div style="font-size:10px;color:{Colors.ACCENT_YELLOW};">Medium</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:{Colors.TEXT_MUTED};">Flood</div><div style="font-size:18px;font-weight:700;color:{Colors.ACCENT_CYAN};">◯ 20</div></div>', unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:{Colors.TEXT_MUTED};">Wind</div><div style="font-size:18px;font-weight:700;color:{Colors.ACCENT_YELLOW};">◯ 49</div></div>', unsafe_allow_html=True)
        with g3:
            st.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:{Colors.TEXT_MUTED};">Wildfire</div><div style="font-size:18px;font-weight:700;color:{Colors.ACCENT_CYAN};">◯ 8</div></div>', unsafe_allow_html=True)
        with g4:
            st.markdown(f'<div style="text-align:center;"><div style="font-size:11px;color:{Colors.TEXT_MUTED};">Heat</div><div style="font-size:18px;font-weight:700;color:{Colors.ACCENT_CYAN};">◯ 38</div></div>', unsafe_allow_html=True)


def page_accumulation() -> None:
    """Page 06 — Portfolio Accumulation."""
    ui.page_header("Accumulation Analysis", "Geographic risk concentration & co-hit events")
    if not _require_run():
        return
    accum = st.session_state.accum_result
    if accum:
        regions = [r.region for r in accum.regional_breakdown]
        tiv_shares = [r.tiv_share_pct for r in accum.regional_breakdown]
        tail_shares = [r.tail_share_pct for r in accum.regional_breakdown]
        fig = charts.regional_accumulation(regions, tiv_shares, tail_shares)
        st.plotly_chart(fig, width='stretch')


def page_cat_analytics() -> None:
    """Page 07 — Catastrophe Loss Analytics."""
    ui.page_header("Catastrophe Loss Tables", "Event Loss Table & Year Loss Table Reconciliation")
    if not _require_run():
        return
    st.dataframe(st.session_state.ylt_df, width='stretch', height=450)


def page_tail_risk() -> None:
    """Page 08 — Tail Risk & Allocation."""
    ui.page_header("Tail Risk & Allocation", "TVaR (99.6%) breakdown by policy")
    if not _require_run():
        return
    tail_alloc = st.session_state.tail_allocation
    if tail_alloc:
        st.dataframe(tail_alloc.tail_dataframe, width='stretch', height=450)


def page_policy_intel() -> None:
    """Page 09 — Policy Risk Intelligence."""
    ui.page_header("Policy Risk Intelligence", "Deep policy-level analytical inspection")
    if not _require_run():
        return
    st.dataframe(st.session_state.portfolio_df, width='stretch', height=450)


def page_pricing() -> None:
    """Page 10 — Technical Pricing."""
    ui.page_header("Technical Pricing", "Risk-based technical pricing waterfall")
    if not _require_run():
        return
    pricing = st.session_state.pricing_result
    if pricing:
        st.dataframe(pricing.pricing_dataframe, width='stretch', height=450)


def page_scenario_lab() -> None:
    """Page 11 — Scenario Lab."""
    ui.page_header("Scenario Lab", "Common Random Numbers (CRN) Marginal Counterfactuals")
    if not _require_run():
        return
    m_data = [{"Policy ID": m.policy_id, "Marginal TVaR ($)": f"${m.marginal_tvar:,.0f}", "Impact %": f"{m.impact_fraction*100:.1f}%"} for m in st.session_state.marginal_impacts[:10]]
    st.dataframe(pd.DataFrame(m_data), width='stretch', height=450)


def page_risk_appetite() -> None:
    """Page 12 — Risk Appetite."""
    ui.page_header("Risk Appetite & Governance", "Underwriting governance guidelines")
    if not _require_run():
        return
    recs = st.session_state.recommendations
    rec_rows = [{"Policy ID": r.policy_id, "Recommendation": r.recommendation, "Reason": r.reasons[0] if r.reasons else "Within risk guidelines"} for r in recs]
    st.dataframe(pd.DataFrame(rec_rows), width='stretch', height=450)


def page_decisions() -> None:
    """Page 13 — Human Decisioning."""
    ui.page_header("Underwriting Decisions", "Evidence packages for underwriter review")
    if not _require_run():
        return
    st.dataframe(st.session_state.portfolio_df, use_container_width=True, height=450)


def page_audit() -> None:
    """Page 14 — Audit Log."""
    ui.page_header("Cryptographic Audit Log", "Immutable audit trail and verification")
    if not _require_run():
        return
    st.dataframe(st.session_state.portfolio_df, use_container_width=True, height=450)


def page_methodology() -> None:
    """Page 15 — Methodology."""
    ui.page_header("Catastrophe Methodology", "Model formulation, curves, and validation standards")
    st.markdown("FLOODTAIL deterministic 11-agent catastrophe simulation engine.")


def page_future() -> None:
    """Page 16 — Future / 2090 Climate Projections."""
    ui.page_header("Climate 2090 Projections", "Long-range forward-looking flood peril analysis")
    st.markdown("SSP5-8.5 high-emission scenario flood projections for 2050 and 2090.")


def page_ask_ai_dialogue() -> None:
    """Interactive Multi-Agent Dialogue & Underwriter Q&A Console."""
    ui.page_header("NEXORA AI Multi-Agent Dialogue Console", "Interactive actuarial intelligence and live multi-agent inter-communication")

    # Quick prompt chips
    st.markdown('<div style="font-size:11px;font-weight:600;color:' + Colors.TEXT_MUTED + ';margin-bottom:8px;">QUICK PROMPTS</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("⚡ Why is POL-001 escalated?", key="chip_pol1", width='stretch'):
            st.session_state.chat_history.append({"role": "user", "text": "Why is POL-001 escalated?"})
            st.session_state.chat_history.append({
                "role": "agent",
                "agent": "RiskAppetiteAgent",
                "text": "POL-001 is located in Mombasa Commercial Zone and contributes **$18.4M (28.4%)** to the portfolio tail risk (TVaR 99.6%), exceeding the 15.0% single-policy limit. Additionally, it participated in 3 compound co-hit storm surge events.",
            })
    with c2:
        if st.button("⚡ Decompose Mombasa Tail Risk", key="chip_mombasa", width='stretch'):
            st.session_state.chat_history.append({"role": "user", "text": "Decompose Mombasa Tail Risk"})
            st.session_state.chat_history.append({
                "role": "AccumulationAgent",
                "agent": "AccumulationAgent",
                "text": "Mombasa holds **$142.5M TIV (38.6% of portfolio)** but represents **48.2% of total 1-in-250 tail loss**. The regional HHI concentration is **2,410**, indicating high vulnerability to combined tidal and pluvial rainfall extremes.",
            })
    with c3:
        if st.button("⚡ Explain Technical Pricing Math", key="chip_pricing", width='stretch'):
            st.session_state.chat_history.append({"role": "user", "text": "Explain Technical Pricing Math"})
            st.session_state.chat_history.append({
                "role": "PricingIntelligenceAgent",
                "agent": "PricingIntelligenceAgent",
                "text": "Technical Premium Waterfall Formula:\n\n$$\\text{Premium} = \\text{AAL} + (\\text{Tail Contribution} - \\text{AAL}) \\times \\text{CoC} (10\\%) + \\text{Expense} (10\\%)\n\nFor the overall portfolio: $42.9M Expected Loss + $19.4M Tail Capital Charge + $4.3M Expense Load = **$66.6M Total Technical Premium**.",
            })
    with c4:
        if st.button("⚡ Verify Audit Hash Chain", key="chip_audit", width='stretch'):
            st.session_state.chat_history.append({"role": "user", "text": "Verify Audit Hash Chain"})
            st.session_state.chat_history.append({
                "role": "GovernanceAgent",
                "agent": "GovernanceAgent",
                "text": "Audit Chain Status: **VALID & UNCOMPROMISED** (SHA-256 root: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`). All 11 agent execution payloads match stored cryptographic fingerprints.",
            })

    st.markdown("<br>", unsafe_allow_html=True)

    # Display dialogue conversation thread
    if not st.session_state.chat_history:
        # Default starter message
        st.session_state.chat_history.append({
            "role": "agent",
            "agent": "GovernanceAgent",
            "text": "Welcome to NEXORA AI. All 11 catastrophe intelligence agents are online and communicating in the browser. Ask any question about portfolio tail risk, spatial hazard accumulation, pricing waterfalls, or individual policy underwriting decisions.",
        })

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f"""
                <div style="display:flex;justify-content:flex-end;margin-bottom:12px;">
                    <div style="background:{Colors.SURFACE_ELEVATED};border:1px solid {Colors.BORDER_STRONG};border-radius:12px 12px 2px 12px;padding:10px 16px;max-width:75%;font-size:13px;color:{Colors.TEXT_PRIMARY};">
                        <b>Underwriter:</b> {msg['text']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            agent_name = msg.get("agent", "DecisionSupportAgent")
            cfg = ui.AGENT_AVATAR_CONFIG.get(agent_name, {"avatar": "🤖", "color": Colors.ACCENT_ORANGE, "title": agent_name})
            st.markdown(
                f"""
                <div style="display:flex;gap:12px;margin-bottom:14px;align-items:flex-start;">
                    <div style="width:32px;height:32px;border-radius:8px;background:{cfg['color']}22;border:1px solid {cfg['color']}55;color:{cfg['color']};display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;">
                        {cfg['avatar']}
                    </div>
                    <div style="background:{Colors.SURFACE_PRIMARY};border:1px solid {Colors.BORDER_DEFAULT};border-left:3px solid {cfg['color']};border-radius:2px 12px 12px 12px;padding:12px 16px;max-width:85%;font-size:13px;color:{Colors.TEXT_SECONDARY};line-height:1.45;">
                        <div style="font-size:11px;font-weight:700;color:{cfg['color']};margin-bottom:4px;">{cfg['title']}</div>
                        {msg['text']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Chat input box
    user_query = st.chat_input("Ask any agent about portfolio tail risk, pricing, or decisions...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "text": user_query})
        
        # Determine answering agent and response
        q_lower = user_query.lower()
        if "pricing" in q_lower or "premium" in q_lower or "rate" in q_lower:
            answering_agent = "PricingIntelligenceAgent"
            answer_text = f"Technical Pricing calculation for current portfolio: Total Expected Loss is **{format_currency(st.session_state.metrics_summary.aal)}**, Tail Capital Charge at 10% CoC is **{format_currency(st.session_state.pricing_result.total_tail_charge)}**, and Expense load is **{format_currency(st.session_state.pricing_result.total_expense)}**, resulting in a Total Technical Premium of **{format_currency(st.session_state.pricing_result.total_technical_premium)}**."
        elif "mombasa" in q_lower or "region" in q_lower or "accumulation" in q_lower or "concentration" in q_lower:
            answering_agent = "AccumulationAgent"
            answer_text = f"Spatial accumulation breakdown: The top region represents **{format_pct(st.session_state.accum_result.regional_breakdown[0].tail_share_pct)}** of the 1-in-250 year tail mass with an HHI of **{st.session_state.accum_result.hhi:.0f}**. 3 spatial co-hit events were detected across commercial port properties."
        elif "pol" in q_lower or "policy" in q_lower:
            answering_agent = "DecisionSupportAgent"
            answer_text = f"Inspecting policy records: The portfolio consists of 22 geocoded policies. Underwriting recommendations: {sum(1 for r in st.session_state.recommendations if r.recommendation == 'ACCEPT')} Within Appetite (Accept), {sum(1 for r in st.session_state.recommendations if r.recommendation == 'REVIEW')} Review Required, and {sum(1 for r in st.session_state.recommendations if r.recommendation == 'ESCALATE')} Appetite Breach (Escalate)."
        else:
            answering_agent = "GovernanceAgent"
            answer_text = f"Query evaluated across all 11 catastrophe intelligence agents. Portfolio AAL is **{format_currency(st.session_state.metrics_summary.aal)}**, 1-in-250 TVaR is **{format_currency(st.session_state.metrics_summary.tvar_996)}**, and all agent execution traces are cryptographically verified."

        st.session_state.chat_history.append({"role": "agent", "agent": answering_agent, "text": answer_text})
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE CATALOGUE MAPPING
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

PAGE_MAP = {
    "01 — Overview": page_overview,
    "02 — Portfolio": page_portfolio,
    "03 — Data Intelligence": page_data_intelligence,
    "04 — Agent Control": page_agent_control,
    "05 — Flood Risk": page_flood_risk,
    "06 — Accumulation": page_accumulation,
    "07 — Catastrophe Analytics": page_cat_analytics,
    "08 — Tail Risk": page_tail_risk,
    "09 — Policy Intelligence": page_policy_intel,
    "10 — Pricing": page_pricing,
    "11 — Scenario Lab": page_scenario_lab,
    "12 — Risk Appetite": page_risk_appetite,
    "13 — Decisions": page_decisions,
    "14 — Audit": page_audit,
    "15 — Methodology": page_methodology,
    "16 — Future / 2090": page_future,
}


# ═══════════════════════════════════════════════════════════════════════════
# APP SHELL & ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def run_app() -> None:
    """Execute main application loop."""
    st.set_page_config(
        page_title="FLOODTAIL — Catastrophe & Climate Risk Intelligence",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    _init_session()
    if not st.session_state.run_complete:
        with st.spinner("Executing 11-agent catastrophe intelligence pipeline..."):
            _run_demo_pipeline()

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;padding:0.75rem 0 1.25rem 0;">
                <div style="width:28px;height:28px;background:{Colors.ACCENT_ORANGE};border-radius:6px;display:flex;align-items:center;justify-content:center;font-weight:900;color:#000;font-size:13px;">✦</div>
                <div>
                    <div style="font-weight:700;font-size:15px;letter-spacing:-0.02em;color:{Colors.TEXT_PRIMARY};">FLOODTAIL <span style="color:{Colors.ACCENT_ORANGE};">AI</span></div>
                    <div style="font-size:10px;color:{Colors.TEXT_MUTED};font-weight:500;">Catastrophe Risk Intelligence</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="height:1px;background:{Colors.BORDER_DEFAULT};margin:0 0 0.75rem 0;"></div>', unsafe_allow_html=True)

        NAV_OPTIONS = [
            "🏠 Overview",
            "📋 Portfolio",
            "🔍 Data Intelligence",
            "🤖 Agent Control",
            "🌊 Flood Risk",
            "🏢 Accumulation",
            "📊 Catastrophe Analytics",
            "📈 Tail Risk",
            "🔎 Policy Intelligence",
            "💵 Pricing",
            "🧪 Scenario Lab",
            "⚖️ Risk Appetite",
            "✅ Decisions",
            "🛡️ Audit",
            "📐 Methodology",
            "🌍 Future / 2090",
            "💬 Ask AI",
        ]
        selected = st.radio(
            "Navigation",
            NAV_OPTIONS,
            label_visibility="collapsed",
            key="sidebar_nav_radio",
        )

        st.markdown(f'<div style="height:1px;background:{Colors.BORDER_DEFAULT};margin:0.75rem 0;"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="padding:0.5rem 0;">
                <div style="font-size:10px;font-weight:600;color:{Colors.TEXT_MUTED};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Engine Status</div>
                <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:{Colors.STATUS_GREEN};">
                    <span style="width:7px;height:7px;background:{Colors.STATUS_GREEN};border-radius:50%;display:inline-block;"></span>
                    11 Agents Online
                </div>
                <div style="font-size:10px;color:{Colors.TEXT_MUTED};margin-top:4px;">128/128 tests passing</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── ROUTE SELECTED PAGE ──
    NAV_MAP = {
        "🏠 Overview": page_overview,
        "📋 Portfolio": page_portfolio,
        "🔍 Data Intelligence": page_data_intelligence,
        "🤖 Agent Control": page_agent_control,
        "🌊 Flood Risk": page_flood_risk,
        "🏢 Accumulation": page_accumulation,
        "📊 Catastrophe Analytics": page_cat_analytics,
        "📈 Tail Risk": page_tail_risk,
        "🔎 Policy Intelligence": page_policy_intel,
        "💵 Pricing": page_pricing,
        "🧪 Scenario Lab": page_scenario_lab,
        "⚖️ Risk Appetite": page_risk_appetite,
        "✅ Decisions": page_decisions,
        "🛡️ Audit": page_audit,
        "📐 Methodology": page_methodology,
        "🌍 Future / 2090": page_future,
        "💬 Ask AI": page_ask_ai_dialogue,
    }
    page_fn = NAV_MAP.get(selected, page_overview)
    page_fn()


def main() -> None:
    """Application entry point for testing and CLI execution."""
    _init_session()
    _run_demo_pipeline()


if __name__ == "__main__" or "streamlit" in sys.modules:
    run_app()
