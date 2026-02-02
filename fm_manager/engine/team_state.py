"""Team and player dynamic state tracking for season simulation.

This module tracks how team and player form changes throughout a season,
including momentum, fatigue, and morale.
"""

import random
from dataclasses import dataclass, field
from typing import Callable

from fm_manager.core.models import Player, Position


@dataclass
class TeamDynamicState:
    """Dynamic state for a team during a season."""
    club_id: int
    club_name: str
    
    # Momentum tracking
    current_streak: int = 0  # Positive for win streak, negative for loss streak
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    # Morale (0-100, affects performance)
    morale: float = 50.0
    
    # Home/Away form
    home_form: float = 50.0  # 0-100
    away_form: float = 50.0
    
    # Recent performance (last 5 matches rating)
    recent_performance: list[float] = field(default_factory=list)
    
    # Consistency (how stable the team's performance is)
    consistency_rating: float = 50.0
    
    # Key player availability
    key_players_available: int = 0
    total_key_players: int = 0
    
    def __post_init__(self):
        """Initialize default values if needed."""
        if not self.recent_performance:
            self.recent_performance = [50.0] * 5
    
    def update_after_match(
        self,
        result: str,  # 'W', 'D', 'L'
        is_home: bool,
        performance_rating: float,  # 0-100 rating of how well they played
        goals_scored: int,
        goals_conceded: int,
    ) -> None:
        """Update team state after a match."""
        # Update streak
        if result == "W":
            if self.current_streak > 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
            self.max_win_streak = max(self.max_win_streak, self.current_streak)
        elif result == "L":
            if self.current_streak < 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1
            self.max_loss_streak = max(self.max_loss_streak, abs(self.current_streak))
        else:  # Draw
            self.current_streak = 0
        
        # Update morale based on result and streak
        morale_change = 0.0
        if result == "W":
            morale_change = 5.0 + (self.current_streak * 1.5)  # Winning streak boosts morale
        elif result == "L":
            morale_change = -5.0 + (self.current_streak * 1.5)  # Losing streak hurts more
        else:
            morale_change = 0.0  # Draw is neutral
        
        # Adjust morale change based on expectations
        # (e.g., beating a strong team gives more morale)
        morale_change += (performance_rating - 50) * 0.1
        
        self.morale = max(10.0, min(100.0, self.morale + morale_change))
        
        # Update home/away form
        if is_home:
            self.home_form = self.home_form * 0.7 + performance_rating * 0.3
        else:
            self.away_form = self.away_form * 0.7 + performance_rating * 0.3
        
        # Update recent performance
        self.recent_performance.append(performance_rating)
        self.recent_performance = self.recent_performance[-5:]
        
        # Update consistency (lower variance = higher consistency)
        if len(self.recent_performance) >= 3:
            variance = sum((x - 50) ** 2 for x in self.recent_performance) / len(self.recent_performance)
            self.consistency_rating = max(10.0, 100.0 - (variance ** 0.5))
    
    def get_form_modifier(self) -> float:
        """Get a performance modifier based on current form.
        
        Returns a multiplier between 0.8 and 1.2
        """
        # Base modifier from morale
        morale_modifier = 0.9 + (self.morale / 100) * 0.2
        
        # Momentum modifier from streak
        if self.current_streak > 0:
            momentum = min(0.1, self.current_streak * 0.02)  # Max 10% boost
        elif self.current_streak < 0:
            momentum = max(-0.1, self.current_streak * 0.02)  # Max 10% penalty
        else:
            momentum = 0.0
        
        return morale_modifier + momentum
    
    def get_home_advantage_modifier(self) -> float:
        """Get additional home advantage based on home form."""
        base = 1.0
        form_bonus = (self.home_form - 50) / 100 * 0.1  # +/- 10%
        return base + form_bonus
    
    def get_away_disadvantage_modifier(self) -> float:
        """Get away performance modifier based on away form."""
        base = 1.0
        form_bonus = (self.away_form - 50) / 100 * 0.1  # +/- 10%
        return base + form_bonus
    
    def form_string(self, length: int = 5) -> str:
        """Get recent form as a string of W/D/L characters."""
        # Convert recent performance to W/D/L
        form_chars = []
        for perf in self.recent_performance[-length:]:
            if perf >= 65:
                form_chars.append("W")
            elif perf >= 45:
                form_chars.append("D")
            else:
                form_chars.append("L")
        
        return "".join(form_chars) if form_chars else "-----"
    
    def get_form_summary(self) -> dict:
        """Get a summary of current form."""
        return {
            "morale": round(self.morale, 1),
            "streak": self.current_streak,
            "home_form": round(self.home_form, 1),
            "away_form": round(self.away_form, 1),
            "consistency": round(self.consistency_rating, 1),
            "modifier": round(self.get_form_modifier(), 3),
        }


