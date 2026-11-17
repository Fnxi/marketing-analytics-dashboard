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


st.set_page_config(page_title="Marketing Analytics", page_icon="📈", layout="wide", initial_sidebar_state="expanded")


@st.cache_resource
def get_dataset():
    """Load the deterministic dataset once for the active Streamlit server."""
    return load_marketing_dataset()


def _inject_styles() -> None:
    """Apply the project-local visual theme."""
    path = Path(__file__).parent / "src" / "styles" / "dashboard.css"
    st.markdown(path.read_text(encoding="utf-8"), unsafe_allow_html=True)


def _render_navigation() -> None:
    """Render the static visual navigation shown in the reference layout."""
    st.sidebar.markdown("<div class='brand'><span class='brand-dot'>MA</span> Marketing<br>Analytics</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='side-section'>Marketing Insights</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='side-item'>Cross Channel</div><div class='side-active'>Executive Summary</div><div class='side-item'>Channel Performance</div><div class='side-item'>Channel Segments &amp; Trends</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='side-section'>Paid Ads x Google Analytics</div>", unsafe_allow_html=True)
    for item in ("Paid Search", "Paid Social", "Search Engine Opt.", "Organic Social", "Programmatic", "eCommerce"):
        st.sidebar.markdown(f"<div class='side-item'>{item}</div>", unsafe_allow_html=True)


def _filter_ids(options: pd.DataFrame, id_column: str, name_column: str, label: str) -> list[str]:
    """Render name-based selection and return matching dimension IDs."""
    selected = st.multiselect(label, options[name_column].tolist(), placeholder=label)
    return options.loc[options[name_column].isin(selected), id_column].tolist()


def main() -> None:
    """Render a responsive, filter-connected dashboard."""
    _inject_styles()
    _render_navigation()
    dataset = get_dataset()
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
            min_value=fact.date.min().date(), max_value=fact.date.max().date(),
        )
    st.markdown("</div>", unsafe_allow_html=True)
    start_date, end_date = selected_dates if isinstance(selected_dates, tuple) and len(selected_dates) == 2 else (selected_dates, selected_dates)
    criteria = FilterCriteria(start_date, end_date, source_ids, channel_ids, campaign_ids, ad_set_ids)

    st.markdown("<div class='dashboard-title'>Executive Summary</div>", unsafe_allow_html=True)
    current = filter_daily_performance(fact, criteria)
    dashboard = build_dashboard_aggregations(dataset, criteria)
    daily_trends = build_daily_metric_trends(current)
    kpi_data = dashboard.kpis.set_index("metric")

    primary, secondary = st.columns([1.66, 1.14], gap="large")
    with primary:
        kpis = [("Spend", "spend"), ("CPM", "cpm"), ("CTR", "ctr"), ("CPC", "cpc"), ("Video Views", "video_views"), ("Impressions", "impressions"), ("Conversions", "conversions"), ("Conversion Rate", "conversion_rate")]
        for start in range(0, len(kpis), 4):
            columns = st.columns(4, gap="medium")
            for column, (label, metric) in zip(columns, kpis[start:start + 4], strict=True):
                with column:
                    values = kpi_data.loc[metric]
                    prior_value = float(values["previous_value"])
                    variation = None if prior_value == 0 else float(values["variation_pct"])
                    render_kpi_card(label, metric, float(values["value"]), variation, daily_trends)
        render_channel_trends(dashboard.monthly_channel_trends)
    with secondary:
        render_performance_table("Channel Performance", dashboard.channel_performance, [
            ("channel_name", "Channel", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"),
            ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("cpc", "CPC", "cpc"), ("conversions", "Conversions", "conversions"),
        ], height=195)
        render_performance_table("Data Source Performance", dashboard.data_source_performance, [
            ("data_source_name", "Data Source", ""), ("spend", "Spend", "spend"), ("impressions", "Impressions", "impressions"),
            ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions"),
        ], height=250)
        render_performance_table("Campaign Performance", dashboard.campaign_performance, [
            ("campaign_name", "Campaign", ""), ("channel_name", "Channel", ""), ("spend", "Spend", "spend"),
            ("impressions", "Impressions", "impressions"), ("clicks", "Clicks", "clicks"), ("ctr", "CTR", "ctr"), ("conversions", "Conversions", "conversions"),
        ], height=305)


if __name__ == "__main__":
    main()
