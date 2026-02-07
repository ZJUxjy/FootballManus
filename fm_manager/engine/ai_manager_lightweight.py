"""Lightweight AI Manager for non-player clubs using cleaned data."""

from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random

from fm_manager.data.cleaned_data_loader import ClubDataFull, PlayerDataFull


class AIPersonality(Enum):
    """AI manager personality types."""

    ATTACKING = "attacking"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    TIKITAKA = "tikitaka"
    LONG_BALL = "long_ball"
    PRAGMATIC = "pragmatic"


class AIAggressiveness(Enum):
    """How aggressive AI is in transfers and tactics."""

    CONSERVATIVE = 1
    MODERATE = 2
    AGGRESSIVE = 3


@dataclass
class AIManager:
    """Lightweight AI manager for a club."""

    club_id: int
    name: str
    personality: AIPersonality = AIPersonality.BALANCED
    aggressiveness: AIAggressiveness = AIAggressiveness.MODERATE

    # Tactical preferences
    preferred_formation: str = "4-3-3"

    # Squad management
    rotation_frequency: float = 0.2
    youth_focus: float = 0.3

    # Transfer behavior
    max_transfer_budget_percent: float = 0.7
    sell_deadwood_threshold: int = 65

    # Memory
    recent_results: List[str] = field(default_factory=list)
    current_mood: str = "neutral"

    def update_mood(self, last_5_results: List[str]) -> None:
        """Update manager mood based on recent results."""
        wins = last_5_results.count("W")
        losses = last_5_results.count("L")

        if wins >= 4:
            self.current_mood = "happy"
        elif wins >= 2 and losses <= 1:
            self.current_mood = "neutral"
        elif losses >= 3:
            self.current_mood = "crisis"
        else:
            self.current_mood = "under_pressure"

    def should_rotate_squad(self, match_importance: float = 0.5) -> bool:
        """Decide if squad should be rotated."""
        base_rotation = self.rotation_frequency

        if self.current_mood == "crisis":
            base_rotation *= 0.5
        elif self.current_mood == "happy":
            base_rotation *= 1.3

        base_rotation *= 1.5 - match_importance

        return random.random() < base_rotation

    def decide_formation(self, opponent_strength: float = 0.5) -> str:
        """Decide formation based on opponent and personality."""
        if self.personality == AIPersonality.ATTACKING:
            formations = ["4-3-3", "3-4-3", "4-2-4"]
        elif self.personality == AIPersonality.DEFENSIVE:
            formations = ["5-4-1", "4-5-1", "5-3-2"]
        elif self.personality == AIPersonality.TIKITAKA:
            formations = ["4-3-3", "4-2-3-1", "3-5-2"]
        elif self.personality == AIPersonality.LONG_BALL:
            formations = ["4-4-2", "4-2-4", "5-3-2"]
        else:
            if opponent_strength > 0.7:
                formations = ["4-5-1", "5-4-1", "4-1-4-1"]
            elif opponent_strength < 0.3:
                formations = ["4-3-3", "3-4-3", "4-2-4"]
            else:
                formations = ["4-3-3", "4-2-3-1", "4-4-2"]

        return random.choice(formations)

    def select_starting_xi(
        self, available_players: List[PlayerDataFull], opponent_strength: float = 0.5
    ) -> List[PlayerDataFull]:
        """Select starting XI."""
        if not available_players:
            return []

        sorted_players = sorted(
            available_players, key=lambda p: getattr(p, "current_ability", 0), reverse=True
        )

        formation = self.decide_formation(opponent_strength)
        position_needs = self._parse_formation(formation)

        selected = []
        used_players = set()

        for position in position_needs:
            for player in sorted_players:
                if player.id in used_players:
                    continue

                player_pos = getattr(player, "position", "").upper()
                if position in player_pos or player_pos in position:
                    selected.append(player)
                    used_players.add(player.id)
                    break

        while len(selected) < 11 and len(used_players) < len(sorted_players):
            for player in sorted_players:
                if player.id not in used_players:
                    selected.append(player)
                    used_players.add(player.id)
                    break

        return selected[:11]

    def _parse_formation(self, formation: str) -> List[str]:
        """Parse formation into position needs."""
        formation_positions = {
            "4-3-3": ["GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD", "FWD"],
            "4-2-3-1": ["GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "FWD", "FWD", "FWD", "FWD"],
            "4-4-2": ["GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "MID", "FWD", "FWD"],
            "3-4-3": ["GK", "DEF", "DEF", "DEF", "MID", "MID", "MID", "MID", "FWD", "FWD", "FWD"],
            "5-4-1": ["GK", "DEF", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "MID", "FWD"],
            "5-3-2": ["GK", "DEF", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD"],
        }
        return formation_positions.get(formation, formation_positions["4-3-3"])

    def evaluate_player_value(self, player: PlayerDataFull, asking_price: int) -> float:
        """Evaluate if player is good value."""
        ca = getattr(player, "current_ability", 0)
        pa = getattr(player, "potential_ability", 0)
        age = getattr(player, "age", 25)

        base_value = ca * 100000
        potential_bonus = (pa - ca) * 50000 if pa > ca else 0
        age_factor = max(0.5, 1 - (age - 20) * 0.05)

        estimated_value = (base_value + potential_bonus) * age_factor
        return estimated_value / max(asking_price, 1)

    def should_accept_offer(
        self, player: PlayerDataFull, offer_fee: int, player_importance: float = 0.5
    ) -> bool:
        """Decide whether to accept transfer offer."""
        market_value = getattr(player, "market_value", 1000000)
        ca = getattr(player, "current_ability", 0)

        if player_importance > 0.8 and offer_fee < market_value * 1.5:
            return False

        if offer_fee >= market_value * 1.5:
            return True

        if ca < self.sell_deadwood_threshold and offer_fee >= market_value * 0.8:
            return True

        if self.aggressiveness == AIAggressiveness.AGGRESSIVE:
            return offer_fee >= market_value * 1.2
        elif self.aggressiveness == AIAggressiveness.CONSERVATIVE:
            return offer_fee >= market_value * 2.0
        else:
            return offer_fee >= market_value * 1.5


class AIManagerRegistry:
    """Registry for all AI managers."""

    def __init__(self):
        self.managers: Dict[int, AIManager] = {}
        self._personality_weights = {
            AIPersonality.BALANCED: 0.4,
            AIPersonality.ATTACKING: 0.2,
            AIPersonality.DEFENSIVE: 0.15,
            AIPersonality.TIKITAKA: 0.1,
            AIPersonality.LONG_BALL: 0.1,
            AIPersonality.PRAGMATIC: 0.05,
        }

    def create_manager_for_club(self, club_id: int, club_name: str) -> AIManager:
        """Create AI manager for a club."""
        personality = random.choices(
            list(self._personality_weights.keys()), weights=list(self._personality_weights.values())
        )[0]

        aggressiveness = random.choice(list(AIAggressiveness))

        manager = AIManager(
            club_id=club_id,
            name=f"AI Manager {club_id}",
            personality=personality,
            aggressiveness=aggressiveness,
        )

        self.managers[club_id] = manager
        return manager

    def get_manager(self, club_id: int) -> Optional[AIManager]:
        """Get AI manager for a club."""
        return self.managers.get(club_id)

    def process_all_managers(self, clubs: Dict[int, ClubDataFull]) -> Dict[int, List[str]]:
        """Process all AI managers for a game week."""
        decisions = {}

        for club_id in clubs:
            if club_id not in self.managers:
                continue

            manager = self.managers[club_id]
            club = clubs[club_id]

            club_decisions = []

            if manager.should_rotate_squad():
                club_decisions.append("rotate_squad")

            formation = manager.decide_formation()
            club_decisions.append(f"formation:{formation}")

            decisions[club_id] = club_decisions

        return decisions
