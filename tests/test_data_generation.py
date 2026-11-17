"""Tests for the relational synthetic marketing data model."""

import pandas as pd
from pandas.testing import assert_frame_equal

from src.config import SyntheticDataConfig
from src.data.generator import generate_marketing_dataset


def test_generation_is_deterministic() -> None:
    """An identical seed and configuration must return identical tables."""
    first = generate_marketing_dataset(SyntheticDataConfig(seed=44))
    second = generate_marketing_dataset(SyntheticDataConfig(seed=44))
    for table in ("data_sources", "channels", "campaigns", "ad_sets", "daily_performance"):
        assert_frame_equal(getattr(first, table), getattr(second, table))


def test_referential_integrity() -> None:
    """Every dimension and fact foreign key must resolve to a valid parent."""
    dataset = generate_marketing_dataset()
    assert set(dataset.campaigns["data_source_id"]).issubset(set(dataset.data_sources["data_source_id"]))
    assert set(dataset.campaigns["channel_id"]).issubset(set(dataset.channels["channel_id"]))
    assert set(dataset.ad_sets["campaign_id"]).issubset(set(dataset.campaigns["campaign_id"]))
    fact = dataset.daily_performance
    assert set(fact["ad_set_id"]).issubset(set(dataset.ad_sets["ad_set_id"]))
    assert set(fact["campaign_id"]).issubset(set(dataset.campaigns["campaign_id"]))
    assert set(fact["data_source_id"]).issubset(set(dataset.data_sources["data_source_id"]))
    assert set(fact["channel_id"]).issubset(set(dataset.channels["channel_id"]))
    campaign_keys = dataset.campaigns.set_index("campaign_id")[["data_source_id", "channel_id"]]
    resolved = fact.join(campaign_keys, on="campaign_id", rsuffix="_dimension")
    assert (resolved["data_source_id"] == resolved["data_source_id_dimension"]).all()
    assert (resolved["channel_id"] == resolved["channel_id_dimension"]).all()


def test_data_consistency_and_numeric_ranges() -> None:
    """Funnel stages and financial metrics must remain mathematically valid."""
    fact = generate_marketing_dataset().daily_performance
    assert (fact["impressions"] >= 0).all()
    assert (fact["clicks"] >= 0).all()
    assert (fact["video_views"] >= 0).all()
    assert (fact["conversions"] >= 0).all()
    assert (fact["spend"] >= 0).all()
    assert (fact["revenue"] >= 0).all()
    assert (fact["clicks"] <= fact["impressions"]).all()
    assert (fact["video_views"] <= fact["impressions"]).all()
    assert (fact["conversions"] <= fact["clicks"]).all()
    assert fact[["impressions", "clicks", "video_views", "spend", "conversions", "revenue"]].notna().all().all()


def test_full_2023_date_coverage() -> None:
    """Every 2023 calendar day must be represented in the fact table."""
    fact = generate_marketing_dataset().daily_performance
    expected = pd.date_range("2023-01-01", "2023-12-31", freq="D")
    assert fact["date"].min() == expected.min()
    assert fact["date"].max() == expected.max()
    assert set(expected).issubset(set(fact["date"]))


def test_required_channel_and_source_coverage() -> None:
    """All mandated channels and data sources must appear in the dimensions and facts."""
    dataset = generate_marketing_dataset()
    assert set(dataset.channels["channel_name"]) == {"Programmatic", "Paid Search", "Paid Social", "Organic"}
    assert set(dataset.data_sources["data_source_name"]) == {
        "Amazon Ad Server", "StackAdapt", "LinkedIn Ads", "Facebook",
        "Google Display & Video 360", "Bing Ads", "Google Search Ads 360",
    }
    assert set(dataset.channels["channel_id"]).issubset(set(dataset.daily_performance["channel_id"]))
    assert set(dataset.data_sources["data_source_id"]).issubset(set(dataset.daily_performance["data_source_id"]))


def test_organic_campaigns_have_no_advertising_spend() -> None:
    """Organic records must have zero spend while retaining measurable traffic."""
    dataset = generate_marketing_dataset()
    organic_id = dataset.channels.loc[dataset.channels["channel_name"] == "Organic", "channel_id"].iloc[0]
    organic_fact = dataset.daily_performance.loc[dataset.daily_performance["channel_id"] == organic_id]
    assert not organic_fact.empty
    assert (organic_fact["spend"] == 0).all()
    assert organic_fact["impressions"].sum() > 0
