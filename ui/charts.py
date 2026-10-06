"""FLOODTAIL — Plotly Chart Builders (Dark Analytical Theme).

All chart constructors consume backend data structures and return Plotly figures.
No calculations are performed here — display only. Charts use the dark analytical
colour system matching NEXORA AI and Jupiter ClimateScore visual specifications.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go

from ui.theme import Colors


# ---------------------------------------------------------------------------
# Chart layout & axis defaults — dark analytical theme
# ---------------------------------------------------------------------------

_LAYOUT_DEFAULTS = dict(
    font=dict(family="Inter, sans-serif", color=Colors.TEXT_SECONDARY, size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=Colors.SURFACE_PRIMARY,
    margin=dict(l=40, r=20, t=30, b=40),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color=Colors.TEXT_MUTED, size=11),
        bgcolor="rgba(0,0,0,0)",
    ),
)

_AXIS_DEFAULTS = dict(
    gridcolor=Colors.BORDER_DEFAULT,
    zerolinecolor=Colors.BORDER_STRONG,
    tickfont=dict(color=Colors.TEXT_MUTED, size=10),
    title_font=dict(color=Colors.TEXT_SECONDARY, size=11),
)


def _base_layout(**overrides: Any) -> dict:
    layout = dict(_LAYOUT_DEFAULTS)
    layout.update(overrides)
    return layout


def _apply_dark_axes(fig: go.Figure) -> go.Figure:
    """Apply dark-themed axis styling to a figure."""
    fig.update_xaxes(**_AXIS_DEFAULTS)
    fig.update_yaxes(**_AXIS_DEFAULTS)
    return fig


# ---------------------------------------------------------------------------
# Sparkline generator for KPI cards
# ---------------------------------------------------------------------------

def sparkline(data: list[float], color: str = Colors.ACCENT_ORANGE, height: int = 36) -> go.Figure:
    """Construct a minimal, clean sparkline for KPI cards."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=data,
        mode="lines",
        line=dict(color=color, width=2, shape="spline"),
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Primary Analytical Chart: Revenue / Loss Over Time (Image 1)
# ---------------------------------------------------------------------------

