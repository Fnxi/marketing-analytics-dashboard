"""Dashboard-ready analytics aggregations and period comparisons."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.analytics.filters import FilterCriteria, filter_daily_performance, previous_equivalent_period
from src.analytics.metrics import BASE_METRICS, add_derived_metrics, calculate_metrics, safe_divide
from src.data.models import MarketingDataset


DERIVED_METRICS = ("cpm", "ctr", "cpc", "conversion_rate", "cpa", "roas")
ALL_METRICS = BASE_METRICS + DERIVED_METRICS


@dataclass(frozen=True)
class DashboardAggregations:
    """The datasets required by the dashboard's analytics components."""

    kpis: pd.DataFrame
    channel_performance: pd.DataFrame
    data_source_performance: pd.DataFrame
    campaign_performance: pd.DataFrame
    monthly_channel_trends: pd.DataFrame


def _aggregate(fact: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    """Sum base metrics and calculate ratios at the requested reporting grain."""
    if fact.empty:
        return pd.DataFrame(columns=group_columns + list(ALL_METRICS))
    return add_derived_metrics(fact.groupby(group_columns, as_index=False)[list(BASE_METRICS)].sum())


def _add_variations(current: pd.DataFrame, previous: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    """Append prior-period metric values and percentage changes to current rows."""
    previous_columns = group_columns + list(ALL_METRICS)
    renamed_previous = previous.loc[:, previous_columns].rename(columns={metric: f"previous_{metric}" for metric in ALL_METRICS})
    result = current.merge(renamed_previous, on=group_columns, how="left")
    for metric in ALL_METRICS:
        prior_column = f"previous_{metric}"
        result[prior_column] = pd.to_numeric(result[prior_column], errors="coerce").fillna(0.0)
        result[f"{metric}_variation_pct"] = result.apply(
            lambda row: safe_divide(row[metric] - row[prior_column], row[prior_column], 100), axis=1
        )
    return result


def build_kpi_summary(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    """Create a KPI-card dataset with current, prior, and percentage variation."""
    current_metrics = calculate_metrics(current)
    previous_metrics = calculate_metrics(previous)
    return pd.DataFrame([
        {
            "metric": metric,
            "value": current_metrics[metric],
            "previous_value": previous_metrics[metric],
            "variation_pct": safe_divide(
                current_metrics[metric] - previous_metrics[metric], previous_metrics[metric], 100
            ),
        }
        for metric in ALL_METRICS
    ])


def _performance_table(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    dimension: pd.DataFrame,
    id_column: str,
    name_column: str,
) -> pd.DataFrame:
    """Build a named dimension performance table and its period variations."""
    group_columns = [id_column]
    current_grouped = _aggregate(current, group_columns)
    previous_grouped = _aggregate(previous, group_columns)
    comparison = _add_variations(current_grouped, previous_grouped, group_columns)
    return comparison.merge(dimension[[id_column, name_column]], on=id_column, how="left").sort_values("spend", ascending=False).reset_index(drop=True)


def build_monthly_channel_trends(current: pd.DataFrame, channels: pd.DataFrame) -> pd.DataFrame:
    """Aggregate selected daily facts by calendar month and channel."""
    monthly = current.copy()
    monthly["month"] = pd.to_datetime(monthly["date"]).dt.to_period("M").dt.to_timestamp()
    result = _aggregate(monthly, ["month", "channel_id"])
    return result.merge(channels[["channel_id", "channel_name"]], on="channel_id", how="left").sort_values(["month", "channel_name"]).reset_index(drop=True)


def build_daily_metric_trends(current: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily metrics for KPI sparklines without averaging ratios."""
    return _aggregate(current, ["date"]).sort_values("date").reset_index(drop=True)


def build_dashboard_aggregations(dataset: MarketingDataset, criteria: FilterCriteria | None = None) -> DashboardAggregations:
    """Build every Phase 3 dashboard dataset from one shared filter selection."""
    current = filter_daily_performance(dataset.daily_performance, criteria)
    previous = previous_equivalent_period(dataset.daily_performance, criteria)
    campaign_performance = _performance_table(current, previous, dataset.campaigns, "campaign_id", "campaign_name")
    campaign_performance = campaign_performance.merge(
        dataset.campaigns[["campaign_id", "channel_id"]], on="campaign_id", how="left"
    ).merge(dataset.channels[["channel_id", "channel_name"]], on="channel_id", how="left")
    return DashboardAggregations(
        kpis=build_kpi_summary(current, previous),
        channel_performance=_performance_table(current, previous, dataset.channels, "channel_id", "channel_name"),
        data_source_performance=_performance_table(current, previous, dataset.data_sources, "data_source_id", "data_source_name"),
        campaign_performance=campaign_performance,
        monthly_channel_trends=build_monthly_channel_trends(current, dataset.channels),
    )
