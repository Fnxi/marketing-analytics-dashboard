"""Central configuration for the synthetic marketing dataset."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SyntheticDataConfig:
    """Configuration controlling deterministic synthetic data generation."""

    seed: int = 2023
    start_date: date = date(2023, 1, 1)
    end_date: date = date(2023, 12, 31)
    campaigns_per_source: int = 3
    min_ad_sets_per_campaign: int = 2
    max_ad_sets_per_campaign: int = 4

    def __post_init__(self) -> None:
        """Validate configuration values that would make generation invalid."""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if self.campaigns_per_source < 1:
            raise ValueError("campaigns_per_source must be at least 1")
        if self.min_ad_sets_per_campaign < 1:
            raise ValueError("min_ad_sets_per_campaign must be at least 1")
        if self.min_ad_sets_per_campaign > self.max_ad_sets_per_campaign:
            raise ValueError("min_ad_sets_per_campaign cannot exceed max_ad_sets_per_campaign")
