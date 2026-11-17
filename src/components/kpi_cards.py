"""KPI card and Plotly sparkline components."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.components.formatters import format_metric, format_variation


def _sparkline(trends: pd.DataFrame, metric: str) -> go.Figure:
    """Create a small, visually quiet Plotly sparkline."""
    figure = go.Figure(go.Scatter(
        x=trends["date"], y=trends[metric], mode="lines",
        line={"color": "#8B4BEA", "width": 2}, hoverinfo="skip",
    ))
    figure.update_layout(
        height=58, margin={"l": 2, "r": 2, "t": 2, "b": 0}, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False}, yaxis={"visible": False},
    )
    return figure


def render_kpi_card(label: str, metric: str, value: float, variation: float | None, trends: pd.DataFrame) -> None:
    """Render one KPI card with value, delta, and daily trend sparkline."""
    if variation is None:
        variation_markup = "<div class='kpi-delta unavailable'>— <span>vs prior period</span></div>"
    else:
        positive = variation >= 0
        color = "#4C9853" if positive else "#DF514A"
        arrow = "↑" if positive else "↓"
        variation_markup = f"<div class='kpi-delta' style='color:{color}'>{arrow} {format_variation(variation)} <span>vs prior period</span></div>"
    with st.container(border=True):
        st.markdown(
            f"<div class='kpi-label'>{label}</div><div class='kpi-value'>{format_metric(value, metric)}</div>"
            f"{variation_markup}",
            unsafe_allow_html=True,
        )
        st.plotly_chart(_sparkline(trends, metric), use_container_width=True, config={"displayModeBar": False})
