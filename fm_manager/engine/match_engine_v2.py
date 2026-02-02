"""Match simulation engine v2 - Shot-based simulation.

This version simulates matches more realistically:
1. Teams create shot chances based on attack vs defense
2. Shot conversion depends on shooter vs goalkeeper duel
3. No artificial upset probability - emerges naturally from simulation
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
    SHOT_SAVED = auto()  # New: Shot saved by keeper
    SHOT_OFF_TARGET = auto()  # New: Shot missed
    HALF_TIME = auto()
    FULL_TIME = auto()


@dataclass
class MatchEvent:
    """A single event during a match."""
    minute: int
    event_type: MatchEventType
    team: str  # "home" or "away"
    player: str | None = None
    secondary_player: str | None = None  # For assists, keeper saves
    description: str = ""


@dataclass
class TeamStrength:
    """Calculated team strength metrics."""
    overall: float = 0.0
    attack: float = 0.0
    midfield: float = 0.0
    defense: float = 0.0
    
    # Position-specific strengths
    forward_line: float = 0.0  # ST, CF, LW, RW
    midfield_line: float = 0.0  # CM, CAM, CDM, LM, RM
    defense_line: float = 0.0  # CB, LB, RB
    goalkeeper: float = 0.0
    
    # Detailed attributes
    pace: float = 0.0
    passing: float = 0.0
    shooting: float = 0.0
    creativity: float = 0.0  # Vision + Decisions
    defending: float = 0.0
    physical: float = 0.0
    
    # Tactical factors
    formation_bonus: float = 1.0
    chemistry: float = 1.0
    morale: float = 1.0
    fatigue: float = 1.0
    
    def get_attack_strength(self) -> float:
        """Get effective attack strength for creating chances."""
        # Normalize attributes to 0.5-1.5 range for multiplication
        creativity_mod = 0.5 + (self.creativity / 100)  # 0.5-1.5
        pace_mod = 0.5 + (self.pace / 100)  # 0.5-1.5
        return self.forward_line * creativity_mod * pace_mod * self.formation_bonus * self.morale * self.fatigue
    
    def get_defense_strength(self) -> float:
        """Get effective defense strength for preventing chances."""
        defending_mod = 0.5 + (self.defending / 100)  # 0.5-1.5
        physical_mod = 0.5 + (self.physical / 100)  # 0.5-1.5
        return self.defense_line * defending_mod * physical_mod * self.formation_bonus * self.morale * self.fatigue
    
    def get_midfield_control(self) -> float:
        """Get midfield strength for possession."""
        passing_mod = 0.5 + (self.passing / 100)  # 0.5-1.5
        return self.midfield_line * passing_mod * self.formation_bonus * self.morale * self.fatigue


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
    
    # Lineups
    home_lineup: list[Player] = field(default_factory=list)
    away_lineup: list[Player] = field(default_factory=list)
    
    # Detailed stats
    home_possession: float = 50.0
    home_shots: int = 0
    home_shots_on_target: int = 0
    home_shots_saved: int = 0
    home_shots_missed: int = 0
    home_corners: int = 0
    home_fouls: int = 0
    home_yellows: int = 0
    home_reds: int = 0
    home_passes: int = 0
    home_passes_completed: int = 0
    
    away_shots: int = 0
    away_shots_on_target: int = 0
    away_shots_saved: int = 0
    away_shots_missed: int = 0
    away_corners: int = 0
    away_fouls: int = 0
    away_yellows: int = 0
    away_reds: int = 0
    away_passes: int = 0
    away_passes_completed: int = 0
    
    def score_string(self) -> str:
        """Get current score as string."""
        return f"{self.home_score}-{self.away_score}"
    
    def get_shot_accuracy(self, team: str) -> float:
        """Get shot on target percentage."""
        if team == "home":
            return (self.home_shots_on_target / self.home_shots * 100) if self.home_shots > 0 else 0
        else:
            return (self.away_shots_on_target / self.away_shots * 100) if self.away_shots > 0 else 0
    
    def get_conversion_rate(self, team: str) -> float:
        """Get goal conversion rate from shots on target."""
        if team == "home":
            score = self.home_score
            on_target = self.home_shots_on_target
        else:
            score = self.away_score
            on_target = self.away_shots_on_target
        
        return (score / on_target * 100) if on_target > 0 else 0


class TeamStrengthCalculator:
    """Calculate team strength based on lineup and tactics."""
    
    POSITION_FORWARD = {Position.ST, Position.CF, Position.LW, Position.RW}
    POSITION_MIDFIELD = {Position.CM, Position.CAM, Position.CDM, Position.LM, Position.RM, Position.LWB, Position.RWB}
    POSITION_DEFENSE = {Position.CB, Position.LB, Position.RB}
    POSITION_GK = {Position.GK}
    
    def calculate(self, lineup: list[Player], formation: str = "4-3-3") -> TeamStrength:
        """Calculate team strength from lineup."""
        if not lineup:
            return TeamStrength()
        
        strength = TeamStrength()
        
        # Group players by position
        forwards = []
        midfielders = []
        defenders = []
        goalkeeper = None
        
        for player in lineup:
            rating = self._calculate_player_rating(player)
            
            if player.position in self.POSITION_FORWARD:
                forwards.append((player, rating))
            elif player.position in self.POSITION_MIDFIELD:
                midfielders.append((player, rating))
            elif player.position in self.POSITION_DEFENSE:
                defenders.append((player, rating))
            elif player.position in self.POSITION_GK:
                goalkeeper = (player, rating)
        
        # Calculate line strengths (use average, weighted by rating)
        if forwards:
            strength.forward_line = sum(r for _, r in forwards) / len(forwards)
        if midfielders:
            strength.midfield_line = sum(r for _, r in midfielders) / len(midfielders)
        if defenders:
            strength.defense_line = sum(r for _, r in defenders) / len(defenders)
        if goalkeeper:
            strength.goalkeeper = goalkeeper[1]
        
        # Calculate area strengths
        strength.attack = strength.forward_line
        strength.midfield = strength.midfield_line
        strength.defense = strength.defense_line
        
        # Overall
        strength.overall = (
            strength.forward_line * 0.25 +
            strength.midfield_line * 0.30 +
            strength.defense_line * 0.30 +
            (strength.goalkeeper if goalkeeper else 50) * 0.15
        )
        
        # Detailed attributes (average across all players)
        strength.pace = sum(p.pace or 50 for p in lineup) / len(lineup)
        strength.passing = sum(p.passing or 50 for p in lineup) / len(lineup)
        strength.shooting = sum(p.shooting or 50 for p in lineup) / len(lineup)
        strength.creativity = sum((p.vision or 50) + (p.decisions or 50) for p in lineup) / (2 * len(lineup))
        
        # Defending from defenders
        if defenders:
            strength.defending = sum(
                ((p.tackling or 50) + (p.marking or 50) + (p.positioning or 50)) / 3
                for p, _ in defenders
            ) / len(defenders)
        else:
            strength.defending = 50
        
        strength.physical = sum(p.strength or 50 for p in lineup) / len(lineup)
        
        # Modifiers
        strength.formation_bonus = self._formation_bonus(lineup, formation)
        strength.chemistry = self._calculate_chemistry(lineup)
        strength.morale = self._calculate_morale(lineup)
        strength.fatigue = self._calculate_fatigue(lineup)
        
        return strength
    
    def _calculate_player_rating(self, player: Player) -> float:
        """Calculate overall effective rating for a player."""
        base = player.current_ability or 50
        
        form = player.form if player.form is not None else 50
        fitness = player.fitness if player.fitness is not None else 100
        morale = player.morale if player.morale is not None else 50
        
        form_factor = (form - 50) / 100  # -0.5 to +0.5
        fitness_factor = fitness / 100
        morale_factor = (morale - 50) / 200  # -0.25 to +0.25
        
        adjusted = base * (1 + form_factor + morale_factor) * fitness_factor
        return max(1, min(99, adjusted))
    
    def _formation_bonus(self, lineup: list[Player], formation: str) -> float:
        """Calculate formation effectiveness bonus."""
        try:
            parts = formation.split("-")
            exp_def = int(parts[0])
            exp_mid = int(parts[1])
            exp_att = int(parts[2]) if len(parts) > 2 else 1
        except (ValueError, IndexError):
            return 1.0
        
        # Count actual positions
        actual_def = sum(1 for p in lineup if p.position in self.POSITION_DEFENSE)
        actual_mid = sum(1 for p in lineup if p.position in self.POSITION_MIDFIELD)
        actual_att = sum(1 for p in lineup if p.position in self.POSITION_FORWARD)
        
        # Calculate mismatch
        mismatch = abs(exp_def - actual_def) + abs(exp_mid - actual_mid) + abs(exp_att - actual_att)
        
        return max(0.85, min(1.10, 1.0 - (mismatch * 0.05)))
    
    def _calculate_chemistry(self, lineup: list[Player]) -> float:
        """Calculate team chemistry."""
        if len(lineup) < 2:
            return 1.0
        
        nationalities = [p.nationality for p in lineup]
        most_common = max(set(nationalities), key=nationalities.count)
        shared = nationalities.count(most_common)
        
        return 0.95 + (shared / len(nationalities)) * 0.1
    
    def _calculate_morale(self, lineup: list[Player]) -> float:
        """Calculate team morale."""
        if not lineup:
            return 1.0
        
        avg = sum((p.morale or 50) for p in lineup) / len(lineup)
        return 0.8 + (avg / 100) * 0.4
    
    def _calculate_fatigue(self, lineup: list[Player]) -> float:
        """Calculate fatigue factor."""
        if not lineup:
            return 1.0
        
        avg = sum((p.fitness or 100) for p in lineup) / len(lineup)
        return 0.7 + (avg / 100) * 0.3


class MatchSimulatorV2:
    """Shot-based match simulator."""
    
    # Core simulation parameters
    HOME_ADVANTAGE = 1.25
    MATCH_LENGTH = 90
    
    # Shot creation parameters
    BASE_SHOT_CHANCE = 0.08  # 8% chance per minute of a shot opportunity
    
    # Shot outcome probabilities
    SHOT_ON_TARGET_BASE = 0.40  # 40% of shots are on target
    SHOT_OFF_TARGET_BASE = 0.35  # 35% miss
    SHOT_BLOCKED_BASE = 0.25  # 25% blocked (not tracked separately)
    
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
        random_seed: int | None = None,
    ) -> MatchState:
        """Simulate a full match using shot-based system."""
        # Reset RNG if seed provided
        if random_seed is not None:
            self.rng = random.Random(random_seed)
        
        state = MatchState(
            match_id=0,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            status=MatchStatus.LIVE,
        )
        
        # Calculate team strengths
        home_strength = self.calculator.calculate(home_lineup, home_formation)
        away_strength = self.calculator.calculate(away_lineup, away_formation)
        
        # Apply home advantage to attack
        home_strength.attack *= self.HOME_ADVANTAGE
        home_strength.forward_line *= self.HOME_ADVANTAGE
        
        # Simulate each minute
        for minute in range(1, self.MATCH_LENGTH + 1):
            state.minute = minute
            self._simulate_minute(state, home_strength, away_strength, home_lineup, away_lineup)
            
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
        home_lineup: list[Player],
        away_lineup: list[Player],
    ) -> None:
        """Simulate a single minute."""
        # Update possession based on midfield
        total_midfield = home_strength.get_midfield_control() + away_strength.get_midfield_control()
        if total_midfield > 0:
            state.home_possession = 30 + (home_strength.get_midfield_control() / total_midfield) * 40
        
        # Check for home team shot opportunity
        home_attack = home_strength.get_attack_strength()
        away_defense = away_strength.get_defense_strength()
        
        # Shot chance depends on attack vs defense
        home_shot_prob = self.BASE_SHOT_CHANCE * (home_attack / (away_defense + 30)) ** 0.8
        home_shot_prob = min(0.15, home_shot_prob)  # Cap at 15%
        
        if self.rng.random() < home_shot_prob:
            self._simulate_shot(state, "home", home_lineup, away_lineup, away_strength)
        
        # Check for away team shot opportunity
        away_attack = away_strength.get_attack_strength()
        home_defense = home_strength.get_defense_strength()
        
        away_shot_prob = self.BASE_SHOT_CHANCE * (away_attack / (home_defense + 30)) ** 0.8
        away_shot_prob = min(0.15, away_shot_prob)
        
        if self.rng.random() < away_shot_prob:
            self._simulate_shot(state, "away", away_lineup, home_lineup, home_strength)
        
        # Random cards
        if self.rng.random() < 0.008:
            self._try_card(state, "home" if self.rng.random() < 0.5 else "away")
    
    def _simulate_shot(
        self,
        state: MatchState,
        attacking_team: str,
        attacking_lineup: list[Player],
        defending_lineup: list[Player],
        defending_strength: TeamStrength,
    ) -> None:
        """Simulate a single shot attempt."""
        # Update shot count
        if attacking_team == "home":
            state.home_shots += 1
        else:
            state.away_shots += 1
        
        # Select shooter (weighted by shooting ability)
        attackers = [p for p in attacking_lineup if p.position not in {Position.GK}]
        if not attackers:
            attackers = attacking_lineup
        
        shooter = self._select_shooter(attackers)
        if not shooter:
            return
        
        # Determine shot quality (based on shooter ability and pressure)
        shot_quality = (shooter.shooting or 50) + self.rng.gauss(0, 10)  # Add randomness
        
        # Determine if shot is on target
        on_target_threshold = 50  # Base threshold
        shot_quality_factor = (shot_quality - 50) * 0.3  # Better shooters more accurate
        pressure_factor = -10  # Pressure reduces accuracy
        
        on_target_roll = self.rng.random() * 100
        on_target_threshold = self.SHOT_ON_TARGET_BASE * 100 + shot_quality_factor + pressure_factor
        
        is_on_target = on_target_roll < on_target_threshold
        
        if not is_on_target:
            # Shot missed
            if attacking_team == "home":
                state.home_shots_missed += 1
            else:
                state.away_shots_missed += 1
            return
        
        # Shot is on target
        if attacking_team == "home":
            state.home_shots_on_target += 1
        else:
            state.away_shots_on_target += 1
        
        # Find goalkeeper
        keeper = self._get_goalkeeper(defending_lineup)
        keeper_rating = keeper.current_ability if keeper else 50
        keeper_reflexes = keeper.reflexes if keeper else 50
        keeper_handling = keeper.handling if keeper else 50
        
        # Calculate save vs goal probability
        # This is the crucial duel: shooter vs keeper
        shooter_power = (shooter.shooting or 50) + (shooter.decisions or 50) * 0.5
        shooter_power += self.rng.gauss(0, 8)  # Random variation (nerves, luck)
        
        keeper_ability = (keeper_rating + keeper_reflexes + keeper_handling) / 3
        keeper_ability += self.rng.gauss(0, 5)  # Keeper can have good/bad moments
        
        # Goal probability based on shooter vs keeper
        # If shooter is much better than keeper, high goal chance
        # If keeper is better, high save chance
        duel_diff = shooter_power - keeper_ability
        
        # Base goal chance when shot is on target: ~30%
        # Adjusted by duel difference
        goal_chance = 0.30 + (duel_diff / 100) * 0.4  # +/- 20% based on duel
        goal_chance = max(0.05, min(0.70, goal_chance))  # Keep between 5% and 70%
        
        if self.rng.random() < goal_chance:
            # GOAL!
            if attacking_team == "home":
                state.home_score += 1
            else:
                state.away_score += 1
            
            event = MatchEvent(
                minute=state.minute,
                event_type=MatchEventType.GOAL,
                team=attacking_team,
                player=shooter.full_name,
                secondary_player=keeper.full_name if keeper else None,
                description=f"GOAL! {shooter.full_name} scores!"
            )
            state.events.append(event)
        else:
            # Saved by keeper
            if attacking_team == "home":
                state.home_shots_saved += 1
            else:
                state.away_shots_saved += 1
            
            # Only log notable saves (1 in 3 chance)
            if self.rng.random() < 0.33:
                event = MatchEvent(
                    minute=state.minute,
                    event_type=MatchEventType.SHOT_SAVED,
                    team=attacking_team,
                    player=shooter.full_name,
                    secondary_player=keeper.full_name if keeper else "Keeper",
                    description=f"Great save by {keeper.full_name if keeper else 'keeper'}!"
                )
                state.events.append(event)
    
    def _select_shooter(self, players: list[Player]) -> Player | None:
        """Select a shooter weighted by shooting ability and position."""
        if not players:
            return None
        
        # Forwards have higher chance to shoot
        weights = []
        for p in players:
            base_weight = (p.shooting or 50) + 10
            
            # Position multipliers
            if p.position in {Position.ST, Position.CF}:
                base_weight *= 2.0  # Strikers shoot most
            elif p.position in {Position.LW, Position.RW}:
                base_weight *= 1.5  # Wingers shoot second most
            elif p.position in {Position.CAM}:
                base_weight *= 1.3  # Attacking midfielders
            else:
                base_weight *= 0.5  # Defenders rarely shoot
            
            weights.append(base_weight)
        
        total = sum(weights)
        if total == 0:
            return self.rng.choice(players)
        
        probs = [w / total for w in weights]
        return self.rng.choices(players, weights=probs)[0]
    
    def _get_goalkeeper(self, lineup: list[Player]) -> Player | None:
        """Get the goalkeeper from lineup."""
        gks = [p for p in lineup if p.position == Position.GK]
        return gks[0] if gks else None
    
    def _try_card(self, state: MatchState, team: str) -> None:
        """Attempt to give a card."""
        lineup = state.home_lineup if team == "home" else state.away_lineup
        if not lineup:
            return
        
        player = self.rng.choice(lineup)
        
        if self.rng.random() < 0.1:  # 10% red card
            event_type = MatchEventType.RED_CARD
            desc = f"RED CARD! {player.full_name} is sent off!"
            if team == "home":
                state.home_reds += 1
            else:
                state.away_reds += 1
        else:
            event_type = MatchEventType.YELLOW_CARD
            desc = f"Yellow card for {player.full_name}"
            if team == "home":
                state.home_yellows += 1
            else:
                state.away_yellows += 1
        
        event = MatchEvent(
            minute=state.minute,
            event_type=event_type,
            team=team,
            player=player.full_name,
            description=desc
        )
        state.events.append(event)


def quick_simulate_v2(
    home_rating: int = 75,
    away_rating: int = 70,
    home_keeper: int = 70,
    away_keeper: int = 70,
    random_seed: int | None = None,
) -> dict:
    """Quick simulation using ratings."""
    rng = random.Random(random_seed)
    
    # Simulate shots
    home_shots = rng.randint(8, 16)
    away_shots = rng.randint(6, 14)
    
    # Shot quality based on ratings
    home_shot_quality = home_rating + rng.gauss(0, 10)
    away_shot_quality = away_rating + rng.gauss(0, 10)
    
    # On target
    home_on_target = sum(1 for _ in range(home_shots) if rng.random() < 0.4 + (home_shot_quality - 60) * 0.003)
    away_on_target = sum(1 for _ in range(away_shots) if rng.random() < 0.4 + (away_shot_quality - 60) * 0.003)
    
    # Goals (shooter vs keeper duel)
    home_goals = 0
    for _ in range(home_on_target):
        duel = home_shot_quality - away_keeper + rng.gauss(0, 15)
        goal_prob = 0.30 + (duel / 100) * 0.4
        if rng.random() < max(0.05, min(0.70, goal_prob)):
            home_goals += 1
    
    away_goals = 0
    for _ in range(away_on_target):
        duel = away_shot_quality - home_keeper + rng.gauss(0, 15)
        goal_prob = 0.30 + (duel / 100) * 0.4
        if rng.random() < max(0.05, min(0.70, goal_prob)):
            away_goals += 1
    
    return {
        "home_goals": home_goals,
        "away_goals": away_goals,
        "score": f"{home_goals}-{away_goals}",
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_on_target": home_on_target,
        "away_on_target": away_on_target,
        "winner": "home" if home_goals > away_goals else ("away" if away_goals > home_goals else "draw"),
    }
