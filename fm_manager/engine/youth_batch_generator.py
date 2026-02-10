"""High-performance youth batch generator with NumPy vectorization.

Generates millions of youth players per country efficiently using vectorized operations.
Supports batched processing for memory efficiency and real-time progress tracking.
"""

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np

from fm_manager.config.youth_generation_config import (
    CountryYouthConfig,
    YouthGenerationConfig,
)
from fm_manager.core.models.player import Position, Foot, WorkRate
from fm_manager.engine.player_generator import PlayerNameGenerator
from fm_manager.engine.youth_attribute_generator import YouthAttributeGenerator


@dataclass
class YouthPlayer:
    """Lightweight youth player dataclass for high-performance generation.
    
    Designed for in-memory generation with minimal overhead.
    Can be converted to full Player model when persisted.
    """

    # Basic info
    first_name: str
    last_name: str
    nationality: str
    birth_date: date
    
    # Position and abilities
    position: Position
    current_ability: int
    potential_ability: int
    
    # Attributes (dict for efficiency)
    attributes: Dict[str, int] = field(default_factory=dict)
    
    # Physical
    height: int = 175  # cm
    weight: int = 70  # kg
    preferred_foot: Foot = Foot.RIGHT
    
    @property
    def full_name(self) -> str:
        """Get player's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int:
        """Calculate player age from birth date."""
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    def to_player(self, player_id: Optional[int] = None, club_id: Optional[int] = None) -> "Player":
        """Convert to full Player model.
        
        Import here to avoid circular dependency.
        """
        from fm_manager.core.models.player import Player
        
        player = Player(
            id=player_id or 0,
            first_name=self.first_name,
            last_name=self.last_name,
            birth_date=self.birth_date,
            nationality=self.nationality,
            position=self.position,
            current_ability=self.current_ability,
            potential_ability=self.potential_ability,
            height=self.height,
            weight=self.weight,
            preferred_foot=self.preferred_foot,
            club_id=club_id,
            fitness=100,  # Youth always fresh
            form=50,
            morale=60,
        )
        
        # Set attributes
        for attr_name, value in self.attributes.items():
            if hasattr(player, attr_name):
                setattr(player, attr_name, value)
        
        return player


class CountryYouthGenerator:
    """Generate youth players for a specific country with NumPy vectorization."""
    
    # Position weights for realistic distribution (sums to 1.0)
    POSITION_WEIGHTS = {
        Position.GK: 0.08,
        Position.CB: 0.14,
        Position.LB: 0.07,
        Position.RB: 0.07,
        Position.LWB: 0.02,
        Position.RWB: 0.02,
        Position.CDM: 0.08,
        Position.CM: 0.15,
        Position.LM: 0.05,
        Position.RM: 0.05,
        Position.CAM: 0.08,
        Position.LW: 0.06,
        Position.RW: 0.06,
        Position.CF: 0.03,
        Position.ST: 0.10,
    }
    
    def __init__(
        self,
        country_code: str,
        country_config: CountryYouthConfig,
        attribute_generator: YouthAttributeGenerator,
        seed: Optional[int] = None,
    ):
        """Initialize country-specific generator.
        
        Args:
            country_code: Three-letter country code (e.g., 'ENG')
            country_config: Country configuration from YouthGenerationConfig
            attribute_generator: Attribute generator for detailed attributes
            seed: Random seed for reproducibility
        """
        self.country_code = country_code
        self.country_config = country_config
        self.attr_gen = attribute_generator
        self.name_gen = PlayerNameGenerator()
        self.np_rng = np.random.default_rng(seed)
        
        # Pre-calculate CA mean based on youth rating
        self.ca_mean = 40 + (country_config.youth_rating - 100) * 0.5
        self.ca_std = 12
        self.pa_mean = 60 + (country_config.youth_rating - 100) * 0.5
        self.pa_std = 20
        
        # Cache positions for weighted random sampling
        self.positions = list(self.POSITION_WEIGHTS.keys())
        self.position_probs = list(self.POSITION_WEIGHTS.values())
    
    def _generate_batch(
        self, batch_size: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate CA, PA, age for a batch using NumPy.
        
        Returns:
            Tuple of (ages, cas, pas) as numpy arrays
        """
        # Age: normal distribution around 16
        ages = self.np_rng.normal(16.0, 2.0, batch_size)
        ages = np.clip(ages, 14, 21)  # Clip first
        ages = np.round(ages).astype(np.int16)  # Then round and convert
        
        # CA: based on country youth rating
        cas = self.np_rng.normal(self.ca_mean, self.ca_std, batch_size)
        cas = np.clip(cas, 20, 100).astype(np.int16)
        
        # PA: independent but must be >= CA
        pas = self.np_rng.normal(self.pa_mean, self.pa_std, batch_size)
        pas = np.clip(pas, 30, 200).astype(np.int16)
        
        # Ensure PA > CA (at least 1.5x ratio for young players)
        min_pa = np.maximum(cas * 1.5, cas + 10)
        pas = np.maximum(pas, min_pa)
        pas = np.clip(pas, cas, 200).astype(np.int16)
        
        return ages, cas, pas
    
    def _generate_positions(self, batch_size: int) -> np.ndarray:
        """Generate positions using weighted random sampling."""
        # Normalize probabilities to ensure they sum to 1.0
        probs = np.array(self.position_probs)
        probs = probs / probs.sum()
        return self.np_rng.choice(
            self.positions,
            size=batch_size,
            replace=True,
            p=probs,
        )
    
    def _generate_dates(self, ages: np.ndarray) -> List[date]:
        """Generate birth dates from ages.
        
        Ensures that Player.age property returns the expected age by setting
        birth month/day appropriately.
        """
        today = date.today()
        dates = []
        for age in ages:
            birth_year = today.year - int(age)
            
            # Set birth month/day to ensure correct age calculation
            # If we use today's month/day, age will match exactly
            # For variety, we adjust month/day but compensate year if needed
            birth_month = self.np_rng.integers(1, 13)
            birth_day = self.np_rng.integers(1, 29)
            
            # Calculate what age this birth date would give
            calculated_age = today.year - birth_year - ((today.month, today.day) < (birth_month, birth_day))
            
            # If calculated age doesn't match, adjust birth year
            if calculated_age != int(age):
                birth_year = today.year - int(age) - 1
            
            dates.append(date(birth_year, birth_month, birth_day))
        return dates
    
    def _generate_players_batch(
        self,
        ages: np.ndarray,
        cas: np.ndarray,
        pas: np.ndarray,
        positions: np.ndarray,
        country_name: str,
    ) -> List[YouthPlayer]:
        """Generate complete youth players for a batch.
        
        Args:
            ages: Array of ages
            cas: Array of current abilities
            pas: Array of potential abilities
            positions: Array of positions
            country_name: Full country name for name generation
            
        Returns:
            List of YouthPlayer objects
        """
        batch_size = len(ages)
        players = []
        
        # Generate names (vectorized selection for first names)
        first_names = self.name_gen.generate_first_names_batch(country_name, batch_size)
        last_names = self.name_gen.generate_last_names_batch(country_name, batch_size)
        
        # Generate dates
        birth_dates = self._generate_dates(ages)
        
        # Generate players
        for i in range(batch_size):
            pos = positions[i]
            
            # Generate attributes using YouthAttributeGenerator
            attrs = self.attr_gen.generate_attributes(
                ca=float(cas[i]),
                pa=float(pas[i]),
                position=pos.value,
                age=int(ages[i]),
                country=country_name,
            )
            
            # Random physical attributes
            height = int(self.np_rng.normal(175, 10))
            height = np.clip(height, 160, 200)
            weight = int(self.np_rng.normal(70, 10))
            weight = np.clip(weight, 50, 110)
            
            # Foot preference
            foot = self.np_rng.choice([Foot.LEFT, Foot.RIGHT, Foot.RIGHT, Foot.RIGHT])  # 75% right-footed
            
            player = YouthPlayer(
                first_name=first_names[i],
                last_name=last_names[i],
                nationality=country_name,
                birth_date=birth_dates[i],
                position=pos,
                current_ability=int(cas[i]),
                potential_ability=int(pas[i]),
                attributes=attrs,
                height=int(height),
                weight=int(weight),
                preferred_foot=foot,
            )
            players.append(player)
        
        return players
    
    def generate(
        self,
        count: int,
        batch_size: int = 100_000,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[YouthPlayer]:
        """Generate youth players for this country.
        
        Args:
            count: Total number of players to generate
            batch_size: Players per batch (controls memory usage)
            progress_callback: Optional callback(progress, total) for tracking
            
        Returns:
            List of generated YouthPlayer objects
        """
        all_players = []
        remaining = count
        
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            
            # Vectorized generation of core stats
            ages, cas, pas = self._generate_batch(current_batch)
            positions = self._generate_positions(current_batch)
            
            # Generate complete players
            batch_players = self._generate_players_batch(
                ages, cas, pas, positions, self.country_config.name
            )
            
            all_players.extend(batch_players)
            remaining -= current_batch
            
            # Progress callback
            if progress_callback:
                progress_callback(count - remaining, count)
        
        return all_players


class YouthBatchGenerator:
    """High-performance orchestrator for generating youth players across all countries."""
    
    def __init__(self, config: YouthGenerationConfig, seed: Optional[int] = None):
        """Initialize batch generator.
        
        Args:
            config: Complete youth generation configuration
            seed: Optional seed for reproducibility
        """
        self.config = config
        self.attr_gen = YouthAttributeGenerator(seed=seed)
        
        # Create country-specific generators
        self.generators = {}
        for code, country_config in config.countries.items():
            self.generators[code] = CountryYouthGenerator(
                country_code=code,
                country_config=country_config,
                attribute_generator=self.attr_gen,
                seed=seed if seed is None else hash(seed + code),
            )
    
    def generate_for_country(
        self,
        country_code: str,
        batch_size: int = 100_000,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[YouthPlayer]:
        """Generate all youth players for a specific country.
        
        Args:
            country_code: Three-letter country code (e.g., 'ENG')
            batch_size: Players per batch
            progress_callback: Optional callback(progress, total)
            
        Returns:
            List of generated YouthPlayer objects
            
        Raises:
            ValueError: If country_code not found in config
        """
        if country_code not in self.generators:
            available = list(self.generators.keys())
            raise ValueError(
                f"Country '{country_code}' not found. Available: {available}"
            )
        
        generator = self.generators[country_code]
        pool_size = self.config.countries[country_code].pool_size
        
        return generator.generate(
            count=pool_size,
            batch_size=batch_size,
            progress_callback=progress_callback,
        )
    
    def generate_all_countries(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        parallel: bool = False,
    ) -> Dict[str, List[YouthPlayer]]:
        """Generate youth players for all configured countries.
        
        Args:
            progress_callback: Optional callback(country_code, progress, total)
            parallel: If True, use concurrent processing (experimental)
            
        Returns:
            Dictionary mapping country codes to lists of players
        """
        results = {}
        
        if parallel:
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_country = {}
                total_by_country = {}
                
                for code, country_config in self.config.countries.items():
                    def _generate_with_wrapper(c=code):
                        return self.generators[c].generate(
                            count=country_config.pool_size,
                            batch_size=50_000,  # Smaller batches for parallel
                            progress_callback=lambda p, t, code=c: (
                                progress_callback(code, p, t) if progress_callback else None
                            ),
                        )
                    
                    future_to_country[executor.submit(_generate_with_wrapper)] = code
                    total_by_country[code] = country_config.pool_size
                
                for future in concurrent.futures.as_completed(future_to_country):
                    country_code = future_to_country[future]
                    try:
                        players = future.result()
                        results[country_code] = players
                    except Exception as e:
                        print(f"Error generating for {country_code}: {e}")
        else:
            # Sequential generation
            for code, country_config in self.config.countries.items():
                players = self.generate_for_country(
                    country_code=code,
                    batch_size=100_000,
                    progress_callback=(
                        lambda p, t, code=code: (
                            progress_callback(code, p, t) if progress_callback else None
                        )
                    ),
                )
                results[code] = players
        
        return results
    
    def generate_with_filtering(
        self,
        country_code: str,
        filtering_pipeline: "YouthFilteringPipeline",
        batch_size: int = 100_000,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[YouthPlayer]:
        """Generate and immediately filter players for a country.
        
        This is memory-efficient for large batches as it filters during generation.
        
        Args:
            country_code: Three-letter country code
            filtering_pipeline: Pipeline to filter players
            batch_size: Players per batch
            progress_callback: Optional callback(progress, total)
            
        Returns:
            List of filtered YouthPlayer objects
        """
        if country_code not in self.generators:
            raise ValueError(f"Country '{country_code}' not found")
        
        generator = self.generators[country_code]
        pool_size = self.config.countries[country_code].pool_size
        
        filtered_players = []
        remaining = pool_size
        processed = 0
        
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            
            # Vectorized generation
            ages, cas, pas = generator._generate_batch(current_batch)
            positions = generator._generate_positions(current_batch)
            
            # Generate complete players
            batch_players = generator._generate_players_batch(
                ages, cas, pas, positions, generator.country_config.name
            )
            
            # Filter this batch
            batch_filtered = filtering_pipeline.filter_batch(batch_players)
            filtered_players.extend(batch_filtered)
            
            remaining -= current_batch
            processed += current_batch
            
            # Progress callback
            if progress_callback:
                progress_callback(processed, pool_size)
        
        return filtered_players


# Convenience filtering pipeline class
@dataclass
class YouthFilteringPipeline:
    """Pipeline for filtering youth players.
    
    Simple implementation that can be extended with more complex filtering logic.
    """
    
    min_ca: int = 50
    min_pa: int = 70
    max_age: int = 20
    
    def filter_batch(self, players: List[YouthPlayer]) -> List[YouthPlayer]:
        """Filter a batch of players.
        
        Args:
            players: List of players to filter
            
        Returns:
            Filtered list of players
        """
        filtered = []
        for player in players:
            if player.current_ability >= self.min_ca:
                if player.potential_ability >= self.min_pa:
                    if player.age <= self.max_age:
                        filtered.append(player)
        return filtered


# Convenience function for quick generation
def generate_country_youth(
    country_code: str,
    count: int,
    batch_size: int = 100_000,
    seed: Optional[int] = None,
) -> List[YouthPlayer]:
    """Quickly generate youth players for a country with default config.
    
    Args:
        country_code: Three-letter country code
        count: Number of players to generate
        batch_size: Batch size for memory management
        seed: Random seed
        
    Returns:
        List of generated YouthPlayer objects
    """
    from fm_manager.config.youth_generation_config import get_default_config, CountryYouthConfig
    
    config = get_default_config()
    
    # If country not in default config, add it
    if country_code not in config.countries:
        config.countries[country_code] = CountryYouthConfig(
            name=country_code,
            pool_size=count,
            youth_rating=100,
        )
    
    # Temporarily override pool size for this generation
    original_pool_size = config.countries[country_code].pool_size
    config.countries[country_code].pool_size = count
    
    # Create generator AFTER modifying config
    generator = YouthBatchGenerator(config, seed=seed)
    
    # Generate
    players = generator.generate_for_country(country_code, batch_size=batch_size)
    
    # Restore original pool size
    config.countries[country_code].pool_size = original_pool_size
    
    return players
