"""Multi-Position Player System

Implements a proficiency-based system where players have different skill levels
for different positions, affecting how their attributes are utilized.

Key Concepts:
- Base Proficiency (0-100): Natural talent for a position
- Actual Proficiency: Base + training (currently simplified to base)
- Attribute Scaling: sqrt(proficiency/100) * attribute
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class Position(Enum):
    """Standard football positions"""
    # Goalkeepers
    GK = "GK"

    # Defenders
    CB = "CB"
    LB = "LB"
    RB = "RB"
    LWB = "LWB"
    RWB = "RWB"

    # Midfielders
    CDM = "CDM"
    CM = "CM"
    CAM = "CAM"
    LM = "LM"
    RM = "RM"

    # Forwards
    LW = "LW"
    RW = "RW"
    CF = "CF"  # Center Forward
    ST = "ST"  # Striker


@dataclass
class PositionProficiency:
    """Represents a player's proficiency level for a specific position"""
    position: Position
    base_proficiency: float  # 0-100, natural talent
    matches_played: int = 0     # Track experience

    @property
    def actual_proficiency(self) -> float:
        """Current proficiency (base + training, simplified to base for now)"""
        # Could add training progression later
        return min(100.0, self.base_proficiency)

    def get_proficiency_modifier(self) -> float:
        """
        Returns scaling factor for attribute utilization.

        Proficiency 90+ -> 1.05 (slight boost from mastery)
        Proficiency 80-90 -> 1.00 (full utilization)
        Proficiency 70-80 -> 0.95 (slight reduction)
        Proficiency 60-70 -> 0.85 (significant reduction)
        Proficiency <60 -> 0.70 (struggling)
        """
        prof = self.actual_proficiency

        if prof >= 90:
            return 1.05  # Master
        elif prof >= 80:
            return 1.00  # Comfortable
        elif prof >= 70:
            return 0.90  # Learning
        elif prof >= 60:
            return 0.80  # Struggling
        else:
            return 0.70  # Out of position