@dataclass
class PlayerMatchState:
    """Track a player's state during a season."""
    player_id: int
    player_name: str
    
    # Physical state
    fitness: float = 100.0  # 0-100
    fatigue: float = 0.0    # 0-100 (inverse of fitness)
    
    # Form and confidence
    form: float = 50.0      # 0-100
    confidence: float = 50.0  # 0-100
    
    # Match history
    matches_played: int = 0
    goals_scored: int = 0
    assists: int = 0
    minutes_played: int = 0
    
    # Recent performances (last 5 match ratings)
    recent_ratings: list[float] = field(default_factory=list)
    
    # Injury status
    is_injured: bool = False
    injury_weeks: int = 0
    
    # Suspension
    is_suspended: bool = False
    suspension_matches: int = 0
    yellow_cards: int = 0
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.recent_ratings:
            self.recent_ratings = [50.0] * 5
    
    def play_match(self, minutes: int = 90, performance_rating: float = 50.0) -> None:
        """Record a match played."""
        self.matches_played += 1
        self.minutes_played += minutes
        
        # Update fitness (players lose fitness after each match)
        fitness_loss = minutes * 0.3  # Lose ~27 fitness per 90 min match
        self.fitness = max(0.0, self.fitness - fitness_loss)
        self.fatigue = 100.0 - self.fitness
        
        # Update form based on performance
        self.form = self.form * 0.7 + performance_rating * 0.3
        
        # Update confidence
        if performance_rating > 60:
            self.confidence = min(100.0, self.confidence + 2.0)
        elif performance_rating < 40:
            self.confidence = max(10.0, self.confidence - 3.0)
        
        # Update recent ratings
        self.recent_ratings.append(performance_rating)
        self.recent_ratings = self.recent_ratings[-5:]
    
    def recover(self, days: int = 7) -> None:
        """Recover fitness between matches."""
        # Players recover ~10-15 fitness per day
        recovery_rate = 12.0
        if self.fitness < 50:  # Extra rest when very tired
            recovery_rate = 15.0
        
        recovery = days * recovery_rate
        self.fitness = min(100.0, self.fitness + recovery)
        self.fatigue = 100.0 - self.fitness
    
    def add_card(self, is_red: bool = False) -> None:
        """Record a card received."""
        if is_red:
            self.is_suspended = True
            self.suspension_matches = 1  # Minimum 1 match
        else:
            self.yellow_cards += 1
            if self.yellow_cards >= 5:  # Suspension after 5 yellows
                self.is_suspended = True
                self.suspension_matches = 1
                self.yellow_cards = 0
    
    def check_injury(self, risk: float = 0.02) -> bool:
        """Check if player gets injured. Higher fatigue = higher risk."""
        if self.is_injured:
            return True
        
        # Fatigue increases injury risk
        fatigue_factor = 1.0 + (self.fatigue / 100) * 2.0  # Up to 3x risk when exhausted
        injury_chance = risk * fatigue_factor
        
        if random.random() < injury_chance:
            self.is_injured = True
            self.injury_weeks = random.randint(1, 4)  # 1-4 weeks out
            return True
        return False
    
    def update_injury(self) -> None:
        """Update injury status (call weekly)."""
        if self.is_injured:
            self.injury_weeks -= 1
            if self.injury_weeks <= 0:
                self.is_injured = False
                self.injury_weeks = 0
                self.fitness = 80.0  # Return at 80% fitness
        
        if self.is_suspended:
            self.suspension_matches -= 1
            if self.suspension_matches <= 0:
                self.is_suspended = False
    
    def is_available(self) -> bool:
        """Check if player is available to play."""
        return not self.is_injured and not self.is_suspended
    
    def get_match_rating(self) -> float:
        """Get expected performance rating for next match."""
        # Base on form, confidence, and fitness
        base = (self.form + self.confidence) / 2
        fitness_penalty = (100 - self.fitness) * 0.3  # Up to 30% penalty
        
        return max(10.0, base - fitness_penalty)
    
    def should_rest(self, threshold: float = 70.0) -> bool:
        """Check if player should be rested due to fatigue."""
        return self.fitness < threshold
    
    def get_state_summary(self) -> dict:
        """Get summary of player state."""
        return {
            "fitness": round(self.fitness, 1),
            "form": round(self.form, 1),
            "confidence": round(self.confidence, 1),
            "available": self.is_available(),
            "should_rest": self.should_rest(),
            "expected_rating": round(self.get_match_rating(), 1),
        }


