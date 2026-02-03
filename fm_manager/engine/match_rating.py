"""Match rating calculation system.

Provides position-specific rating calculations for player performance
evaluation in matches.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RatingWeights:
    """Rating weights for different positions."""
    # Offensive weights
    goals_weight: float = 0.5
    assists_weight: float = 0.35
    key_passes_weight: float = 0.08
    shots_on_target_weight: float = 0.05
    crosses_successful_weight: float = 0.05
    dribbles_weight: float = 0.08

    # Defensive weights
    tackles_weight: float = 0.08
    interceptions_weight: float = 0.08
    blocks_weight: float = 0.10
    clearances_weight: float = 0.05
    aerial_duels_won_weight: float = 0.05

    # Passing weights
    passes_completed_weight: float = 0.02

    # Goalkeeper weights
    saves_weight: float = 0.15
    goals_conceded_weight: float = -0.25
    clean_sheet_weight: float = 1.0
    one_on_one_saves_weight: float = 0.20


class MatchRatingCalculator:
    """
    Calculate match ratings based on player statistics and position.

    Rating system:
    - Base rating: 6.0
    - Performance bonuses: goals, assists, key passes, defensive actions
    - Result bonus: winning/losing
    - Range: 4.0 - 10.0
    """

    BASE_RATING = 6.0
    MIN_RATING = 4.0
    MAX_RATING = 10.0

    # Position-specific weights
    POSITION_WEIGHTS = {
        "GK": RatingWeights(
            goals_weight=0.0,
            assists_weight=0.0,
            key_passes_weight=0.0,
            saves_weight=0.15,
            goals_conceded_weight=-0.25,
            clean_sheet_weight=1.0,
            one_on_one_saves_weight=0.20,
            aerial_duels_won_weight=0.10,
        ),
        "DEF": RatingWeights(
            goals_weight=0.50,
            assists_weight=0.30,
            tackles_weight=0.08,
            interceptions_weight=0.08,
            clearances_weight=0.05,
            blocks_weight=0.10,
            aerial_duels_won_weight=0.08,
            passes_completed_weight=0.02,
        ),
        "MID": RatingWeights(
            goals_weight=0.45,
            assists_weight=0.40,
            key_passes_weight=0.10,
            tackles_weight=0.05,
            interceptions_weight=0.05,
            passes_completed_weight=0.02,
            dribbles_weight=0.06,
            crosses_successful_weight=0.03,
        ),
        "ATT": RatingWeights(
            goals_weight=0.50,
            assists_weight=0.35,
            key_passes_weight=0.08,
            shots_on_target_weight=0.05,
            dribbles_weight=0.08,
            crosses_successful_weight=0.03,
        ),
    }

    @classmethod
    def get_position_group(cls, position: str) -> str:
        """Map specific position to position group."""
        position = position.upper()

        # Goalkeepers
        if position == "GK":
            return "GK"

        # Defenders
        if position in ["CB", "LB", "RB", "LWB", "RWB", "DC", "DL", "DR", "SW"]:
            return "DEF"

        # Midfielders
        if position in ["CM", "CDM", "CAM", "LM", "RM", "MC", "ML", "MR", "AMC", "DM"]:
            return "MID"

        # Attackers
        if position in ["ST", "CF", "LW", "RW", "AML", "AMR", "TS", "FS"]:
            return "ATT"

        # Default to midfielder
        return "MID"

    @classmethod
    def calculate(
        cls,
        stats: object,  # PlayerMatchStats or PlayerMatchState
        position: str,
        minutes: int,
        team_score: int,
        opp_score: int,
    ) -> float:
        """
        Calculate match rating for a player.

        Args:
            stats: Player statistics object
            position: Player position
            minutes: Minutes played
            team_score: Team's goals scored
            opp_score: Opponent's goals scored

        Returns:
            Match rating (4.0 - 10.0)
        """
        if minutes == 0:
            return 0.0

        position_group = cls.get_position_group(position)
        weights = cls.POSITION_WEIGHTS[position_group]

        rating = cls.BASE_RATING

        # === Offensive contributions ===
        if hasattr(stats, 'goals'):
            rating += stats.goals * weights.goals_weight
        if hasattr(stats, 'assists'):
            rating += stats.assists * weights.assists_weight
        if hasattr(stats, 'key_passes'):
            rating += stats.key_passes * weights.key_passes_weight

        # === Shot accuracy ===
        if hasattr(stats, 'shots') and hasattr(stats, 'shots_on_target'):
            if stats.shots > 0:
                accuracy = stats.shots_on_target / stats.shots
                rating += (accuracy - 0.5) * weights.shots_on_target_weight

        # === Passing accuracy ===
        if hasattr(stats, 'passes_attempted') and hasattr(stats, 'passes_completed'):
            if stats.passes_attempted > 0:
                pass_accuracy = stats.passes_completed / stats.passes_attempted
                if position_group in ["DEF", "MID"]:
                    rating += (pass_accuracy - 0.75) * weights.passes_completed_weight * 100
                else:
                    rating += (pass_accuracy - 0.70) * weights.passes_completed_weight * 50

        # === Defensive contributions ===
        if hasattr(stats, 'tackles'):
            rating += stats.tackles * weights.tackles_weight
        if hasattr(stats, 'interceptions'):
            rating += stats.interceptions * weights.interceptions_weight
        if hasattr(stats, 'blocks'):
            rating += stats.blocks * weights.blocks_weight
        if hasattr(stats, 'clearances'):
            rating += stats.clearances * weights.clearances_weight

        # === Aerial duels ===
        if hasattr(stats, 'aerial_duels_won') and hasattr(stats, 'aerial_duels_lost'):
            total_aerial = stats.aerial_duels_won + stats.aerial_duels_lost
            if total_aerial > 0:
                win_rate = stats.aerial_duels_won / total_aerial
                rating += (win_rate - 0.5) * weights.aerial_duels_won_weight

        # === Dribbles ===
        if hasattr(stats, 'dribbles') and hasattr(stats, 'dribbles_failed'):
            total_dribbles = stats.dribbles + stats.dribbles_failed
            if total_dribbles > 0:
                success_rate = stats.dribbles / total_dribbles
                rating += (success_rate - 0.5) * weights.dribbles_weight
            rating += stats.dribbles * 0.02

        # === Crosses ===
        if hasattr(stats, 'crosses') and hasattr(stats, 'crosses_successful'):
            if stats.crosses > 0:
                cross_rate = stats.crosses_successful / stats.crosses
                rating += (cross_rate - 0.3) * weights.crosses_successful_weight

        # === Goalkeeper specific ===
        if position_group == "GK":
            if hasattr(stats, 'saves'):
                rating += stats.saves * weights.saves_weight
            if hasattr(stats, 'one_on_one_saves'):
                rating += stats.one_on_one_saves * weights.one_on_one_saves_weight
            if hasattr(stats, 'goals_conceded'):
                rating += stats.goals_conceded * weights.goals_conceded_weight
            if hasattr(stats, 'clean_sheets') and minutes >= 90:
                rating += stats.clean_sheets * weights.clean_sheet_weight

        # === Match result ===
        score_diff = team_score - opp_score
        if score_diff > 0:
            rating += 0.3  # Winner bonus
        elif score_diff == 0:
            rating += 0.1  # Draw bonus
        else:
            rating -= 0.2  # Loser penalty

        # === Minutes played ===
        if minutes >= 90:
            rating += 0.1  # Full match bonus
        elif minutes < 45:
            rating -= 0.2  # Sub penalty

        # === Cards ===
        if hasattr(stats, 'yellow_cards'):
            rating -= stats.yellow_cards * 0.3
        if hasattr(stats, 'red_cards'):
            rating -= stats.red_cards * 1.5

        # === Own goals ===
        if hasattr(stats, 'own_goals'):
            rating -= stats.own_goals * 1.0

        # Clamp to valid range
        return max(cls.MIN_RATING, min(cls.MAX_RATING, rating))

    @classmethod
    def calculate_from_state(
        cls,
        player_state: object,  # PlayerMatchState from match engine
        team_score: int,
        opp_score: int,
    ) -> float:
        """
        Calculate rating from PlayerMatchState (in-match tracking).

        Args:
            player_state: PlayerMatchState object
            team_score: Team's goals
            opp_score: Opponent's goals

        Returns:
            Match rating (4.0 - 10.0)
        """
        position = "MID"
        if hasattr(player_state, 'player') and hasattr(player_state.player, 'position'):
            position = player_state.player.position.value

        return cls.calculate(
            stats=player_state,
            position=position,
            minutes=player_state.minutes_played,
            team_score=team_score,
            opp_score=opp_score,
        )

    @classmethod
    def get_rating_description(cls, rating: float) -> str:
        """Get textual description of rating."""
        if rating >= 9.0:
            return "World Class"
        elif rating >= 8.0:
            return "Excellent"
        elif rating >= 7.0:
            return "Very Good"
        elif rating >= 6.0:
            return "Good"
        elif rating >= 5.0:
            return "Average"
        elif rating >= 4.0:
            return "Poor"
        else:
            return "Terrible"
