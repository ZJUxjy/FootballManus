"""Player injury and team chemistry system.

Features:
- Injury types (short, long-term, career-ending)
- Injury recovery system with realistic timelines
- Team chemistry based on player compatibility
- Dynamic chemistry affecting match performance
- Fitness and recovery integration
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum, auto
from typing import Optional, Dict, List, Tuple
from sqlalchemy import select

from fm_manager.core.models import Player, Club, Match, Position
from fm_manager.core.database import get_db_session
from fm_manager.engine.team_state import TeamStateManager, PlayerMatchState


class InjuryType(Enum):
    """Types of injuries."""
    MINOR = "minor"           # 1-3 weeks out
    MODERATE = "moderate"       # 3-6 weeks out
    SERIOUS = "serious"          # 2-3 months out
    CAREER_ENDING = "career_ending"  # Season-ending
    FRACTURE = "fracture"       # 6 weeks out


class InjuryStatus(Enum):
    """Status of player injury."""
    INJURED = "injured"
    RECOVERING = "recovering"
    FIT = "fit"
    RETURNING = "returning"
    SUSPENDED = "suspended"


@dataclass
class Injury:
    """Record of an injury."""
    injury_id: str
    player_id: int
    club_id: int

    # Injury details
    injury_type: InjuryType
    occurred_at: date
    expected_return: date

    # Status
    status: InjuryStatus = InjuryStatus.RECOVERING
    days_out: int = 0  # Days injured so far

    # Impact
    severity: int = 0  # 0-100
    effects: List[str] = field(default_factory=list)

    def is_active(self) -> bool:
        """Check if player is currently injured."""
        return self.status == InjuryStatus.RECOVERING


@dataclass
class PlayerChemistry:
    """Chemistry between players."""
    player1_id: int
    player2_id: int

    # Compatibility score (0-100)
    compatibility_score: float = 0.0

    # Playing style compatibility (0-100)
    attacking_compatibility: float = 50.0
    defensive_compatibility: float = 50.0
    tactical_compatibility: float = 50.0

    # Relationship
    relationship_score: float = 0.0
    relationship_type: str = "neutral"

    # Performance impact
    attacking_synergy: float = 0.0
    defensive_synergy: float = 0.0

    def get_total_chemistry(self) -> float:
        """Get overall chemistry score."""
        return (
            self.compatibility_score * 0.4 +
            self.attacking_compatibility * 0.3 +
            self.defensive_compatibility * 0.2 +
            self.tactical_compatibility * 0.1 +
            self.relationship_score * 0.2
        )


@dataclass
class InjuryReport:
    """Summary of injuries for a season."""
    season_year: int

    # Injury statistics
    total_injuries: int = 0
    injuries_by_type: Dict[InjuryType, int] = field(default_factory=dict)

    # Most injured players
    most_injured_player: Optional[str] = None
    most_injured_club: Optional[str] = None

    # Days lost to injury
    total_days_lost: int = 0

    # Season ending injuries
    season_ending_injuries: List[Dict] = field(default_factory=list)  # Players whose careers ended
    club_ending_injuries: Dict[str, List[Dict]] = field(default_factory=dict)  # club_id -> list of injury records


class InjuryEngine:
    """Handle player injuries and recovery."""

    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)

        # Injury rates (per match)
        self.base_injury_rate = 0.005  # 0.5% per match per player

        # Injury multipliers
        self.fatigue_injury_multiplier = 1.0
        self.high_press_injury_multiplier = 1.5
        self.rivalry_match_injury_multiplier = 1.2
        self.bad_formation_injury_multiplier = 1.3

        # Injury duration distributions (weeks)
        self.minor_duration_range = (1, 3)  # 1-3 weeks
        self.moderate_duration_range = (3, 6)  # 3-6 weeks
        self.serious_duration_range = (8, 12)  # 2-3 months

    def simulate_injury_risk(
        self,
        player: Player,
        match_importance: str = "normal",
        fatigue: float = 0.0,
        team_chemistry: float = 50.0,
    ) -> float:
        """Calculate injury probability for a player for a match."""
        base_risk = self.base_injury_rate

        # Fatigue factor (higher fatigue = higher risk)
        fatigue_factor = 1.0 + ((fatigue / 100) * self.fatigue_injury_multiplier - 1.0)

        # Team chemistry factor (good chemistry reduces risk)
        chemistry_factor = 1.0 - ((team_chemistry / 100) * 0.5)

        # Match importance
        if match_importance == "title_race":
            importance_factor = 1.2  # High pressure games
        elif match_importance == "derby":
            importance_factor = 1.0  # Local derbies
        elif match_importance == "cup":
            importance_factor = 1.3
        else:
            importance_factor = 1.0  # Normal league games

        # Position risk
        position = player.position.value if player.position else "MID"
        high_risk_positions = ["ST", "CF", "CAM", "LW", "RW"]

        if position in high_risk_positions:
            position_factor = 1.1
        elif position in ["CB", "LB", "RB"]:
            position_factor = 1.05
        else:
            position_factor = 1.0

        # Age factor
        age = player.age or 25
        if age > 30:
            age_factor = 1.3
        elif age > 24:
            age_factor = 1.1
        else:
            age_factor = 1.0

        # Calculate total risk
        risk = base_risk * fatigue_factor * chemistry_factor * importance_factor * position_factor * age_factor

        return max(0.001, min(0.05, risk))

    def check_for_injury(
        self,
        player: Player,
        session,
    ) -> bool:
        """Check if player should be injured."""
        # Calculate risk
        risk = self.simulate_injury_risk(player, "normal", player.fitness, 50.0)

        # Roll for injury
        if self.rng.random() < risk:
            return True

        return False

    def generate_injury(self, player: Player, club_id: int, occurred_at: date) -> Injury:
        """Generate a random injury for a player."""
        # Randomly select injury type based on probability weights
        injury_types = [
            InjuryType.MINOR,
            InjuryType.MODERATE,
            InjuryType.SERIOUS,
            InjuryType.FRACTURE,
            InjuryType.CAREER_ENDING,
        ]
        injury_weights = [0.50, 0.30, 0.12, 0.06, 0.02]

        injury_type = self.rng.choices(injury_types, weights=injury_weights)[0]

        # Determine duration
        if injury_type == InjuryType.MINOR:
            weeks = self.rng.randint(*self.minor_duration_range)
        elif injury_type == InjuryType.MODERATE:
            weeks = self.rng.randint(*self.moderate_duration_range)
        elif injury_type == InjuryType.SERIOUS:
            weeks = self.rng.randint(*self.serious_duration_range)
        elif injury_type == InjuryType.FRACTURE:
            weeks = 6
        else:  # CAREER_ENDING
            weeks = 52  # Full year

        # Calculate expected return date
        expected_return = occurred_at + timedelta(weeks=weeks)

        # Determine severity
        severity = min(100, weeks * 2)

        # Determine effects
        effects = []
        if injury_type == InjuryType.MINOR:
            effects.append("Slight performance reduction")
        elif injury_type == InjuryType.MODERATE:
            effects.extend(["Moderate performance reduction", "Reduced mobility"])
        elif injury_type == InjuryType.SERIOUS:
            effects.extend(["Significant performance reduction", "Reduced mobility", "Loss of match fitness"])
        elif injury_type == InjuryType.FRACTURE:
            effects.extend(["Significant performance reduction", "Bone injury", "Extended rehabilitation"])
        else:  # CAREER_ENDING
            effects.extend(["Career-threatening injury", "Extended rehabilitation", "Potential retirement"])

        return Injury(
            injury_id=f"inj_{player.id}_{occurred_at.isoformat()}",
            player_id=player.id,
            club_id=club_id,
            injury_type=injury_type,
            occurred_at=occurred_at,
            expected_return=expected_return,
            status=InjuryStatus.RECOVERING,
            days_out=0,
            severity=severity,
            effects=effects,
        )


class ChemistryEngine:
    """Handle team chemistry calculations."""

    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)

        # Position compatibility factors
        self.position_weights = {
            "GK": {"ST": 0.1, "CB": 0.2, "LB": 0.2, "RB": 0.2},
            "CB": {"ST": 0.15, "CB": 0.25, "LB": 0.2, "RB": 0.2},
            "LB": {"CB": 0.2, "RB": 0.2, "ST": 0.15, "CM": 0.1, "LB": 0.2, "RB": 0.2},
            "RB": {"CB": 0.15, "CM": 0.1, "LB": 0.2, "RB": 0.2},
            "CDM": {"ST": 0.05, "CB": 0.15, "CM": 0.1, "LB": 0.15, "RB": 0.1},
            "CM": {"CM": 0.1, "CB": 0.15, "CDM": 0.25, "LB": 0.15, "RB": 0.1},
            "LM": {"ST": 0.1, "CM": 0.1, "LB": 0.2, "RB": 0.1},
            "RM": {"ST": 0.1, "CM": 0.1, "LB": 0.2, "RB": 0.1},
            "CAM": {"CM": 0.05, "CB": 0.15, "CDM": 0.25, "LB": 0.1, "RB": 0.1},
            "LW": {"ST": 0.15, "CM": 0.2, "CB": 0.3, "LB": 0.2, "RM": 0.2},
            "RW": {"ST": 0.1, "CAM": 0.05, "CB": 0.15, "CM": 0.1, "LW": 0.15, "RW": 0.1},
            "CF": {"ST": 0.25, "CF": 0.35, "CM": 0.2, "CB": 0.15, "CF": 0.3, "LB": 0.25, "RB": 0.2, "CM": 0.1, "LB": 0.2, "RM": 0.2},
            "ST": {"ST": 0.25, "CF": 0.35, "CM": 0.2, "CB": 0.3, "LB": 0.25, "RW": 0.2},
        }

        self.style_compatibility = {
            ("direct", "direct"): 0.9,
            ("direct", "possession"): 0.7,
            ("direct", "tiki_taka"): 0.5,
            ("direct", "counter"): 0.8,
            ("possession", "direct"): 0.7,
            ("possession", "possession"): 0.95,
            ("possession", "tiki_taka"): 0.85,
            ("possession", "counter"): 0.6,
            ("tiki_taka", "direct"): 0.5,
            ("tiki_taka", "possession"): 0.85,
            ("tiki_taka", "tiki_taka"): 1.0,
            ("tiki_taka", "counter"): 0.4,
            ("counter", "direct"): 0.8,
            ("counter", "possession"): 0.6,
            ("counter", "tiki_taka"): 0.4,
            ("counter", "counter"): 0.9,
        }

    def calculate_pairwise_chemistry(
        self,
        player1: Player,
        player2: Player,
    ) -> PlayerChemistry:
        """Calculate chemistry between two players."""
        # Get positions
        pos1 = player1.position.value if player1.position else "MID"
        pos2 = player2.position.value if player2.position else "MID"

        # Get position weights
        pos1_weights = self.position_weights.get(pos1, {})
        pos2_weights = self.position_weights.get(pos2, {})

        # Calculate positional compatibility
        pos_compatibility = 0.0
        for pos in [pos1, pos2]:
            weight = pos1_weights.get(pos, 0)
            pos_compatibility += pos2_weights.get(pos, 0)

        avg_compatibility = pos_compatibility / 2 if pos1 != pos2 else pos_compatibility

        # Determine dominant playing styles
        style1 = "direct" if player1.current_ability > 75 else "possession"
        style2 = "direct" if player2.current_ability > 75 else "possession"

        style_compatibility = self.style_compatibility.get((style1, style2), 0.5)

        avg_style = (style_compatibility + 1.0) / 2

        # Calculate overall positional compatibility
        overall_compatibility = (avg_compatibility * 0.5) + (avg_style * 0.3) + (avg_compatibility * 0.2)

        # Relationship factor
        # Would need to track shared history or interactions
        relationship_score = 50.0  # Default neutral

        # Calculate final chemistry
        compatibility_score = overall_compatibility * 0.7 + relationship_score * 0.3

        return PlayerChemistry(
            player1_id=player1.id,
            player2_id=player2.id,
            compatibility_score=compatibility_score,
            attacking_compatibility=pos_compatibility,
            defensive_compatibility=pos_compatibility,
            tactical_compatibility=avg_style,
            relationship_score=relationship_score,
            relationship_type="neutral",
            attacking_synergy=0.0,
            defensive_synergy=0.0,
        )

    def calculate_team_chemistry(
        self,
        players: List[Player],
        formation: str = "4-3-3",
    ) -> Dict[int, float]:
        """Calculate overall team chemistry for each player in squad."""
        chemistry_scores = {}

        # Calculate pair-wise chemistry for all pairs
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                p1 = players[i]
                p2 = players[j]

                # Skip same player check
                if p1.id == p2.id:
                    continue

                chemistry = self.calculate_pairwise_chemistry(p1, p2)

                # Update chemistry scores
                if p1.id not in chemistry_scores:
                    chemistry_scores[p1.id] = 0.0
                if p2.id not in chemistry_scores:
                    chemistry_scores[p2.id] = 0.0

                chemistry_scores[p1.id] += chemistry.get_total_chemistry()
                chemistry_scores[p2.id] += chemistry.get_total_chemistry()

        # Normalize by number of teammates
        num_players = len(players)
        for player_id in chemistry_scores:
            chemistry_scores[player_id] /= (num_players - 1) if num_players > 1 else 1

        return chemistry_scores

    def get_team_chemistry_modifier(
        self,
        players: List[Player],
    ) -> float:
        """Get overall team chemistry modifier (0.8 to 1.2)."""
        if not players:
            return 1.0

        chemistry_scores = self.calculate_team_chemistry(players)
        avg_chemistry = sum(chemistry_scores.values()) / len(chemistry_scores)

        # Map chemistry to modifier (clamp between 0.8 and 1.2)
        # Base modifier is 0.8 at 30 chemistry, increasing to 1.2 at 70 chemistry
        # Chemistry can range from 0-100+ in practice
        chemistry_factor = max(0, min(100, avg_chemistry))
        modifier = 0.8 + ((chemistry_factor - 30) / 40) * 0.4
        return max(0.8, min(1.2, modifier))
