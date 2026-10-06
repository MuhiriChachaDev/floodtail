"""FLOODTAIL — Reusable UI Components.

Provides cards, badges, status indicators, metric displays, section headers,
and panel builders used across all pages.
"""

from __future__ import annotations

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
# Page header
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "") -> None:
    """Render a styled page header."""
    sub_html = f'<p class="ft-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="ft-page-header">'
        f'<h1 class="ft-page-title">{title}</h1>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metric card
# ---------------------------------------------------------------------------

def metric_card(label: str, value: str, context: str = "", border_color: str = "") -> None:
    """Render a styled metric card."""
    border_style = f"border-top: 3px solid {border_color};" if border_color else ""
    st.markdown(
        f'<div class="ft-metric-card" style="{border_style}">'
        f'<div class="ft-metric-label">{label}</div>'
        f'<div class="ft-metric-value">{value}</div>'
        f'<div class="ft-metric-context">{context}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Status badge
# ---------------------------------------------------------------------------

def status_badge(status: str) -> str:
    """Return HTML for a coloured status badge."""
    cfg = AGENT_STATUS_COLORS.get(status, (Colors.GRAY_400, Colors.GRAY_100, "●"))
    color, bg, icon = cfg
    return (
        f'<span class="ft-badge" style="background:{bg};color:{color};">'
        f'{icon} {status}</span>'
    )


def risk_badge(recommendation: str) -> str:
    """Return HTML for a risk appetite badge (ACCEPT/REVIEW/ESCALATE)."""
    cfg = RISK_STATUS_MAP.get(recommendation, RISK_STATUS_MAP["REVIEW"])
    return (
        f'<span class="ft-badge" style="background:{cfg["bg"]};color:{cfg["color"]};">'
        f'{cfg["icon"]} {cfg["label"]}</span>'
    )


def confidence_badge(level: str) -> str:
    """Return HTML for a confidence level badge."""
    cfg = CONFIDENCE_MAP.get(level, CONFIDENCE_MAP["LOW"])
    return (
        f'<span class="ft-badge" style="background:{cfg["bg"]};color:{cfg["color"]};">'
        f'{level} CONFIDENCE</span>'
    )


# ---------------------------------------------------------------------------
# Section title
# ---------------------------------------------------------------------------

def section_title(text: str) -> None:
    """Render a styled section divider title."""
    st.markdown(f'<div class="ft-section-title">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Card surface
# ---------------------------------------------------------------------------

def card(content_html: str) -> None:
    """Render arbitrary HTML in a card surface."""
    st.markdown(f'<div class="ft-card">{content_html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Agent step in workflow
# ---------------------------------------------------------------------------

def agent_step(name: str, status: str, message: str = "", duration_ms: float = 0) -> None:
    """Render one agent step in the vertical workflow."""
    cfg = AGENT_STATUS_COLORS.get(status, (Colors.GRAY_400, Colors.GRAY_100, "●"))
    color, bg, icon = cfg
    dur_text = f"{duration_ms:.0f}ms" if duration_ms > 0 else ""
    st.markdown(
        f'<div class="ft-agent-step" style="border-left: 3px solid {color};">'
        f'<div class="ft-agent-icon" style="color:{color};">{icon}</div>'
        f'<div>'
        f'<div class="ft-agent-name">{name}</div>'
        f'<div class="ft-agent-msg">{message}</div>'
        f'</div>'
        f'<div class="ft-agent-duration">{dur_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def agent_connector() -> None:
    """Render a vertical connector line between agent steps."""
    st.markdown('<div class="ft-connector">↓</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Trace step (mathematical derivation)
# ---------------------------------------------------------------------------

def trace_step(
    step_num: int,
    name: str,
    formula: str,
    output_name: str,
    output_value: str,
    explanation: str,
    css_class: str = "",
) -> None:
    """Render one step of the 7-step mathematical trace."""
    cls = f"ft-trace-step {css_class}" if css_class else "ft-trace-step"
    st.markdown(
        f'<div class="{cls}">'
        f'<div class="ft-metric-label">STEP {step_num} — {name}</div>'
        f'<div style="font-size:13px;color:{Colors.GRAY_600};margin:4px 0;">{formula}</div>'
        f'<div style="font-size:18px;font-weight:700;color:{Colors.NAVY_800};">{output_name} = {output_value}</div>'
        f'<div style="font-size:12px;color:{Colors.GRAY_500};margin-top:4px;">{explanation}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Info / Warning / Error banners
# ---------------------------------------------------------------------------

def info_banner(icon: str, title: str, message: str, color: str = Colors.INFO_BLUE, bg: str = Colors.INFO_BLUE_BG) -> None:
    """Render a styled information banner."""
    st.markdown(
        f'<div style="background:{bg};border:1px solid {color};border-radius:8px;padding:16px;margin:12px 0;">'
        f'<div style="font-weight:600;color:{color};font-size:14px;">{icon} {title}</div>'
        f'<div style="color:{Colors.GRAY_700};font-size:13px;margin-top:4px;">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def empty_state(icon: str, message: str) -> None:
    """Render an empty-state placeholder."""
    st.markdown(
        f'<div style="text-align:center;padding:60px 20px;color:{Colors.GRAY_400};">'
        f'<div style="font-size:48px;margin-bottom:12px;">{icon}</div>'
        f'<div style="font-size:14px;">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Comparison table helper
# ---------------------------------------------------------------------------

def compare_metric(label: str, val_a: float, val_b: float, fmt_fn=format_currency) -> tuple[str, str, str]:
    """Return (label, formatted_a, formatted_b) with highlighting."""
    return label, fmt_fn(val_a), fmt_fn(val_b)
