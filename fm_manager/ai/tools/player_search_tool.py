"""Player Search Tool for Natural Language Game Interface.

Provides flexible player search capabilities with support for complex queries
like "find English midfielders under 23 with high potential".
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import re

from fm_manager.data.cleaned_data_loader import load_for_match_engine, PlayerDataFull


class PositionCategory(Enum):
    """Broad position categories that map to specific positions."""

    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    ATTACKER = "attacker"
    WINGER = "winger"


# Position mapping from broad categories to specific positions
POSITION_MAPPING = {
    PositionCategory.GOALKEEPER: ["GK"],
    PositionCategory.DEFENDER: ["CB", "LB", "RB", "LWB", "RWB", "DC", "DL", "DR", "WBL", "WBR"],
    PositionCategory.MIDFIELDER: ["CM", "CDM", "CAM", "DM", "MC", "ML", "MR"],
    PositionCategory.ATTACKER: ["ST", "CF", "TS", "FS"],
    PositionCategory.WINGER: ["LW", "RW", "AML", "AMR", "LM", "RM"],
}

# Alias mappings for common terms
POSITION_ALIASES = {
    "gk": "GK",
    "goalkeeper": "GK",
    "keeper": "GK",
    "cb": "CB",
    "center back": "CB",
    "centre back": "CB",
    "defender": "CB",
    "lb": "LB",
    "left back": "LB",
    "rb": "RB",
    "right back": "RB",
    "dm": "DM",
    "cdm": "DM",
    "defensive midfielder": "DM",
    "cm": "CM",
    "central midfielder": "CM",
    "midfielder": "CM",
    "cam": "CAM",
    "attacking midfielder": "CAM",
    "lw": "LW",
    "left winger": "LW",
    "rw": "RW",
    "right winger": "RW",
    "st": "ST",
    "cf": "ST",
    "striker": "ST",
    "forward": "ST",
    "centre forward": "ST",
}


@dataclass
class PlayerSearchCriteria:
    """Criteria for searching players."""

    # Basic filters
    name: Optional[str] = None
    nationality: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None

    # Position filters
    position: Optional[str] = None  # Specific position like "CM"
    position_category: Optional[PositionCategory] = None  # Broad category like "midfielder"

    # Ability filters
    min_current_ability: Optional[float] = None
    max_current_ability: Optional[float] = None
    min_potential_ability: Optional[float] = None
    max_potential_ability: Optional[float] = None

    # Value filters
    min_market_value: Optional[int] = None
    max_market_value: Optional[int] = None
    min_weekly_wage: Optional[int] = None
    max_weekly_wage: Optional[int] = None

    # Club filters
    club_id: Optional[int] = None
    exclude_club_id: Optional[int] = None  # Exclude players from specific club

    # Sorting
    sort_by: str = "current_ability"  # current_ability, potential_ability, market_value, age
    sort_descending: bool = True

    # Pagination
    limit: int = 20
    offset: int = 0


@dataclass
class PlayerSearchResult:
    """Result of a player search."""

    players: List[PlayerDataFull] = field(default_factory=list)
    total_count: int = 0
    criteria: Optional[PlayerSearchCriteria] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for LLM consumption."""
        return {
            "total_found": self.total_count,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "full_name": p.full_name,
                    "position": p.position,
                    "age": p.age,
                    "nationality": p.nationality,
                    "current_ability": round(p.current_ability, 1),
                    "potential_ability": round(p.potential_ability, 1),
                    "market_value": p.market_value,
                    "weekly_wage": p.weekly_wage,
                    "club_id": p.club_id,
                    "club_name": p.club_name,
                }
                for p in self.players[:10]  # Limit to first 10 for LLM context
            ],
        }


