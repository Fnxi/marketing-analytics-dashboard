"""Tests for UI formatting helpers that do not require a Streamlit runtime."""

from src.components.formatters import format_metric, format_variation


def test_metric_formatting() -> None:
    """Currency, percentages, and compact values retain predictable formats."""
    assert format_metric(1_234.5, "spend") == "$1.2K"
    assert format_metric(1.234, "ctr") == "1.23%"
    assert format_metric(12_345, "impressions") == "12.3K"


def test_variation_formatting() -> None:
    """Percentage deltas include their direction."""
    assert format_variation(4.25) == "+4.2%"
    assert format_variation(-4.25) == "-4.2%"
