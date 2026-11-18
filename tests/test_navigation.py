"""Tests for navigation filter scoping without a Streamlit runtime."""

from src.analytics.aggregations import build_dashboard_aggregations
from src.analytics.filters import FilterCriteria, filter_daily_performance
from src.data.generator import generate_marketing_dataset
from src.navigation import ANALYTICS_VIEWS, INFORMATIONAL_VIEWS, apply_channel_scope, intersect_ids


def test_channel_scope_intersects_with_global_filter() -> None:
    """A drill-down keeps only global channel selections allowed by its page scope."""
    criteria = FilterCriteria(
        data_source_ids=["DS006"],
        channel_ids=["CH003", "CH002"],
        campaign_ids=["CP016"],
    )
    scoped = apply_channel_scope(criteria, ["CH002"])
    assert scoped.channel_ids == ("CH002",)
    assert scoped.data_source_ids == criteria.data_source_ids
    assert scoped.campaign_ids == criteria.campaign_ids


def test_channel_scope_uses_page_channel_when_global_selection_is_empty() -> None:
    """An unselected global channel filter means all values before page scoping."""
    assert intersect_ids([], ["CH001"]) == ("CH001",)


def test_channel_scope_can_produce_no_records() -> None:
    """An incompatible channel filter produces an honest empty result."""
    dataset = generate_marketing_dataset()
    criteria = apply_channel_scope(FilterCriteria(channel_ids=["CH003"]), ["CH002"])
    assert criteria.channel_ids == ("__no_matching_channel__",)
    assert filter_daily_performance(dataset.daily_performance, criteria).empty


def test_informational_views_are_explicitly_registered() -> None:
    """Views without adequate data are separated from analytical views."""
    assert set(INFORMATIONAL_VIEWS) == {"Search Engine Opt.", "Organic Social", "eCommerce"}
    assert not set(INFORMATIONAL_VIEWS).intersection(ANALYTICS_VIEWS)


def test_cross_channel_data_contains_all_channels_without_filters() -> None:
    """The unscoped cross-channel dataset includes every available channel."""
    dataset = generate_marketing_dataset()
    dashboard = build_dashboard_aggregations(dataset)
    assert set(dashboard.channel_performance["channel_name"]) == {
        "Programmatic", "Paid Search", "Paid Social", "Organic"
    }