def revenue_over_time_chart(
    dates: list[str],
    actual_values: list[float],
    expected_values: list[float],
    anomaly_index: Optional[int] = None,
    value_prefix: str = "$",
) -> go.Figure:
    """Build the primary analytical line chart with expected baseline and anomaly highlighting."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=expected_values,
        name="Expected Benchmark",
        mode="lines",
        line=dict(color=Colors.TEXT_MUTED, width=1.5, dash="dash"),
    ))

    fig.add_trace(go.Scatter(
        x=dates,
        y=actual_values,
        name="Actual Trend",
        mode="lines+markers",
        line=dict(color=Colors.ACCENT_ORANGE, width=2.5, shape="spline"),
        marker=dict(size=5, color=Colors.ACCENT_ORANGE),
    ))

    if anomaly_index is not None and 0 <= anomaly_index < len(dates):
        anom_date = dates[anomaly_index]
        anom_val = actual_values[anomaly_index]

        fig.add_trace(go.Scatter(
            x=[anom_date],
            y=[anom_val],
            name="Anomaly Detected",
            mode="markers",
            marker=dict(size=12, color=Colors.ACCENT_ORANGE_BRIGHT, line=dict(color="#FFFFFF", width=2)),
            showlegend=False,
        ))

        start_idx = max(0, anomaly_index - 2)
        end_idx = min(len(dates) - 1, anomaly_index + 1)
        fig.add_vrect(
            x0=dates[start_idx],
            x1=dates[end_idx],
            fillcolor=Colors.ACCENT_ORANGE_BG,
            layer="below",
            line_width=0,
        )

    fig.update_layout(
        **_base_layout(),
        yaxis=dict(
            tickprefix=value_prefix,
            gridcolor=Colors.BORDER_DEFAULT,
            tickfont=dict(color=Colors.TEXT_MUTED, size=10),
        ),
        xaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(color=Colors.TEXT_MUTED, size=10),
        ),
        height=320,
    )
    return fig


# ---------------------------------------------------------------------------
# Horizontal Bar Chart: Revenue / Loss by Channel / Region (Image 1)
# ---------------------------------------------------------------------------

def horizontal_bar_chart(
    categories: list[str],
    values: list[float],
    percentages: list[float],
    color: str = Colors.ACCENT_ORANGE,
) -> go.Figure:
    """Build horizontal bar chart with percentage labels at the right."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=categories,
        x=percentages,
        orientation="h",
        marker=dict(color=color, cornerradius=4),
        text=[f"{p:.1f}%" for p in percentages],
        textposition="outside",
        textfont=dict(color=Colors.TEXT_SECONDARY, size=11),
        hoverinfo="y+x",
    ))
    fig.update_layout(
        **_base_layout(margin=dict(l=80, r=45, t=10, b=30)),
        height=260,
        xaxis=dict(
            ticksuffix="%",
            gridcolor=Colors.BORDER_DEFAULT,
            range=[0, max(percentages) * 1.25 if percentages else 100],
            tickfont=dict(color=Colors.TEXT_MUTED, size=10),
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(color=Colors.TEXT_SECONDARY, size=11),
            gridcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Donut Chart: Users / Portfolio by Segment (Image 1)
# ---------------------------------------------------------------------------

def segment_donut_chart(
    labels: list[str],
    values: list[float],
    center_title: str = "Total",
    center_value: str = "1,240",
) -> go.Figure:
    """Build donut chart with central summary text and clean dark legend."""
    colors = [Colors.ACCENT_BLUE, Colors.ACCENT_ORANGE, Colors.ACCENT_PURPLE, Colors.ACCENT_CYAN, Colors.ACCENT_YELLOW]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.68,
        marker=dict(colors=colors, line=dict(color=Colors.SURFACE_PRIMARY, width=2)),
        textinfo="none",
        hoverinfo="label+percent+value",
    )])

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(color=Colors.TEXT_SECONDARY, size=11),
        ),
        annotations=[
            dict(
                text=f"<span style='font-size:11px;color:{Colors.TEXT_MUTED};'>{center_title}</span><br><b style='font-size:16px;color:{Colors.TEXT_PRIMARY};'>{center_value}</b>",
                x=0.5,
                y=0.5,
                font_size=14,
                showarrow=False,
            )
        ],
    )
    return fig


# ---------------------------------------------------------------------------
# Pricing Waterfall Chart
# ---------------------------------------------------------------------------

def pricing_waterfall(
    expected_loss: float,
    tail_charge: float,
    expense: float,
    total_premium: float,
    title: str = "Technical Pricing Waterfall",
) -> go.Figure:
    """Waterfall chart showing technical premium build-up."""
    fig = go.Figure(go.Waterfall(
        name="Premium",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Expected Loss", "Tail Risk Charge", "Expense Load", "Technical Premium"],
        textposition="outside",
        text=[f"KES {v:,.0f}" for v in [expected_loss, tail_charge, expense, total_premium]],
        y=[expected_loss, tail_charge, expense, 0],
        connector={"line": {"color": Colors.BORDER_STRONG}},
        decreasing={"marker": {"color": Colors.ACCENT_RED}},
        increasing={"marker": {"color": Colors.ACCENT_BLUE}},
        totals={"marker": {"color": Colors.ACCENT_ORANGE}},
    ))
    fig.update_layout(
        **_base_layout(title=dict(text=title, font=dict(size=14, color=Colors.TEXT_PRIMARY))),
        yaxis=dict(title="Amount (KES)"),
    )
    return _apply_dark_axes(fig)


# ---------------------------------------------------------------------------
# Exceedance curve (OEP / AEP)
# ---------------------------------------------------------------------------

