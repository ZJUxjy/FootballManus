"""Youth player filtering system for FM Manager.

Implements a multi-stage filtering pipeline for selecting top youth players:
1. Stage 1: CA Filtering - Keep top 0.1% by Current Ability
2. Stage 2: PA Filtering - Keep top 0.2% by Potential Ability from remaining
3. Stage 3: Minimum Guarantee - Ensure minimum player count per country
4. Stage 4: CA/PA Ratio Validation - Ensure CA >= 40% of PA
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np

from fm_manager.core.models.player import Player, Position


@dataclass
class FilteringConfig:
    """Configuration for youth filtering pipeline."""
    
    # Percentage of top players to keep by CA
    ca_percentile: float = 0.001  # 0.1%
    
    # Percentage of top players to keep by PA (from remaining)
    pa_percentile: float = 0.002  # 0.2%
    
    # Minimum players per country
    min_players_per_country: int = 1000
    
    # Minimum CA/PA ratio
    ca_pa_ratio_min: float = 0.4


@dataclass
class YouthPlayer:
    """Lightweight youth player dataclass for bulk processing."""
    
    id: int
    full_name: str
    nationality: str
    age: int
    position: str
    ca: float
    pa: float
    attributes: Dict[str, int] = field(default_factory=dict)
    
    def to_player(self) -> Player:
        """Convert to full Player model."""
        # Parse position
        position_map = {
            "GK": Position.GK,
            "CB": Position.CB,
            "LB": Position.LB,
            "RB": Position.RB,
            "LWB": Position.LWB,
            "RWB": Position.RWB,
            "CDM": Position.CDM,
            "CM": Position.CM,
            "LM": Position.LM,
            "RM": Position.RM,
            "CAM": Position.CAM,
            "LW": Position.LW,
            "RW": Position.RW,
            "CF": Position.CF,
            "ST": Position.ST,
        }
        pos = position_map.get(self.position.upper(), Position.CM)
        
        # Split name
        name_parts = self.full_name.split(" ", 1)
        first_name = name_parts[0] if len(name_parts) > 0 else self.full_name
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create player
        player = Player(
            id=self.id,
            first_name=first_name,
            last_name=last_name,
            nationality=self.nationality,
            position=pos,
            current_ability=int(self.ca),
            potential_ability=int(self.pa),
            age=self.age,
        )
        
        # Set attributes
        for attr_name, attr_value in self.attributes.items():
            if hasattr(player, attr_name):
                setattr(player, attr_name, attr_value)
        
        return player


@dataclass
class FilteringResult:
    """Results from filtering pipeline."""
    
    selected_players: List[YouthPlayer]
    stage1_count: int = 0
    stage2_count: int = 0
    stage3_count: int = 0
    total_count: int = 0
    execution_time: float = 0.0
    
    def get_summary(self) -> Dict:
        """Get summary of filtering results."""
        return {
            "total_selected": self.total_count,
            "stage1_ca_filtered": self.stage1_count,
            "stage2_pa_filtered": self.stage2_count,
            "stage3_minimum_added": self.stage3_count,
            "execution_time_seconds": self.execution_time,
        }


class YouthFilteringPipeline:
    """Multi-stage youth player filtering pipeline.
    
    Uses efficient NumPy operations for processing large datasets.
    """
    
    def __init__(self, config: FilteringConfig):
        """Initialize the filtering pipeline with configuration.
        
        Args:
            config: Filtering configuration parameters
        """
        self.ca_percentile = config.ca_percentile
        self.pa_percentile = config.pa_percentile
        self.min_players = config.min_players_per_country
        self.ca_pa_ratio = config.ca_pa_ratio_min
    
    def filter_players(
        self, 
        players: List[YouthPlayer],
        by_country: bool = False
    ) -> FilteringResult:
        """Apply full filtering pipeline to youth players.
        
        Args:
            players: List of youth players to filter
            by_country: If True, apply minimum guarantee per country
        
        Returns:
            FilteringResult with selected players and statistics
        """
        start_time = time.time()
        
        if not players:
            return FilteringResult(selected_players=[], execution_time=time.time() - start_time)
        
        # Convert to NumPy arrays for efficient processing
        player_array = np.array(players, dtype=object)
        cas = np.array([p.ca for p in players], dtype=np.float64)
        pas = np.array([p.pa for p in players], dtype=np.float64)
        nationalities = np.array([p.nationality for p in players], dtype=object)
        
        # Stage 1: Filter by CA (top 0.1%)
        stage1_indices, remaining_indices, stage1_cas = self._filter_by_ca(
            player_array, cas
        )
        stage1_count = len(stage1_indices)
        
        # Stage 2: Filter by PA from remaining (top 0.2%)
        stage2_indices = self._filter_by_pa(
            player_array[remaining_indices], pas[remaining_indices], remaining_indices
        )
        stage2_count = len(stage2_indices)
        
        # Combine Stage 1 and Stage 2 selections
        selected_indices = np.concatenate([stage1_indices, stage2_indices])
        selected_indices = np.unique(selected_indices)  # Remove duplicates
        
        # Stage 3: Ensure minimum player count (per country or overall)
        if by_country:
            selected_indices = self._ensure_minimum_by_country(
                selected_indices, player_array, cas, self.min_players
            )
            stage3_count = len(selected_indices) - (stage1_count + stage2_count)
        else:
            selected_indices = self._ensure_minimum(
                selected_indices, player_array, cas, self.min_players
            )
            stage3_count = len(selected_indices) - (stage1_count + stage2_count)
        
        # Get selected players
        final_players = player_array[selected_indices].tolist()
        
        # Stage 4: Validate and fix CA/PA ratio
        final_players = self._validate_ca_pa_ratio(final_players)
        
        execution_time = time.time() - start_time
        
        result = FilteringResult(
            selected_players=final_players,
            stage1_count=stage1_count,
            stage2_count=stage2_count,
            stage3_count=max(0, stage3_count),
            total_count=len(final_players),
            execution_time=execution_time
        )
        
        return result
    
    def _filter_by_ca(
        self, 
        players: np.ndarray, 
        cas: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Stage 1: Keep top percentile by Current Ability.
        
        Uses np.argpartition for O(n) performance instead of O(n log n) sorting.
        
        Args:
            players: NumPy array of YouthPlayer objects
            cas: NumPy array of Current Ability values
        
        Returns:
            Tuple of (selected_indices, remaining_indices, selected_cas)
        """
        n = len(cas)
        k = max(1, int(n * self.ca_percentile))
        
        # Use argpartition for O(n) performance
        # This finds the k largest elements without full sort
        top_k_indices = np.argpartition(cas, -k)[-k:]
        
        # Sort only the top k to get actual ranking
        top_k_sorted = top_k_indices[np.argsort(-cas[top_k_indices])]
        
        # Create boolean mask for remaining
        selected_mask = np.zeros(n, dtype=bool)
        selected_mask[top_k_sorted] = True
        remaining_mask = ~selected_mask
        
        return top_k_sorted, np.where(remaining_mask)[0], cas[top_k_sorted]
    
    def _filter_by_pa(
        self, 
        remaining: np.ndarray, 
        pas: np.ndarray,
        original_indices: np.ndarray
    ) -> np.ndarray:
        """Stage 2: Keep top percentile by Potential Ability from remaining.
        
        Args:
            remaining: NumPy array of remaining YouthPlayer objects
            pas: NumPy array of Potential Ability values for remaining
            original_indices: Original indices in the full array
        
        Returns:
            NumPy array of selected original indices
        """
        n = len(pas)
        k = max(1, int(n * self.pa_percentile))
        
        # Use argpartition for O(n) performance
        top_k_indices = np.argpartition(pas, -k)[-k:]
        
        # Sort only the top k
        top_k_sorted = top_k_indices[np.argsort(-pas[top_k_indices])]
        
        # Map back to original indices
        return original_indices[top_k_sorted]
    
    def _ensure_minimum(
        self, 
        selected: np.ndarray,
        all_players: np.ndarray,
        cas: np.ndarray,
        min_count: int
    ) -> np.ndarray:
        """Stage 3: Ensure minimum player count.
        
        If current selection is below minimum, fill with highest CA players
        from the remaining pool, maintaining deduplication.
        
        Args:
            selected: Array of currently selected indices
            all_players: Array of all players
            cas: Array of all CA values
            min_count: Minimum number of players required
        
        Returns:
            Array of selected indices meeting minimum count
        """
        current_count = len(selected)
        
        if current_count >= min_count:
            return selected
        
        # Find remaining players (not selected)
        selected_mask = np.zeros(len(all_players), dtype=bool)
        selected_mask[selected] = True
        remaining_mask = ~selected_mask
        remaining_indices = np.where(remaining_mask)[0]
        
        # Calculate how many more we need
        needed = min_count - current_count
        
        if needed > len(remaining_indices):
            # Not enough players, take all remaining
            additional = remaining_indices
        else:
            # Take highest CA from remaining
            remaining_cas = cas[remaining_indices]
            top_additional = np.argpartition(remaining_cas, -needed)[-needed:]
            top_additional_sorted = top_additional[np.argsort(-remaining_cas[top_additional])]
            additional = remaining_indices[top_additional_sorted]
        
        # Combine and deduplicate
        final_selected = np.concatenate([selected, additional])
        final_selected = np.unique(final_selected)
        
        return final_selected
    
    def _ensure_minimum_by_country(
        self,
        selected: np.ndarray,
        all_players: np.ndarray,
        cas: np.ndarray,
        min_count: int
    ) -> np.ndarray:
        """Stage 3: Ensure minimum player count per country.
        
        For each country, if selection is below minimum, fill with highest
        CA players from that country's remaining pool.
        
        Args:
            selected: Array of currently selected indices
            all_players: Array of all players
            cas: Array of all CA values
            min_count: Minimum players per country
        
        Returns:
            Array of selected indices meeting minimum per country
        """
        # Get nationalities of all players
        nationalities = np.array([p.nationality for p in all_players])
        unique_countries = np.unique(nationalities)
        
        final_selected = set(selected)
        
        for country in unique_countries:
            # Find players from this country
            country_mask = (nationalities == country)
            country_indices = np.where(country_mask)[0]
            
            # Count how many from this country are already selected
            country_selected_mask = np.isin(country_indices, list(final_selected))
            country_selected_count = np.sum(country_selected_mask)
            
            if country_selected_count >= min_count:
                continue
            
            # Find remaining players from this country
            country_remaining_indices = country_indices[~country_selected_mask]
            country_remaining_cas = cas[country_remaining_indices]
            
            # Calculate how many more we need
            needed = min_count - country_selected_count
            
            if needed > len(country_remaining_indices):
                # Take all remaining from this country
                additional = country_remaining_indices
            else:
                # Take highest CA from remaining
                top_additional = np.argpartition(country_remaining_cas, -needed)[-needed:]
                top_additional_sorted = top_additional[np.argsort(-country_remaining_cas[top_additional])]
                additional = country_remaining_indices[top_additional_sorted]
            
            # Add to final selection
            final_selected.update(additional)
        
        return np.array(sorted(final_selected))
    
    def _validate_ca_pa_ratio(self, players: List[YouthPlayer]) -> List[YouthPlayer]:
        """Stage 4: Ensure all players have CA >= 40% of PA.
        
        If CA < 0.4 * PA, boost CA to meet the minimum ratio.
        
        Args:
            players: List of selected youth players
        
        Returns:
            List of players with validated CA/PA ratios
        """
        validated = []
        
        for player in players:
            min_ca = player.pa * self.ca_pa_ratio
            
            if player.ca < min_ca:
                # Create a new player with boosted CA
                # Keep other attributes the same, only update CA
                updated_player = YouthPlayer(
                    id=player.id,
                    full_name=player.full_name,
                    nationality=player.nationality,
                    age=player.age,
                    position=player.position,
                    ca=min_ca,
                    pa=player.pa,
                    attributes=player.attributes.copy()
                )
                validated.append(updated_player)
            else:
                validated.append(player)
        
        return validated


