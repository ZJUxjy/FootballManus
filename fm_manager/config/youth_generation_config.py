"""Youth Generation Configuration System.

This module provides comprehensive configuration for youth player generation,
including country-specific pool sizes, filtering parameters, generation settings,
and export configurations.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import yaml
import os


class ExportFormat(Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"
    SQLITE = "sqlite"


@dataclass
class CountryYouthConfig:
    """Configuration for a country's youth generation.

    Attributes:
        name: Full country name
        pool_size: Annual youth pool size (number of youth players generated)
        youth_rating: Quality multiplier (1-200, based on FM youth ratings)
        attribute_modifiers: Country-specific attribute biases (e.g., {"pace": 5, "technique": -3})
    """

    name: str
    pool_size: int
    youth_rating: int = 100
    attribute_modifiers: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration values."""
        if self.pool_size < 0:
            raise ValueError(f"Pool size must be non-negative, got {self.pool_size}")
        if not 1 <= self.youth_rating <= 200:
            raise ValueError(f"Youth rating must be between 1-200, got {self.youth_rating}")


@dataclass
class FilteringConfig:
    """Configuration for filtering youth players.

    Attributes:
        ca_percentile: Top percentile by CA to keep (0.0-1.0)
        pa_percentile: Top percentile by PA to keep from remaining (0.0-1.0)
        min_players_per_country: Minimum players to retain per country
        ca_pa_ratio_min: Minimum CA/PA ratio (CA must be >= this ratio * PA)
    """

    ca_percentile: float = 0.1
    pa_percentile: float = 0.2
    min_players_per_country: int = 1000
    ca_pa_ratio_min: float = 0.4

    def __post_init__(self):
        """Validate filtering configuration."""
        if not 0.0 < self.ca_percentile <= 1.0:
            raise ValueError(f"CA percentile must be between 0.0-1.0, got {self.ca_percentile}")
        if not 0.0 < self.pa_percentile <= 1.0:
            raise ValueError(f"PA percentile must be between 0.0-1.0, got {self.pa_percentile}")
        if self.min_players_per_country < 0:
            raise ValueError(
                f"Min players must be non-negative, got {self.min_players_per_country}"
            )
        if not 0.0 <= self.ca_pa_ratio_min <= 1.0:
            raise ValueError(f"CA/PA ratio must be between 0.0-1.0, got {self.ca_pa_ratio_min}")


@dataclass
class DistributionParams:
    """Parameters for a normal distribution.

    Attributes:
        mean: Distribution mean (μ)
        std: Standard deviation (σ)
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    """

    mean: float
    std: float
    min_val: float
    max_val: float

    def __post_init__(self):
        """Validate distribution parameters."""
        if self.std < 0:
            raise ValueError(f"Standard deviation must be non-negative, got {self.std}")
        if self.min_val >= self.max_val:
            raise ValueError(f"Min value must be less than max value")


@dataclass
class GenerationParams:
    """Parameters for youth player generation.

    Attributes:
        age: Age distribution parameters (μ=16, σ=2, range 14-21)
        ca: Current Ability distribution (μ=40, σ=15, range 0-100)
        pa: Potential Ability distribution (μ=60, σ=20, range 0-200)
    """

    age: DistributionParams = field(
        default_factory=lambda: DistributionParams(mean=16.0, std=2.0, min_val=14.0, max_val=21.0)
    )
    ca: DistributionParams = field(
        default_factory=lambda: DistributionParams(mean=40.0, std=15.0, min_val=0.0, max_val=100.0)
    )
    pa: DistributionParams = field(
        default_factory=lambda: DistributionParams(mean=60.0, std=20.0, min_val=0.0, max_val=200.0)
    )


@dataclass
class ExportConfig:
    """Configuration for exporting youth players.

    Attributes:
        formats: List of supported export formats
        batch_size: Number of players per export batch
        output_dir: Directory for output files
        compression: Whether to use gzip compression for JSON/CSV exports
    """

    formats: List[ExportFormat] = field(
        default_factory=lambda: [ExportFormat.JSON, ExportFormat.CSV, ExportFormat.SQLITE]
    )
    batch_size: int = 10000
    output_dir: str = "data/youth_players/"
    compression: bool = False

    def __post_init__(self):
        """Validate export configuration."""
        if self.batch_size <= 0:
            raise ValueError(f"Batch size must be positive, got {self.batch_size}")
        if not self.output_dir:
            raise ValueError("Output directory cannot be empty")


