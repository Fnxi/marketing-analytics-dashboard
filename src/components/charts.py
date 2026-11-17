"""Plotly charts used by the Streamlit dashboard."""

from __future__ import annotations

import plotly.express as px
import pandas as pd
import streamlit as st


def render_channel_trends(trends: pd.DataFrame) -> None:
    """Render monthly impressions so all channels, including organic, remain visible."""
    st.markdown("<h3 class='section-title'>Channel Segments &amp; Trends</h3>", unsafe_allow_html=True)
    colors = {"Programmatic": "#7B3FE4", "Paid Search": "#F05BA9", "Paid Social": "#55BDED", "Organic": "#EF7B26"}
    figure = px.line(trends, x="month", y="impressions", color="channel_name", markers=False, color_discrete_map=colors)
    figure.update_traces(line={"width": 2.5})
    figure.update_layout(
        height=465, margin={"l": 30, "r": 20, "t": 42, "b": 28},
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        legend={"orientation": "h", "y": 1.12, "x": 0, "xanchor": "left"},
        font={"family": "Inter, Arial, sans-serif", "color": "#2E2D34"},
        xaxis={"showgrid": True, "gridcolor": "#EEECEF", "title": None, "tickformat": "%b\n%Y"},
        yaxis={"showgrid": True, "gridcolor": "#EEECEF", "tickformat": ".2s", "title": None},
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
