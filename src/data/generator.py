"""Deterministic generator for realistic marketing performance data."""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from src.config import SyntheticDataConfig
from src.data.models import MarketingDataset


DATA_SOURCES: Final[tuple[tuple[str, str], ...]] = (
    ("DS001", "Amazon Ad Server"),
    ("DS002", "StackAdapt"),
    ("DS003", "LinkedIn Ads"),
    ("DS004", "Facebook"),
    ("DS005", "Google Display & Video 360"),
    ("DS006", "Bing Ads"),
    ("DS007", "Google Search Ads 360"),
)

CHANNELS: Final[tuple[tuple[str, str], ...]] = (
    ("CH001", "Programmatic"),
    ("CH002", "Paid Search"),
    ("CH003", "Paid Social"),
    ("CH004", "Organic"),
)

# Each data source receives campaigns across a plausible primary channel. The
# final source also includes organic reporting, which intentionally has no media cost.
SOURCE_CHANNELS: Final[dict[str, tuple[str, ...]]] = {
    "DS001": ("CH001",),
    "DS002": ("CH001",),
    "DS003": ("CH003",),
    "DS004": ("CH003",),
    "DS005": ("CH001",),
    "DS006": ("CH002",),
    "DS007": ("CH002", "CH004"),
}

CHANNEL_PROFILES: Final[dict[str, dict[str, float]]] = {
    "Programmatic": {"daily_budget": 950.0, "cpm": 12.0, "ctr": 0.0045, "cvr": 0.025, "aov": 165.0, "view_rate": 0.32},
    "Paid Search": {"daily_budget": 1_250.0, "cpm": 28.0, "ctr": 0.045, "cvr": 0.072, "aov": 210.0, "view_rate": 0.01},
    "Paid Social": {"daily_budget": 1_050.0, "cpm": 15.0, "ctr": 0.011, "cvr": 0.035, "aov": 145.0, "view_rate": 0.20},
    "Organic": {"daily_budget": 0.0, "cpm": 0.0, "ctr": 0.028, "cvr": 0.055, "aov": 190.0, "view_rate": 0.06},
}

CAMPAIGN_THEMES: Final[tuple[str, ...]] = (
    "Brand Growth", "Q1 Acquisition", "Always On", "Retargeting", "Product Launch",
    "Audience Expansion", "Holiday Preview", "Lead Generation", "Conversion Drive",
)
AD_SET_AUDIENCES: Final[tuple[str, ...]] = (
    "Prospecting", "Remarketing", "High Intent", "Lookalike", "In-Market", "Returning Visitors",
)


def _seasonality_factor(day: pd.Timestamp) -> float:
    """Return a deterministic annual demand multiplier for a calendar day."""
    # Mild summer softness plus a pronounced year-end demand period.
    day_of_year = day.dayofyear
    annual_wave = 1.0 + 0.10 * np.sin(2 * np.pi * (day_of_year - 20) / 365)
    holiday_lift = 1.32 if day.month in (11, 12) else 1.0
    return annual_wave * holiday_lift


def _weekday_factor(day: pd.Timestamp, channel_name: str) -> float:
    """Return channel-sensitive weekday/weekend activity adjustment."""
    if day.weekday() < 5:
        return 1.06 if channel_name in {"Paid Search", "Programmatic"} else 1.02
    return 0.62 if channel_name in {"Paid Search", "Programmatic"} else 0.86


