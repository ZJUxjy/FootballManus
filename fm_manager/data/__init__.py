"""Data module for FM Manager."""

from fm_manager.data.fetcher import (
    FootballDataAPI,
    APIFootballClient,
    DataFetcher,
    fetch_sample_data,
)
from fm_manager.data.importer import DataImporter
from fm_manager.data.generators import (
    PlayerGenerator,
    generate_youth_player,
    calculate_market_value,
)

__all__ = [
    # Fetchers
    "FootballDataAPI",
    "APIFootballClient",
    "DataFetcher",
    "fetch_sample_data",
    # Importer
    "DataImporter",
    # Generators
    "PlayerGenerator",
    "generate_youth_player",
    "calculate_market_value",
]
