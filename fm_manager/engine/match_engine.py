"""Match simulation engine for FM Manager.

The match engine simulates football matches based on:
- Player abilities and form
- Team tactics and formations
- Home/away advantage
- Match events (goals, cards, substitutions)
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Callable

from fm_manager.core.models import Match, MatchStatus, Player, Position, Club


class MatchEventType(Enum):
    """Types of events that can occur during a match."""
    GOAL = auto()
    OWN_GOAL = auto()
    YELLOW_CARD = auto()
    RED_CARD = auto()
    SUBSTITUTION = auto()
    INJURY = auto()
    HALF_TIME = auto()
    FULL_TIME = auto()


@dataclass
class MatchEvent:
    """A single event during a match."""
    minute: int
    event_type: MatchEventType
    team: str  # "home" or "away"
    player: str | None = None
    secondary_player: str | None = None  # For assists, substitutions
    description: str = ""


@dataclass
class TeamStrength:
    """Calculated team strength metrics."""
    overall: float = 0.0
    attack: float = 0.0
    midfield: float = 0.0
    defense: float = 0.0
    
    # Detailed factors
    pace: float = 0.0
    passing: float = 0.0
    shooting: float = 0.0
    defending: float = 0.0
    physical: float = 0.0
    
    # Tactical factors
    formation_bonus: float = 1.0
    chemistry: float = 1.0
    morale: float = 1.0
    fatigue: float = 1.0
    
    def effective_attack(self) -> float:
        """Calculate effective attack strength."""
        return self.attack * self.formation_bonus * self.chemistry * self.morale * self.fatigue
    
    def effective_defense(self) -> float:
        """Calculate effective defense strength."""
        return self.defense * self.formation_bonus * self.chemistry * self.morale * self.fatigue


@dataclass
class MatchState:
    """Current state of a match being simulated."""
    match_id: int
    minute: int = 0
    home_score: int = 0
    away_score: int = 0
    status: MatchStatus = MatchStatus.SCHEDULED
    
    # Events
    events: list[MatchEvent] = field(default_factory=list)
    
    # Player tracking
    home_lineup: list[Player] = field(default_factory=list)
    away_lineup: list[Player] = field(default_factory=list)
    home_subs: list[Player] = field(default_factory=list)
    away_subs: list[Player] = field(default_factory=list)
    
    # Match stats
    home_possession: float = 50.0
    home_shots: int = 0
    home_shots_on_target: int = 0
    home_corners: int = 0
    home_fouls: int = 0
    home_yellows: int = 0
    home_reds: int = 0
    
    away_shots: int = 0
    away_shots_on_target: int = 0
    away_corners: int = 0
    away_fouls: int = 0
    away_yellows: int = 0
    away_reds: int = 0
    
    def score_string(self) -> str:
        """Get current score as string."""
        return f"{self.home_score}-{self.away_score}"
    
    def winning_team(self) -> str | None:
        """Get winning team or None for draw."""
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        return None


class TeamStrengthCalculator:
    """Calculate team strength based on lineup and tactics."""
    
    # Position weights for different areas
    POSITION_ATTACK = {Position.ST, Position.CF, Position.LW, Position.RW}
    POSITION_MIDFIELD = {Position.CM, Position.CAM, Position.CDM, Position.LM, Position.RM}
    POSITION_DEFENSE = {Position.CB, Position.LB, Position.RB, Position.LWB, Position.RWB}
    POSITION_GK = {Position.GK}
    
    def calculate(self, lineup: list[Player], formation: str = "4-3-3") -> TeamStrength:
        """Calculate team strength from lineup.
        
        Args:
            lineup: List of 11 starting players
            formation: Formation string (e.g., "4-3-3", "4-4-2")
        
        Returns:
            TeamStrength object with calculated metrics
        """
        if not lineup:
            return TeamStrength()
        
        strength = TeamStrength()
        
        # Calculate average abilities by area
        attack_ratings = []
        midfield_ratings = []
        defense_ratings = []
        gk_rating = []
        
        # Collect attribute ratings
        pace_ratings = []
        passing_ratings = []
        shooting_ratings = []
        defending_ratings = []
        physical_ratings = []
        
        for player in lineup:
            rating = self._calculate_player_rating(player)
            
            if player.position in self.POSITION_ATTACK:
                attack_ratings.append(rating)
            elif player.position in self.POSITION_MIDFIELD:
                midfield_ratings.append(rating)
            elif player.position in self.POSITION_DEFENSE:
                defense_ratings.append(rating)
            elif player.position in self.POSITION_GK:
                gk_rating.append(rating)
            
            # Collect attributes (handle None with defaults)
            pace_ratings.append(player.pace or 50)
            passing_ratings.append(player.passing or 50)
            shooting_ratings.append(player.shooting or 50)
            # Calculate defending as average of defensive attributes
            tackling = player.tackling or 50
            marking = player.marking or 50
            positioning = player.positioning or 50
            defending_avg = (tackling + marking + positioning) / 3
            defending_ratings.append(defending_avg)
            physical_ratings.append(player.strength or 50)
        
        # Calculate area strengths
        strength.attack = self._weighted_average(attack_ratings, 70) if attack_ratings else 50
        strength.midfield = self._weighted_average(midfield_ratings, 70) if midfield_ratings else 50
        strength.defense = self._weighted_average(defense_ratings, 70) if defense_ratings else 50
        gk_strength = self._weighted_average(gk_rating, 80) if gk_rating else 50
        
        # Overall is weighted average
        strength.overall = (
            strength.attack * 0.25 +
            strength.midfield * 0.30 +
            strength.defense * 0.30 +
            gk_strength * 0.15
        )
        
        # Detailed attributes
        strength.pace = sum(pace_ratings) / len(pace_ratings) if pace_ratings else 50
        strength.passing = sum(passing_ratings) / len(passing_ratings) if passing_ratings else 50
        strength.shooting = sum(shooting_ratings) / len(shooting_ratings) if shooting_ratings else 50
        strength.defending = sum(defending_ratings) / len(defending_ratings) if defending_ratings else 50
        strength.physical = sum(physical_ratings) / len(physical_ratings) if physical_ratings else 50
        
        # Apply modifiers
        strength.formation_bonus = self._formation_bonus(lineup, formation)
        strength.chemistry = self._calculate_chemistry(lineup)
        strength.morale = self._calculate_morale(lineup)
        strength.fatigue = self._calculate_fatigue(lineup)
        
        return strength
    
    def _calculate_player_rating(self, player: Player) -> float:
        """Calculate overall effective rating for a player."""
        base_rating = player.current_ability or 50
        
        # Modifiers (handle None values)
        form = player.form if player.form is not None else 50
        fitness = player.fitness if player.fitness is not None else 100
        morale = player.morale if player.morale is not None else 50
        
        form_factor = (form - 50) / 100  # -0.5 to +0.5
        fitness_factor = fitness / 100
        morale_factor = (morale - 50) / 200  # -0.25 to +0.25
        
        adjusted_rating = base_rating * (1 + form_factor + morale_factor) * fitness_factor
        return max(1, min(99, adjusted_rating))
    
    def _weighted_average(self, values: list[float], weight_for_high: float = 50) -> float:
        """Calculate weighted average favoring higher values."""
        if not values:
            return 50
        
        # Simple average for now, could be more sophisticated
        return sum(values) / len(values)
    
    def _formation_bonus(self, lineup: list[Player], formation: str) -> float:
        """Calculate formation effectiveness bonus."""
        # Parse formation (e.g., "4-3-3" -> [4, 3, 3])
        try:
            parts = formation.split("-")
            defenders = int(parts[0])
            midfielders = int(parts[1])
            attackers = int(parts[2]) if len(parts) > 2 else 1
        except (ValueError, IndexError):
            return 1.0
        
        # Count actual positions
        actual_defenders = sum(1 for p in lineup if p.position in self.POSITION_DEFENSE)
        actual_midfielders = sum(1 for p in lineup if p.position in self.POSITION_MIDFIELD)
        actual_attackers = sum(1 for p in lineup if p.position in self.POSITION_ATTACK)
        
        # Check if formation matches player positions
        matches = (
            abs(defenders - actual_defenders) +
            abs(midfielders - actual_midfielders) +
            abs(attackers - actual_attackers)
        )
        
        # Bonus for good match, penalty for bad match
        return max(0.8, min(1.1, 1.0 - (matches * 0.05)))
    
    def _calculate_chemistry(self, lineup: list[Player]) -> float:
        """Calculate team chemistry based on shared nationality, club, etc."""
        if len(lineup) < 2:
            return 1.0
        
        # Simple chemistry: bonus for shared nationality
        nationalities = [p.nationality for p in lineup]
        most_common = max(set(nationalities), key=nationalities.count)
        shared_count = nationalities.count(most_common)
        
        chemistry = 0.95 + (shared_count / len(lineup)) * 0.1
        return min(1.1, chemistry)
    
    def _calculate_morale(self, lineup: list[Player]) -> float:
        """Calculate team morale from individual player morale."""
        if not lineup:
            return 1.0
        
        avg_morale = sum((p.morale or 50) for p in lineup) / len(lineup)
        return 0.8 + (avg_morale / 100) * 0.4
    
    def _calculate_fatigue(self, lineup: list[Player]) -> float:
        """Calculate fatigue factor."""
        if not lineup:
            return 1.0
        
        avg_fitness = sum((p.fitness or 100) for p in lineup) / len(lineup)
        return 0.7 + (avg_fitness / 100) * 0.3


class MatchSimulator:
    """Simulates a football match."""
    
    # Simulation constants
    HOME_ADVANTAGE = 1.30  # 30% home advantage (includes crowd, familiarity, referee bias)
    MATCH_LENGTH = 90
    
    # Goal probability settings (tuned for ~2.5 goals per match)
    GOAL_CHANCE_PER_MINUTE = 0.035  # Base chance per minute
    ATTACK_MODIFIER = 1.5  # How much attack rating affects goals
    DEFENSE_MODIFIER = 1.2  # How much defense rating affects goals
    
    def __init__(self, random_seed: int | None = None):
        self.rng = random.Random(random_seed)
        self.calculator = TeamStrengthCalculator()
    
    def simulate(
        self,
        home_lineup: list[Player],
        away_lineup: list[Player],
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        callback: Callable[[MatchState], None] | None = None,
    ) -> MatchState:
        """Simulate a full match.
        
        Args:
            home_lineup: 11 home team players
            away_lineup: 11 away team players
            home_formation: Home team formation
            away_formation: Away team formation
            callback: Optional callback called each minute for live updates
        
        Returns:
            Final match state
        """
        # Initialize state
        state = MatchState(
            match_id=0,  # Will be set when saving
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            status=MatchStatus.LIVE,
        )
        
        # Calculate team strengths
        home_strength = self.calculator.calculate(home_lineup, home_formation)
        away_strength = self.calculator.calculate(away_lineup, away_formation)
        
        # Apply home advantage
        home_strength.overall *= self.HOME_ADVANTAGE
        home_strength.attack *= self.HOME_ADVANTAGE
        
        # Simulate each minute
        for minute in range(1, self.MATCH_LENGTH + 1):
            state.minute = minute
            
            # Simulate minute
            self._simulate_minute(state, home_strength, away_strength, minute)
            
            # Call callback if provided
            if callback:
                callback(state)
        
        # Match complete
        state.status = MatchStatus.FULL_TIME
        state.events.append(MatchEvent(
            minute=90,
            event_type=MatchEventType.FULL_TIME,
            team="",
            description=f"Full Time: {state.score_string()}"
        ))
        
        return state
    
    def _simulate_minute(
        self,
        state: MatchState,
        home_strength: TeamStrength,
        away_strength: TeamStrength,
        minute: int,
    ) -> None:
        """Simulate a single minute of play."""
        # Calculate attack/defense ratings
        home_attack = home_strength.effective_attack()
        home_defense = home_strength.effective_defense()
        away_attack = away_strength.effective_attack()
        away_defense = away_strength.effective_defense()
        
        # Calculate goal probabilities for each team this minute
        # Formula: attack vs defense comparison with base rate
        # Higher exponent makes quality differences more pronounced
        home_goal_prob = self.GOAL_CHANCE_PER_MINUTE * (
            (home_attack / (away_defense + 40)) ** 1.2
        )
        away_goal_prob = self.GOAL_CHANCE_PER_MINUTE * (
            (away_attack / (home_defense + 40)) ** 1.2
        )
        
        # Cap probabilities
        home_goal_prob = min(0.08, home_goal_prob)
        away_goal_prob = min(0.08, away_goal_prob)
        
        # Check for home team goal
        if self.rng.random() < home_goal_prob:
            self._score_goal(state, "home", minute)
        
        # Check for away team goal
        if self.rng.random() < away_goal_prob:
            self._score_goal(state, "away", minute)
        
        # Check for cards (low probability)
        if self.rng.random() < 0.008:  # ~0.8% per minute = ~0.7 cards per match
            self._try_card(state, minute)
        
        # Update possession based on midfield battle
        total_midfield = home_strength.midfield + away_strength.midfield
        if total_midfield > 0:
            state.home_possession = 30 + (home_strength.midfield / total_midfield) * 40
        
        # Update shot stats (rough estimation)
        shot_chance = 0.12  # ~11 shots per team per match
        if self.rng.random() < shot_chance:
            if self.rng.random() < (home_attack / (home_attack + away_attack)):
                state.home_shots += 1
                if self.rng.random() < 0.35:  # 35% on target
                    state.home_shots_on_target += 1
            else:
                state.away_shots += 1
                if self.rng.random() < 0.35:
                    state.away_shots_on_target += 1
    
    def _try_goal(
        self,
        state: MatchState,
        home_strength: TeamStrength,
        away_strength: TeamStrength,
        home_pressure: float,
        minute: int,
    ) -> None:
        """Attempt to score a goal."""
        # Determine attacking team
        if self.rng.random() < home_pressure:
            attacking_team = "home"
            attack_strength = home_strength.effective_attack()
            defense_strength = away_strength.effective_defense()
            lineup = state.home_lineup
        else:
            attacking_team = "away"
            attack_strength = away_strength.effective_attack()
            defense_strength = home_strength.effective_defense()
            lineup = state.away_lineup
        
        # Select potential scorers (attackers preferred, but any outfield player can score)
        scoring_players = [p for p in lineup if p.position in TeamStrengthCalculator.POSITION_ATTACK]
        if not scoring_players:
            scoring_players = [p for p in lineup if p.position != Position.GK]
        if not scoring_players:
            scoring_players = lineup
        
        # Calculate goal probability (tuned for realistic match scores)
        goal_chance = attack_strength / (attack_strength + defense_strength + 50)
        goal_chance *= 0.08  # Scale for appropriate goal frequency
        
        if self.rng.random() < goal_chance:
            # Goal scored!
            scorer = self.rng.choice(scoring_players) if scoring_players else None
            
            if attacking_team == "home":
                state.home_score += 1
            else:
                state.away_score += 1
            
            event = MatchEvent(
                minute=minute,
                event_type=MatchEventType.GOAL,
                team=attacking_team,
                player=scorer.full_name if scorer else "Unknown",
                description=f"GOAL! {scorer.full_name if scorer else 'Unknown'} scores!"
            )
            state.events.append(event)
    
    def _score_goal(self, state: MatchState, team: str, minute: int) -> None:
        """Record a goal scored by a team."""
        lineup = state.home_lineup if team == "home" else state.away_lineup
        
        # Select potential scorers (attackers preferred, but any outfield player can score)
        scoring_players = [p for p in lineup if p.position in TeamStrengthCalculator.POSITION_ATTACK]
        if not scoring_players:
            scoring_players = [p for p in lineup if p.position != Position.GK]
        if not scoring_players:
            scoring_players = lineup
        
        # Select scorer (weighted by shooting ability)
        if scoring_players:
            weights = [(p.shooting or 50) + 10 for p in scoring_players]
            total_weight = sum(weights)
            probs = [w / total_weight for w in weights]
            scorer = self.rng.choices(scoring_players, weights=probs)[0]
        else:
            scorer = None
        
        # Update score
        if team == "home":
            state.home_score += 1
        else:
            state.away_score += 1
        
        # Create event
        event = MatchEvent(
            minute=minute,
            event_type=MatchEventType.GOAL,
            team=team,
            player=scorer.full_name if scorer else "Unknown",
            description=f"GOAL! {scorer.full_name if scorer else 'Unknown'} scores!"
        )
        state.events.append(event)
    
    def _try_card(self, state: MatchState, minute: int) -> None:
        """Attempt to give a card."""
        # Simplified: random player gets yellow card
        team = "home" if self.rng.random() < 0.5 else "away"
        lineup = state.home_lineup if team == "home" else state.away_lineup
        
        if lineup:
            player = self.rng.choice(lineup)
            
            # 10% chance of red, 90% yellow
            if self.rng.random() < 0.1:
                event_type = MatchEventType.RED_CARD
                description = f"RED CARD! {player.full_name} is sent off!"
                if team == "home":
                    state.home_reds += 1
                else:
                    state.away_reds += 1
            else:
                event_type = MatchEventType.YELLOW_CARD
                description = f"Yellow card for {player.full_name}"
                if team == "home":
                    state.home_yellows += 1
                else:
                    state.away_yellows += 1
            
            event = MatchEvent(
                minute=minute,
                event_type=event_type,
                team=team,
                player=player.full_name,
                description=description
            )
            state.events.append(event)


def quick_simulate(
    home_rating: int = 75,
    away_rating: int = 70,
    random_seed: int | None = None,
) -> dict:
    """Quick simulation using ratings instead of full player data.
    
    Useful for testing and simple simulations.
    
    Args:
        home_rating: Home team average rating (1-99)
        away_rating: Away team average rating (1-99)
        random_seed: Optional seed for reproducibility
    
    Returns:
        Dictionary with match result
    """
    rng = random.Random(random_seed)
    
    # Simple simulation formula
    home_advantage = 3
    home_effective = home_rating + home_advantage
    
    # Calculate expected goals
    base_xg = 1.3
    home_xg = base_xg * (home_effective / 70)
    away_xg = base_xg * (away_rating / 70)
    
    # Simulate goals using Poisson-like distribution
    home_goals = rng.choices(
        [0, 1, 2, 3, 4, 5],
        weights=[15, 35, 30, 15, 4, 1]
    )[0] if rng.random() < 0.85 else 0
    
    away_goals = rng.choices(
        [0, 1, 2, 3, 4, 5],
        weights=[20, 35, 28, 12, 4, 1]
    )[0] if rng.random() < 0.80 else 0
    
    # Adjust based on rating difference
    rating_diff = home_effective - away_rating
    if rating_diff > 10:
        home_goals += rng.randint(0, 1)
    elif rating_diff < -10:
        away_goals += rng.randint(0, 1)
    
    return {
        "home_goals": home_goals,
        "away_goals": away_goals,
        "score": f"{home_goals}-{away_goals}",
        "winner": "home" if home_goals > away_goals else ("away" if away_goals > home_goals else "draw"),
        "home_xg": round(home_xg, 2),
        "away_xg": round(away_xg, 2),
    }
