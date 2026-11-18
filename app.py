"""Streamlit entry point for the marketing analytics dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics.aggregations import build_dashboard_aggregations, build_daily_metric_trends
from src.analytics.filters import FilterCriteria, filter_daily_performance
from src.components.charts import render_channel_trends
from src.components.kpi_cards import render_kpi_card
from src.components.tables import render_performance_table
from src.data.repository import load_marketing_dataset
from src.navigation import (
    CHANNEL_PERFORMANCE,
    CHANNEL_SEGMENTS,
    CHANNEL_VIEW_NAMES,
    CROSS_CHANNEL,
    ECOMMERCE,
    EXECUTIVE_SUMMARY,
    INFORMATIONAL_VIEWS,
    ORGANIC_SOCIAL,
    PAID_SEARCH,
    PAID_SOCIAL,
    PROGRAMMATIC,
    SEARCH_ENGINE_OPT,
    apply_channel_scope,
)


st.set_page_config(page_title="Marketing Analytics", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

KPI_DEFINITIONS = (
    ("Spend", "spend"), ("CPM", "cpm"), ("CTR", "ctr"), ("CPC", "cpc"),
    ("Video Views", "video_views"), ("Impressions", "impressions"),
    ("Conversions", "conversions"), ("Conversion Rate", "conversion_rate"),
)
INFORMATIONAL_COPY = {
    SEARCH_ENGINE_OPT: ("Search Engine Optimization", "Esta fuente no incluye una clasificación SEO, palabras clave orgánicas, rankings ni sesiones de búsqueda.", "Para habilitar este análisis se necesitarían datos de rendimiento SEO y búsqueda orgánica."),
    ORGANIC_SOCIAL: ("Organic Social", "El dataset contiene tráfico Organic agregado, pero no identifica plataformas o publicaciones de redes sociales orgánicas.", "Para habilitar este análisis se necesitarían datos orgánicos por red social, publicación y audiencia."),
    ECOMMERCE: ("eCommerce", "Hay conversiones y revenue, pero no existen pedidos, productos, categorías, clientes ni eventos de carrito.", "Para habilitar este análisis se necesitarían datos transaccionales y de catálogo."),
}


@st.cache_resource
def get_dataset():
    """Load the deterministic dataset once for the active Streamlit server."""
    return load_marketing_dataset()


def _inject_styles() -> None:
    """Apply the project-local visual theme."""
    path = Path(__file__).parent / "src" / "styles" / "dashboard.css"
    st.markdown(path.read_text(encoding="utf-8"), unsafe_allow_html=True)


def _render_navigation() -> str:
    """Render stable sidebar navigation and return the selected view."""
    insight_views = (CROSS_CHANNEL, EXECUTIVE_SUMMARY, CHANNEL_PERFORMANCE, CHANNEL_SEGMENTS)
    paid_media_views = (PAID_SEARCH, PAID_SOCIAL, SEARCH_ENGINE_OPT, ORGANIC_SOCIAL, PROGRAMMATIC, ECOMMERCE)
    if "active_view" not in st.session_state:
        st.session_state["active_view"] = EXECUTIVE_SUMMARY
    active_view = st.session_state["active_view"]
    st.session_state["nav_marketing_insights"] = active_view if active_view in insight_views else None
    st.session_state["nav_paid_media"] = active_view if active_view in paid_media_views else None

    def activate_insight_view() -> None:
        """Persist an insight-page selection without adding a manual rerun."""
        selected = st.session_state["nav_marketing_insights"]
        if selected:
            st.session_state["active_view"] = selected
            st.session_state["nav_paid_media"] = None

    def activate_paid_media_view() -> None:
        """Persist a paid-media-page selection without adding a manual rerun."""
        selected = st.session_state["nav_paid_media"]
        if selected:
            st.session_state["active_view"] = selected
            st.session_state["nav_marketing_insights"] = None

    st.sidebar.markdown("<div class='brand'><span class='brand-dot'>MA</span> Marketing<br>Analytics</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='side-section'>Marketing Insights</div>", unsafe_allow_html=True)
    st.sidebar.radio("Marketing Insights", insight_views, index=None, key="nav_marketing_insights", on_change=activate_insight_view, label_visibility="collapsed")
    st.sidebar.markdown("<div class='side-section'>Paid Ads x Google Analytics</div>", unsafe_allow_html=True)
    st.sidebar.radio("Paid Ads x Google Analytics", paid_media_views, index=None, key="nav_paid_media", on_change=activate_paid_media_view, label_visibility="collapsed")
    return st.session_state["active_view"]


def _filter_ids(options: pd.DataFrame, id_column: str, name_column: str, label: str) -> list[str]:
    """Render a persistent name-based selection and return matching IDs."""
    selected = st.multiselect(label, options[name_column].tolist(), placeholder=label, key=f"filter_{label}")
    return options.loc[options[name_column].isin(selected), id_column].tolist()


def _render_global_filters(dataset) -> FilterCriteria:
    """Render the shared filters once and return their global selection."""
    fact = dataset.daily_performance
    st.markdown("<div class='topbar'>", unsafe_allow_html=True)
    source_col, channel_col, campaign_col, ad_set_col, date_col = st.columns([1.15, 1.15, 1.25, 1.15, 1.2])
    with source_col:
        source_ids = _filter_ids(dataset.data_sources, "data_source_id", "data_source_name", "Data Source")
    with channel_col:
        channel_ids = _filter_ids(dataset.channels, "channel_id", "channel_name", "Channel")
    campaign_options = dataset.campaigns
    if source_ids:
        campaign_options = campaign_options[campaign_options["data_source_id"].isin(source_ids)]
    if channel_ids:
        campaign_options = campaign_options[campaign_options["channel_id"].isin(channel_ids)]
    with campaign_col:
        campaign_ids = _filter_ids(campaign_options, "campaign_id", "campaign_name", "Campaign")
    ad_set_options = dataset.ad_sets if not campaign_ids else dataset.ad_sets[dataset.ad_sets["campaign_id"].isin(campaign_ids)]
    with ad_set_col:
        ad_set_ids = _filter_ids(ad_set_options, "ad_set_id", "ad_set_name", "Ad Set")
    with date_col:
        selected_dates = st.date_input(
            "Date Range", value=(pd.Timestamp("2023-01-01").date(), pd.Timestamp("2023-12-31").date()),
            min_value=fact.date.min().date(), max_value=fact.date.max().date(), key="filter_date_range",
        )
    st.markdown("</div>", unsafe_allow_html=True)
    start_date, end_date = selected_dates if isinstance(selected_dates, tuple) and len(selected_dates) == 2 else (selected_dates, selected_dates)
    return FilterCriteria(start_date, end_date, source_ids, channel_ids, campaign_ids, ad_set_ids)


def _render_kpis(kpi_data: pd.DataFrame, daily_trends: pd.DataFrame) -> None:
    """Render the existing eight-card KPI layout."""
    for start in range(0, len(KPI_DEFINITIONS), 4):
        columns = st.columns(4, gap="medium")
        for column, (label, metric) in zip(columns, KPI_DEFINITIONS[start:start + 4], strict=True):
            with column:
                values = kpi_data.loc[metric]
                prior_value = float(values["previous_value"])
                variation = None if prior_value == 0 else float(values["variation_pct"])
                render_kpi_card(label, metric, float(values["value"]), variation, daily_trends)


def _render_executive_summary(dashboard, daily_trends: pd.DataFrame) -> None:
    """Render the existing executive dashboard unchanged in composition."""
    st.markdown("<div class='dashboard-title'>Executive Summary</div>", unsafe_allow_html=True)
    primary, secondary = st.columns([1.66, 1.14], gap="large")
    with primary:
        _render_kpis(dashboard.kpis.set_index("metric"), daily_trends)
        render_channel_trends(dashboard.monthly_channel_trends)
    with secondary:
        render_performance_table("Channel Performance", dashboard.channel_performance, [("channel_name", "Channel", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("cpc", "CPC", "cpc"), ("conversions", "Conversions", "conversions")], height=195)
        render_performance_table("Data Source Performance", dashboard.data_source_performance, [("data_source_name", "Data Source", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions")], height=250)
        render_performance_table("Campaign Performance", dashboard.campaign_performance, [("campaign_name", "Campaign", ""), ("channel_name", "Channel", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions")], height=305)


def _render_cross_channel(dashboard) -> None:
    """Render a concise comparison of all channels and their monthly trends."""
    st.markdown("<div class='dashboard-title'>Cross Channel</div>", unsafe_allow_html=True)
    render_performance_table("Channel Performance", dashboard.channel_performance, [("channel_name", "Channel", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("cpc", "CPC", "cpc"), ("conversions", "Conversions", "conversions")], height=220)
    render_channel_trends(dashboard.monthly_channel_trends)


def _render_channel_performance(dashboard) -> None:
    """Render detailed channel results with supporting source context."""
    st.markdown("<div class='dashboard-title'>Channel Performance</div>", unsafe_allow_html=True)
    render_performance_table("Performance by Channel", dashboard.channel_performance, [("channel_name", "Channel", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("cpc", "CPC", "cpc"), ("conversions", "Conversions", "conversions")], height=235)
    left, right = st.columns([1.45, 1], gap="large")
    with left:
        render_channel_trends(dashboard.monthly_channel_trends)
    with right:
        render_performance_table("Data Source Performance", dashboard.data_source_performance, [("data_source_name", "Data Source", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions")], height=430)


def _render_segments_and_trends(dashboard) -> None:
    """Render monthly trends alongside campaign and source performance slices."""
    st.markdown("<div class='dashboard-title'>Channel Segments &amp; Trends</div>", unsafe_allow_html=True)
    render_channel_trends(dashboard.monthly_channel_trends)
    left, right = st.columns(2, gap="large")
    with left:
        render_performance_table("Campaign Performance", dashboard.campaign_performance, [("campaign_name", "Campaign", ""), ("channel_name", "Channel", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions")], height=310)
    with right:
        render_performance_table("Data Source Performance", dashboard.data_source_performance, [("data_source_name", "Data Source", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions")], height=310)


def _render_channel_drilldown(view: str, dashboard, daily_trends: pd.DataFrame) -> None:
    """Render a scoped channel drill-down using the established components."""
    st.markdown(f"<div class='dashboard-title'>{view}</div>", unsafe_allow_html=True)
    _render_kpis(dashboard.kpis.set_index("metric"), daily_trends)
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        render_channel_trends(dashboard.monthly_channel_trends)
    with right:
        render_performance_table("Campaign Performance", dashboard.campaign_performance, [("campaign_name", "Campaign", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions")], height=465)
        render_performance_table("Data Source Performance", dashboard.data_source_performance, [("data_source_name", "Data Source", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"), ("ctr", "CTR", "ctr")], height=230)


def _render_informational_view(view: str) -> None:
    """Explain why an approved informational view does not show invented metrics."""
    title, current_limit, required_data = INFORMATIONAL_COPY[view]
    st.markdown(f"<div class='dashboard-title'>{title}</div>", unsafe_allow_html=True)
    st.info(f"**Datos no disponibles para este análisis.** {current_limit}")
    st.caption(required_data)


def main() -> None:
    """Render one selected navigation view with shared, persistent global filters."""
    _inject_styles()
    view = _render_navigation()
    dataset = get_dataset()
    global_criteria = _render_global_filters(dataset)
    if view in INFORMATIONAL_VIEWS:
        _render_informational_view(view)
        return

    scope_ids: tuple[str, ...] | None = None
    if view in CHANNEL_VIEW_NAMES:
        channel_name = CHANNEL_VIEW_NAMES[view]
        scope_ids = tuple(dataset.channels.loc[dataset.channels["channel_name"] == channel_name, "channel_id"])
    criteria = apply_channel_scope(global_criteria, scope_ids)
    current = filter_daily_performance(dataset.daily_performance, criteria)
    if current.empty:
        st.markdown(f"<div class='dashboard-title'>{view}</div>", unsafe_allow_html=True)
        st.info("No hay resultados para la combinación actual de filtros y el alcance de esta vista.")
        return

    dashboard = build_dashboard_aggregations(dataset, criteria)
    daily_trends = build_daily_metric_trends(current)
    if view == EXECUTIVE_SUMMARY:
        _render_executive_summary(dashboard, daily_trends)
    elif view == CROSS_CHANNEL:
        _render_cross_channel(dashboard)
    elif view == CHANNEL_PERFORMANCE:
        _render_channel_performance(dashboard)
    elif view == CHANNEL_SEGMENTS:
        _render_segments_and_trends(dashboard)
    else:
        _render_channel_drilldown(view, dashboard, daily_trends)


if __name__ == "__main__":
    main()
