"""Aggregate-first marketing metric calculations."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


BASE_METRICS = ("spend", "impressions", "clicks", "video_views", "conversions", "revenue")


def safe_divide(numerator: float, denominator: float, multiplier: float = 1.0) -> float:
    """Return a safe ratio, using zero when its denominator is zero."""
    return 0.0 if denominator == 0 else numerator / denominator * multiplier


def calculate_metrics(data: pd.DataFrame | Mapping[str, float]) -> dict[str, float]:
    """Calculate dashboard metrics from aggregated base values.

    Passing a DataFrame sums its base metric columns before calculating ratios;
    this prevents incorrect averaging of row-level ratios.
    """
    if isinstance(data, pd.DataFrame):
        totals = data.loc[:, BASE_METRICS].sum().to_dict()
    else:
        totals = {metric: float(data.get(metric, 0.0)) for metric in BASE_METRICS}
    spend = float(totals["spend"])
    impressions = float(totals["impressions"])
    clicks = float(totals["clicks"])
    conversions = float(totals["conversions"])
    revenue = float(totals["revenue"])
    return {
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "video_views": float(totals["video_views"]),
        "cpm": safe_divide(spend, impressions, 1_000),
        "ctr": safe_divide(clicks, impressions, 100),
        "cpc": safe_divide(spend, clicks),
        "conversions": conversions,
        "conversion_rate": safe_divide(conversions, clicks, 100),
        "cpa": safe_divide(spend, conversions),
        "revenue": revenue,
        "roas": safe_divide(revenue, spend),
    }


def add_derived_metrics(aggregated: pd.DataFrame) -> pd.DataFrame:
    """Add aggregate-first ratio columns to a grouped base-metrics table."""
    result = aggregated.copy()
    result["cpm"] = result.apply(lambda row: safe_divide(row.spend, row.impressions, 1_000), axis=1)
    result["ctr"] = result.apply(lambda row: safe_divide(row.clicks, row.impressions, 100), axis=1)
    result["cpc"] = result.apply(lambda row: safe_divide(row.spend, row.clicks), axis=1)
    result["conversion_rate"] = result.apply(lambda row: safe_divide(row.conversions, row.clicks, 100), axis=1)
    result["cpa"] = result.apply(lambda row: safe_divide(row.spend, row.conversions), axis=1)
    result["roas"] = result.apply(lambda row: safe_divide(row.revenue, row.spend), axis=1)
    return result
