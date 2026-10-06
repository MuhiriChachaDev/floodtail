"""FLOODTAIL — Plotly Chart Builders.

All chart constructors consume backend data structures and return Plotly figures.
No calculations are performed here — display only.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from ui.theme import Colors


# ---------------------------------------------------------------------------
# Chart defaults
# ---------------------------------------------------------------------------

_LAYOUT_DEFAULTS = dict(
    font=dict(family="Inter, sans-serif", color=Colors.GRAY_700),
    paper_bgcolor=Colors.WHITE,
    plot_bgcolor=Colors.GRAY_50,
    margin=dict(l=50, r=20, t=40, b=50),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

def _base_layout(**overrides: Any) -> dict:
    layout = dict(_LAYOUT_DEFAULTS)
    layout.update(overrides)
    return layout


# ---------------------------------------------------------------------------
# Exceedance curve (OEP / AEP)
# ---------------------------------------------------------------------------

def exceedance_curve(oep_points: list, aep_points: list, title: str = "Loss Exceedance Curve") -> go.Figure:
    """Build an interactive OEP/AEP exceedance curve from ExceedancePoint lists."""
    fig = go.Figure()
    if oep_points:
        fig.add_trace(go.Scatter(
            x=[p.return_period_years for p in oep_points],
            y=[p.loss for p in oep_points],
            name="OEP",
            mode="lines+markers",
            line=dict(color=Colors.ACCENT_RED, width=2),
            marker=dict(size=6),
        ))
    if aep_points:
        fig.add_trace(go.Scatter(
            x=[p.return_period_years for p in aep_points],
            y=[p.loss for p in aep_points],
            name="AEP",
            mode="lines+markers",
            line=dict(color=Colors.NAVY_500, width=2),
            marker=dict(size=6),
        ))
    fig.update_layout(
        **_base_layout(title=title),
        xaxis=dict(title="Return Period (Years)", type="log"),
        yaxis=dict(title="Loss (KES)"),
    )
    return fig


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
        marker_color=Colors.NAVY_500,
        text=[f"KES {c:,.0f}" for c in contributions],
        textposition="outside",
    ))
    fig.update_layout(
        **_base_layout(title="Policy Tail Contribution to Portfolio TVaR"),
        xaxis=dict(title="Tail Contribution (KES)"),
        yaxis=dict(autorange="reversed"),
        height=max(300, len(policy_ids) * 35 + 100),
    )
    return fig


# ---------------------------------------------------------------------------
# Pricing waterfall
# ---------------------------------------------------------------------------

def pricing_waterfall(expected_loss: float, tail_charge: float, expense: float, total_premium: float) -> go.Figure:
    """Waterfall chart showing pricing decomposition."""
    fig = go.Figure(go.Waterfall(
        name="Premium Waterfall",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Expected Loss (AAL)", "Tail Risk Charge", "Expense Loading", "Technical Premium"],
        y=[expected_loss, tail_charge, expense, total_premium],
        text=[f"KES {v:,.0f}" for v in [expected_loss, tail_charge, expense, total_premium]],
        textposition="outside",
        connector=dict(line=dict(color=Colors.GRAY_300)),
        increasing=dict(marker=dict(color=Colors.NAVY_500)),
        decreasing=dict(marker=dict(color=Colors.STATUS_GREEN)),
        totals=dict(marker=dict(color=Colors.ACCENT_RED)),
    ))
    fig.update_layout(
        **_base_layout(title="Technical Premium Waterfall"),
        yaxis=dict(title="KES"),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Regional accumulation bars
# ---------------------------------------------------------------------------

def regional_accumulation(regions: list[str], tiv_shares: list[float], tail_shares: list[float]) -> go.Figure:
    """Grouped bar chart: TIV share vs tail contribution share by region."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="TIV Share %", x=regions, y=tiv_shares, marker_color=Colors.NAVY_500))
    fig.add_trace(go.Bar(name="Tail Share %", x=regions, y=tail_shares, marker_color=Colors.ACCENT_RED))
    fig.update_layout(
        **_base_layout(title="Regional Concentration: TIV vs Tail Risk"),
        barmode="group",
        yaxis=dict(title="Share (%)"),
    )
    return fig


# ---------------------------------------------------------------------------
# Policy comparison radar
# ---------------------------------------------------------------------------

def policy_comparison_bars(labels: list[str], values_a: list[float], values_b: list[float], name_a: str, name_b: str) -> go.Figure:
    """Side-by-side bar chart for A/B policy comparison."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name=name_a, x=labels, y=values_a, marker_color=Colors.NAVY_500))
    fig.add_trace(go.Bar(name=name_b, x=labels, y=values_b, marker_color=Colors.FLOOD_TEAL))
    fig.update_layout(
        **_base_layout(title=f"{name_a} vs {name_b}"),
        barmode="group",
    )
    return fig


# ---------------------------------------------------------------------------
# Loss distribution histogram
# ---------------------------------------------------------------------------

def annual_loss_distribution(annual_losses: list[float], aal: float, var_996: float) -> go.Figure:
    """Histogram of annual losses with AAL and VaR reference lines."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=annual_losses,
        nbinsx=50,
        marker_color=Colors.NAVY_500,
        opacity=0.7,
        name="Annual Losses",
    ))
    fig.add_vline(x=aal, line_dash="dash", line_color=Colors.STATUS_GREEN,
                  annotation_text=f"AAL: KES {aal:,.0f}", annotation_position="top right")
    fig.add_vline(x=var_996, line_dash="dash", line_color=Colors.ACCENT_RED,
                  annotation_text=f"VaR(99.6%): KES {var_996:,.0f}", annotation_position="top right")
    fig.update_layout(
        **_base_layout(title="Annual Loss Distribution"),
        xaxis=dict(title="Annual Loss (KES)"),
        yaxis=dict(title="Frequency"),
    )
    return fig


# ---------------------------------------------------------------------------
# What-if delta comparison
# ---------------------------------------------------------------------------

def what_if_delta(metrics: list[str], before: list[float], after: list[float]) -> go.Figure:
    """Grouped bar chart showing before/after for what-if analysis."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Before", x=metrics, y=before, marker_color=Colors.GRAY_400))
    fig.add_trace(go.Bar(name="After", x=metrics, y=after, marker_color=Colors.ACCENT_RED))
    fig.update_layout(
        **_base_layout(title="What-If Impact Analysis"),
        barmode="group",
        yaxis=dict(title="KES"),
    )
    return fig
