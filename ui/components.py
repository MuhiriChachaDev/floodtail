"""FLOODTAIL — Reusable UI Components (Dark Analytical Theme).

Provides pixel-exact header, navigation, KPI cards, AI insight panels,
anomaly callouts, climate score gauges, badges, table renderers, and
interactive multi-agent communication dialogue components.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

from ui.theme import (
    AGENT_STATUS_COLORS,
    CONFIDENCE_MAP,
    RISK_STATUS_MAP,
    Colors,
    format_currency,
    format_pct,
)


# ---------------------------------------------------------------------------
# BADGES & STATUS INDICATORS
# ---------------------------------------------------------------------------

def status_badge(status: str) -> str:
    """Return styled HTML badge for an agent or process execution status."""
    color, bg, icon = AGENT_STATUS_COLORS.get(status, (Colors.TEXT_MUTED, "rgba(100,116,139,0.1)", "●"))
    return (
        f'<span class="ft-badge" style="background:{bg};color:{color};border:1px solid {color}44;">'
        f'{icon} {status}</span>'
    )


def risk_badge(recommendation: str) -> str:
    """Return styled HTML badge for a policy risk appetite classification."""
    cfg = RISK_STATUS_MAP.get(recommendation, {"color": Colors.TEXT_MUTED, "bg": "rgba(100,116,139,0.1)", "icon": "●", "label": recommendation})
    return (
        f'<span class="ft-badge" style="background:{cfg["bg"]};color:{cfg["color"]};border:1px solid {cfg["color"]}44;">'
        f'{cfg["icon"]} {cfg["label"]}</span>'
    )


def confidence_badge(level: str) -> str:
    """Return styled HTML badge for a decision confidence tier."""
    cfg = CONFIDENCE_MAP.get(level, {"color": Colors.TEXT_MUTED, "bg": "rgba(100,116,139,0.1)"})
    return (
        f'<span class="ft-badge" style="background:{cfg["bg"]};color:{cfg["color"]};border:1px solid {cfg["color"]}44;">'
        f'{level}</span>'
    )


def provenance_badge(source_type: str) -> str:
    """Return styled HTML badge for data provenance (Observed / Modeled / Assumed / Audited)."""
    st_upper = source_type.upper()
    if "OBSERVE" in st_upper:
        return '<span class="ft-badge" style="background:rgba(59,130,246,0.15);color:#60A5FA;border:1px solid #3B82F644;font-size:10px;padding:2px 6px;">👁️ Observed</span>'
    elif "MODEL" in st_upper:
        return '<span class="ft-badge" style="background:rgba(249,115,22,0.15);color:#FB923C;border:1px solid #F9731644;font-size:10px;padding:2px 6px;">⚙️ Modeled</span>'
    elif "ASSUM" in st_upper:
        return '<span class="ft-badge" style="background:rgba(168,85,247,0.15);color:#C084FC;border:1px solid #A855F744;font-size:10px;padding:2px 6px;">📐 Assumed</span>'
    elif "AUDIT" in st_upper or "CHAIN" in st_upper:
        return '<span class="ft-badge" style="background:rgba(16,185,129,0.15);color:#34D399;border:1px solid #10B98144;font-size:10px;padding:2px 6px;">🔒 Audited</span>'
    return f'<span class="ft-badge" style="background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid #64748B44;font-size:10px;padding:2px 6px;">● {source_type}</span>'



# ---------------------------------------------------------------------------
# GENERAL CONTAINERS & HEADERS
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "", badge: Optional[str] = None) -> None:
    """Render a standard dark analytical page header."""
    badge_html = f" &nbsp; {badge}" if badge else ""
    st.markdown(
        f"""
        <div style="margin-bottom:1.25rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <h1 style="font-size:1.4rem;font-weight:700;color:{Colors.TEXT_PRIMARY};margin:0;letter-spacing:-0.02em;">{title}</h1>
                {badge_html}
            </div>
            {f'<p style="color:{Colors.TEXT_MUTED};font-size:0.82rem;margin:0.25rem 0 0 0;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = "") -> None:
    """Render a section divider with title and optional subtitle."""
    st.markdown(
        f"""
        <div style="margin:1rem 0 0.5rem 0;">
            <div style="font-size:0.88rem;font-weight:600;color:{Colors.TEXT_PRIMARY};letter-spacing:-0.01em;">{title}</div>
            {f'<div style="font-size:0.75rem;color:{Colors.TEXT_MUTED};margin-top:2px;">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str = "📊", message: str = "No data available for this view.") -> None:
    """Render a clean empty state card."""
    st.markdown(
        f"""
        <div class="ft-card" style="text-align:center;padding:2.5rem 1rem;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">{icon}</div>
            <div style="font-size:0.88rem;color:{Colors.TEXT_MUTED};">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_banner(icon: str, title: str, text: str, border_color: str = Colors.ACCENT_ORANGE, bg_color: str = Colors.SURFACE_PRIMARY) -> None:
    """Render a styled information banner."""
    st.markdown(
        f"""
        <div class="ft-card" style="border-left:3px solid {border_color};background:{bg_color};margin-bottom:0.75rem;padding:0.75rem 1rem;">
            <div style="font-size:0.8rem;font-weight:600;color:{Colors.TEXT_PRIMARY};margin-bottom:0.2rem;">{icon} {title}</div>
            <div style="font-size:0.76rem;color:{Colors.TEXT_SECONDARY};line-height:1.4;">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title: str, value: str, subtitle: str = "", border_color: str = "", delta: str = "") -> None:
    """Render a compact KPI metric card."""
    b_style = f"border-left:3px solid {border_color};" if border_color else ""
    d_html = f'<div style="font-size:0.72rem;color:{Colors.STATUS_GREEN};margin-top:0.2rem;">{delta}</div>' if delta else ""
    s_html = f'<div style="font-size:0.72rem;color:{Colors.TEXT_MUTED};margin-top:0.2rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="ft-card" style="{b_style}">
            <div style="font-size:0.72rem;color:{Colors.TEXT_MUTED};font-weight:500;text-transform:uppercase;letter-spacing:0.04em;">{title}</div>
            <div style="font-size:1.35rem;font-weight:700;color:{Colors.TEXT_PRIMARY};margin:0.2rem 0;letter-spacing:-0.02em;">{value}</div>
            {d_html}{s_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# TOP HEADER COMPONENT (Image 1)
# ---------------------------------------------------------------------------

def top_header(
    active_view: str,
    view_options: list[str],
    user_name: str = "Admin User",
    user_plan: str = "Enterprise Plan",
) -> dict[str, Any]:
    """Render the top header matching Image 1 with view selector, search, and action icons."""
    col_brand, col_selector, col_search, col_actions = st.columns([1.8, 2.2, 3.2, 2.2])

    with col_brand:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:8px;padding-top:4px;">
                <div style="width:20px;height:20px;background:{Colors.ACCENT_ORANGE};border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:900;color:#000;font-size:11px;">✦</div>
                <div style="font-weight:700;font-size:15px;letter-spacing:-0.02em;color:{Colors.TEXT_PRIMARY};">NEXORA <span style="color:{Colors.ACCENT_ORANGE};">AI</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_selector:
        selected_view = st.selectbox(
            "Select View",
            options=view_options,
            index=view_options.index(active_view) if active_view in view_options else 0,
            label_visibility="collapsed",
            key="header_view_selector",
        )

    with col_search:
        search_query = st.text_input(
            "Search",
            placeholder="🔍  Ask AI or search metrics...                     ⌘ K",
            label_visibility="collapsed",
            key="header_search_input",
        )

    with col_actions:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;justify-content:flex-end;gap:12px;padding-top:2px;">
                <div title="AI Assistant" style="color:{Colors.ACCENT_ORANGE};cursor:pointer;font-size:15px;">✧</div>
                <div title="Notifications" style="color:{Colors.TEXT_MUTED};cursor:pointer;font-size:15px;position:relative;">
                    🔔<span style="position:absolute;top:-4px;right:-4px;width:6px;height:6px;background:{Colors.ACCENT_RED};border-radius:50%;"></span>
                </div>
                <div title="Knowledge Base" style="color:{Colors.TEXT_MUTED};cursor:pointer;font-size:15px;">❔</div>
                <div style="width:1px;height:18px;background:{Colors.BORDER_DEFAULT};"></div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="width:28px;height:28px;border-radius:50%;background:{Colors.SURFACE_ELEVATED};border:1px solid {Colors.BORDER_STRONG};display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:{Colors.TEXT_PRIMARY};">AM</div>
                    <div style="line-height:1.1;">
                        <div style="font-size:12px;font-weight:600;color:{Colors.TEXT_PRIMARY};">{user_name}</div>
                        <div style="font-size:10px;color:{Colors.TEXT_MUTED};">{user_plan} ▾</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f'<div style="height:1px;background:{Colors.BORDER_DEFAULT};margin:8px 0 14px 0;"></div>', unsafe_allow_html=True)
    return {"selected_view": selected_view, "search_query": search_query}


# ---------------------------------------------------------------------------
# DATE & FILTER CONTROLS ROW (Image 1)
# ---------------------------------------------------------------------------

def date_and_filter_row(
    date_options: list[str] = None,
    current_date: str = "May 1 – May 31, 2025",
) -> tuple[str, bool]:
    """Render top right date picker and filters button row."""
    if date_options is None:
        date_options = ["May 1 – May 31, 2025", "Q1 2025", "Trailing 12 Months", "Full Simulation 10,000Y"]

    col_space, col_date, col_filters = st.columns([6.5, 2.2, 1.3])

    with col_date:
        selected_date = st.selectbox(
            "Date Range",
            options=date_options,
            index=0,
            label_visibility="collapsed",
            key="top_date_selector",
        )

    with col_filters:
        filters_clicked = st.button("☰ Filters ▾", key="top_filter_button", width='stretch')

    return selected_date, filters_clicked


# ---------------------------------------------------------------------------
# KPI CARD COMPONENT (Image 1)
# ---------------------------------------------------------------------------

def kpi_card(
    title: str,
    value_str: str,
    delta_str: str = "",
    delta_positive: bool = True,
    accent_color: str = Colors.ACCENT_ORANGE,
    icon_symbol: str = "💵",
    sparkline_fig: Optional[Any] = None,
    provenance: Optional[str] = None,
    corridor_str: Optional[str] = None,
    sublabel: Optional[str] = None,
) -> None:
    """Render single KPI card matching dark analytical theme with provenance and confidence corridor."""
    delta_color = Colors.STATUS_GREEN if delta_positive else Colors.STATUS_RED
    delta_arrow = "↗" if delta_positive else "↘"
    prov_html = f"&nbsp;{provenance_badge(provenance)}" if provenance else ""
    corridor_html = f'<div style="font-size:10px;color:{Colors.TEXT_MUTED};margin-top:2px;font-family:monospace;">{corridor_str}</div>' if corridor_str else ""
    sub_text = sublabel if sublabel is not None else "vs Prior Calibration"
    trend_html = f"""
        <div class="ft-kpi-trend" style="color:{delta_color};">
            <span>{delta_arrow} {delta_str}</span>
            <span style="color:{Colors.TEXT_MUTED};font-size:10px;margin-left:2px;">{sub_text}</span>
        </div>
    """ if delta_str else f'<div style="font-size:10px;color:{Colors.TEXT_MUTED};margin-top:4px;">{sub_text}</div>'

    st.markdown(
        f"""
        <div class="ft-kpi-card">
            <div class="ft-kpi-header" style="display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;align-items:center;gap:6px;">
                    <div class="ft-kpi-icon" style="background:{accent_color}22;color:{accent_color};border:1px solid {accent_color}44;">
                        {icon_symbol}
                    </div>
                    <span>{title}</span>
                </div>
                {prov_html}
            </div>
            <div class="ft-kpi-value-row">
                <div class="ft-kpi-value">{value_str}</div>
            </div>
            {corridor_html}
            {trend_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if sparkline_fig is not None:
        st.plotly_chart(sparkline_fig, width='stretch', config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# ANOMALY CALLOUT BOX (Image 1)
# ---------------------------------------------------------------------------

def anomaly_callout_box(
    date_str: str = "May 29, 2025",
    description: str = "Revenue was 46% higher than expected, driving $142K additional revenue.",
    confidence_pct: int = 92,
) -> bool:
    """Render the floating Anomaly Detected callout box inside the main chart area."""
    st.markdown(
        f"""
        <div class="ft-anomaly-callout">
            <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:{Colors.ACCENT_ORANGE};">
                <span style="width:7px;height:7px;border-radius:50%;background:{Colors.ACCENT_ORANGE};display:inline-block;"></span>
                Anomaly Detected
            </div>
            <div style="font-size:11px;color:{Colors.TEXT_MUTED};margin:4px 0 6px 0;">{date_str}</div>
            <div style="font-size:12px;color:{Colors.TEXT_PRIMARY};line-height:1.35;margin-bottom:12px;">{description}</div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:{Colors.TEXT_MUTED};margin-bottom:4px;">
                <span>AI Confidence</span>
                <span style="color:{Colors.TEXT_PRIMARY};font-weight:600;">{confidence_pct}%</span>
            </div>
            <div class="ft-progress-bar-bg" style="margin-bottom:12px;">
                <div class="ft-progress-bar-fill" style="width:{confidence_pct}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.button("View Anomaly", key=f"btn_view_anomaly_{date_str}", width='stretch')


# ---------------------------------------------------------------------------
# AI INSIGHT CARD (Image 1)
# ---------------------------------------------------------------------------

def ai_insight_card(
    headline: str,
    explanation: str,
    factors: list[dict[str, Any]],
    button_label: str = "View Full Analysis",
    impact_level: str = "High Impact",
) -> bool:
    """Render the AI Insight panel on the right side of the main analytics row."""
    st.markdown(
        f"""
        <div class="ft-ai-insight-card">
            <div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <div style="font-size:13px;font-weight:600;color:{Colors.TEXT_PRIMARY};display:flex;align-items:center;gap:6px;">
                        <span style="color:{Colors.ACCENT_ORANGE};">✧</span> AI Insight
                    </div>
                    <span class="ft-badge" style="background:{Colors.ACCENT_ORANGE}22;color:{Colors.ACCENT_ORANGE};border:1px solid {Colors.ACCENT_ORANGE}44;">
                        {impact_level}
                    </span>
                </div>
                <div style="font-size:14px;font-weight:700;color:{Colors.TEXT_PRIMARY};line-height:1.3;margin-bottom:8px;">
                    {headline}
                </div>
                <div style="font-size:12px;color:{Colors.TEXT_SECONDARY};line-height:1.4;margin-bottom:14px;">
                    {explanation}
                </div>
                <div style="font-size:11px;font-weight:600;color:{Colors.TEXT_MUTED};text-transform:uppercase;letter-spacing:0.04em;margin-bottom:10px;">
                    Top Contributing Factors
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    for f in factors:
        icon = f.get("icon", "🔹")
        name = f.get("name", "")
        pct = f.get("pct", 50)
        pct_str = f.get("pct_str", f"+{pct}%")
        st.markdown(
            f"""
            <div style="margin-bottom:10px;">
                <div class="ft-factor-row">
                    <div style="display:flex;align-items:center;gap:6px;color:{Colors.TEXT_SECONDARY};">
                        <span>{icon}</span>
                        <span>{name}</span>
                    </div>
                    <span style="font-weight:600;color:{Colors.ACCENT_ORANGE};">{pct_str}</span>
                </div>
                <div class="ft-progress-bar-bg">
                    <div class="ft-progress-bar-fill" style="width:{min(100, pct)}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return st.button(button_label, key=f"btn_ai_insight_{headline[:15]}", width='stretch')


# ---------------------------------------------------------------------------
# RECENT ANOMALIES TABLE COMPONENT (Image 1)
# ---------------------------------------------------------------------------

def recent_anomalies_table(anomalies: list[dict[str, Any]]) -> bool:
    """Render the Recent Anomalies table in the lower right analytical panel."""
    col_t, col_b = st.columns([3, 1])
    with col_t:
        st.markdown(
            f'<div style="font-size:13px;font-weight:600;color:{Colors.TEXT_PRIMARY};display:flex;align-items:center;gap:6px;">Recent Anomalies <span style="font-size:11px;color:{Colors.TEXT_MUTED};">ⓘ</span></div>',
            unsafe_allow_html=True,
        )
    with col_b:
        view_all_clicked = st.button("View All", key="btn_view_all_anomalies", width='stretch')

    st.markdown(
        f"""
        <table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
            <thead>
                <tr style="border-bottom:1px solid {Colors.BORDER_DEFAULT};color:{Colors.TEXT_MUTED};text-align:left;">
                    <th style="padding:6px 4px;font-weight:500;">Metric</th>
                    <th style="padding:6px 4px;font-weight:500;">Date</th>
                    <th style="padding:6px 4px;font-weight:500;">Impact</th>
                    <th style="padding:6px 4px;font-weight:500;text-align:right;">AI Confidence</th>
                </tr>
            </thead>
            <tbody>
        """,
        unsafe_allow_html=True,
    )

    for a in anomalies:
        metric = a.get("metric", "Payment Spike")
        date_str = a.get("date", "May 29")
        impact = a.get("impact", "High ↑")
        conf = a.get("confidence", 92)

        impact_color = Colors.STATUS_RED if "High" in impact else (Colors.STATUS_AMBER if "Medium" in impact else Colors.STATUS_GREEN)
        conf_bg = Colors.STATUS_GREEN_BG if conf >= 80 else (Colors.STATUS_AMBER_BG if conf >= 70 else Colors.STATUS_RED_BG)
        conf_color = Colors.STATUS_GREEN if conf >= 80 else (Colors.STATUS_AMBER if conf >= 70 else Colors.STATUS_RED)

        st.markdown(
            f"""
            <tr style="border-bottom:1px solid {Colors.BORDER_SUBTLE};">
                <td style="padding:8px 4px;color:{Colors.TEXT_PRIMARY};font-weight:500;">{metric}</td>
                <td style="padding:8px 4px;color:{Colors.TEXT_MUTED};">{date_str}</td>
                <td style="padding:8px 4px;color:{impact_color};font-weight:600;">{impact}</td>
                <td style="padding:8px 4px;text-align:right;">
                    <span class="ft-pill-confidence" style="background:{conf_bg};color:{conf_color};">
                        {conf}%
                    </span>
                </td>
            </tr>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</tbody></table>", unsafe_allow_html=True)
    return view_all_clicked


# ---------------------------------------------------------------------------
# JUPITER CLIMATESCORE FOCUSED CATEGORY COMPONENTS (Image 2)
# ---------------------------------------------------------------------------

def category_header(
    title: str = "International Loan Portfolio",
    portfolio_meta: str = "Ports, GL-Global (v3.1.0)",
) -> None:
    """Render Image 2 Category / Portfolio header."""
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
            <div style="font-size:11px;color:{Colors.TEXT_MUTED};margin-bottom:2px;">‹ Home</div>
            <div style="display:flex;align-items:baseline;gap:12px;">
                <div style="font-size:20px;font-weight:700;color:{Colors.TEXT_PRIMARY};">{title}</div>
                <div style="font-size:12px;color:{Colors.TEXT_MUTED};">{portfolio_meta}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def category_horizontal_tabs(
    tabs: list[str] = None,
    active_tab: str = "OVERVIEW",
) -> str:
    """Render Image 2 horizontal category tabs (OVERVIEW | HAZARD | LOCATIONS | IMPACTS | SCORING | COMPLIANCE)."""
    if tabs is None:
        tabs = ["OVERVIEW", "HAZARD", "LOCATIONS", "IMPACTS", "SCORING", "COMPLIANCE"]

    cols = st.columns(len(tabs))
    selected = active_tab
    for idx, tab_name in enumerate(tabs):
        with cols[idx]:
            is_active = (tab_name == active_tab)
            btn_style = "primary" if is_active else "secondary"
            if st.button(tab_name, key=f"cat_tab_{tab_name}", type=btn_style, width='stretch'):
                selected = tab_name
    return selected


def hazard_filter_pills(
    hazards: list[str] = None,
    active_hazard: str = "ALL PERILS",
) -> str:
    """Render the compact hazard filter selector strip over the map."""
    if hazards is None:
        hazards = ["ALL PERILS", "FLOOD", "WIND", "WILDFIRE", "HEAT", "PRECIP", "COLD", "DROUGHT", "HAIL"]

    cols = st.columns(len(hazards))
    selected = active_hazard
    for idx, h in enumerate(hazards):
        with cols[idx]:
            is_active = (h == active_hazard)
            btn_style = "primary" if is_active else "secondary"
            if st.button(h, key=f"hazard_pill_{h}", type=btn_style, width='stretch'):
                selected = h
    return selected


# ---------------------------------------------------------------------------
# MULTI-AGENT INTER-COMMUNICATION DIALOGUE STREAM (Browser Visualizer)
# ---------------------------------------------------------------------------

AGENT_AVATAR_CONFIG = {
    "ExposureIntelligenceAgent": {"avatar": "🔍", "color": Colors.ACCENT_CYAN, "title": "Exposure Intelligence Agent"},
    "HazardAnalysisAgent": {"avatar": "🌊", "color": Colors.ACCENT_BLUE, "title": "Spatial Hazard Agent"},
    "VulnerabilityReviewAgent": {"avatar": "🏗️", "color": Colors.ACCENT_YELLOW, "title": "Vulnerability Review Agent"},
    "LossAnalysisAgent": {"avatar": "📊", "color": Colors.ACCENT_ORANGE, "title": "Loss Reconciliation Agent"},
    "TailRiskAgent": {"avatar": "📈", "color": Colors.ACCENT_RED, "title": "Tail Risk Allocation Agent"},
    "AccumulationAgent": {"avatar": "🏢", "color": Colors.AI_PURPLE, "title": "Accumulation & Co-Hit Agent"},
    "PricingIntelligenceAgent": {"avatar": "💵", "color": Colors.ACCENT_GREEN, "title": "Technical Pricing Agent"},
    "ScenarioAgent": {"avatar": "🧪", "color": Colors.ACCENT_CYAN, "title": "CRN Counterfactual Scenario Agent"},
    "RiskAppetiteAgent": {"avatar": "⚖️", "color": Colors.ACCENT_ORANGE, "title": "Risk Appetite Rule Engine"},
    "DecisionSupportAgent": {"avatar": "📋", "color": Colors.ACCENT_BLUE, "title": "Decision Support Agent"},
    "GovernanceAgent": {"avatar": "🛡️", "color": Colors.ACCENT_GREEN, "title": "Audit Governance Agent"},
    "User": {"avatar": "👤", "color": Colors.TEXT_PRIMARY, "title": "Underwriter / Human Lead"},
}


def render_agent_dialogue_stream(
    dialogue_records: list[dict[str, Any]],
) -> None:
    """Render the real-time inter-agent conversation thread in the browser."""
    for item in dialogue_records:
        agent = item.get("agent", "ExposureIntelligenceAgent")
        recipient = item.get("recipient", "Next Agent")
        message = item.get("message", "")
        payload = item.get("payload", None)
        timestamp = item.get("timestamp", "08:42:15 UTC")
        status = item.get("status", "SUCCESS")

        cfg = AGENT_AVATAR_CONFIG.get(agent, {"avatar": "🤖", "color": Colors.ACCENT_ORANGE, "title": agent})
        avatar = cfg["avatar"]
        color = cfg["color"]
        title = cfg["title"]

        payload_html = f'<div class="ft-agent-payload">📦 <b>Payload:</b> {payload}</div>' if payload else ""

        st.markdown(
            f"""
            <div class="ft-dialogue-item">
                <div class="ft-agent-avatar" style="background:{color}22;border:1px solid {color}55;color:{color};">
                    {avatar}
                </div>
                <div class="ft-agent-bubble" style="border-left:3px solid {color};">
                    <div class="ft-agent-bubble-header">
                        <div class="ft-agent-bubble-title">
                            <span style="color:{color};">{title}</span>
                            <span style="font-size:10px;color:{Colors.TEXT_MUTED};font-weight:400;">➔ {recipient}</span>
                        </div>
                        <div style="display:flex;align-items:center;gap:6px;">
                            <span style="font-size:10px;color:{Colors.TEXT_MUTED};">{timestamp}</span>
                            {status_badge(status)}
                        </div>
                    </div>
                    <div class="ft-agent-bubble-body">{message}</div>
                    {payload_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# BOTTOM FOOTER (Image 1)
# ---------------------------------------------------------------------------

def bottom_footer() -> bool:
    """Render footer matching Image 1 with UTC timestamp and Refresh button."""
    st.markdown(f'<div style="height:1px;background:{Colors.BORDER_DEFAULT};margin:24px 0 10px 0;"></div>', unsafe_allow_html=True)
    col_l, col_r = st.columns([6, 4])
    with col_l:
        st.markdown(
            f'<div style="font-size:11px;color:{Colors.TEXT_MUTED};">All times shown in UTC</div>',
            unsafe_allow_html=True,
        )
    with col_r:
        col_text, col_btn = st.columns([3, 1])
        with col_text:
            st.markdown(
                f'<div style="font-size:11px;color:{Colors.TEXT_MUTED};text-align:right;padding-top:4px;">Data Refreshed: 5m ago</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            refresh_clicked = st.button("↻", key="btn_footer_refresh", help="Refresh Analysis")
            return refresh_clicked
    return False