def create_test_players(
    num_players: int = 1000000,
    num_countries: int = 10,
    seed: Optional[int] = None
) -> List[YouthPlayer]:
    """Create test youth players for benchmarking.
    
    Args:
        num_players: Number of players to generate
        num_countries: Number of different countries
        seed: Random seed for reproducibility
    
    Returns:
        List of generated YouthPlayer objects
    """
    if seed is not None:
        np.random.seed(seed)
    
    countries = [
        "England", "Spain", "Germany", "France", "Italy",
        "Brazil", "Argentina", "Portugal", "Netherlands", "Belgium"
    ][:num_countries]
    
    positions = ["GK", "CB", "LB", "RB", "CDM", "CM", "LM", "RM", "CAM", "LW", "RW", "CF", "ST"]
    
    players = []
    
    for i in range(num_players):
        # Generate CA (normal distribution around 50)
        ca = np.random.normal(50, 15)
        ca = max(10, min(200, ca))
        
        # Generate PA (higher than CA, with some variance)
        pa = ca + np.random.normal(20, 10)
        pa = max(ca, min(200, pa))  # PA must be >= CA
        
        player = YouthPlayer(
            id=i,
            full_name=f"Player_{i}",
            nationality=np.random.choice(countries),
            age=np.random.randint(15, 21),
            position=np.random.choice(positions),
            ca=ca,
            pa=pa,
            attributes={}
        )
        players.append(player)
    
    return players