def _build_dimensions(config: SyntheticDataConfig, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create source, channel, campaign, and ad set dimensions with valid keys."""
    data_sources = pd.DataFrame(DATA_SOURCES, columns=["data_source_id", "data_source_name"])
    channels = pd.DataFrame(CHANNELS, columns=["channel_id", "channel_name"])
    channel_names = dict(CHANNELS)
    campaigns: list[dict[str, str]] = []
    ad_sets: list[dict[str, str]] = []
    campaign_number = 1
    ad_set_number = 1

    for source_id, source_name in DATA_SOURCES:
        allowed_channels = SOURCE_CHANNELS[source_id]
        for index in range(config.campaigns_per_source):
            channel_id = allowed_channels[index % len(allowed_channels)]
            campaign_id = f"CP{campaign_number:03d}"
            theme = CAMPAIGN_THEMES[(campaign_number - 1) % len(CAMPAIGN_THEMES)]
            campaigns.append({
                "campaign_id": campaign_id,
                "campaign_name": f"{source_name} | {theme}",
                "data_source_id": source_id,
                "channel_id": channel_id,
            })
            ad_set_count = int(rng.integers(config.min_ad_sets_per_campaign, config.max_ad_sets_per_campaign + 1))
            for audience_index in range(ad_set_count):
                ad_sets.append({
                    "ad_set_id": f"AS{ad_set_number:04d}",
                    "ad_set_name": f"{channel_names[channel_id]} - {AD_SET_AUDIENCES[(campaign_number + audience_index) % len(AD_SET_AUDIENCES)]}",
                    "campaign_id": campaign_id,
                })
                ad_set_number += 1
            campaign_number += 1

    return data_sources, channels, pd.DataFrame(campaigns), pd.DataFrame(ad_sets)


def _generate_daily_performance(
    config: SyntheticDataConfig,
    campaigns: pd.DataFrame,
    ad_sets: pd.DataFrame,
    channels: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate daily fact records by deriving funnel stages in valid order."""
    channel_lookup = channels.set_index("channel_id")["channel_name"].to_dict()
    campaign_ad_sets = ad_sets.groupby("campaign_id")["ad_set_id"].apply(list).to_dict()
    dates = pd.date_range(config.start_date, config.end_date, freq="D")
    rows: list[dict[str, object]] = []

    for campaign in campaigns.itertuples(index=False):
        channel_name = channel_lookup[campaign.channel_id]
        profile = CHANNEL_PROFILES[channel_name]
        # Campaign-level multipliers establish persistent performance differences.
        budget_multiplier = float(rng.uniform(0.65, 1.55))
        ctr_multiplier = float(rng.uniform(0.75, 1.30))
        cvr_multiplier = float(rng.uniform(0.70, 1.35))
        aov_multiplier = float(rng.uniform(0.80, 1.25))
        campaign_ad_set_ids = campaign_ad_sets[campaign.campaign_id]
        ad_set_weights = rng.dirichlet(np.ones(len(campaign_ad_set_ids)) * 2.0)

        for day in dates:
            volume_factor = _seasonality_factor(day) * _weekday_factor(day, channel_name)
            day_noise = float(rng.lognormal(mean=0.0, sigma=0.13))
            for ad_set_id, ad_set_weight in zip(campaign_ad_set_ids, ad_set_weights, strict=True):
                ad_set_multiplier = float(rng.uniform(0.88, 1.12))
                if channel_name == "Organic":
                    impressions = int(max(0, round(38_000 * budget_multiplier * ad_set_weight * volume_factor * day_noise * ad_set_multiplier)))
                    spend = 0.0
                else:
                    spend = max(0.0, profile["daily_budget"] * budget_multiplier * ad_set_weight * volume_factor * day_noise * ad_set_multiplier)
                    cpm = max(0.5, profile["cpm"] * rng.normal(1.0, 0.08))
                    impressions = int(max(0, round(spend * 1_000 / cpm)))

                ctr = float(np.clip(profile["ctr"] * ctr_multiplier * rng.normal(1.0, 0.10), 0.0001, 0.25))
                video_views = int(rng.binomial(impressions, profile["view_rate"]))
                clicks = int(rng.binomial(impressions, ctr))
                conversion_rate = float(np.clip(profile["cvr"] * cvr_multiplier * rng.normal(1.0, 0.10), 0.0001, 0.50))
                conversions = int(rng.binomial(clicks, conversion_rate))
                average_order_value = max(1.0, profile["aov"] * aov_multiplier * rng.normal(1.0, 0.06))
                revenue = round(conversions * average_order_value, 2)
                rows.append({
                    "date": day,
                    "data_source_id": campaign.data_source_id,
                    "channel_id": campaign.channel_id,
                    "campaign_id": campaign.campaign_id,
                    "ad_set_id": ad_set_id,
                    "impressions": impressions,
                    "clicks": clicks,
                    "video_views": video_views,
                    "spend": round(spend, 2),
                    "conversions": conversions,
                    "revenue": revenue,
                })
    return pd.DataFrame(rows)


def generate_marketing_dataset(config: SyntheticDataConfig | None = None) -> MarketingDataset:
    """Return a reproducible, referentially valid synthetic marketing dataset.

    Parameters
    ----------
    config:
        Generation options. Defaults to the 2023 reporting period and seed 2023.
    """
    active_config = config or SyntheticDataConfig()
    rng = np.random.default_rng(active_config.seed)
    data_sources, channels, campaigns, ad_sets = _build_dimensions(active_config, rng)
    daily_performance = _generate_daily_performance(active_config, campaigns, ad_sets, channels, rng)
    return MarketingDataset(data_sources, channels, campaigns, ad_sets, daily_performance)