@dataclass
class MultiPositionPlayer:
    """
    Enhanced player that supports multiple positions with proficiency levels.

    Replaces/extends AdaptedPlayer with position-aware attribute calculation.
    """

    def __init__(self, player_data, primary_position: Position):
        """
        Initialize multi-position player.

        Args:
            player_data: Original player data object
            primary_position: Player's natural/best position
        """
        self._data = player_data
        self.full_name = player_data.name
        self.primary_position = primary_position
        self.nationality = player_data.nationality

        # Base attributes (at natural position)
        self.base_attributes = self._extract_base_attributes(player_data)

        # Position proficiencies
        self.proficiencies: Dict[Position, PositionProficiency] = {}

        # Set primary position proficiency
        self.proficiencies[primary_position] = PositionProficiency(
            position=primary_position,
            base_proficiency=90.0  # Natural position
        )

        # Calculate proficiencies for other positions based on compatibility
        self._calculate_secondary_proficiencies()

    def _extract_base_attributes(self, player_data) -> Dict[str, int]:
        """Extract base attributes at natural position"""
        return {
            'pace': getattr(player_data, 'pace', 70) or 70,
            'shooting': getattr(player_data, 'shooting', 70) or 70,
            'passing': getattr(player_data, 'passing', 70) or 70,
            'dribbling': getattr(player_data, 'dribbling', 70) or 70,
            'tackling': getattr(player_data, 'tackling', 70) or 70,
            'marking': getattr(player_data, 'marking', 70) or 70,
            'positioning': getattr(player_data, 'positioning', 70) or 70,
            'strength': getattr(player_data, 'strength', 70) or 70,
            'current_ability': getattr(player_data, 'current_ability', 70) or 70,
        }

    def _calculate_secondary_proficiencies(self):
        """Calculate proficiency for secondary positions based on compatibility"""
        # Position compatibility matrix
        # Primary -> List of (Secondary, Base Proficiency)
        compatibilities = {
            Position.ST: [(Position.CF, 85), (Position.LW, 70), (Position.RW, 70)],
            Position.CF: [(Position.ST, 85), (Position.CAM, 70)],
            Position.CAM: [(Position.CM, 85), (Position.CM, 80), (Position.LW, 75), (Position.RW, 75), (Position.ST, 70)],
            Position.CM: [(Position.CAM, 80), (Position.CDM, 75), (Position.LM, 65), (Position.RM, 65)],
            Position.LW: [(Position.RW, 80), (Position.LM, 75), (Position.CAM, 75)],
            Position.RW: [(Position.LW, 80), (Position.RM, 75), (Position.CAM, 75)],
            Position.CB: [(Position.LB, 60), (Position.RB, 60)],
            Position.LB: [(Position.LWB, 75), (Position.CB, 60)],
            Position.RB: [(Position.RWB, 75), (Position.CB, 60)],
        }

        primary = self.primary_position

        # Get compatible positions for primary position
        compatible_positions = compatibilities.get(primary, [])

        for secondary, base_prof in compatible_positions:
            if secondary not in self.proficiencies:
                self.proficiencies[secondary] = PositionProficiency(
                    position=secondary,
                    base_proficiency=base_prof
                )

    def get_attributes_for_position(self, position: Position) -> Dict[str, int]:
        """
        Get effective attributes when playing at specific position.

        Adjusts attributes based on position proficiency.
        """
        proficiency = self.proficiencies.get(position)

        if not proficiency:
            # Unknown position - use base attributes with penalty
            proficiency = PositionProficiency(
                position=position,
                base_proficiency=50.0
            )

        modifier = proficiency.get_proficiency_modifier()

        # Apply modifier to attributes
        effective_attrs = {}
        for attr, value in self.base_attributes.items():
            effective_attrs[attr] = int(value * modifier)

        return effective_attrs

    def get_position_modifier(self, position: Position) -> float:
        """
        Get overall modifier for playing at this position.
        Considers: proficiency + natural fit
        """
        proficiency = self.proficiencies.get(position)
        if not proficiency:
            return 0.70  # Heavy penalty for unfamiliar position

        return proficiency.get_proficiency_modifier()

    def can_play_position(self, position: Position) -> bool:
        """Check if player is capable of playing this position (min 50 proficiency)"""
        proficiency = self.proficiencies.get(position)
        if not proficiency:
            # Check if it's compatible
            compatibilities = {
                Position.ST: [Position.CF, Position.LW, Position.RW],
                Position.CF: [Position.ST, Position.CAM],
                Position.CAM: [Position.CM, Position.LW, Position.RW, Position.ST],
                Position.CM: [Position.CAM, Position.CDM, Position.LM, Position.RM],
                Position.LW: [Position.RW, Position.LAM, Position.CAM],
                Position.RW: [Position.LW, Position.RM, Position.CAM],
                Position.CB: [Position.LB, Position.RB],
                Position.LB: [Position.LWB, Position.CB],
                Position.RB: [Position.RWB, Position.CB],
            }

            if position in compatibilities.get(self.primary_position, []):
                # Compatible but not yet initialized - use base proficiency
                self.proficiencies[position] = PositionProficiency(
                    position=position,
                    base_proficiency=60.0
                )
                return True
            return False

        return proficiency.base_proficiency >= 50.0

    def set_current_position(self, position: Position):
        """Set the position player is currently playing at"""
        self.current_position = position


def create_multi_position_player(player_data, primary_position: Position = None) -> MultiPositionPlayer:
    """
    Factory function to create MultiPositionPlayer from PlayerDataFull.

    Auto-detects primary position if not provided.
    """
    if primary_position is None:
        primary_position = _detect_primary_position(player_data)

    return MultiPositionPlayer(player_data, primary_position)


def _detect_primary_position(player_data) -> Position:
    """
    Smart primary position detection based on:
    1. Position ratings
    2. Real football knowledge
    3. Common position mappings
    """
    ratings = {}
    for pos in ['ST', 'CF', 'CAM', 'CM', 'CDM', 'LW', 'RW', 'CB', 'LB', 'RB', 'GK']:
        ratings[pos] = player_data.get_rating_for_position(pos)

    # Find best rated positions
    sorted_positions = sorted(ratings.items(), key=lambda x: x[1], reverse=True)

    if not sorted_positions:
        return Position.CM  # Default

    best_pos, best_rating = sorted_positions[0]

    # Smart position mapping
    position_map = {
        # Forward mappings
        'TS': Position.CF,  # Target Shadow -> Center Forward
        'FS': Position.CF,  # Forward Striker -> Center Forward
        'AML': Position.LW,
        'AMR': Position.RW,
        'Winger': Position.RW,

        # Midfielder mappings
        'MC': Position.CM,
        'ML': Position.LM,
        'MR': Position.RM,
        'DM': Position.CDM,

        # Defender mappings
        'DC': Position.CB,
        'DL': Position.LB,
        'DR': Position.RB,
        'WBL': Position.LWB,
        'WBR': Position.RWB,
    }

    # Use mapping if available
    if best_pos in position_map:
        return position_map[best_pos]

    # Convert string to Position enum
    try:
        return Position[best_pos]
    except KeyError:
        # Default to CM if unknown
        return Position.CM