def exceedance_curve(oep_points: list, aep_points: list, title: str = "Loss Exceedance Curve") -> go.Figure:
    """Build an interactive OEP/AEP exceedance curve."""
    fig = go.Figure()
    if oep_points:
        fig.add_trace(go.Scatter(
            x=[p.return_period_years for p in oep_points],
            y=[p.loss for p in oep_points],
            name="OEP",
            mode="lines+markers",
            line=dict(color=Colors.ACCENT_RED, width=2),
            marker=dict(size=5, color=Colors.ACCENT_RED),
        ))
    if aep_points:
        fig.add_trace(go.Scatter(
            x=[p.return_period_years for p in aep_points],
            y=[p.loss for p in aep_points],
            name="AEP",
            mode="lines+markers",
            line=dict(color=Colors.ACCENT_CYAN, width=2),
            marker=dict(size=5, color=Colors.ACCENT_CYAN),
        ))
    fig.update_layout(
        **_base_layout(title=dict(text=title, font=dict(size=14, color=Colors.TEXT_PRIMARY))),
        xaxis=dict(title="Return Period (Years)", type="log"),
        yaxis=dict(title="Loss (KES)"),
    )
    return _apply_dark_axes(fig)


# ---------------------------------------------------------------------------
# Tail contribution bar chart
# ---------------------------------------------------------------------------

def tail_contribution_bars(policy_ids: list[str], contributions: list[float], portfolio_tvar: float) -> go.Figure:
    """Horizontal bar chart of policy tail contributions ranked by magnitude."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=policy_ids,
        x=contributions,
        orientation="h",
        marker_color=Colors.ACCENT_ORANGE,
        text=[f"KES {c:,.0f}" for c in contributions],
        textposition="outside",
        textfont=dict(color=Colors.TEXT_MUTED, size=10),
    ))
    fig.update_layout(
        **_base_layout(title=dict(text="Tail Risk Contribution (TVaR 99.6%)", font=dict(size=14, color=Colors.TEXT_PRIMARY))),
        xaxis=dict(title="Tail Contribution (KES)"),
        yaxis=dict(autorange="reversed"),
    )
    return _apply_dark_axes(fig)


# ---------------------------------------------------------------------------
# Regional Accumulation chart
# ---------------------------------------------------------------------------

def regional_accumulation(regions: list[str], tiv_shares: list[float], tail_shares: list[float]) -> go.Figure:
    """Grouped bar chart comparing TIV share vs Tail Risk share by region."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="TIV Share %",
        x=regions,
        y=tiv_shares,
        marker_color=Colors.ACCENT_BLUE,
    ))
    fig.add_trace(go.Bar(
        name="Tail Share %",
        x=regions,
        y=tail_shares,
        marker_color=Colors.ACCENT_ORANGE,
    ))
    fig.update_layout(
        **_base_layout(title=dict(text="Regional Accumulation: TIV vs Tail Share", font=dict(size=14, color=Colors.TEXT_PRIMARY))),
        barmode="group",
        yaxis=dict(title="Share (%)"),
    )
    return _apply_dark_axes(fig)


# ---------------------------------------------------------------------------
# Marginal TVaR Scatter Chart
# ---------------------------------------------------------------------------

def marginal_tvar_scatter(tivs: list[float], marginals: list[float], labels: list[str]) -> go.Figure:
    """Scatter plot of TIV vs Marginal TVaR."""
    fig = go.Figure(go.Scatter(
        x=tivs,
        y=marginals,
        mode="markers+text",
        text=labels,
        textposition="top center",
        marker=dict(size=8, color=Colors.ACCENT_ORANGE),
    ))
    fig.update_layout(
        **_base_layout(title=dict(text="Exposure vs Marginal TVaR", font=dict(size=14, color=Colors.TEXT_PRIMARY))),
        xaxis=dict(title="Total Insured Value (KES)"),
        yaxis=dict(title="Marginal TVaR (KES)"),
    )
    return _apply_dark_axes(fig)
