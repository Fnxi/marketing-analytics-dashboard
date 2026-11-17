"""Tests for metrics, global filtering, and dashboard aggregations."""

import pandas as pd
import pytest

from src.analytics.aggregations import build_dashboard_aggregations, build_kpi_summary, build_monthly_channel_trends
from src.analytics.filters import FilterCriteria, filter_daily_performance, previous_equivalent_period
from src.analytics.metrics import calculate_metrics
from src.data.generator import generate_marketing_dataset


@pytest.fixture()
def sample_fact() -> pd.DataFrame:
    """Return a small fact table with hand-verifiable aggregate values."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        "data_source_id": ["DS001", "DS002"],
        "channel_id": ["CH001", "CH002"],
        "campaign_id": ["CP001", "CP002"],
        "ad_set_id": ["AS0001", "AS0002"],
        "spend": [100.0, 300.0],
        "impressions": [10_000, 30_000],
        "clicks": [100, 600],
        "video_views": [2_000, 3_000],
        "conversions": [10, 60],
        "revenue": [500.0, 3_000.0],
    })


def test_metric_formulas_are_calculated_from_aggregates(sample_fact: pd.DataFrame) -> None:
    """Ratios must use summed numerators and denominators, not row averages."""
    metrics = calculate_metrics(sample_fact)
    assert metrics["spend"] == 400.0
    assert metrics["impressions"] == 40_000.0
    assert metrics["cpm"] == 10.0
    assert metrics["ctr"] == pytest.approx(1.75)
    assert metrics["cpc"] == pytest.approx(400 / 700)
    assert metrics["conversion_rate"] == 10.0
    assert metrics["cpa"] == pytest.approx(400 / 70)
    assert metrics["roas"] == 8.75


def test_zero_denominators_return_zero() -> None:
    """All derived ratios should be safe for empty performance."""
    metrics = calculate_metrics({})
    assert all(metrics[name] == 0.0 for name in ("cpm", "ctr", "cpc", "conversion_rate", "cpa", "roas"))


def test_global_and_combined_filters() -> None:
    """Filters combine by intersection; empty selections leave a dimension unfiltered."""
    dataset = generate_marketing_dataset()
    fact = dataset.daily_performance
    selected = fact.iloc[0]
    criteria = FilterCriteria(
        start_date="2023-02-01",
        end_date="2023-02-28",
        data_source_ids=[selected.data_source_id],
        channel_ids=[selected.channel_id],
        campaign_ids=[selected.campaign_id],
        ad_set_ids=[selected.ad_set_id],
    )
    filtered = filter_daily_performance(fact, criteria)
    assert len(filtered) == 28
    assert filtered["campaign_id"].eq(selected.campaign_id).all()
    assert filtered["ad_set_id"].eq(selected.ad_set_id).all()
    assert filter_daily_performance(fact, FilterCriteria(channel_ids=[])).equals(fact)


def test_previous_equivalent_period_and_variation() -> None:
    """A selected period compares to the immediately preceding same-length period."""
    fact = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]),
        "spend": [10.0, 10.0, 20.0, 20.0], "impressions": [100, 100, 200, 200],
        "clicks": [10, 10, 20, 20], "video_views": [0, 0, 0, 0],
        "conversions": [1, 1, 2, 2], "revenue": [20.0, 20.0, 40.0, 40.0],
        "data_source_id": ["DS001"] * 4, "channel_id": ["CH001"] * 4,
        "campaign_id": ["CP001"] * 4, "ad_set_id": ["AS0001"] * 4,
    })
    criteria = FilterCriteria(start_date="2023-01-03", end_date="2023-01-04")
    current = filter_daily_performance(fact, criteria)
    previous = previous_equivalent_period(fact, criteria)
    assert previous["date"].tolist() == pd.to_datetime(["2023-01-01", "2023-01-02"]).tolist()
    kpis = build_kpi_summary(current, previous).set_index("metric")
    assert kpis.loc["spend", "variation_pct"] == 100.0


def test_dashboard_aggregations_and_monthly_grouping() -> None:
    """Dashboard datasets contain expected grouping columns and aggregate totals."""
    dataset = generate_marketing_dataset()
    criteria = FilterCriteria(start_date="2023-01-01", end_date="2023-03-31")
    dashboard = build_dashboard_aggregations(dataset, criteria)
    filtered = filter_daily_performance(dataset.daily_performance, criteria)
    assert dashboard.kpis.set_index("metric").loc["spend", "value"] == pytest.approx(filtered["spend"].sum())
    assert {"channel_name", "spend", "ctr", "spend_variation_pct"}.issubset(dashboard.channel_performance.columns)
    assert {"data_source_name", "roas"}.issubset(dashboard.data_source_performance.columns)
    assert {"campaign_name", "conversion_rate"}.issubset(dashboard.campaign_performance.columns)
    assert set(dashboard.monthly_channel_trends["month"].dt.month) == {1, 2, 3}
    assert dashboard.monthly_channel_trends["spend"].sum() == pytest.approx(filtered["spend"].sum())