class TeamStateManager:
    """Manages dynamic state for all teams in a league."""
    
    def __init__(self):
        self.team_states: dict[int, TeamDynamicState] = {}
        self.player_states: dict[int, PlayerMatchState] = {}
    
    def initialize_team(self, club_id: int, club_name: str) -> TeamDynamicState:
        """Initialize state for a team."""
        state = TeamDynamicState(club_id=club_id, club_name=club_name)
        self.team_states[club_id] = state
        return state
    
    def initialize_player(self, player: Player) -> PlayerMatchState:
        """Initialize state for a player."""
        state = PlayerMatchState(
            player_id=player.id,
            player_name=player.full_name,
            fitness=player.fitness or 100.0,
            form=player.form or 50.0,
            confidence=50.0,
        )
        self.player_states[player.id] = state
        return state
    
    def get_team_state(self, club_id: int) -> TeamDynamicState | None:
        """Get state for a team."""
        return self.team_states.get(club_id)
    
    def get_player_state(self, player_id: int) -> PlayerMatchState | None:
        """Get state for a player."""
        return self.player_states.get(player_id)
    
    def get_available_players(self, club_id: int) -> list[PlayerMatchState]:
        """Get all available players for a team."""
        # This would need to be connected to the database
        # For now, return all players that are available
        return [
            state for state in self.player_states.values()
            if state.is_available()
        ]
    
    def get_best_lineup(
        self,
        club_id: int,
        players: list[Player],
        formation: str = "4-3-3"
    ) -> list[Player]:
        """Get the best available lineup considering form and fitness."""
        # Get states for all players
        player_states = [
            (player, self.get_player_state(player.id))
            for player in players
        ]
        
        # Filter available players and calculate effective rating
        available = []
        for player, state in player_states:
            if state is None:
                state = self.initialize_player(player)
            
            if state.is_available():
                effective_rating = state.get_match_rating()
                # Add base ability
                base = player.current_ability or 50
                combined = (base + effective_rating) / 2
                available.append((player, combined, state.fitness))
        
        # Sort by effective rating
        available.sort(key=lambda x: x[1], reverse=True)
        
        # Simple position-based selection (could be more sophisticated)
        # For now, just take top 11 available players
        return [p[0] for p in available[:11]]
    
    def recover_all_players(self, days: int = 7) -> None:
        """Recover all players (call between matchdays)."""
        for state in self.player_states.values():
            state.recover(days)
            state.update_injury()
    
    def get_league_form_table(self) -> list[tuple[str, float, int]]:
        """Get table sorted by current form."""
        form_data = []
        for state in self.team_states.values():
            avg_recent = sum(state.recent_performance) / len(state.recent_performance) if state.recent_performance else 50.0
            form_data.append((state.club_name, avg_recent, state.current_streak))
        
        return sorted(form_data, key=lambda x: x[1], reverse=True)


def calculate_performance_rating(
    goals_scored: int,
    goals_conceded: int,
    possession: float,
    shots_on_target: int,
    is_winner: bool,
) -> float:
    """Calculate a performance rating (0-100) for a team in a match."""
    rating = 50.0  # Base
    
    # Result
    if is_winner:
        rating += 20.0
    elif goals_scored == goals_conceded:
        rating += 5.0
    else:
        rating -= 10.0
    
    # Goal difference
    gd = goals_scored - goals_conceded
    rating += gd * 5.0
    
    # Possession
    rating += (possession - 50) * 0.3
    
    # Attacking threat
    rating += shots_on_target * 1.0
    
    return max(10.0, min(100.0, rating))
