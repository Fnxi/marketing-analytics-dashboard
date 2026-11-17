"""Display-only formatting helpers for dashboard components."""

from __future__ import annotations

import math


def format_metric(value: float, metric: str) -> str:
    """Format one metric for compact dashboard display."""
    if metric in {"spend", "revenue", "cpm", "cpc", "cpa"}:
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:,.2f}"
    if metric in {"ctr", "conversion_rate"}:
        return f"{value:.2f}%"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def format_variation(value: float) -> str:
    """Format a percentage delta with an explicit direction."""
    return "—" if not math.isfinite(value) else f"{value:+.1f}%"