class PlayerSearchTool:
    """Tool for searching players with complex criteria."""

    def __init__(self):
        """Initialize the search tool with player data."""
        self.clubs, self.players = load_for_match_engine()
        self._cache: Dict[str, PlayerSearchResult] = {}

    def search(self, criteria: PlayerSearchCriteria) -> PlayerSearchResult:
        """
        Search for players matching the given criteria.

        Args:
            criteria: Search criteria

        Returns:
            PlayerSearchResult with matching players
        """
        # Build filter functions
        filters: List[Callable[[PlayerDataFull], bool]] = []

        # Name filter
        if criteria.name:
            name_lower = criteria.name.lower()
            filters.append(lambda p: name_lower in p.full_name.lower())

        # Nationality filter
        if criteria.nationality:
            nat_lower = criteria.nationality.lower()
            # Handle "English" -> "England" mapping
            if nat_lower == "english":
                nat_lower = "england"
            filters.append(lambda p: nat_lower in p.nationality.lower())

        # Age filters
        if criteria.min_age is not None:
            filters.append(lambda p: p.age >= criteria.min_age)
        if criteria.max_age is not None:
            filters.append(lambda p: p.age <= criteria.max_age)

        # Position filter (specific)
        if criteria.position:
            pos_upper = criteria.position.upper()
            filters.append(lambda p: pos_upper in p.position.upper())

        # Position category filter (broad)
        if criteria.position_category:
            valid_positions = POSITION_MAPPING[criteria.position_category]
            filters.append(lambda p: p.position in valid_positions)

        # Current ability filters
        if criteria.min_current_ability is not None:
            filters.append(lambda p: p.current_ability >= criteria.min_current_ability)
        if criteria.max_current_ability is not None:
            filters.append(lambda p: p.current_ability <= criteria.max_current_ability)

        # Potential ability filters
        if criteria.min_potential_ability is not None:
            filters.append(lambda p: p.potential_ability >= criteria.min_potential_ability)
        if criteria.max_potential_ability is not None:
            filters.append(lambda p: p.potential_ability <= criteria.max_potential_ability)

        # Market value filters
        if criteria.min_market_value is not None:
            filters.append(lambda p: p.market_value >= criteria.min_market_value)
        if criteria.max_market_value is not None:
            filters.append(lambda p: p.market_value <= criteria.max_market_value)

        # Weekly wage filters
        if criteria.min_weekly_wage is not None:
            filters.append(lambda p: p.weekly_wage >= criteria.min_weekly_wage)
        if criteria.max_weekly_wage is not None:
            filters.append(lambda p: p.weekly_wage <= criteria.max_weekly_wage)

        # Club filters
        if criteria.club_id is not None:
            filters.append(lambda p: p.club_id == criteria.club_id)
        if criteria.exclude_club_id is not None:
            filters.append(lambda p: p.club_id != criteria.exclude_club_id)

        # Apply all filters
        filtered_players = self.players.values()
        for filter_fn in filters:
            filtered_players = [p for p in filtered_players if filter_fn(p)]

        # Sort results
        sort_key = {
            "current_ability": lambda p: p.current_ability,
            "potential_ability": lambda p: p.potential_ability,
            "market_value": lambda p: p.market_value,
            "age": lambda p: p.age,
            "name": lambda p: p.full_name,
        }.get(criteria.sort_by, lambda p: p.current_ability)

        filtered_players = sorted(filtered_players, key=sort_key, reverse=criteria.sort_descending)

        # Apply pagination
        total_count = len(filtered_players)
        paginated_players = filtered_players[criteria.offset : criteria.offset + criteria.limit]

        return PlayerSearchResult(
            players=paginated_players, total_count=total_count, criteria=criteria
        )

    def parse_position(
        self, position_text: str
    ) -> tuple[Optional[str], Optional[PositionCategory]]:
        """
        Parse position text into specific position and/or category.

        Args:
            position_text: Raw position text like "midfielder" or "CM"

        Returns:
            Tuple of (specific_position, position_category)
        """
        position_lower = position_text.lower().strip()

        # Check aliases first
        if position_lower in POSITION_ALIASES:
            specific = POSITION_ALIASES[position_lower]
            # Determine category
            for cat, positions in POSITION_MAPPING.items():
                if specific in positions:
                    return specific, cat
            return specific, None

        # Check if it's a specific position code
        if position_upper := position_text.upper():
            for cat, positions in POSITION_MAPPING.items():
                if position_upper in positions:
                    return position_upper, cat

        # Check if it's a category
        for cat in PositionCategory:
            if cat.value in position_lower:
                return None, cat

        return None, None

    def build_criteria_from_natural_language(
        self,
        nationality: Optional[str] = None,
        age: Optional[str] = None,
        position: Optional[str] = None,
        ability: Optional[str] = None,
        potential: Optional[str] = None,
        max_price: Optional[str] = None,
    ) -> PlayerSearchCriteria:
        """
        Build search criteria from natural language parameters.

        Args:
            nationality: Player nationality
            age: Age description (e.g., "under 23", "25", "over 30")
            position: Position description
            ability: Ability level (e.g., "high", "80+", "good")
            potential: Potential level
            max_price: Maximum price (e.g., "50M", "50 million")

        Returns:
            PlayerSearchCriteria
        """
        criteria = PlayerSearchCriteria()

        # Parse nationality
        if nationality:
            criteria.nationality = nationality

        # Parse age
        if age:
            age_lower = age.lower()
            # Check for age range (e.g., "between 18 to 22", "18-22", "18到22岁")
            range_patterns = [
                r"between\s+(\d+)\s+(?:to|and)\s+(\d+)",
                r"(\d+)\s*[-~]\s*(\d+)",
                r"(\d+)\s*到\s*(\d+)",
            ]
            for pattern in range_patterns:
                range_match = re.search(pattern, age_lower)
                if range_match:
                    criteria.min_age = int(range_match.group(1))
                    criteria.max_age = int(range_match.group(2))
                    break
            else:
                # Single age or under/over
                age_match = re.search(r"(\d+)", age_lower)
                if age_match:
                    age_num = int(age_match.group(1))
                    if "under" in age_lower or "below" in age_lower or "younger" in age_lower:
                        criteria.max_age = age_num
                    elif "over" in age_lower or "above" in age_lower or "older" in age_lower:
                        criteria.min_age = age_num
                    else:
                        criteria.min_age = age_num
                        criteria.max_age = age_num

        # Parse position
        if position:
            specific_pos, category = self.parse_position(position)
            if specific_pos:
                criteria.position = specific_pos
            if category:
                criteria.position_category = category

        # Parse ability
        if ability:
            ability_lower = ability.lower()
            ability_match = re.search(r"(\d+)", ability_lower)
            if ability_match:
                ability_num = int(ability_match.group(1))
                criteria.min_current_ability = ability_num
            elif "high" in ability_lower or "good" in ability_lower or "star" in ability_lower:
                criteria.min_current_ability = 75
            elif "decent" in ability_lower or "average" in ability_lower:
                criteria.min_current_ability = 60

        # Parse potential
        if potential:
            potential_lower = potential.lower()
            potential_match = re.search(r"(\d+)", potential_lower)
            if potential_match:
                potential_num = int(potential_match.group(1))
                criteria.min_potential_ability = potential_num
            elif (
                "high" in potential_lower
                or "great" in potential_lower
                or "excellent" in potential_lower
            ):
                criteria.min_potential_ability = 80
            elif "good" in potential_lower:
                criteria.min_potential_ability = 70

        # Parse price
        if max_price:
            price_lower = max_price.lower().replace(",", "")
            # Extract number
            price_match = re.search(r"(\d+(?:\.\d+)?)\s*(m|million|k|thousand)?", price_lower)
            if price_match:
                price_num = float(price_match.group(1))
                unit = price_match.group(2) or "m"
                if unit in ["m", "million"]:
                    criteria.max_market_value = int(price_num * 1_000_000)
                elif unit in ["k", "thousand"]:
                    criteria.max_market_value = int(price_num * 1_000)
                else:
                    criteria.max_market_value = int(price_num)

        return criteria


# Global instance for reuse
_search_tool: Optional[PlayerSearchTool] = None


def get_player_search_tool() -> PlayerSearchTool:
    """Get or create the global player search tool instance."""
    global _search_tool
    if _search_tool is None:
        _search_tool = PlayerSearchTool()
    return _search_tool


# Convenience function for quick searches
def search_players(
    nationality: Optional[str] = None,
    max_age: Optional[int] = None,
    position: Optional[str] = None,
    min_potential: Optional[int] = None,
    limit: int = 10,
) -> PlayerSearchResult:
    """
    Quick search function for common queries.

    Example:
        result = search_players(
            nationality="England",
            max_age=23,
            position="midfielder",
            min_potential=80
        )
    """
    tool = get_player_search_tool()
    criteria = PlayerSearchCriteria(
        nationality=nationality,
        max_age=max_age,
        position=position,
        min_potential_ability=min_potential,
        limit=limit,
        sort_by="potential_ability",
    )
    return tool.search(criteria)
