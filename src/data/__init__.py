"""Data entities, generation, and loading utilities."""

from src.data.generator import generate_marketing_dataset
from src.data.models import MarketingDataset

__all__ = ["MarketingDataset", "generate_marketing_dataset"]
