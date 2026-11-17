"""Reusable global filtering for the daily marketing fact table."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

import pandas as pd


DateLike = date | datetime | pd.Timestamp


@dataclass(frozen=True)
class FilterCriteria:
    """Optional global filters represented by dimension IDs.

    A missing or empty dimension selection means "all values". Date boundaries
    are inclusive; omitted boundaries use the available fact-table range.
    """

    start_date: DateLike | None = None
    end_date: DateLike | None = None
    data_source_ids: Sequence[str] | None = None
    channel_ids: Sequence[str] | None = None
    campaign_ids: Sequence[str] | None = None
    ad_set_ids: Sequence[str] | None = None


def filter_daily_performance(fact: pd.DataFrame, criteria: FilterCriteria | None = None) -> pd.DataFrame:
    """Apply all supplied global filters to one daily fact table.

    The returned DataFrame is a copy so downstream aggregations cannot mutate
    the source dataset. Empty dimension selections deliberately do not filter.
    """
    active = criteria or FilterCriteria()
    filtered = fact.copy()
    dates = pd.to_datetime(filtered["date"])
    if active.start_date is not None:
        filtered = filtered.loc[dates >= pd.Timestamp(active.start_date)]
        dates = pd.to_datetime(filtered["date"])
    if active.end_date is not None:
        filtered = filtered.loc[dates <= pd.Timestamp(active.end_date)]
    for column, selected_ids in (
        ("data_source_id", active.data_source_ids),
        ("channel_id", active.channel_ids),
        ("campaign_id", active.campaign_ids),
        ("ad_set_id", active.ad_set_ids),
    ):
        if selected_ids:
            filtered = filtered.loc[filtered[column].isin(selected_ids)]
    return filtered.copy()


def previous_equivalent_period(fact: pd.DataFrame, criteria: FilterCriteria | None = None) -> pd.DataFrame:
    """Return the filtered period immediately preceding the selected date range."""
    active = criteria or FilterCriteria()
    fact_dates = pd.to_datetime(fact["date"])
    start = pd.Timestamp(active.start_date) if active.start_date is not None else fact_dates.min()
    end = pd.Timestamp(active.end_date) if active.end_date is not None else fact_dates.max()
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    period_days = (end.normalize() - start.normalize()).days + 1
    previous_end = start.normalize() - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=period_days - 1)
    previous_criteria = FilterCriteria(
        start_date=previous_start,
        end_date=previous_end,
        data_source_ids=active.data_source_ids,
        channel_ids=active.channel_ids,
        campaign_ids=active.campaign_ids,
        ad_set_ids=active.ad_set_ids,
    )
    return filter_daily_performance(fact, previous_criteria)
