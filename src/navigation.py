"""Navigation definitions and page-specific filter scope helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from src.analytics.filters import FilterCriteria


EXECUTIVE_SUMMARY = "Executive Summary"
CROSS_CHANNEL = "Cross Channel"
CHANNEL_PERFORMANCE = "Channel Performance"
CHANNEL_SEGMENTS = "Channel Segments & Trends"
PAID_SEARCH = "Paid Search"
PAID_SOCIAL = "Paid Social"
PROGRAMMATIC = "Programmatic"
SEARCH_ENGINE_OPT = "Search Engine Opt."
ORGANIC_SOCIAL = "Organic Social"
ECOMMERCE = "eCommerce"

ANALYTICS_VIEWS = (EXECUTIVE_SUMMARY, CROSS_CHANNEL, CHANNEL_PERFORMANCE, CHANNEL_SEGMENTS, PAID_SEARCH, PAID_SOCIAL, PROGRAMMATIC)
INFORMATIONAL_VIEWS = (SEARCH_ENGINE_OPT, ORGANIC_SOCIAL, ECOMMERCE)
CHANNEL_VIEW_NAMES = {
    PAID_SEARCH: "Paid Search",
    PAID_SOCIAL: "Paid Social",
    PROGRAMMATIC: "Programmatic",
}
_NO_MATCHING_CHANNEL_ID = "__no_matching_channel__"


def intersect_ids(selected_ids: Sequence[str] | None, scoped_ids: Sequence[str] | None) -> tuple[str, ...] | None:
    """Intersect an optional global selection with an optional page scope.

    An empty selection means all values, matching the global filter behavior.
    The return value preserves the global selection order when both are present.
    """
    selected = tuple(selected_ids or ())
    scoped = tuple(scoped_ids or ())
    if not scoped:
        return selected or None
    if not selected:
        return scoped
    scoped_set = set(scoped)
    return tuple(item for item in selected if item in scoped_set)


def apply_channel_scope(criteria: FilterCriteria, channel_ids: Sequence[str] | None) -> FilterCriteria:
    """Return criteria restricted to a page's channel scope without changing other filters."""
    intersected = intersect_ids(criteria.channel_ids, channel_ids)
    # Empty sequences normally mean "all" in FilterCriteria. Preserve an
    # incompatible intersection as an explicit non-existent ID instead.
    if criteria.channel_ids and channel_ids and not intersected:
        intersected = (_NO_MATCHING_CHANNEL_ID,)
    return replace(criteria, channel_ids=intersected)
