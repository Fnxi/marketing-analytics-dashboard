"""Cached data-loading boundary for consumers of the synthetic dataset."""

from functools import lru_cache

from src.config import SyntheticDataConfig
from src.data.generator import generate_marketing_dataset
from src.data.models import MarketingDataset


@lru_cache(maxsize=8)
def load_marketing_dataset(config: SyntheticDataConfig = SyntheticDataConfig()) -> MarketingDataset:
    """Generate and cache the dataset for a given immutable configuration."""
    return generate_marketing_dataset(config)
