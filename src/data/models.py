"""Typed containers for the marketing dimensional data model."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class MarketingDataset:
    """Relational dimension and fact tables used by the dashboard.

    Each attribute is a Pandas DataFrame. `daily_performance` is the fact table;
    the remaining attributes are its supporting dimensions.
    """

    data_sources: pd.DataFrame
    channels: pd.DataFrame
    campaigns: pd.DataFrame
    ad_sets: pd.DataFrame
    daily_performance: pd.DataFrame