if __name__ == "__main__":
    # Quick test with 1M players
    print("Testing YouthFilteringPipeline with 1M players...")
    
    config = FilteringConfig(
        ca_percentile=0.001,
        pa_percentile=0.002,
        min_players_per_country=1000,
        ca_pa_ratio_min=0.4
    )
    
    pipeline = YouthFilteringPipeline(config)
    
    # Generate test players
    print("Generating 1M test players...")
    test_players = create_test_players(num_players=1000000, seed=42)
    
    # Run filtering
    print("Running filtering pipeline...")
    result = pipeline.filter_players(test_players, by_country=True)
    
    # Print results
    print("\n=== Filtering Results ===")
    summary = result.get_summary()
    print(f"Total players selected: {summary['total_selected']}")
    print(f"Stage 1 (CA filtering): {summary['stage1_ca_filtered']}")
    print(f"Stage 2 (PA filtering): {summary['stage2_pa_filtered']}")
    print(f"Stage 3 (minimum guarantee): {summary['stage3_minimum_added']}")
    print(f"Execution time: {summary['execution_time_seconds']:.3f} seconds")
    
    # Verify CA/PA ratio
    ca_pa_ok = all(p.ca >= p.pa * 0.4 for p in result.selected_players)
    print(f"\nCA/PA ratio validation (CA >= 0.4 * PA): {'PASS' if ca_pa_ok else 'FAIL'}")
    
    # Verify minimum per country
    from collections import Counter
    country_counts = Counter(p.nationality for p in result.selected_players)
    min_per_country_met = all(count >= 1000 for count in country_counts.values())
    print(f"Minimum players per country (>= 1000): {'PASS' if min_per_country_met else 'FAIL'}")
    print(f"Country counts: {dict(country_counts)}")
    
    # Verify no duplicates
    unique_ids = len(set(p.id for p in result.selected_players))
    no_duplicates = unique_ids == len(result.selected_players)
    print(f"No duplicates in selection: {'PASS' if no_duplicates else 'FAIL'}")
