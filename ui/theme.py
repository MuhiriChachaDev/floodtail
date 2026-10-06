"""FLOODTAIL — Design System & Theme Engine.

Defines semantic colour tokens, typography scale, spacing, and injectable CSS
for the Streamlit application shell. All visual constants live here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# COLOUR PALETTE — Semantic Design Tokens
# ---------------------------------------------------------------------------

class Colors:
    """Semantic colour palette for the FLOODTAIL platform."""

    # Primary structure — Deep Navy
    NAVY_900 = "#0A1628"
    NAVY_800 = "#0F1F3A"
    NAVY_700 = "#162D50"
    NAVY_600 = "#1C3A65"
    NAVY_500 = "#1E4D8C"
    NAVY_400 = "#2563A8"
    NAVY_100 = "#D4E4F7"

    # Brand accent — Kenya Re–inspired Red
    ACCENT_RED = "#C8102E"
    ACCENT_RED_LIGHT = "#E63E57"
    ACCENT_RED_MUTED = "#F5D0D6"

    # Flood / Hazard — Teal / Cyan
    FLOOD_TEAL = "#0891B2"
    FLOOD_CYAN = "#22D3EE"
    FLOOD_DARK = "#0E7490"
    FLOOD_LIGHT = "#CFFAFE"

    # AI / Machine Intelligence — Purple / Violet
    AI_PURPLE = "#7C3AED"
    AI_VIOLET = "#A78BFA"
    AI_LIGHT = "#EDE9FE"

    # Risk status
    STATUS_GREEN = "#16A34A"
    STATUS_GREEN_BG = "#DCFCE7"
    STATUS_AMBER = "#D97706"
    STATUS_AMBER_BG = "#FEF3C7"
    STATUS_RED = "#DC2626"
    STATUS_RED_BG = "#FEE2E2"

    # Information
    INFO_BLUE = "#2563EB"
    INFO_BLUE_BG = "#DBEAFE"

    # Neutrals
    WHITE = "#FFFFFF"
    GRAY_50 = "#F8FAFC"
    GRAY_100 = "#F1F5F9"
    GRAY_200 = "#E2E8F0"
    GRAY_300 = "#CBD5E1"
    GRAY_400 = "#94A3B8"
    GRAY_500 = "#64748B"
    GRAY_600 = "#475569"
    GRAY_700 = "#334155"
    GRAY_800 = "#1E293B"
    GRAY_900 = "#0F172A"

    # Chart palette (controlled tonal variations)
    CHART_1 = "#1E4D8C"   # Navy
    CHART_2 = "#0891B2"   # Teal
    CHART_3 = "#7C3AED"   # Purple
    CHART_4 = "#D97706"   # Amber
    CHART_5 = "#16A34A"   # Green
    CHART_6 = "#C8102E"   # Red accent
    CHART_PALETTE = [CHART_1, CHART_2, CHART_3, CHART_4, CHART_5, CHART_6]


# ---------------------------------------------------------------------------
# AGENT STATUS STYLING
# ---------------------------------------------------------------------------

AGENT_STATUS_COLORS = {
    "SUCCESS": (Colors.STATUS_GREEN, Colors.STATUS_GREEN_BG, "✓"),
    "WARNING": (Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG, "⚠"),
    "FAILED": (Colors.STATUS_RED, Colors.STATUS_RED_BG, "✕"),
    "RUNNING": (Colors.INFO_BLUE, Colors.INFO_BLUE_BG, "⟳"),
    "PENDING": (Colors.GRAY_400, Colors.GRAY_100, "●"),
    "REVIEW_REQUIRED": (Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG, "⚠"),
}


# ---------------------------------------------------------------------------
# RISK APPETITE STYLING
# ---------------------------------------------------------------------------

RISK_STATUS_MAP = {
    "ACCEPT": {"color": Colors.STATUS_GREEN, "bg": Colors.STATUS_GREEN_BG, "icon": "✓", "label": "WITHIN APPETITE"},
    "REVIEW": {"color": Colors.STATUS_AMBER, "bg": Colors.STATUS_AMBER_BG, "icon": "⚠", "label": "REVIEW REQUIRED"},
    "ESCALATE": {"color": Colors.STATUS_RED, "bg": Colors.STATUS_RED_BG, "icon": "✕", "label": "BREACH"},
}


# ---------------------------------------------------------------------------
# CONFIDENCE STYLING
# ---------------------------------------------------------------------------

CONFIDENCE_MAP = {
    "HIGH": {"color": Colors.STATUS_GREEN, "bg": Colors.STATUS_GREEN_BG},
    "MEDIUM": {"color": Colors.STATUS_AMBER, "bg": Colors.STATUS_AMBER_BG},
    "LOW": {"color": Colors.STATUS_RED, "bg": Colors.STATUS_RED_BG},
}


# ---------------------------------------------------------------------------
# MASTER INJECTABLE CSS
# ---------------------------------------------------------------------------

def get_custom_css() -> str:
    """Return the complete FLOODTAIL design system as injectable CSS."""
    return f"""
    <style>
    /* ---- Google Font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ---- Root tokens ---- */
    :root {{
        --ft-navy: {Colors.NAVY_800};
        --ft-accent: {Colors.ACCENT_RED};
        --ft-teal: {Colors.FLOOD_TEAL};
        --ft-purple: {Colors.AI_PURPLE};
        --ft-bg: {Colors.GRAY_50};
        --ft-surface: {Colors.WHITE};
        --ft-border: {Colors.GRAY_200};
        --ft-text: {Colors.GRAY_800};
        --ft-text-secondary: {Colors.GRAY_500};
        --ft-radius: 8px;
    }}

    /* ---- Global ---- */
    html, body, [class*="st-"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    .stApp {{
        background: var(--ft-bg) !important;
    }}

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {{
        background: {Colors.NAVY_800} !important;
        min-width: 280px !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: {Colors.GRAY_200} !important;
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        color: {Colors.GRAY_300} !important;
        font-weight: 500 !important;
        padding: 6px 12px !important;
        border-radius: var(--ft-radius) !important;
        transition: background 0.15s !important;
    }}
    section[data-testid="stSidebar"] .stRadio label:hover {{
        background: {Colors.NAVY_600} !important;
    }}
    section[data-testid="stSidebar"] .stRadio label[data-checked="true"] {{
        background: {Colors.NAVY_500} !important;
        color: {Colors.WHITE} !important;
    }}

    /* ---- Page header ---- */
    .ft-page-header {{
        padding: 0 0 20px 0;
        border-bottom: 2px solid {Colors.NAVY_500};
        margin-bottom: 24px;
    }}
    .ft-page-title {{
        font-size: 28px;
        font-weight: 700;
        color: {Colors.NAVY_800};
        letter-spacing: -0.02em;
        margin: 0;
    }}
    .ft-page-subtitle {{
        font-size: 14px;
        color: {Colors.GRAY_500};
        margin-top: 4px;
    }}

    /* ---- Metric card ---- */
    .ft-metric-card {{
        background: {Colors.WHITE};
        border: 1px solid {Colors.GRAY_200};
        border-radius: var(--ft-radius);
        padding: 20px;
        min-height: 110px;
    }}
    .ft-metric-label {{
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {Colors.GRAY_500};
        margin-bottom: 6px;
    }}
    .ft-metric-value {{
        font-size: 28px;
        font-weight: 700;
        color: {Colors.NAVY_800};
        line-height: 1.1;
    }}
    .ft-metric-context {{
        font-size: 12px;
        color: {Colors.GRAY_400};
        margin-top: 6px;
    }}

    /* ---- Status badge ---- */
    .ft-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.04em;
    }}

    /* ---- Section header ---- */
    .ft-section-title {{
        font-size: 16px;
        font-weight: 600;
        color: {Colors.NAVY_700};
        margin: 28px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid {Colors.GRAY_200};
    }}

    /* ---- Agent step ---- */
    .ft-agent-step {{
        background: {Colors.WHITE};
        border: 1px solid {Colors.GRAY_200};
        border-radius: var(--ft-radius);
        padding: 16px 20px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    .ft-agent-icon {{
        font-size: 20px;
        width: 32px;
        text-align: center;
    }}
    .ft-agent-name {{
        font-weight: 600;
        color: {Colors.NAVY_800};
        font-size: 14px;
    }}
    .ft-agent-msg {{
        font-size: 12px;
        color: {Colors.GRAY_500};
        margin-top: 2px;
    }}
    .ft-agent-duration {{
        font-size: 11px;
        color: {Colors.GRAY_400};
        margin-left: auto;
    }}

    /* ---- Connector line ---- */
    .ft-connector {{
        text-align: center;
        color: {Colors.GRAY_300};
        font-size: 18px;
        margin: -4px 0;
        padding-left: 15px;
    }}

    /* ---- Card surface ---- */
    .ft-card {{
        background: {Colors.WHITE};
        border: 1px solid {Colors.GRAY_200};
        border-radius: var(--ft-radius);
        padding: 20px;
        margin-bottom: 16px;
    }}

    /* ---- Waterfall block ---- */
    .ft-trace-step {{
        background: {Colors.WHITE};
        border-left: 3px solid {Colors.NAVY_500};
        padding: 12px 16px;
        margin-bottom: 6px;
        border-radius: 0 var(--ft-radius) var(--ft-radius) 0;
    }}
    .ft-trace-step.ft-trace-ai {{
        border-left-color: {Colors.AI_PURPLE};
    }}
    .ft-trace-step.ft-trace-flood {{
        border-left-color: {Colors.FLOOD_TEAL};
    }}
    .ft-trace-step.ft-trace-risk {{
        border-left-color: {Colors.ACCENT_RED};
    }}

    /* ---- Table styling ---- */
    .stDataFrame {{
        border: 1px solid {Colors.GRAY_200} !important;
        border-radius: var(--ft-radius) !important;
    }}

    /* ---- Comparison highlight ---- */
    .ft-compare-higher {{
        color: {Colors.STATUS_RED};
        font-weight: 600;
    }}
    .ft-compare-lower {{
        color: {Colors.STATUS_GREEN};
        font-weight: 600;
    }}

    /* ---- Hide Streamlit branding ---- */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
    """


def format_currency(value: float, prefix: str = "KES") -> str:
    """Format a number as a currency string with appropriate magnitude suffix."""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1e9:
        return f"{sign}{prefix} {abs_val / 1e9:,.1f}B"
    elif abs_val >= 1e6:
        return f"{sign}{prefix} {abs_val / 1e6:,.1f}M"
    elif abs_val >= 1e3:
        return f"{sign}{prefix} {abs_val / 1e3:,.0f}K"
    else:
        return f"{sign}{prefix} {abs_val:,.0f}"


def format_pct(value: float, decimals: int = 1) -> str:
    """Format a value as a percentage string."""
    return f"{value:.{decimals}f}%"


def format_bps(value: float) -> str:
    """Format a value as basis points."""
    return f"{value:,.0f} bps"