@dataclass
class YouthGenerationConfig:
    """Complete youth generation configuration.

    This is the main configuration class that aggregates all youth generation
    settings including country configurations, filtering rules, generation
    parameters, and export settings.

    Attributes:
        countries: Dictionary mapping country codes to CountryYouthConfig
        filtering: Filtering parameters for player selection
        generation: Distribution parameters for player attributes
        export: Export configuration settings
    """

    countries: Dict[str, CountryYouthConfig] = field(default_factory=dict)
    filtering: FilteringConfig = field(default_factory=FilteringConfig)
    generation: GenerationParams = field(default_factory=GenerationParams)
    export: ExportConfig = field(default_factory=ExportConfig)

    @classmethod
    def load(cls, yaml_path: Optional[str] = None) -> "YouthGenerationConfig":
        """Load configuration from YAML file.

        Args:
            yaml_path: Path to YAML config file. If None, uses default path.

        Returns:
            YouthGenerationConfig instance loaded from YAML

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML contains invalid configuration
        """
        if yaml_path is None:
            # Default path relative to this file
            config_dir = os.path.dirname(os.path.abspath(__file__))
            yaml_path = os.path.join(os.path.dirname(config_dir), "config", "youth_generation.yaml")

        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YouthGenerationConfig":
        """Create configuration from dictionary.

        Args:
            data: Dictionary containing configuration values

        Returns:
            YouthGenerationConfig instance
        """
        # Parse countries
        countries = {}
        if "countries" in data:
            for code, country_data in data["countries"].items():
                countries[code] = CountryYouthConfig(
                    name=country_data["name"],
                    pool_size=country_data["pool_size"],
                    youth_rating=country_data.get("youth_rating", 100),
                    attribute_modifiers=country_data.get("attribute_modifiers", {}),
                )

        # Parse filtering config
        filtering = FilteringConfig()
        if "filtering" in data:
            filtering = FilteringConfig(**data["filtering"])

        # Parse generation params
        generation = GenerationParams()
        if "generation" in data:
            gen_data = data["generation"]
            if "age" in gen_data:
                generation.age = DistributionParams(**gen_data["age"])
            if "ca" in gen_data:
                generation.ca = DistributionParams(**gen_data["ca"])
            if "pa" in gen_data:
                generation.pa = DistributionParams(**gen_data["pa"])

        # Parse export config
        export = ExportConfig()
        if "export" in data:
            export_data = data["export"]
            if "formats" in export_data:
                export.formats = [ExportFormat(f) for f in export_data["formats"]]
            if "batch_size" in export_data:
                export.batch_size = export_data["batch_size"]
            if "output_dir" in export_data:
                export.output_dir = export_data["output_dir"]

        return cls(countries=countries, filtering=filtering, generation=generation, export=export)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "countries": {
                code: {
                    "name": c.name,
                    "pool_size": c.pool_size,
                    "youth_rating": c.youth_rating,
                    "attribute_modifiers": c.attribute_modifiers,
                }
                for code, c in self.countries.items()
            },
            "filtering": {
                "ca_percentile": self.filtering.ca_percentile,
                "pa_percentile": self.filtering.pa_percentile,
                "min_players_per_country": self.filtering.min_players_per_country,
                "ca_pa_ratio_min": self.filtering.ca_pa_ratio_min,
            },
            "generation": {
                "age": {
                    "mean": self.generation.age.mean,
                    "std": self.generation.age.std,
                    "min_val": self.generation.age.min_val,
                    "max_val": self.generation.age.max_val,
                },
                "ca": {
                    "mean": self.generation.ca.mean,
                    "std": self.generation.ca.std,
                    "min_val": self.generation.ca.min_val,
                    "max_val": self.generation.ca.max_val,
                },
                "pa": {
                    "mean": self.generation.pa.mean,
                    "std": self.generation.pa.std,
                    "min_val": self.generation.pa.min_val,
                    "max_val": self.generation.pa.max_val,
                },
            },
            "export": {
                "formats": [f.value for f in self.export.formats],
                "batch_size": self.export.batch_size,
                "output_dir": self.export.output_dir,
            },
        }

    def save(self, yaml_path: str) -> None:
        """Save configuration to YAML file.

        Args:
            yaml_path: Path to save YAML file
        """
        data = self.to_dict()

        # Ensure directory exists
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def get_country(self, code: str) -> Optional[CountryYouthConfig]:
        """Get configuration for a specific country.

        Args:
            code: Country code (e.g., 'ENG', 'BRA')

        Returns:
            Country configuration or None if not found
        """
        return self.countries.get(code)

    def get_total_pool_size(self) -> int:
        """Get total youth pool size across all countries.

        Returns:
            Sum of all country pool sizes
        """
        return sum(c.pool_size for c in self.countries.values())

    def validate(self) -> List[str]:
        """Validate complete configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check countries
        if not self.countries:
            errors.append("No countries configured")

        for code, country in self.countries.items():
            if country.pool_size < 1000:
                errors.append(f"Country {code} pool size ({country.pool_size}) seems too low")

        # Check filtering
        if self.filtering.ca_percentile * self.filtering.pa_percentile < 0.001:
            errors.append("Filtering percentiles too restrictive (< 0.1% total retention)")

        return errors


def create_default_config() -> YouthGenerationConfig:
    """Create default youth generation configuration with 40+ countries.

    Returns:
        YouthGenerationConfig with default country settings
    """
    # Major football nations (top tier)
    major_nations = {
        # Country Code: (Name, Pool Size, Youth Rating, Attribute Modifiers)
        "ENG": ("England", 2_000_000, 145, {"work_rate": 3, "determination": 2}),
        "ESP": ("Spain", 1_500_000, 140, {"technique": 4, "passing": 3, "vision": 2}),
        "GER": ("Germany", 1_500_000, 142, {"tactical_awareness": 3, "work_rate": 2}),
        "FRA": ("France", 1_400_000, 145, {"pace": 3, "athleticism": 3, "technique": 2}),
        "ITA": (
            "Italy",
            1_300_000,
            138,
            {"tactical_awareness": 4, "positioning": 3, "defending": 2},
        ),
        "BRA": ("Brazil", 2_000_000, 150, {"technique": 5, "flair": 4, "dribbling": 3}),
        "ARG": ("Argentina", 1_200_000, 145, {"technique": 4, "flair": 3, "vision": 2}),
    }

    # Secondary football nations (strong youth systems)
    secondary_nations = {
        "NED": (
            "Netherlands",
            800_000,
            135,
            {"technique": 3, "vision": 2, "tactical_awareness": 2},
        ),
        "POR": ("Portugal", 700_000, 135, {"technique": 3, "flair": 2}),
        "BEL": ("Belgium", 500_000, 130, {"technique": 3, "tactical_awareness": 2}),
        "URU": ("Uruguay", 400_000, 132, {"determination": 3, "work_rate": 2, "toughness": 2}),
        "CRO": ("Croatia", 350_000, 128, {"technique": 3, "vision": 2}),
        "DEN": ("Denmark", 350_000, 125, {"work_rate": 3, "teamwork": 2}),
        "SUI": ("Switzerland", 320_000, 120, {"tactical_awareness": 2, "work_rate": 2}),
        "AUT": ("Austria", 300_000, 118, {"work_rate": 2, "tactical_awareness": 1}),
        "SWE": ("Sweden", 350_000, 115, {"physical": 2, "aerial": 2}),
        "NOR": ("Norway", 300_000, 115, {"physical": 3, "aerial": 2}),
        "POL": ("Poland", 600_000, 118, {"finishing": 2, "physical": 1}),
        "UKR": ("Ukraine", 550_000, 115, {"technique": 2, "physical": 1}),
        "RUS": ("Russia", 900_000, 110, {"physical": 2, "aerial": 2}),
        "TUR": ("Turkey", 800_000, 112, {"technique": 2, "flair": 1}),
        "SRB": ("Serbia", 400_000, 118, {"technique": 2, "physical": 1}),
        "CZE": ("Czech Republic", 380_000, 115, {"tactical_awareness": 2, "work_rate": 1}),
        "GRE": ("Greece", 350_000, 110, {"tactical_awareness": 2, "defending": 1}),
        "SCO": ("Scotland", 400_000, 112, {"determination": 2, "work_rate": 1}),
        "WAL": ("Wales", 200_000, 110, {"physical": 1, "pace": 1}),
    }

    # Growing/developing football nations
    developing_nations = {
        "USA": ("United States", 800_000, 115, {"athleticism": 3, "pace": 2, "physical": 2}),
        "MEX": ("Mexico", 1_000_000, 118, {"technique": 2, "flair": 1}),
        "JPN": ("Japan", 600_000, 120, {"work_rate": 3, "tactical_awareness": 2, "discipline": 2}),
        "KOR": ("South Korea", 500_000, 118, {"work_rate": 3, "pace": 2, "determination": 2}),
        "CHN": ("China", 200_000, 95, {"work_rate": 1}),
        "AUS": ("Australia", 350_000, 110, {"physical": 2, "aerial": 2}),
        "CAN": ("Canada", 280_000, 108, {"athleticism": 2, "pace": 1}),
        "IRN": ("Iran", 450_000, 105, {"physical": 2, "defending": 1}),
        "KSA": ("Saudi Arabia", 400_000, 100, {"technique": 1}),
        "QAT": ("Qatar", 80_000, 95, {"technique": 1}),
        "UAE": ("UAE", 100_000, 92, {}),
        "EGY": ("Egypt", 700_000, 108, {"technique": 2, "flair": 1}),
        "MAR": ("Morocco", 450_000, 110, {"technique": 2, "flair": 1}),
        "TUN": ("Tunisia", 300_000, 105, {"tactical_awareness": 1}),
        "NGA": ("Nigeria", 800_000, 115, {"pace": 4, "athleticism": 3, "physical": 2}),
        "CMR": ("Cameroon", 350_000, 110, {"physical": 3, "pace": 2}),
        "GHA": ("Ghana", 400_000, 108, {"physical": 2, "pace": 1}),
        "CIV": ("Ivory Coast", 380_000, 110, {"physical": 2, "pace": 2}),
        "SEN": ("Senegal", 320_000, 112, {"physical": 3, "pace": 2}),
        "ALG": ("Algeria", 350_000, 108, {"technique": 2}),
        "COL": ("Colombia", 600_000, 118, {"technique": 2, "flair": 1}),
        "CHI": ("Chile", 450_000, 115, {"work_rate": 2, "determination": 1}),
        "ECU": ("Ecuador", 380_000, 108, {"pace": 2, "physical": 1}),
        "PER": ("Peru", 350_000, 105, {"technique": 1}),
        "PAR": ("Paraguay", 300_000, 108, {"toughness": 2, "determination": 1}),
        "BOL": ("Bolivia", 200_000, 95, {"physical": 1}),
        "VEN": ("Venezuela", 350_000, 100, {"pace": 1}),
    }

    # Combine all nations
    all_nations = {}
    all_nations.update(major_nations)
    all_nations.update(secondary_nations)
    all_nations.update(developing_nations)

    # Create country configs
    countries = {}
    for code, (name, pool_size, rating, modifiers) in all_nations.items():
        countries[code] = CountryYouthConfig(
            name=name, pool_size=pool_size, youth_rating=rating, attribute_modifiers=modifiers
        )

    return YouthGenerationConfig(
        countries=countries,
        filtering=FilteringConfig(),
        generation=GenerationParams(),
        export=ExportConfig(),
    )


# Module-level singleton for easy access
_default_config: Optional[YouthGenerationConfig] = None


def get_default_config() -> YouthGenerationConfig:
    """Get the default configuration singleton.

    Returns:
        Default YouthGenerationConfig instance
    """
    global _default_config
    if _default_config is None:
        _default_config = create_default_config()
    return _default_config


def reload_config() -> YouthGenerationConfig:
    """Reload configuration from YAML or create defaults.

    Returns:
        YouthGenerationConfig instance
    """
    global _default_config
    try:
        _default_config = YouthGenerationConfig.load()
    except FileNotFoundError:
        _default_config = create_default_config()
    return _default_config
