"""FLOODTAIL — Enterprise Dark Design System & Theme Engine.

Defines semantic colour tokens, typography scale, spacing, and injectable CSS
for the Streamlit dark analytical shell matching NEXORA AI and Jupiter ClimateScore.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# COLOUR PALETTE — Semantic Design Tokens
# ---------------------------------------------------------------------------

class Colors:
    """Semantic colour palette for the FLOODTAIL dark analytical platform."""

    # Application backgrounds — deep navy-black layers
    BG_APP = "#0B0F19"
    BG_DEEPER = "#070A10"
    BG_SIDEBAR = "#0D121F"

    # Panel / card surfaces
    SURFACE_PRIMARY = "#111827"
    SURFACE_SECONDARY = "#161F33"
    SURFACE_ELEVATED = "#1C263E"
    SURFACE_ACTIVE = "#222E4A"

    # Borders
    BORDER_DEFAULT = "#1E293B"
    BORDER_STRONG = "#334155"
    BORDER_SUBTLE = "#162032"

    # Text hierarchy
    TEXT_PRIMARY = "#F8FAFC"
    TEXT_SECONDARY = "#CBD5E1"
    TEXT_MUTED = "#64748B"
    TEXT_DISABLED = "#475569"

    # Master Accent Colors (Image 1 specification)
    ACCENT_ORANGE = "#F97316"
    ACCENT_ORANGE_BRIGHT = "#FB923C"
    ACCENT_ORANGE_DIM = "#C2410C"
    ACCENT_ORANGE_BG = "rgba(249, 115, 22, 0.12)"

    ACCENT_BLUE = "#3B82F6"
    ACCENT_BLUE_BRIGHT = "#60A5FA"
    ACCENT_BLUE_DIM = "#1D4ED8"
    ACCENT_BLUE_BG = "rgba(59, 130, 246, 0.12)"

    ACCENT_PURPLE = "#A855F7"
    ACCENT_PURPLE_BRIGHT = "#C084FC"
    ACCENT_PURPLE_DIM = "#7E22CE"
    ACCENT_PURPLE_BG = "rgba(168, 85, 247, 0.12)"

    ACCENT_YELLOW = "#EAB308"
    ACCENT_YELLOW_BRIGHT = "#FDE047"
    ACCENT_YELLOW_DIM = "#A16207"
    ACCENT_YELLOW_BG = "rgba(234, 179, 8, 0.12)"

    ACCENT_RED = "#EF4444"
    ACCENT_RED_BRIGHT = "#F87171"
    ACCENT_RED_DIM = "#B91C1C"
    ACCENT_RED_BG = "rgba(239, 68, 68, 0.12)"

    ACCENT_GREEN = "#10B981"
    ACCENT_GREEN_BRIGHT = "#34D399"
    ACCENT_GREEN_DIM = "#047857"
    ACCENT_GREEN_BG = "rgba(16, 185, 129, 0.12)"

    ACCENT_CYAN = "#06B6D4"
    ACCENT_CYAN_BRIGHT = "#22D3EE"
    ACCENT_CYAN_BG = "rgba(6, 182, 212, 0.12)"

    # AI / Agent — Purple / Amber
    AI_PURPLE = "#8B5CF6"
    AI_PURPLE_BRIGHT = "#A78BFA"
    AI_PURPLE_BG = "rgba(139, 92, 246, 0.15)"

    # Status indicators
    STATUS_GREEN = "#10B981"
    STATUS_GREEN_BG = "rgba(16, 185, 129, 0.15)"
    STATUS_AMBER = "#F59E0B"
    STATUS_AMBER_BG = "rgba(245, 158, 11, 0.15)"
    STATUS_RED = "#EF4444"
    STATUS_RED_BG = "rgba(239, 68, 68, 0.15)"

    # Chart palette
    CHART_ORANGE = "#F97316"
    CHART_BLUE = "#3B82F6"
    CHART_PURPLE = "#A855F7"
    CHART_YELLOW = "#EAB308"
    CHART_RED = "#EF4444"
    CHART_GREEN = "#10B981"
    CHART_CYAN = "#06B6D4"
    CHART_PINK = "#EC4899"
    CHART_PALETTE = [CHART_ORANGE, CHART_BLUE, CHART_PURPLE, CHART_YELLOW, CHART_RED, CHART_GREEN, CHART_CYAN, CHART_PINK]

    # Legacy compatibility aliases
    NAVY_900 = BG_APP
    NAVY_800 = SURFACE_PRIMARY
    NAVY_700 = SURFACE_ELEVATED
    NAVY_600 = SURFACE_ACTIVE
    NAVY_500 = ACCENT_BLUE
    NAVY_400 = ACCENT_BLUE_DIM
    NAVY_100 = ACCENT_BLUE_BG
    ACCENT_RED_LIGHT = ACCENT_RED_BRIGHT
    FLOOD_TEAL = ACCENT_CYAN
    FLOOD_CYAN = ACCENT_CYAN_BRIGHT
    FLOOD_DARK = "#0891B2"
    FLOOD_LIGHT = ACCENT_CYAN_BG
    AI_VIOLET = AI_PURPLE_BRIGHT
    AI_LIGHT = AI_PURPLE_BG
    WHITE = TEXT_PRIMARY
    GRAY_50 = "#F8FAFC"
    GRAY_100 = TEXT_PRIMARY
    GRAY_200 = TEXT_SECONDARY
    GRAY_300 = TEXT_SECONDARY
    GRAY_400 = TEXT_MUTED
    GRAY_500 = TEXT_MUTED
    GRAY_600 = TEXT_DISABLED
    GRAY_700 = BORDER_DEFAULT
    GRAY_800 = SURFACE_PRIMARY
    GRAY_900 = BG_APP
    STATUS_GREEN_BG_LIGHT = STATUS_GREEN_BG
    STATUS_AMBER_BG_LIGHT = STATUS_AMBER_BG
    STATUS_RED_BG_LIGHT = STATUS_RED_BG


# ---------------------------------------------------------------------------
# AGENT STATUS STYLING
# ---------------------------------------------------------------------------

AGENT_STATUS_COLORS = {
    "SUCCESS": (Colors.STATUS_GREEN, Colors.STATUS_GREEN_BG, "✓"),
    "WARNING": (Colors.STATUS_AMBER, Colors.STATUS_AMBER_BG, "⚠"),
    "FAILED": (Colors.STATUS_RED, Colors.STATUS_RED_BG, "✕"),
    "RUNNING": (Colors.ACCENT_ORANGE, Colors.ACCENT_ORANGE_BG, "⟳"),
    "PENDING": (Colors.TEXT_MUTED, "rgba(100, 116, 139, 0.1)", "●"),
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
# NUMBER FORMATTING HELPERS
# ---------------------------------------------------------------------------

def format_currency(val: float, prefix: str = "KES ") -> str:
    """Format currency values in financial shorthand (KES 1.2M, KES 500, etc.)."""
    if val is None:
        return "—"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1e9:
        return f"{sign}{prefix}{abs_val / 1e9:.1f}B".replace(".0B", "B")
    if abs_val >= 1e6:
        return f"{sign}{prefix}{abs_val / 1e6:.1f}M".replace(".0M", "M")
    if abs_val >= 1e3 and abs_val >= 10_000:
        return f"{sign}{prefix}{abs_val / 1e3:.1f}K".replace(".0K", "K")
    if abs_val == int(abs_val):
        return f"{sign}{prefix}{int(abs_val):,}"
    return f"{sign}{prefix}{abs_val:,.0f}"


def format_currency_exact(val: float, prefix: str = "KES ") -> str:
    """Format exact currency with commas."""
    if val is None:
        return "—"
    return f"{prefix}{val:,.2f}"


def format_pct(val: float, decimals: int = 1) -> str:
    """Format percentage."""
    if val is None:
        return "—"
    return f"{val:.{decimals}f}%"


def format_bps(val: float) -> str:
    """Format basis points."""
    if val is None:
        return "—"
    if val == int(val):
        return f"{int(val)} bps"
    return f"{val:.1f} bps"


# ---------------------------------------------------------------------------
# INJECTABLE CSS STYLESHEET
# ---------------------------------------------------------------------------

def get_custom_css() -> str:
    """Return complete dark theme CSS stylesheet."""
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global reset and backgrounds */
    html, body, [data-testid="stAppViewContainer"], .main {{
        background-color: {Colors.BG_APP} !important;
        color: {Colors.TEXT_PRIMARY} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }}

    [data-testid="stHeader"] {{
        background-color: rgba(11, 15, 25, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        border-bottom: 1px solid {Colors.BORDER_DEFAULT} !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {Colors.BG_SIDEBAR} !important;
        border-right: 1px solid {Colors.BORDER_DEFAULT} !important;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        background-color: {Colors.BG_SIDEBAR} !important;
        padding-top: 1rem;
    }}

    /* Hide standard Streamlit chrome decorations */
    #MainMenu, footer, header {{visibility: hidden;}}
    [data-testid="stToolbar"] {{display: none !important;}}

    /* Main container padding */
    .block-container {{
        padding: 1.25rem 2rem 3rem 2rem !important;
        max-width: 1560px !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {Colors.SURFACE_PRIMARY} !important;
        color: {Colors.TEXT_PRIMARY} !important;
        border: 1px solid {Colors.BORDER_DEFAULT} !important;
        border-radius: 6px !important;
        padding: 0.45rem 0.9rem !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }}
    .stButton > button:hover {{
        border-color: {Colors.ACCENT_ORANGE} !important;
        color: {Colors.ACCENT_ORANGE_BRIGHT} !important;
        background: {Colors.SURFACE_ELEVATED} !important;
    }}
    .stButton > button:active {{
        background: {Colors.SURFACE_ACTIVE} !important;
    }}

    /* Primary CTA Button */
    .stButton > button[kind="primary"] {{
        background: {Colors.ACCENT_ORANGE} !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {Colors.ACCENT_ORANGE_BRIGHT} !important;
        box-shadow: 0 0 15px rgba(249, 115, 22, 0.4) !important;
    }}

    /* Inputs, Selectboxes, Text Areas */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stChatInput > div {{
        background-color: {Colors.SURFACE_PRIMARY} !important;
        color: {Colors.TEXT_PRIMARY} !important;
        border: 1px solid {Colors.BORDER_DEFAULT} !important;
        border-radius: 6px !important;
        font-size: 0.84rem !important;
    }}
    .stTextInput > div > div > input:focus, .stChatInput > div:focus-within {{
        border-color: {Colors.ACCENT_ORANGE} !important;
        box-shadow: 0 0 0 1px {Colors.ACCENT_ORANGE} !important;
    }}

    /* Dataframes and Tables */
    [data-testid="stDataFrame"], .stTable {{
        border: 1px solid {Colors.BORDER_DEFAULT} !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        background-color: {Colors.SURFACE_PRIMARY} !important;
    }}

    /* Metric and analytical cards */
    .ft-card, .ft-metric-card {{
        background-color: {Colors.SURFACE_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: 8px;
        padding: 1.1rem;
        transition: border-color 0.15s ease;
    }}
    .ft-card:hover, .ft-metric-card:hover {{
        border-color: {Colors.BORDER_STRONG};
    }}

    .ft-kpi-card {{
        background-color: {Colors.SURFACE_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: 8px;
        padding: 1rem;
        position: relative;
        overflow: hidden;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .ft-kpi-card:hover {{
        border-color: {Colors.BORDER_STRONG};
    }}

    .ft-kpi-header {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.78rem;
        font-weight: 500;
        color: {Colors.TEXT_MUTED};
    }}

    .ft-kpi-icon {{
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
    }}

    .ft-kpi-value-row {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin: 0.2rem 0;
    }}

    .ft-kpi-value {{
        font-size: 1.45rem;
        font-weight: 700;
        color: {Colors.TEXT_PRIMARY};
        letter-spacing: -0.02em;
    }}

    .ft-kpi-trend {{
        font-size: 0.74rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }}

    /* Anomaly callout card inside chart */
    .ft-anomaly-callout {{
        background: {Colors.SURFACE_SECONDARY};
        border: 1px solid {Colors.ACCENT_ORANGE};
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }}

    /* AI Insight Panel */
    .ft-ai-insight-card {{
        background: {Colors.SURFACE_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: 8px;
        padding: 1.2rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}

    .ft-factor-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.6rem;
        font-size: 0.78rem;
    }}

    .ft-progress-bar-bg {{
        background: {Colors.SURFACE_ELEVATED};
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        margin-top: 0.25rem;
    }}

    .ft-progress-bar-fill {{
        height: 100%;
        border-radius: 3px;
        background: {Colors.ACCENT_ORANGE};
    }}

    /* Badge styles */
    .ft-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}

    .ft-pill-confidence {{
        padding: 0.15rem 0.55rem;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 600;
        text-align: center;
        display: inline-block;
    }}

    /* Horizontal Category tabs (Image 2) */
    .ft-category-tabs {{
        display: flex;
        gap: 1.5rem;
        border-bottom: 1px solid {Colors.BORDER_DEFAULT};
        margin-bottom: 1rem;
        padding-bottom: 0.25rem;
    }}

    .ft-category-tab {{
        font-size: 0.8rem;
        font-weight: 600;
        color: {Colors.TEXT_MUTED};
        padding: 0.4rem 0;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .ft-category-tab.active {{
        color: {Colors.ACCENT_ORANGE};
        border-bottom-color: {Colors.ACCENT_ORANGE};
    }}

    /* Multi-Agent Communication & Dialogue Styles */
    .ft-dialogue-item {{
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
        align-items: flex-start;
        animation: fadeIn 0.3s ease;
    }}

    .ft-agent-avatar {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 700;
        flex-shrink: 0;
    }}

    .ft-agent-bubble {{
        background: {Colors.SURFACE_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: 8px;
        padding: 10px 14px;
        flex-grow: 1;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }}

    .ft-agent-bubble-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }}

    .ft-agent-bubble-title {{
        font-size: 12px;
        font-weight: 700;
        color: {Colors.TEXT_PRIMARY};
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    .ft-agent-bubble-body {{
        font-size: 12px;
        color: {Colors.TEXT_SECONDARY};
        line-height: 1.45;
    }}

    .ft-agent-payload {{
        margin-top: 8px;
        background: {Colors.SURFACE_SECONDARY};
        border: 1px solid {Colors.BORDER_SUBTLE};
        border-radius: 6px;
        padding: 6px 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: {Colors.ACCENT_ORANGE_BRIGHT};
    }}

    .ft-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: {Colors.SURFACE_PRIMARY};
        border: 1px solid {Colors.BORDER_DEFAULT};
        border-radius: 16px;
        padding: 5px 12px;
        font-size: 11px;
        color: {Colors.TEXT_SECONDARY};
        cursor: pointer;
        transition: all 0.15s ease;
    }}
    .ft-chip:hover {{
        border-color: {Colors.ACCENT_ORANGE};
        color: {Colors.ACCENT_ORANGE};
        background: {Colors.SURFACE_ELEVATED};
    }}

    /* Custom scrollbars */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {Colors.BG_APP};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {Colors.BORDER_DEFAULT};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {Colors.BORDER_STRONG};
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(4px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    """
