"""Match simulation engine v3 - Enhanced realistic simulation.

This version improves on v2 with:
1. Better goal rate calibration (tuned per league)
2. More realistic score distribution
3. Improved home advantage
4. League-specific parameters
5. Better upset mechanics
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
    SHOT_SAVED = auto()
    SHOT_OFF_TARGET = auto()
    HALF_TIME = auto()
    FULL_TIME = auto()


@dataclass
class MatchEvent:
    """A single event during a match."""
    minute: int
    event_type: MatchEventType
    team: str  # "home" or "away"
    player: str | None = None
    secondary_player: str | None = None
    description: str = ""


@dataclass
class TeamStrength:
    """Calculated team strength metrics."""
    overall: float = 0.0
    attack: float = 0.0
    midfield: float = 0.0
    defense: float = 0.0

    # Position-specific strengths
    forward_line: float = 0.0
    midfield_line: float = 0.0
    defense_line: float = 0.0
    goalkeeper: float = 0.0

    # Detailed attributes
    pace: float = 0.0
    passing: float = 0.0
    shooting: float = 0.0
    creativity: float = 0.0
    defending: float = 0.0
    physical: float = 0.0

    # Tactical factors
    formation_bonus: float = 1.0
    chemistry: float = 1.0
    morale: float = 1.0
    fatigue: float = 1.0

    def get_attack_strength(self) -> float:
        """Get effective attack strength for creating chances."""
        creativity_mod = 0.5 + (self.creativity / 100)
        pace_mod = 0.5 + (self.pace / 100)
        return self.forward_line * creativity_mod * pace_mod * self.formation_bonus * self.morale * self.fatigue

    def get_defense_strength(self) -> float:
        base_defense = max(self.defending, 60)
        defending_mod = 0.5 + (base_defense / 100)
        physical_mod = 0.5 + (self.physical / 100)
        return max(self.defense_line, base_defense) * defending_mod * physical_mod * self.formation_bonus * self.morale * self.fatigue

    def get_midfield_control(self) -> float:
        """Get midfield strength for possession."""
        passing_mod = 0.5 + (self.passing / 100)
        return self.midfield_line * passing_mod * self.formation_bonus * self.morale * self.fatigue


@dataclass
class MatchState:
    """Current state of a match being simulated."""
    match_id: int
    minute: int = 0
    home_score: int = 0
    away_score: int = 0
    status: MatchStatus = MatchStatus.SCHEDULED

    events: list[MatchEvent] = field(default_factory=list)

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


class LeagueParameters:
    """League-specific simulation parameters."""

    def __init__(
        self,
        name: str,
        avg_goals_per_match: float,
        home_advantage: float,
        tempo: float,
        upsets: float,
    ):
        self.name = name
        self.avg_goals_per_match = avg_goals_per_match
        self.home_advantage = home_advantage
        self.tempo = tempo
        self.upsets = upsets

    @classmethod
    def get_by_name(cls, name: str) -> "LeagueParameters":
        """Get parameters by league name."""
        params_map = {
            "Premier League": LeagueParameters(
                name="Premier League",
                avg_goals_per_match=2.60,
                home_advantage=1.12,
                tempo=1.12,
                upsets=0.9,
            ),
            "La Liga": LeagueParameters(
                name="La Liga",
                avg_goals_per_match=2.40,
                home_advantage=1.12,
                tempo=1.32,
                upsets=0.85,
            ),
            "Bundesliga": LeagueParameters(
                name="Bundesliga",
                avg_goals_per_match=2.82,
                home_advantage=1.18,
                tempo=1.18,
                upsets=1.15,
            ),
            "Serie A": LeagueParameters(
                name="Serie A",
                avg_goals_per_match=2.25,
                home_advantage=1.12,
                tempo=0.88,
                upsets=0.95,
            ),
            "Bundesliga": LeagueParameters(
                name="Bundesliga",
                avg_goals_per_match=2.75,
                home_advantage=1.15,
                tempo=1.10,
                upsets=1.1,
            ),
            "Serie A": LeagueParameters(
                name="Serie A",
                avg_goals_per_match=2.35,
                home_advantage=1.12,
                tempo=0.85,
                upsets=0.95,
            ),
            "Ligue 1": LeagueParameters(
                name="Ligue 1",
                avg_goals_per_match=2.40,
                home_advantage=1.10,
                tempo=1.08,
                upsets=1.0,
            ),
        }
        return params_map.get(name, LeagueParameters(name, 2.5, 1.15, 1.0, 1.0))


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

        # Calculate line strengths
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

        strength.pace = sum(p.pace or 50 for p in lineup) / len(lineup)
        strength.passing = sum(p.passing or 50 for p in lineup) / len(lineup)
        strength.shooting = sum(
            max(p.shooting or 50, (p.current_ability or 50) * 0.7) for p in lineup
        ) / len(lineup)
        strength.creativity = sum(
            max((p.vision or 50) + (p.decisions or 50), (p.current_ability or 50) * 1.4)
            for p in lineup
        ) / (2 * len(lineup))

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

        form_factor = (form - 50) / 100
        fitness_factor = fitness / 100
        morale_factor = (morale - 50) / 200

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

        actual_def = sum(1 for p in lineup if p.position in self.POSITION_DEFENSE)
        actual_mid = sum(1 for p in lineup if p.position in self.POSITION_MIDFIELD)
        actual_att = sum(1 for p in lineup if p.position in self.POSITION_FORWARD)

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


class MatchSimulatorV3:
    """Enhanced match simulator with league-specific parameters."""

    MATCH_LENGTH = 90

    def __init__(self, league_params: LeagueParameters | None = None, random_seed: int | None = None):
        self.rng = random.Random(random_seed)
        self.calculator = TeamStrengthCalculator()
        self.league_params = league_params or LeagueParameters("Default", 2.5, 1.15, 1.0, 1.0)
        self.BASE_SHOT_CHANCE = 0.065

    def simulate(
        self,
        home_lineup: list[Player],
        away_lineup: list[Player],
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        callback: Callable[[MatchState], None] | None = None,
        random_seed: int | None = None,
    ) -> MatchState:
        """Simulate a full match using enhanced system."""
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

        # Apply league-specific home advantage
        home_strength.attack *= self.league_params.home_advantage
        home_strength.forward_line *= self.league_params.home_advantage

        # Apply league-specific tempo
        temp_factor = self.league_params.tempo

        # Simulate each minute
        for minute in range(1, self.MATCH_LENGTH + 1):
            state.minute = minute
            self._simulate_minute(state, home_strength, away_strength, home_lineup, away_lineup, temp_factor)

            if callback:
                callback(state)

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
        temp_factor: float,
    ) -> None:
        """Simulate a single minute with league adjustments."""
        # Update possession based on midfield
        total_midfield = home_strength.get_midfield_control() + away_strength.get_midfield_control()
        if total_midfield > 0:
            state.home_possession = 30 + (home_strength.get_midfield_control() / total_midfield) * 40

        # Calculate strength gap for upset probability
        strength_gap = abs(home_strength.overall - away_strength.overall)
        upset_bonus = (100 - strength_gap) / 200  # More balanced = higher upsets

        # Check for home team shot opportunity
        home_attack = home_strength.get_attack_strength()
        away_defense = away_strength.get_defense_strength()

        home_shot_prob = self.BASE_SHOT_CHANCE * temp_factor * (home_attack / (away_defense + 30)) ** 0.8
        home_shot_prob *= self.league_params.upsets
        home_shot_prob = min(0.18, home_shot_prob)

        if self.rng.random() < home_shot_prob:
            self._simulate_shot(state, "home", home_lineup, away_lineup, away_strength)

        # Check for away team shot opportunity
        away_attack = away_strength.get_attack_strength()
        home_defense = home_strength.get_defense_strength()

        away_shot_prob = self.BASE_SHOT_CHANCE * temp_factor * (away_attack / (home_defense + 30)) ** 0.8
        away_shot_prob *= self.league_params.upsets
        away_shot_prob = min(0.15, away_shot_prob)  # Away has slightly lower cap

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

        # Select shooter
        attackers = [p for p in attacking_lineup if p.position not in {Position.GK}]
        if not attackers:
            attackers = attacking_lineup

        shooter = self._select_shooter(attackers)
        if not shooter:
            return

        # Shot quality with league-specific variance
        shot_quality = (shooter.shooting or 50) + self.rng.gauss(0, 12 * self.league_params.upsets)

        # V3: Improved on-target calculation
        # Base on-target rate adjusted by league tempo
        base_on_target = 0.48 + (self.league_params.tempo - 1.0) * 0.09
        shot_quality_factor = (shot_quality - 50) * 0.32

        on_target_roll = self.rng.random() * 100
        on_target_threshold = base_on_target * 100 + shot_quality_factor

        is_on_target = on_target_roll < on_target_threshold

        if not is_on_target:
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

        keeper = self._get_goalkeeper(defending_lineup)
        keeper_rating = keeper.current_ability if keeper else 50
        keeper_reflexes = max(keeper.reflexes if keeper else 50, (keeper.current_ability if keeper else 50) * 0.8)
        keeper_handling = max(keeper.handling if keeper else 50, (keeper.current_ability if keeper else 50) * 0.75)

        league_goal_adjustment = (self.league_params.avg_goals_per_match - 2.5) * 0.25

        shooter_rating = max(shooter.shooting or 50, (shooter.current_ability or 50) * 0.75)
        shooter_power = shooter_rating + (shooter.decisions or 50) * 0.5
        shooter_power += self.rng.gauss(0, 10 * self.league_params.upsets)

        keeper_ability = (keeper_rating + keeper_reflexes + keeper_handling) / 3
        keeper_ability += self.rng.gauss(0, 6 * self.league_params.upsets)

        duel_diff = shooter_power - keeper_ability

        goal_chance = 0.58 + (duel_diff / 100) * 0.35 + league_goal_adjustment
        goal_chance = max(0.22, min(0.80, goal_chance))

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

        weights = []
        for p in players:
            effective_shooting = max(p.shooting or 50, (p.current_ability or 50) * 0.75)
            base_weight = effective_shooting + 10

            if p.position in {Position.ST, Position.CF}:
                base_weight *= 2.0
            elif p.position in {Position.LW, Position.RW}:
                base_weight *= 1.5
            elif p.position in {Position.CAM}:
                base_weight *= 1.3
            else:
                base_weight *= 0.5

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

        if self.rng.random() < 0.1:
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


def quick_simulate_v3(
    home_rating: int = 75,
    away_rating: int = 70,
    home_keeper: int = 70,
    away_keeper: int = 70,
    league_params: LeagueParameters | None = None,
    random_seed: int | None = None,
) -> dict:
    """Quick simulation using ratings with league parameters."""
    rng = random.Random(random_seed)
    params = league_params or LeagueParameters("Default", 2.5, 1.15, 1.0, 1.0)

    # Adjust shots by tempo
    home_shots = rng.randint(int(8 * params.tempo), int(16 * params.tempo))
    away_shots = rng.randint(int(6 * params.tempo), int(14 * params.tempo))

    home_shot_quality = home_rating + rng.gauss(0, 10)
    away_shot_quality = away_rating + rng.gauss(0, 10)

    # On target with tempo adjustment
    base_accuracy = 0.40 + (params.tempo - 1.0) * 0.05
    home_on_target = sum(1 for _ in range(home_shots) if rng.random() < base_accuracy + (home_shot_quality - 60) * 0.003)
    away_on_target = sum(1 for _ in range(away_shots) if rng.random() < base_accuracy + (away_shot_quality - 60) * 0.003)

    # Goals with league adjustment
    league_adj = (params.avg_goals_per_match - 2.5) * 0.1

    home_goals = 0
    for _ in range(home_on_target):
        duel = home_shot_quality - away_keeper + rng.gauss(0, 15 * params.upsets)
        goal_prob = 0.30 + (duel / 100) * 0.40 + league_adj
        if rng.random() < max(0.08, min(0.70, goal_prob)):
            home_goals += 1

    away_goals = 0
    for _ in range(away_on_target):
        duel = away_shot_quality - home_keeper + rng.gauss(0, 15 * params.upsets)
        goal_prob = 0.30 + (duel / 100) * 0.40 + league_adj
        if rng.random() < max(0.08, min(0.70, goal_prob)):
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
