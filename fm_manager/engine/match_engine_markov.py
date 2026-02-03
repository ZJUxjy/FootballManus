"""Markov Chain based match engine.

Simulates a football match minute-by-minute with state transitions.
Each minute, based on current game state (pitch zone + ball possession),
calculates probabilities for next events.
"""

import random
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable
from collections import defaultdict

# Import the new PlayerMatchStats class
from fm_manager.engine.team_state import PlayerMatchStats


# ============================================================================
# SHOOTING PROBABILITY MODEL - xG Based
# Expected Goals model with player attributes and shot location
# ============================================================================

def compute_shot_xg(
    shooter_ca: int,
    shooter_shooting: int,
    shooter_positioning: int,
    shooter_strength: int,
    gk_ca: int,
    gk_positioning: int,
    gk_reflexes: int,
    shot_distance: float,    # meters from goal
    shot_angle: float,       # degrees from center (0-90)
    is_header: bool = False,
    is_breakaway: bool = False,  # 单刀机会
    pressure: float = 0.0,    # 0-1, match pressure
    defensive_pressure: float = 0.0  # 0-1, defender pressure (NEW)
) -> dict:
    """
    Calculate shot outcome probabilities using Expected Goals (xG) model.

    Based on modern xG models from football analytics:
    - Distance and angle are primary factors
    - Player attributes modify base probability
    - Goalkeeper quality affects save probability
    - Defender pressure affects shot quality (NEW)

    References:
    - Frontiers in Sports (2021): Goal probability model, RPS 0.197
    - Soccermatics: Fitting the xG model
    - MLFA: Expected Goals model implementation

    Args:
        shooter_ca: Shooter's current_ability (0-100)
        shooter_shooting: Shooter's shooting attribute (0-100)
        shooter_positioning: Shooter's positioning attribute (0-100)
        shooter_strength: Shooter's strength attribute (0-100)
        gk_ca: Goalkeeper's current_ability (0-100)
        gk_positioning: Goalkeeper's positioning attribute (0-100)
        gk_reflexes: Goalkeeper's reflexes attribute (0-100)
        shot_distance: Distance from goal in meters
        shot_angle: Shot angle in degrees (0-90, 0=dead center)
        is_header: Whether this is a header
        is_breakaway: Whether this is a breakaway/one-on-one
        pressure: Match pressure (0-1)
        defensive_pressure: Defender pressure (0-1, 0=no pressure, 1=heavy pressure)

    Returns:
        dict with keys: 'goal', 'save', 'miss', 'xg', 'on_target'
    """
    # ========================================
    # 1. Base xG from shot location
    # ========================================
    # Distance factor: exponential decay
    # 8m = ~0.45, 16m = ~0.25, 25m = ~0.10
    distance_factor = math.exp(-0.095 * shot_distance)

    # Angle factor: better angle = higher probability
    # 0° (center) = 1.0, 45° (wide) = ~0.5
    angle_radians = math.radians(shot_angle)
    angle_factor = math.cos(angle_radians)

    # Base xG before player attributes
    base_xg = 0.48 * distance_factor * angle_factor

    # ========================================
    # 2. Player attribute modifiers
    # ========================================
    # Attacker composite (40% CA + 48% shooting + 9% positioning + 3% strength)
    attacker_score = shooter_ca*(
        shooter_shooting * 0.50 +
        shooter_positioning * 0.3 +
        shooter_strength * 0.2
    )/13.0

    # Goalkeeper composite (40% CA + 30% positioning + 30% reflexes)
    gk_score =  gk_ca*(
        gk_positioning * 0.5 +
        gk_reflexes*0.5
    )/10

    # Skill difference (-100 to +100)
    skill_diff = attacker_score - gk_score

    # Skill factor: amplified to show meaningful difference between players
    # Elite (CA 96) vs Poor (CA 55): ~38 point diff = ~38% boost (goal rate ~45% higher)
    skill_factor = 1.0 + (skill_diff / 100.0)
    skill_factor = max(0.60, min(1.50, skill_factor))

    # ========================================
    # 3. Shot type & pressure modifiers
    # ========================================
    # Headers are less accurate
    if is_header:
        header_penalty = 0.75
    else:
        header_penalty = 1.0

    # Breakaways increase probability
    if is_breakaway:
        breakaway_bonus = 1.15
    else:
        breakaway_bonus = 1.0

    # Match pressure reduces accuracy slightly
    pressure_factor = 1.0 - (0.10 * pressure)

    # Defender pressure significantly reduces shot quality (NEW)
    # Heavy pressure (0.8-1.0) = rushed shot, poor angle
    # Light pressure (0.0-0.3) = time to set up shot
    defender_factor = 1.0 - (0.35 * defensive_pressure)
    defender_factor = max(0.65, min(1.0, defender_factor))

    # ========================================
    # 4. Final xG calculation
    # ========================================
    final_xg = base_xg * skill_factor * header_penalty * breakaway_bonus * pressure_factor * defender_factor

    # Clamp to reasonable range
    final_xg = max(0.03, min(0.65, final_xg))

    # ========================================
    # 5. On-target probability
    # ========================================
    # Better shooters = more accurate
    accuracy_base = 0.50 + (shooter_shooting - 70) * 0.005
    accuracy_base = max(0.35, min(0.75, accuracy_base))

    # Positioning helps accuracy
    positioning_bonus = (shooter_positioning - 70) * 0.003

    # Defender pressure reduces on-target rate (NEW)
    # Under pressure, shots are more hurried
    defender_accuracy_penalty = 0.15 * defensive_pressure

    on_target_prob = accuracy_base + positioning_bonus - defender_accuracy_penalty
    on_target_prob = max(0.25, min(0.80, on_target_prob))

    # ========================================
    # 6. Decompose into goal/save/miss
    # ========================================
    goal_prob = final_xg
    save_prob = max(0, on_target_prob - goal_prob)
    miss_prob = 1.0 - on_target_prob

    return {
        'goal': goal_prob,
        'save': save_prob,
        'miss': miss_prob,
        'xg': final_xg,
        'on_target': on_target_prob
    }


# Legacy functions (kept for compatibility)
FRAME_K = 0.08
SAVE_K = 0.12

def sigmoid(x: float, k: float) -> float:
    """Standard sigmoid function centered at 0."""
    return 1.0 / (1.0 + math.exp(-k * x))

def sigmoid(x: float, k: float) -> float:
    """Standard sigmoid function centered at 0."""
    return 1.0 / (1.0 + math.exp(-k * x))

def compute_shot_probabilities(shooter: float, goalkeeper: float) -> dict:
    """
    Compute shot outcome probabilities based on shooter vs goalkeeper abilities.
    
    Targets:
    - Elite shooter vs elite keeper: ~25-30% goal
    - Elite shooter vs average keeper: ~35-40% goal
    - Average shooter vs elite keeper: ~15-20% goal
    - Average vs average: ~25% goal
    
    Args:
        shooter: Shooter's ability rating (0-100)
        goalkeeper: Goalkeeper's ability rating (0-100)
    
    Returns:
        dict with keys: 'goal', 'save', 'miss', 'frame', 'corner'
    """
    # Base on-target probability (30-60% range)
    shooter = 3.1622*(shooter**0.75)*1.05
    goalkeeper = 3.1622*(goalkeeper**0.75)
    base_on_target = 0.30 + 0.30 * sigmoid((shooter - goalkeeper) / 2, FRAME_K)
    
    # Goal probability given on-target (varies by skill difference)
    if shooter > goalkeeper:
        goal_given_on_target = 0.25 + 0.35 * (shooter - goalkeeper) / 100
    else:
        goal_given_on_target = 0.25 - 0.15 * (goalkeeper - shooter) / 100
    goal_given_on_target = max(0.10, min(0.60, goal_given_on_target))
    
    # Corner/dead angle probability (more likely for less accurate shooters)
    corner_prob = 0.20 * math.exp(-0.05 * shooter)
    
    # Save probabilities
    corner_save = 0.15 * sigmoid(goalkeeper - shooter, SAVE_K) + 0.05
    normal_save = 0.15 + 0.7 * sigmoid(goalkeeper - shooter+20, FRAME_K)
    
    # Calculate final probabilities
    p_corner = base_on_target * corner_prob
    p_normal = base_on_target * (1 - corner_prob)
    
    goal_prob = p_corner * (1 - corner_save) + p_normal * (1 - normal_save)
    save_prob = p_corner * corner_save + p_normal * normal_save
    miss_prob = 1 - base_on_target
    
    return {
        'goal': goal_prob,
        'save': save_prob,
        'miss': miss_prob,
        'frame': base_on_target,
        'corner': corner_prob
    }


def compute_shot_probabilities_with_attributes(
    shooter_ca: int,
    shooter_shooting: int,
    shooter_positioning: int,
    shooter_strength: int,
    gk_ca: int,
    gk_positioning: int,
    gk_reflexes: int
) -> dict:
    """
    Calculate shot outcome probabilities using specific player attributes.

    More realistic two-stage model:
    1) On-target probability driven mostly by shooter accuracy/positioning.
    2) Goal vs save given on-target, driven by shot power vs keeper handling.
    Both stages are moderated by current_ability to reflect absolute level.

    Args:
        shooter_ca: Shooter's current_ability (0-100) - base absolute level
        shooter_shooting: Shooter's shooting attribute (0-100)
        shooter_positioning: Shooter's positioning attribute (0-100)
        shooter_strength: Shooter's strength attribute (0-100)
        gk_ca: Goalkeeper's current_ability (0-100) - base absolute level
        gk_positioning: Goalkeeper's positioning attribute (0-100)
        gk_reflexes: Goalkeeper's reflexes attribute (0-100)

    Returns:
        dict with keys: 'goal', 'save', 'miss', 'frame', 'corner'
    """
    def clamp(val: float, low: float, high: float) -> float:
        return max(low, min(high, val))

    # Composite attributes (0-100)
    shooter_accuracy = (
        shooter_shooting * 0.55 +
        shooter_positioning * 0.25 +
        shooter_ca * 0.20
    )
    shooter_power = (
        shooter_strength * 0.55 +
        shooter_shooting * 0.25 +
        shooter_ca * 0.20
    )
    gk_handling = (
        gk_reflexes * 0.45 +
        gk_positioning * 0.35 +
        gk_ca * 0.20
    )

    # Stage 1: on-target probability (accuracy-driven)
    accuracy_factor = sigmoid((shooter_accuracy - 50) / 7.5, 1.0)
    on_target = clamp(0.22 + 0.40 * accuracy_factor, 0.20, 0.65)

    # Stage 2: goal vs save given on-target (power vs keeper)
    power_diff = shooter_power - gk_handling
    goal_given_on_target = clamp(
        0.18 + 0.35 * sigmoid(power_diff / 10.0, 1.0),
        0.12,
        0.55
    )

    # Corner share of on-target shots (worse accuracy + stronger keeper => more corners)
    corner_share = 0.08 + 0.10 * (1 - accuracy_factor) + 0.06 * sigmoid(-power_diff / 12.0, 1.0)
    corner_share = clamp(corner_share, 0.05, 0.22)

    p_corner = on_target * corner_share
    p_normal = on_target * (1 - corner_share)

    # Save probabilities split by corner/normal
    corner_save = clamp(0.35 + 0.35 * sigmoid(-power_diff / 8.0, 1.0), 0.35, 0.75)
    normal_save = clamp(0.45 + 0.40 * sigmoid(-power_diff / 10.0, 1.0), 0.40, 0.85)

    goal_prob = p_corner * (1 - corner_save) + p_normal * goal_given_on_target
    save_prob = p_corner * corner_save + p_normal * (1 - goal_given_on_target)
    miss_prob = 1 - on_target

    return {
        'goal': goal_prob,
        'save': save_prob,
        'miss': miss_prob,
        'frame': on_target,
        'corner': corner_share
    }


class PitchZone(Enum):
    """Five zones on the pitch."""
    HOME_BOX = auto()      # Home team penalty area
    HOME_THIRD = auto()    # Home team defensive third
    MIDFIELD = auto()      # Middle third
    AWAY_THIRD = auto()    # Away team attacking third  
    AWAY_BOX = auto()      # Away team penalty area


class Possession(Enum):
    """Ball possession state."""
    HOME = auto()
    AWAY = auto()
    DEAD_BALL = auto()  # For set pieces, goals, etc.


class MatchEventType(Enum):
    """All possible match events."""
    # Possession events
    PASS_SUCCESS = auto()
    PASS_FAIL = auto()  # Intercepted or out
    DRIBBLE_SUCCESS = auto()
    DRIBBLE_FAIL = auto()  # Tackled
    
    # Defensive events
    TACKLE = auto()
    INTERCEPTION = auto()
    CLEARANCE = auto()
    
    # Set pieces
    CORNER_HOME = auto()
    CORNER_AWAY = auto()
    GOAL_KICK_HOME = auto()
    GOAL_KICK_AWAY = auto()
    THROW_IN = auto()
    
    # Fouls & Cards
    FOUL = auto()
    FREE_KICK = auto()
    PENALTY = auto()
    YELLOW_CARD = auto()
    RED_CARD = auto()
    
    # Shots
    SHOT_ON_TARGET = auto()
    SHOT_OFF_TARGET = auto()
    SHOT_BLOCKED = auto()
    
    # Goals
    GOAL_HOME = auto()
    GOAL_AWAY = auto()
    
    # Other
    OFFSIDE = auto()
    SUBSTITUTE = auto()
    INJURY = auto()
    
    FULL_TIME = auto()


@dataclass
class GameState:
    """Current state of the game at any minute."""
    minute: int = 0
    zone: PitchZone = PitchZone.MIDFIELD
    possession: Possession = Possession.HOME
    
    # Score
    home_score: int = 0
    away_score: int = 0
    
    # Match context
    home_pressure: float = 0.0  # 0-1, recent attacking momentum
    away_pressure: float = 0.0
    
    # Fatigue factors (degrade over time)
    home_fatigue: dict = field(default_factory=dict)  # player_id -> fatigue
    away_fatigue: dict = field(default_factory=dict)
    
    # Recent events (for context)
    last_event: Optional[MatchEventType] = None
    consecutive_passes: int = 0  # For build-up play
    
    def get_attacking_team(self) -> str:
        """Return which team is attacking."""
        if self.possession == Possession.HOME:
            return "home"
        elif self.possession == Possession.AWAY:
            return "away"
        return "none"


@dataclass
class MatchEvent:
    """A single event in the match."""
    minute: int
    event_type: MatchEventType
    team: str  # "home", "away", or ""
    player: Optional[str] = None
    description: str = ""
    zone: Optional[PitchZone] = None


@dataclass
class PlayerMatchState:
    """Track player performance during match."""
    player: object
    minutes_played: int = 0
    passes_attempted: int = 0
    passes_completed: int = 0
    shots: int = 0
    shots_on_target: int = 0
    tackles: int = 0
    interceptions: int = 0
    fouls: int = 0
    distance_covered: float = 0.0  # km
    fatigue: float = 0.0  # 0-100, increases with minutes
    form_rating: float = 0.0  # Dynamic match rating

    # === New statistics ===
    goals: int = 0
    assists: int = 0
    key_passes: int = 0
    crosses: int = 0
    crosses_successful: int = 0
    dribbles: int = 0
    dribbles_failed: int = 0
    big_chances_created: int = 0
    big_chances_missed: int = 0
    through_balls: int = 0
    blocks: int = 0
    clearances: int = 0
    aerial_duels_won: int = 0
    aerial_duels_lost: int = 0
    offsides: int = 0
    saves: int = 0
    saves_caught: int = 0
    saves_parried: int = 0
    punches: int = 0
    one_on_one_saves: int = 0
    high_claims: int = 0
    goals_conceded: int = 0
    clean_sheets: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    own_goals: int = 0

    def update_fatigue(self, intensity: float = 1.0):
        """Increase fatigue based on activity."""
        base_increase = 0.5 * intensity
        # Stamina affects fatigue accumulation
        if hasattr(self.player, '_data'):
            stamina_factor = 1.0 - (self.player._data.stamina / 200)  # Less stamina = more fatigue
        else:
            stamina_factor = 0.5
        self.fatigue = min(100, self.fatigue + base_increase * (0.5 + stamina_factor))


@dataclass
class MatchState:
    """Full match state for external interface."""
    match_id: int = 0
    minute: int = 0
    home_lineup: list = field(default_factory=list)
    away_lineup: list = field(default_factory=list)
    home_score: int = 0
    away_score: int = 0
    events: list = field(default_factory=list)

    # === Basic Stats ===
    home_shots: int = 0
    home_shots_on_target: int = 0
    away_shots: int = 0
    away_shots_on_target: int = 0
    home_possession: float = 50.0
    home_passes: int = 0
    away_passes: int = 0
    home_fouls: int = 0
    away_fouls: int = 0
    home_corners: int = 0
    away_corners: int = 0

    # === New Team Statistics ===
    # Offensive
    home_key_passes: int = 0
    away_key_passes: int = 0
    home_crosses: int = 0
    away_crosses: int = 0
    home_crosses_successful: int = 0
    away_crosses_successful: int = 0
    home_dribbles: int = 0
    away_dribbles: int = 0
    home_dribbles_failed: int = 0
    away_dribbles_failed: int = 0
    home_big_chances: int = 0
    away_big_chances: int = 0
    home_through_balls: int = 0
    away_through_balls: int = 0

    # Defensive
    home_blocks: int = 0
    away_blocks: int = 0
    home_clearances: int = 0
    away_clearances: int = 0
    home_aerial_duels_won: int = 0
    away_aerial_duels_won: int = 0
    home_aerial_duels_total: int = 0
    away_aerial_duels_total: int = 0
    home_offsides: int = 0
    away_offsides: int = 0

    # Goalkeeper
    home_saves: int = 0
    away_saves: int = 0
    home_goals_conceded: int = 0
    away_goals_conceded: int = 0

    # Player tracking
    home_player_stats: dict = field(default_factory=dict)
    away_player_stats: dict = field(default_factory=dict)
    
    def score_string(self) -> str:
        return f"{self.home_score}-{self.away_score}"
    
    def winning_team(self) -> Optional[str]:
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        return None


class MarkovMatchEngine:
    """
    Match engine based on Markov chains.
    
    State = (PitchZone, Possession)
    Each minute, transition to next state based on probabilities
    influenced by player abilities and tactics.
    """
    
    # Zone transitions (simplified pitch geometry)
    ZONE_PROGRESSION = {
        # Current Zone: [possible next zones with possession change]
        PitchZone.HOME_BOX: {
            "forward": [PitchZone.HOME_THIRD],
            "back": [],  # Can't go back from own box
        },
        PitchZone.HOME_THIRD: {
            "forward": [PitchZone.MIDFIELD, PitchZone.AWAY_THIRD],
            "back": [PitchZone.HOME_BOX],
        },
        PitchZone.MIDFIELD: {
            "forward": [PitchZone.AWAY_THIRD, PitchZone.AWAY_BOX],
            "back": [PitchZone.HOME_THIRD, PitchZone.HOME_BOX],
        },
        PitchZone.AWAY_THIRD: {
            "forward": [PitchZone.AWAY_BOX],
            "back": [PitchZone.MIDFIELD, PitchZone.HOME_THIRD],
        },
        PitchZone.AWAY_BOX: {
            "forward": [],  # Can't go further
            "back": [PitchZone.AWAY_THIRD],
        },
    }
    
    # Base probabilities for different zones
    BASE_EVENT_PROBS = {
        PitchZone.HOME_BOX: {
            # Defensive zone - clearances common, shots rare
            "clearance": 0.28,
            "pass": 0.45,
            "dribble": 0.12,
            "foul": 0.12,
            "shot": 0.03,
        },
        PitchZone.HOME_THIRD: {
            "pass": 0.53,
            "dribble": 0.26,
            "foul": 0.14,
            "clearance": 0.04,
            "shot": 0.03,
        },
        PitchZone.MIDFIELD: {
            "pass": 0.55,
            "dribble": 0.32,
            "foul": 0.10,
            "shot": 0.03,
        },
        PitchZone.AWAY_THIRD: {
            "pass": 0.44,
            "dribble": 0.28,
            "foul": 0.12,
            "shot": 0.16,
        },
        PitchZone.AWAY_BOX: {
            # Attacking zone - shots very likely
            "shot": 0.32,
            "pass": 0.36,
            "dribble": 0.22,
            "foul": 0.10,
        },
    }
    
    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)

        # Assist tracking
        self._last_passer: dict = {}  # {team: (player_state, minute)}
        self._last_key_pass: dict = {}  # {team: (player_state, minute)}

    def get_player_attribute(self, player, attr_name: str, default: int = 70, apply_proficiency: bool = True) -> int:
        """
        Safely get a player attribute, falling back to current_ability if not found.

        If apply_proficiency is True and the player has a get_proficiency_modifier method,
        the attribute value will be adjusted based on the player's proficiency at their
        current position.

        Args:
            player: Player object (AdaptedPlayer or similar)
            attr_name: Name of the attribute to retrieve
            default: Default value if attribute doesn't exist
            apply_proficiency: Whether to apply position proficiency modifier

        Returns:
            Effective attribute value (proficiency-adjusted if enabled)
        """
        value = getattr(player, attr_name, None)
        if value is None:
            value = getattr(player, 'current_ability', default)

        # Apply proficiency modifier if enabled and player supports it
        if apply_proficiency and hasattr(player, 'get_proficiency_modifier') and hasattr(player, 'position'):
            try:
                modifier = player.get_proficiency_modifier(player.position)
                return int(value * modifier)
            except (AttributeError, TypeError):
                # If modifier calculation fails, return base value
                pass

        return value

    def _get_shot_location(self, zone: PitchZone, attacking_team: str) -> tuple[float, float, bool]:
        """
        Determine shot location based on pitch zone.

        Returns:
            (distance_meters, angle_degrees, is_breakaway)
            - distance: Distance from goal in meters (8-35)
            - angle: Angle from goal center in degrees (0-45)
            - is_breakaway: Whether this is likely a 1v1 situation
        """
        # Base distance by zone
        if zone == PitchZone.AWAY_BOX:
            # Penalty area shots (8-12m)
            distance_base = 10.0
            distance_var = 2.5
            angle_base = 15.0
            angle_var = 20.0
            # 10% chance of breakaway in box
            is_breakaway = self.rng.random() < 0.10
        elif zone == PitchZone.AWAY_THIRD:
            # Edge of box shots (16-25m)
            distance_base = 20.0
            distance_var = 5.0
            angle_base = 25.0
            angle_var = 15.0
            is_breakaway = False
        else:
            # Long range shots from midfield (25-35m)
            distance_base = 30.0
            distance_var = 5.0
            angle_base = 30.0
            angle_var = 15.0
            is_breakaway = False

        # Add randomness
        distance = distance_base + self.rng.uniform(-distance_var, distance_var)
        distance = max(8.0, min(35.0, distance))

        angle = angle_base + self.rng.uniform(-angle_var, angle_var)
        angle = max(0.0, min(45.0, angle))

        return distance, angle, is_breakaway

    def simulate(
        self,
        home_lineup: list,
        away_lineup: list,
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        callback: Callable[[MatchState], None] | None = None,
    ) -> MatchState:
        """Simulate a full 90-minute match."""
        
        # Initialize states
        game_state = GameState(
            minute=0,
            zone=PitchZone.MIDFIELD,
            possession=random.choice([Possession.HOME, Possession.AWAY])
        )
        
        match_state = MatchState(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_player_stats={p.full_name: PlayerMatchState(p) for p in home_lineup},
            away_player_stats={p.full_name: PlayerMatchState(p) for p in away_lineup},
        )
        
        # Calculate team strengths for probability adjustments
        home_strength = self._calculate_team_strength(home_lineup)
        away_strength = self._calculate_team_strength(away_lineup)

        # Simulate each minute
        for minute in range(1, 91):
            game_state.minute = minute
            match_state.minute = minute

            # 大比分领先时的战术调整（垃圾时间）
            # 领先方降低进攻欲望，落后方保持进攻欲望
            score_diff = game_state.home_score - game_state.away_score
            # Each minute can have multiple events (a "phase of play")
            # Continue until possession changes or shot taken
            max_events_per_minute = 6
            events_this_minute = 0
            
            while events_this_minute < max_events_per_minute:
                event = self._simulate_minute(
                    game_state, match_state,
                    home_strength, away_strength
                )
                
                if event:
                    match_state.events.append(event)
                    game_state.last_event = event.event_type
                    self._update_stats(match_state, event, game_state)
                    events_this_minute += 1
                    
                    # Stop this minute's sequence if:
                    # - Goal scored (必须break，重新开球)
                    # - Set piece (死球状态)
                    # - 解围/球门球 (球出危险区域)
                    # 
                    # 以下情况继续（不break）：
                    # - 被抢断 → 快速反抢机会
                    # - 射门被挡 → 补射机会
                    # - 射正被扑 → 混战/二点球
                    # - 传球失败 → 争抢落点
                    if event.event_type in [
                        MatchEventType.GOAL_HOME, MatchEventType.GOAL_AWAY,
                        MatchEventType.CORNER_HOME, MatchEventType.CORNER_AWAY,
                        MatchEventType.FREE_KICK, MatchEventType.PENALTY,
                        MatchEventType.CLEARANCE,
                        MatchEventType.SHOT_OFF_TARGET,  # 射偏出界/球门球
                    ]:
                        break
                else:
                    break
            
            # Update fatigue
            self._update_fatigue(match_state, minute)
            
            # Check for substitutions (every 15 mins after 60th)
            if minute in [60, 75, 80, 85]:
                self._check_substitutions(match_state, minute)
            
            # Injury check
            if self.rng.random() < 0.002:
                self._handle_injury(match_state, minute)
            
            if callback:
                callback(match_state)

        # Final event
        match_state.events.append(MatchEvent(
            minute=90,
            event_type=MatchEventType.FULL_TIME,
            team="",
            description=f"Full Time: {match_state.score_string()}"
        ))

        # Calculate final possession
        total_passes = match_state.home_passes + match_state.away_passes
        if total_passes > 0:
            match_state.home_possession = (match_state.home_passes / total_passes) * 100

        # Calculate player match ratings
        self._calculate_match_ratings(match_state)

        # 检查零封 (Clean Sheets)
        # 主队零封
        if match_state.away_score == 0:
            home_goalkeeper = self._select_player(match_state, "home", "gk")
            if home_goalkeeper and home_goalkeeper.minutes_played >= 90:
                home_goalkeeper.clean_sheets += 1

        # 客队零封
        if match_state.home_score == 0:
            away_goalkeeper = self._select_player(match_state, "away", "gk")
            if away_goalkeeper and away_goalkeeper.minutes_played >= 90:
                away_goalkeeper.clean_sheets += 1

        return match_state

    def _calculate_match_ratings(self, match_state: MatchState) -> None:
        """Calculate match rating for each player based on performance."""
        for team in ["home", "away"]:
            player_stats = match_state.home_player_stats if team == "home" else match_state.away_player_stats
            team_score = match_state.home_score if team == "home" else match_state.away_score
            opp_score = match_state.away_score if team == "home" else match_state.home_score

            is_winner = (team_score > opp_score)
            is_draw = (team_score == opp_score)

            for stats in player_stats.values():
                if stats.minutes_played == 0:
                    stats.match_rating = 0.0
                    continue

                # Base rating
                rating = 6.0

                # Get position
                position = stats.player.position.value if hasattr(stats.player, 'position') else "MID"

                # Goals (huge boost)
                if position in ["ST", "CF", "CAM", "LW", "RW"]:
                    rating += stats.goals * 0.7  # Attackers get more for goals
                elif position in ["CM", "CDM", "LM", "RM"]:
                    rating += stats.goals * 0.8  # Mids get even more (rarer)
                else:
                    rating += stats.goals * 1.0  # Defenders/GK goals are very valuable

                # Assists
                rating += stats.assists * 0.5

                # Key passes
                rating += stats.key_passes * 0.08

                # Shot accuracy
                if stats.shots > 0:
                    accuracy = stats.shots_on_target / stats.shots
                    rating += (accuracy - 0.5) * 0.3

                # Pass accuracy
                if stats.passes_attempted > 0:
                    pass_accuracy = stats.passes_completed / stats.passes_attempted
                    if position in ["CB", "LB", "RB", "CDM", "CM"]:
                        rating += (pass_accuracy - 0.75) * 2.0  # Passers valued more
                    else:
                        rating += (pass_accuracy - 0.70) * 1.0

                # Defensive contributions (for defenders/mids)
                if position in ["CB", "LB", "RB", "LWB", "RWB", "CDM", "CM"]:
                    rating += stats.tackles * 0.08
                    rating += stats.interceptions * 0.08
                    rating += stats.blocks * 0.10
                    rating += stats.clearances * 0.05

                # Dribbles (for attackers)
                if position in ["ST", "CF", "CAM", "LW", "RW"]:
                    total_dribbles = stats.dribbles + stats.dribbles_failed
                    if total_dribbles > 0:
                        success_rate = stats.dribbles / total_dribbles
                        rating += (success_rate - 0.5) * 0.5
                    rating += stats.dribbles * 0.05

                # Goalkeeper stats
                if position == "GK":
                    if stats.goals_conceded == 0 and stats.minutes_played >= 90:
                        rating =7.5  # Clean sheet bonus
                        rating += math.log(stats.saves*0.1+1)
                    else:
                        rating += stats.saves * 0.1
                        rating -= stats.goals_conceded * 1.0
                    

                # Match result bonus
                if is_winner:
                    rating += 0.5
                elif is_draw:
                    rating += 0.0
                else:
                    rating -= 0.3

                # Minutes played (full 90 gets slight bonus)
                if stats.minutes_played >= 90:
                    rating += 0.1

                # Cards penalty
                rating -= stats.yellow_cards * 0.3
                rating -= stats.red_cards * 1.5

                # Own goals penalty
                rating -= stats.own_goals * 1.0

                # Clamp rating between 4.0 and 10.0
                stats.match_rating = max(4.0, min(10.0, rating))
    
    def _calculate_team_strength(self, lineup: list) -> dict:
        """Calculate team strength in different areas."""
        # Group by position
        gk = [p for p in lineup if p.position.value == "GK"]
        defs = [p for p in lineup if p.position.value in ["CB", "LB", "RB", "LWB", "RWB"]]
        mids = [p for p in lineup if p.position.value in ["CM", "CDM", "LM", "RM", "CAM"]]
        atts = [p for p in lineup if p.position.value in ["ST", "CF", "LW", "RW"]]
        
        def avg_rating(players):
            if not players:
                return 50.0
            return sum(p.current_ability for p in players) / len(players)
        
        return {
            "gk": avg_rating(gk),
            "def": avg_rating(defs),
            "mid": avg_rating(mids),
            "att": avg_rating(atts),
            "overall": avg_rating(lineup),
        }
    
    def _simulate_minute(
        self,
        game_state: GameState,
        match_state: MatchState,
        home_strength: dict,
        away_strength: dict,
    ) -> Optional[MatchEvent]:
        """Simulate one minute of play."""

        # Get current team stats
        attacking_team = "home" if game_state.possession == Possession.HOME else "away"
        defending_team = "away" if attacking_team == "home" else "home"

        att_strength = home_strength if attacking_team == "home" else away_strength
        def_strength = away_strength if attacking_team == "home" else home_strength

        # 检查是否大比分领先（垃圾时间）
        score_diff = game_state.home_score - game_state.away_score
        is_winning_team = None
        if game_state.minute > 70 and abs(score_diff) >= 3:
            if attacking_team == "home" and score_diff > 0:
                is_winning_team = True  # 主队领先且正在进攻
            elif attacking_team == "away" and score_diff < 0:
                is_winning_team = True  # 客队领先且正在进攻

        # Get event probabilities based on zone
        zone_probs = self.BASE_EVENT_PROBS[game_state.zone].copy()

        # Adjust probabilities based on team strengths
        zone_probs = self._adjust_probs_for_strengths(
            zone_probs, att_strength, def_strength, game_state.zone, is_winning_team
        )
        
        # Select event type
        event_type = self._select_event(zone_probs)
        
        # Execute event and determine outcome
        return self._execute_event(
            event_type, game_state, match_state,
            attacking_team, defending_team,
            att_strength, def_strength
        )
    
    def _adjust_probs_for_strengths(
        self,
        probs: dict,
        att_strength: dict,
        def_strength: dict,
        zone: PitchZone,
        is_winning_team: bool = None,
    ) -> dict:
        """Adjust event probabilities based on team strengths."""
        adjusted = probs.copy()

        # Calculate strength differences
        mid_diff = att_strength["mid"] - def_strength["mid"]  # -50 to +50
        att_diff = att_strength["att"] - def_strength["def"]

        # Better midfield = more successful passes
        if "pass" in adjusted:
            adjusted["pass"] += (mid_diff / 100)  # ±0.50

        # Better attack vs defense = more shots
        if "shot" in adjusted:
            adjusted["shot"] += (att_diff / 130)  # ±0.50

        # Better defense = more clearances
        if "clearance" in adjusted:
            adjusted["clearance"] -= (att_diff / 100)

        # ===== 垃圾时间调整：领先方降低进攻欲望 =====
        if is_winning_team:
            # 领先方在70分钟后领先3球以上：
            # - 降低射门概率50%（控场）
            # - 增加传球概率（倒脚）
            # - 增加解围/回传概率（安全第一）
            if "shot" in adjusted:
                adjusted["shot"] *= 0.5  # 射门减半
            if "pass" in adjusted:
                adjusted["pass"] *= 1.3  # 更多传球
            if "clearance" in adjusted:
                adjusted["clearance"] *= 1.5  # 更多安全回传

        # Normalize to sum to 1
        total = sum(adjusted.values())
        return {k: v/total for k, v in adjusted.items()}
    
    def _select_event(self, probs: dict) -> str:
        """Randomly select an event based on probabilities."""
        r = self.rng.random()
        cumulative = 0
        for event, prob in probs.items():
            cumulative += prob
            if r <= cumulative:
                return event
        return list(probs.keys())[-1]
    
    def _execute_event(
        self,
        event_type: str,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> Optional[MatchEvent]:
        """Execute the selected event and update game state."""
        
        if event_type == "pass":
            return self._handle_pass(game_state, match_state, attacking_team, att_strength, def_strength)
        elif event_type == "dribble":
            return self._handle_dribble(game_state, match_state, attacking_team, defending_team, att_strength, def_strength)
        elif event_type == "shot":
            return self._handle_shot(game_state, match_state, attacking_team, defending_team, att_strength, def_strength)
        elif event_type == "foul":
            return self._handle_foul(game_state, match_state, attacking_team, defending_team, def_strength)
        elif event_type == "clearance":
            return self._handle_clearance(game_state, match_state, defending_team)
        
        return None
    
    def _handle_pass(
        self,
        game_state: GameState,
        match_state: MatchState,
        team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle a pass attempt."""
        
        # Get passer
        passer = self._select_player(match_state, team, "mid" if game_state.zone == PitchZone.MIDFIELD else "att")
        if passer:
            passer.passes_attempted += 1
            passer.update_fatigue(0.3)
        
        # Success probability using player attributes
        # Pass: 40% CA (base level) + 36% passing + 18% positioning + 6% pace
        # Defense: 60% marking, 40% positioning
        if passer:
            ca = passer.player.current_ability
            passing = self.get_player_attribute(passer.player, 'passing', 70)
            positioning = self.get_player_attribute(passer.player, 'positioning', 70)
            pace = self.get_player_attribute(passer.player, 'pace', 70)
            attacker_score = ca * 0.40 + passing * 0.36 + positioning * 0.18 + pace * 0.06
        else:
            attacker_score = att_strength["mid"]

        # Get defender rating (use team average for zone defense)
        defender_score = def_strength["mid"]

        success_prob = 0.74 + (attacker_score - defender_score) / 200
        success_prob = max(0.54, min(0.92, success_prob))
        
        success = self.rng.random() < success_prob
        
        if success:
            # Move forward or sideways
            new_zone = self._advance_zone(game_state.zone, team)
            game_state.zone = new_zone
            game_state.consecutive_passes += 1

            if passer:
                passer.passes_completed += 1

                # 记录潜在助攻传球（改进版）
                # 助攻来源：
                # 1. 危险区域传球（禁区、进攻三区）
                # 2. 中场向前传球（推进到进攻区域）
                # 3. 传球属性高的球员更有可能创造助攻
                is_forward_pass = (new_zone != game_state.zone) and (
                    (team == "home" and new_zone.value > game_state.zone.value) or
                    (team == "away" and new_zone.value < game_state.zone.value)
                )

                passing_attr = getattr(passer.player, 'passing', None) or passer.player.current_ability

                # 危险区域直接记录
                if game_state.zone in [PitchZone.AWAY_BOX, PitchZone.AWAY_THIRD]:
                    self._last_passer[team] = (passer, game_state.minute)
                    self._last_key_pass[team] = (passer, game_state.minute)
                # 中场向前传球，且传球属性高（>75）记录
                elif game_state.zone == PitchZone.MIDFIELD and is_forward_pass and passing_attr > 75:
                    self._last_passer[team] = (passer, game_state.minute)

                # 清理过期的助攻记录（超过1.5分钟的传球不算助攻）
                if team in self._last_passer:
                    _, pass_minute = self._last_passer[team]
                    if game_state.minute - pass_minute > 1.5:
                        del self._last_passer[team]

            # Update possession stats
            if team == "home":
                match_state.home_passes += 1
            else:
                match_state.away_passes += 1
            
            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.PASS_SUCCESS,
                team=team,
                player=passer.player.full_name if passer else None,
                description=f"Pass completed, moving into {new_zone.name}",
                zone=game_state.zone
            )
        else:
            # Intercepted or failed
            game_state.possession = Possession.AWAY if team == "home" else Possession.HOME
            game_state.consecutive_passes = 0
            
            # Pass intercepted - but ball is loose
            # 60% chance: 防守方拦截但球权不稳，进攻方可以反抢（继续）
            # 40% chance: 防守方彻底控制（会break）
            second_ball_prob = 0.60
            
            if self.rng.random() < second_ball_prob:
                # 球权转换但进攻方可以反抢
                game_state.possession = Possession.AWAY if team == "home" else Possession.HOME
                game_state.consecutive_passes = 0
                
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.PASS_FAIL,
                    team=team,
                    player=passer.player.full_name if passer else None,
                    description="Pass intercepted - loose ball, second ball chance",
                    zone=game_state.zone
                )
            else:
                # 防守方彻底控制
                game_state.possession = Possession.AWAY if team == "home" else Possession.HOME
                game_state.consecutive_passes = 0
                
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.PASS_FAIL,
                    team=team,
                    player=passer.player.full_name if passer else None,
                    description="Pass intercepted - defense gains control",
                    zone=game_state.zone
                )
    
    def _handle_dribble(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle a dribble attempt."""
        
        # Select dribbler (attacker)
        dribbler = self._select_player(match_state, attacking_team, "att")
        if dribbler:
            dribbler.update_fatigue(0.5)
        
        # Success based on player attributes
        # Dribble: 40% CA (base level) + 30% dribbling + 18% pace + 12% strength
        # Defense: 50% tackling, 30% positioning, 20% strength
        if dribbler:
            ca = dribbler.player.current_ability
            dribbling = self.get_player_attribute(dribbler.player, 'dribbling', 70)
            pace = self.get_player_attribute(dribbler.player, 'pace', 70)
            strength = self.get_player_attribute(dribbler.player, 'strength', 70)
            attacker_score = ca * 0.40 + dribbling * 0.30 + pace * 0.18 + strength * 0.12
        else:
            attacker_score = att_strength["att"]

        defender_score = def_strength["def"]

        success_prob = 0.58 + (attacker_score - defender_score) / 155
        success_prob = max(0.38, min(0.82, success_prob))
        
        success = self.rng.random() < success_prob
        
        if success:
            new_zone = self._advance_zone(game_state.zone, attacking_team)
            game_state.zone = new_zone

            if dribbler:
                dribbler.dribbles += 1

            # Update team dribble stats
            if attacking_team == "home":
                match_state.home_dribbles += 1
            else:
                match_state.away_dribbles += 1

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.DRIBBLE_SUCCESS,
                team=attacking_team,
                player=dribbler.player.full_name if dribbler else None,
                description=f"Dribble successful into {new_zone.name}",
                zone=game_state.zone
            )
        else:
            # Tackled - but ball is loose, chance for second ball/scramble
            tackler = self._select_player(match_state, defending_team, "def")
            if tackler:
                tackler.tackles += 1

            if dribbler:
                dribbler.dribbles_failed += 1

            # Update team dribble stats
            if attacking_team == "home":
                match_state.home_dribbles_failed += 1
            else:
                match_state.away_dribbles_failed += 1

            # 70% chance: 防守方抢到球权但进攻方可以反抢（不break，继续）
            # 30% chance: 防守方彻底控制（会break，因为不在列表里了）
            scramble_prob = 0.70
            
            if self.rng.random() < scramble_prob:
                # 混战状态：球权转换但进攻方可以立即反抢
                # 球在原地附近，不移动zone
                game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
                
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.TACKLE,
                    team=defending_team,
                    player=tackler.player.full_name if tackler else None,
                    description="Tackle - ball loose, scramble for possession",
                    zone=game_state.zone
                )
            else:
                # 防守方彻底控制
                game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
                game_state.consecutive_passes = 0
                
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.TACKLE,
                    team=defending_team,
                    player=tackler.player.full_name if tackler else None,
                    description="Tackle won cleanly",
                    zone=game_state.zone
                )
    
    def _handle_shot(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle a shot attempt."""
        
        # Select shooter based on zone and build-up
        shooter = self._select_shooter(match_state, attacking_team, game_state)
        if shooter:
            shooter.shots += 1
            shooter.update_fatigue(0.7)
        
        shooter_rating = att_strength["att"] if shooter is None else shooter.player.current_ability
        gk_rating = def_strength["gk"]

        # ========================================================================
        # xG-BASED SHOOTING MODEL WITH PLAYER ATTRIBUTES
        # Expected Goals model: distance, angle, player skills, goalkeeper quality
        # ========================================================================
        # Get shot location based on zone
        shot_distance, shot_angle, is_breakaway = self._get_shot_location(
            game_state.zone, attacking_team
        )

        # Determine if header (15% chance for in-box shots, lower outside)
        is_header = False
        if shooter and game_state.zone == PitchZone.AWAY_BOX:
            # Headers more likely in the box
            header_chance = 0.20 if shooter.player.position.value in ["ST", "CF"] else 0.10
            is_header = self.rng.random() < header_chance

        # Get shooter attributes
        if shooter:
            shooting = self.get_player_attribute(shooter.player, 'shooting', 70)
            shooter_positioning = self.get_player_attribute(shooter.player, 'positioning', 70)
            shooter_strength = self.get_player_attribute(shooter.player, 'strength', 70)
        else:
            shooting = shooter_rating
            shooter_positioning = 70
            shooter_strength = 70

        # Get goalkeeper
        goalkeeper = self._select_player(match_state, defending_team, "gk")
        if goalkeeper:
            gk_positioning = self.get_player_attribute(goalkeeper.player, 'positioning', 70)
            gk_reflexes = self.get_player_attribute(goalkeeper.player, 'positioning', 70)
            gk_ca = goalkeeper.player.current_ability
        else:
            gk_positioning = gk_rating
            gk_reflexes = gk_rating
            gk_ca = gk_rating

        # Calculate match pressure (score difference in late stages)
        pressure = 0.0
        if game_state.minute > 75:
            score_diff = abs(game_state.home_score - game_state.away_score)
            if score_diff <= 1:
                pressure = 0.3  # High pressure in close late games

        # ========================================
        # Calculate defender pressure (NEW)
        # ========================================
        defensive_pressure = 0.0

        # If not a breakaway, select defender and calculate pressure
        if not is_breakaway:
            # Select a defender (60% chance we have one involved)
            if self.rng.random() < 0.60:
                defender = self._select_player(match_state, defending_team, "def")
                if defender:
                    # Calculate defender pressure based on defensive attributes
                    # Higher tackling, marking, positioning = more pressure on shooter
                    tackling = self.get_player_attribute(defender.player, 'tackling', 70)
                    marking = self.get_player_attribute(defender.player, 'marking', 70)
                    def_positioning = self.get_player_attribute(defender.player, 'positioning', 70)

                    # Defender composite score
                    defender_score = tackling * 0.40 + marking * 0.35 + def_positioning * 0.25

                    # Pressure = 0.0 (poor defender) to 0.8 (elite defender)
                    # Average defender (70) = 0.35 pressure
                    defensive_pressure = (defender_score - 50) / 100.0
                    defensive_pressure = max(0.0, min(0.8, defensive_pressure))

        # Compute outcome probabilities using xG model
        probs = compute_shot_xg(
            shooter_ca=shooter_rating,
            shooter_shooting=shooting,
            shooter_positioning=shooter_positioning,
            shooter_strength=shooter_strength,
            gk_ca=gk_ca,
            gk_positioning=gk_positioning,
            gk_reflexes=gk_reflexes,
            shot_distance=shot_distance,
            shot_angle=shot_angle,
            is_header=is_header,
            is_breakaway=is_breakaway,
            pressure=pressure,
            defensive_pressure=defensive_pressure  # NEW parameter
        )
        
        # Roll for outcome
        roll = self.rng.random()
        
        if roll < probs['miss']:
            # =====================================================================
            # OUTCOME: MISS (射偏)
            # =====================================================================
            # Determine miss type based on zone
            miss_type = self.rng.random()
            
            if miss_type < 0.5:
                # 50%: 直接射偏出界 → 球门球
                gk_zone = PitchZone.HOME_BOX if attacking_team == "away" else PitchZone.AWAY_BOX
                game_state.zone = gk_zone
                game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_OFF_TARGET,
                    team=attacking_team,
                    player=shooter.player.full_name if shooter else None,
                    description="Shot missed wide - goal kick",
                    zone=game_state.zone
                )
            elif miss_type < 0.8:
                # 30%: 打偏但造成角球
                game_state.possession = Possession.DEAD_BALL
                if attacking_team == "home":
                    match_state.home_corners += 1
                    return MatchEvent(
                        minute=game_state.minute,
                        event_type=MatchEventType.CORNER_HOME,
                        team=attacking_team,
                        player=shooter.player.full_name if shooter else None,
                        description="Shot deflected for corner",
                        zone=game_state.zone
                    )
                else:
                    match_state.away_corners += 1
                    return MatchEvent(
                        minute=game_state.minute,
                        event_type=MatchEventType.CORNER_AWAY,
                        team=attacking_team,
                        player=shooter.player.full_name if shooter else None,
                        description="Shot deflected for corner",
                        zone=game_state.zone
                    )
            else:
                # 20%: 被封堵后反弹
                rebound_prob = 0.60
                if self.rng.random() < rebound_prob:
                    return MatchEvent(
                        minute=game_state.minute,
                        event_type=MatchEventType.SHOT_BLOCKED,
                        team=attacking_team,
                        player=shooter.player.full_name if shooter else None,
                        description="Shot blocked - REBOUND! attack continues",
                        zone=game_state.zone
                    )
                else:
                    game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
                    return MatchEvent(
                        minute=game_state.minute,
                        event_type=MatchEventType.SHOT_BLOCKED,
                        team=attacking_team,
                        player=shooter.player.full_name if shooter else None,
                        description="Shot blocked by defender - defense clears",
                        zone=game_state.zone
                    )
        
        elif roll < probs['miss'] + probs['save']:
            # =====================================================================
            # OUTCOME: SAVE (射正被扑出)
            # =====================================================================
            if shooter:
                shooter.shots_on_target += 1

            # Track key pass for the shot
            if attacking_team in self._last_key_pass:
                key_passer, _ = self._last_key_pass[attacking_team]
                key_passer.key_passes += 1
                del self._last_key_pass[attacking_team]

            if attacking_team == "home":
                match_state.home_shots += 1
                match_state.home_shots_on_target += 1
            else:
                match_state.away_shots += 1
                match_state.away_shots_on_target += 1

            # 记录门将扑救统计
            goalkeeper = self._select_player(match_state, defending_team, "gk")
            save_type = "caught"
            if goalkeeper:
                goalkeeper.saves += 1

                # 扑救质量计算：基于门将和射手的能力对比
                gk_rating = goalkeeper.player.current_ability if goalkeeper else 70
                shooter_rating = shooter.player.current_ability if shooter else 70

                # 基础扑稳率 50%
                # 门将能力越高，扑稳率越高（+0.5% per ability）
                # 射手能力越高，扑稳率越低（-0.3% per ability）
                base_caught_prob = 0.50
                gk_bonus = (gk_rating - 70) * 0.005  # ±10% for 50-90 ability
                shooter_penalty = (shooter_rating - 70) * 0.003  # ±6% for 50-90 ability

                caught_prob = base_caught_prob + gk_bonus - shooter_penalty
                caught_prob = max(0.30, min(0.85, caught_prob))  # 限制在 30%-85%

                if self.rng.random() < caught_prob:
                    goalkeeper.saves_caught += 1
                    save_type = "caught"
                    # 扑稳的球，反弹概率更低（20%）
                    rebound_prob = 0.20
                else:
                    goalkeeper.saves_parried += 1
                    save_type = "parried"
                    # 扑出的球，反弹概率更高（60%）
                    rebound_prob = 0.60

                # 更新团队扑救统计
                if defending_team == "home":
                    match_state.home_saves += 1
                else:
                    match_state.away_saves += 1
            else:
                # 没有门将信息，使用默认值
                rebound_prob = 0.50
            if self.rng.random() < rebound_prob:
                # Rebound opportunity
                gk_name = goalkeeper.player.full_name if goalkeeper else "Goalkeeper"
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_ON_TARGET,
                    team=attacking_team,
                    player=shooter.player.full_name if shooter else None,
                    description=f"Great {save_type} save by {gk_name}! - REBOUND!",
                    zone=game_state.zone
                )
            else:
                # Keeper holds the ball
                game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
                game_state.zone = PitchZone.HOME_BOX if attacking_team == "away" else PitchZone.AWAY_BOX
                gk_name = goalkeeper.player.full_name if goalkeeper else "Goalkeeper"
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_ON_TARGET,
                    team=attacking_team,
                    player=shooter.player.full_name if shooter else None,
                    description=f"Shot saved by {gk_name} ({save_type})",
                    zone=game_state.zone
                )
        
        else:
            # =====================================================================
            # OUTCOME: GOAL (进球！)
            # =====================================================================
            if shooter:
                shooter.shots += 1
                shooter.shots_on_target += 1
                shooter.goals += 1  # Track goals in player stats

            # Check for assist (1-minute window)
            # 助攻是直接的传球配合，但允许一定的连续传递时间
            if attacking_team in self._last_passer:
                assister, pass_minute = self._last_passer[attacking_team]
                if game_state.minute - pass_minute <= 1.0:  # 1分钟窗口
                    assister.assists += 1
                    # Clear after successful assist
                    del self._last_passer[attacking_team]

            if attacking_team == "home":
                match_state.home_shots += 1
                match_state.home_shots_on_target += 1
                match_state.home_score += 1
                game_state.home_score += 1
                event_type = MatchEventType.GOAL_HOME

                # 记录客队门将失球
                away_goalkeeper = self._select_player(match_state, "away", "gk")
                if away_goalkeeper:
                    away_goalkeeper.goals_conceded += 1
                match_state.away_goals_conceded += 1
            else:
                match_state.away_shots += 1
                match_state.away_shots_on_target += 1
                match_state.away_score += 1
                game_state.away_score += 1
                event_type = MatchEventType.GOAL_AWAY

                # 记录主队门将失球
                home_goalkeeper = self._select_player(match_state, "home", "gk")
                if home_goalkeeper:
                    home_goalkeeper.goals_conceded += 1
                match_state.home_goals_conceded += 1

            # Reset to midfield
            game_state.zone = PitchZone.MIDFIELD
            game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
            
            return MatchEvent(
                minute=game_state.minute,
                event_type=event_type,
                team=attacking_team,
                player=shooter.player.full_name if shooter else None,
                description=f"GOAL! {shooter.player.full_name if shooter else 'Player'} scores!",
                zone=PitchZone.MIDFIELD
            )
    
    def _handle_foul(
        self,
        game_state: GameState,
        match_state: GameState,
        attacking_team: str,
        defending_team: str,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle a foul."""
        
        # Select fouler
        fouler = self._select_player(match_state, defending_team, "def")
        if fouler:
            fouler.fouls += 1
        
        # Update foul count
        if defending_team == "home":
            match_state.home_fouls += 1
        else:
            match_state.away_fouls += 1
        
        # Card probability - reduced for realism
        card_roll = self.rng.random()
        if card_roll < 0.005:  # 0.5% red card (avg 0.45 per match)
            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.RED_CARD,
                team=defending_team,
                player=fouler.player.full_name if fouler else None,
                description=f"RED CARD! {fouler.player.full_name if fouler else 'Player'} sent off!",
                zone=game_state.zone
            )
        elif card_roll < 0.08:  # 7.5% yellow (avg 3-4 per match)
            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.YELLOW_CARD,
                team=defending_team,
                player=fouler.player.full_name if fouler else None,
                description=f"Yellow card for {fouler.player.full_name if fouler else 'Player'}",
                zone=game_state.zone
            )
        
        # Check for penalty
        if game_state.zone in [PitchZone.HOME_BOX, PitchZone.AWAY_BOX]:
            penalty_prob = 0.15  # 15% of box fouls are penalties
            if self.rng.random() < penalty_prob:
                return self._handle_penalty(game_state, match_state, attacking_team, defending_team, def_strength)
        
        # Free kick
        game_state.possession = Possession.DEAD_BALL
        return MatchEvent(
            minute=game_state.minute,
            event_type=MatchEventType.FREE_KICK,
            team=attacking_team,
            description="Free kick awarded",
            zone=game_state.zone
        )
    
    def _handle_penalty(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle a penalty kick."""
        
        # Select taker
        taker = self._select_player(match_state, attacking_team, "att")
        
        # Penalty conversion ~75-80%
        taker_rating = taker.player.current_ability if taker else 70
        gk_rating = def_strength["gk"]
        
        goal_prob = 0.78 + (taker_rating - gk_rating) / 400
        goal_prob = max(0.75, min(0.85, goal_prob))
        
        is_goal = self.rng.random() < goal_prob
        
        if is_goal:
            if attacking_team == "home":
                match_state.home_score += 1
                game_state.home_score += 1
                event_type = MatchEventType.GOAL_HOME
            else:
                match_state.away_score += 1
                game_state.away_score += 1
                event_type = MatchEventType.GOAL_AWAY
            
            game_state.zone = PitchZone.MIDFIELD
            game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
            
            return MatchEvent(
                minute=game_state.minute,
                event_type=event_type,
                team=attacking_team,
                player=taker.player.full_name if taker else None,
                description=f"PENALTY GOAL! {taker.player.full_name if taker else 'Player'} scores from the spot!",
                zone=PitchZone.MIDFIELD
            )
        else:
            game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
            game_state.zone = PitchZone.HOME_BOX if attacking_team == "away" else PitchZone.AWAY_BOX
            
            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.PENALTY,
                team=attacking_team,
                player=taker.player.full_name if taker else None,
                description="Penalty saved!",
                zone=game_state.zone
            )
    
    def _handle_clearance(
        self,
        game_state: GameState,
        match_state: MatchState,
        defending_team: str,
    ) -> MatchEvent:
        """Handle a defensive clearance."""

        # Select defender making clearance
        defender = self._select_player(match_state, defending_team, "def")
        if defender:
            defender.clearances += 1

        # Update team clearance stats
        if defending_team == "home":
            match_state.home_clearances += 1
        else:
            match_state.away_clearances += 1

        # Move ball to midfield or opposite third
        if game_state.zone == PitchZone.HOME_BOX:
            new_zone = PitchZone.MIDFIELD
        elif game_state.zone == PitchZone.AWAY_BOX:
            new_zone = PitchZone.MIDFIELD
        else:
            new_zone = PitchZone.MIDFIELD

        game_state.zone = new_zone
        game_state.possession = Possession.AWAY if defending_team == "home" else Possession.HOME
        game_state.consecutive_passes = 0

        return MatchEvent(
            minute=game_state.minute,
            event_type=MatchEventType.CLEARANCE,
            team=defending_team,
            player=defender.player.full_name if defender else None,
            description="Defensive clearance",
            zone=game_state.zone
        )

    def _handle_block(
        self,
        game_state: GameState,
        match_state: MatchState,
        defending_team: str,
    ) -> MatchEvent:
        """Handle a shot/block event."""
        # Select defender making block
        defender = self._select_player(match_state, defending_team, "def")
        if defender:
            defender.blocks += 1

        # Update team block stats
        if defending_team == "home":
            match_state.home_blocks += 1
        else:
            match_state.away_blocks += 1

        # Ball may remain in attacking third for rebound chance
        if game_state.zone in [PitchZone.HOME_BOX, PitchZone.AWAY_BOX]:
            # 50% chance of rebound opportunity
            if self.rng.random() < 0.5:
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_BLOCKED,
                    team=defending_team,
                    player=defender.player.full_name if defender else None,
                    description="Shot blocked - rebound chance",
                    zone=game_state.zone
                )

        # Defense clears
        game_state.zone = PitchZone.MIDFIELD
        game_state.possession = Possession.AWAY if defending_team == "home" else Possession.HOME

        return MatchEvent(
            minute=game_state.minute,
            event_type=MatchEventType.SHOT_BLOCKED,
            team=defending_team,
            player=defender.player.full_name if defender else None,
            description="Shot blocked and cleared",
            zone=game_state.zone
        )

    def _handle_cross(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle a cross attempt."""
        # Select crosser (usually wide player)
        crosser = self._select_player(match_state, attacking_team, "att")
        if crosser:
            crosser.crosses += 1
            crosser.update_fatigue(0.4)

        # Cross success based on player attributes
        # Cross: 40% CA (base level) + 36% passing + 15% pace + 9% positioning
        # Defense: 50% strength, 50% positioning
        if crosser:
            ca = crosser.player.current_ability
            passing = self.get_player_attribute(crosser.player, 'passing', 70)
            pace = self.get_player_attribute(crosser.player, 'pace', 70)
            positioning = self.get_player_attribute(crosser.player, 'positioning', 70)
            attacker_score = ca * 0.40 + passing * 0.36 + pace * 0.15 + positioning * 0.09
        else:
            attacker_score = att_strength["att"]

        defender_score = def_strength["def"]

        success_prob = 0.58 + (attacker_score - defender_score) / 195
        success_prob = max(0.40, min(0.77, success_prob))

        success = self.rng.random() < success_prob

        if success:
            if crosser:
                crosser.crosses_successful += 1
                crosser.key_passes += 1  # Successful cross is a key pass
                # 传中成功也记录为潜在助攻
                self._last_passer[attacking_team] = (crosser, game_state.minute)
                self._last_key_pass[attacking_team] = (crosser, game_state.minute)

            # Update team stats
            if attacking_team == "home":
                match_state.home_crosses += 1
                match_state.home_crosses_successful += 1
                match_state.home_key_passes += 1
            else:
                match_state.away_crosses += 1
                match_state.away_crosses_successful += 1
                match_state.away_key_passes += 1

            # Cross finds teammate - shot opportunity
            game_state.zone = PitchZone.AWAY_BOX if attacking_team == "home" else PitchZone.HOME_BOX

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.PASS_SUCCESS,
                team=attacking_team,
                player=crosser.player.full_name if crosser else None,
                description="Successful cross - heading chance!",
                zone=game_state.zone
            )
        else:
            # Cross cleared or intercepted
            if attacking_team == "home":
                match_state.home_crosses += 1
            else:
                match_state.away_crosses += 1

            game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
            game_state.zone = PitchZone.MIDFIELD

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.PASS_FAIL,
                team=attacking_team,
                player=crosser.player.full_name if crosser else None,
                description="Cross intercepted and cleared",
                zone=game_state.zone
            )

    def _handle_aerial_duel(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle an aerial duel (header challenge)."""
        # Select players
        attacker = self._select_player(match_state, attacking_team, "att")
        defender = self._select_player(match_state, defending_team, "def")

        # Calculate winner based on player attributes
        # Aerial duel: 40% CA (base level) + 36% strength + 24% positioning (for both attacker and defender)
        if attacker:
            ca = attacker.player.current_ability
            att_strength_attr = self.get_player_attribute(attacker.player, 'strength', 70)
            att_positioning = self.get_player_attribute(attacker.player, 'positioning', 70)
            attacker_score = ca * 0.40 + att_strength_attr * 0.36 + att_positioning * 0.24
        else:
            attacker_score = att_strength["att"]

        if defender:
            ca = defender.player.current_ability
            def_strength_attr = self.get_player_attribute(defender.player, 'strength', 70)
            def_positioning = self.get_player_attribute(defender.player, 'positioning', 70)
            defender_score = ca * 0.40 + def_strength_attr * 0.36 + def_positioning * 0.24
        else:
            defender_score = def_strength["def"]

        # Aerial duel probability
        att_win_prob = 0.50 + (attacker_score - defender_score) / 200
        att_win_prob = max(0.25, min(0.75, att_win_prob))

        att_wins = self.rng.random() < att_win_prob

        if attacker:
            if att_wins:
                attacker.aerial_duels_won += 1
            else:
                attacker.aerial_duels_lost += 1

        if defender:
            if not att_wins:
                defender.aerial_duels_won += 1
            else:
                defender.aerial_duels_lost += 1

        # Update team stats
        if att_wins:
            if attacking_team == "home":
                match_state.home_aerial_duels_won += 1
                match_state.home_aerial_duels_total += 1
            else:
                match_state.away_aerial_duels_won += 1
                match_state.away_aerial_duels_total += 1
        else:
            if defending_team == "home":
                match_state.home_aerial_duels_won += 1
                match_state.home_aerial_duels_total += 1
            else:
                match_state.away_aerial_duels_won += 1
                match_state.away_aerial_duels_total += 1

        if att_wins:
            # Attacker wins header - can lead to shot or pass
            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.PASS_SUCCESS,
                team=attacking_team,
                player=attacker.player.full_name if attacker else None,
                description="Header won - attacking team keeps possession",
                zone=game_state.zone
            )
        else:
            # Defender wins header - clearance
            game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
            game_state.zone = PitchZone.MIDFIELD

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.CLEARANCE,
                team=defending_team,
                player=defender.player.full_name if defender else None,
                description="Defensive header - ball cleared",
                zone=game_state.zone
            )

    def _handle_offside(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
    ) -> MatchEvent:
        """Handle an offside call."""
        # Select attacker who was offside
        attacker = self._select_player(match_state, attacking_team, "att")
        if attacker:
            attacker.offsides += 1

        # Update team stats
        if attacking_team == "home":
            match_state.home_offsides += 1
        else:
            match_state.away_offsides += 1

        # Offside = free kick for defending team
        game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME

        return MatchEvent(
            minute=game_state.minute,
            event_type=MatchEventType.OFFSIDE,
            team=attacking_team,
            player=attacker.player.full_name if attacker else None,
            description="Offside called",
            zone=game_state.zone
        )

    def _handle_goalkeeper_save(
        self,
        game_state: GameState,
        match_state: MatchState,
        defending_team: str,
        is_one_on_one: bool = False,
    ) -> MatchEvent:
        """Handle a goalkeeper save."""
        # Select goalkeeper
        gk = self._select_player(match_state, defending_team, "gk")

        if gk:
            gk.saves += 1

            if is_one_on_one:
                gk.one_on_one_saves += 1

            # Save type: caught vs parried
            if self.rng.random() < 0.6:
                gk.saves_caught += 1
                save_type = "caught"
            else:
                gk.saves_parried += 1
                save_type = "parried"

            # Update team stats
            if defending_team == "home":
                match_state.home_saves += 1
            else:
                match_state.away_saves += 1

            # If parried, may lead to rebound
            if save_type == "parried" and self.rng.random() < 0.4:
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_ON_TARGET,
                    team=defending_team,
                    player=gk.player.full_name if gk else None,
                    description=f"Save parried - rebound chance!",
                    zone=game_state.zone
                )

            # Caught - GK controls ball
            game_state.possession = Possession.HOME if defending_team == "home" else Possession.AWAY
            gk_zone = PitchZone.HOME_BOX if defending_team == "home" else PitchZone.AWAY_BOX
            game_state.zone = gk_zone

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.SHOT_ON_TARGET,
                team=defending_team,
                player=gk.player.full_name if gk else None,
                description=f"Save {save_type} by goalkeeper",
                zone=game_state.zone
            )

        # No GK available - treat as regular shot on target
        return MatchEvent(
            minute=game_state.minute,
            event_type=MatchEventType.SHOT_ON_TARGET,
            team=defending_team,
            description="Shot on target",
            zone=game_state.zone
        )
    
    def _advance_zone(self, current: PitchZone, direction: str) -> PitchZone:
        """Advance to next zone based on team direction."""
        zones = list(PitchZone)
        current_idx = zones.index(current)
        
        if direction == "home":
            # Home team attacking = moving toward AWAY_BOX (index increases)
            new_idx = min(current_idx + 1, len(zones) - 1)
        else:
            # Away team attacking = moving toward HOME_BOX (index decreases)
            new_idx = max(current_idx - 1, 0)
        
        return zones[new_idx]
    
    # Position-based shot weights - controls how often each position shoots
    POSITION_SHOT_WEIGHTS = {
        # Central attacking positions shoot most often
        "ST": 1.00,   # Striker - primary scorer
        "CF": 0.95,   # Center forward
        "FS": 0.90,   # Second striker / shadow striker
        "TS": 0.85,   # Target man / Trequartista
        
        # Attacking midfielders (often play as forwards in modern systems)
        "CAM": 0.75,  # Central attacking mid - high for false 9s
        "AMC": 0.70,  # Attacking mid center
        
        # Wide positions shoot from angles
        "LW": 0.75,   # Left winger
        "RW": 0.75,   # Right winger
        "AML": 0.65,  # Attacking mid left
        "AMR": 0.65,  # Attacking mid right
        
        # Central midfielders shoot from distance
        "CM": 0.30,
        "LM": 0.25,
        "RM": 0.25,
        "MC": 0.30,
        "ML": 0.25,
        "MR": 0.25,
        "CDM": 0.12,  # Defensive mid rarely shoots
        "DM": 0.12,
        
        # Defenders shoot rarely (set pieces mainly)
        "CB": 0.06,
        "LB": 0.10,
        "RB": 0.10,
        "DC": 0.06,
        "DL": 0.10,
        "DR": 0.10,
        "LWB": 0.12,
        "RWB": 0.12,
        
        # Others
        "GK": 0.01,   # Almost never
        "SW": 0.03,   # Sweeper
    }
    
    def _select_shooter(
        self,
        match_state: MatchState,
        team: str,
        game_state: GameState,
        build_up_type: str = "mixed",  # "mixed", "wing", "through", "long"
    ) -> Optional[PlayerMatchState]:
        """
        Select shooter based on zone and build-up type.

        Different zones favor different positions:
        - AWAY_BOX (attacking box): ST/CF highest priority, wingers from sides
        - AWAY_THIRD: Wingers and attacking mids shoot from distance
        - MIDFIELD: Central mids shoot long range

        方案E: 增加随机性和比赛关键时刻因素
        """
        zone = game_state.zone
        stats = match_state.home_player_stats if team == "home" else match_state.away_player_stats
        candidates = list(stats.values())

        if not candidates:
            return None

        # 方案E: 计算比赛关键时刻加成
        clutch_factor = 1.0
        if game_state.minute > 75:
            score_diff = abs(game_state.home_score - game_state.away_score)
            if score_diff <= 1:
                # 最后15分钟，比分接近时，增加随机性（任何人可能成为英雄）
                clutch_factor = 1.3
            elif score_diff == 0:
                # 平局时，随机性更高
                clutch_factor = 1.4

        # Calculate weights based on position and zone
        weights = []
        for player_stat in candidates:
            pos = player_stat.player.position.value
            base_weight = self.POSITION_SHOT_WEIGHTS.get(pos, 0.20)
            
            # Zone-based adjustments
            if zone == PitchZone.AWAY_BOX:
                # In the box - central positions preferred
                # 方案C: 降低ST/CF权重加成，增加边锋权重
                if pos in ["ST", "CF"]:
                    base_weight *= 1.8  # Reduced from 2.5 to 1.8
                elif pos in ["CAM", "AMC"]:
                    base_weight *= 1.6  # Reduced from 1.8 to 1.6
                elif pos in ["LW", "RW", "AML", "AMR"]:
                    base_weight *= 1.5  # Increased from 1.2 to 1.5
                elif pos in ["CM", "CDM", "DM"]:
                    base_weight *= 0.4  # Slightly increased from 0.3
                    
            elif zone == PitchZone.AWAY_THIRD:
                # Outside box - wingers and mids shoot more
                if pos in ["LW", "RW", "AML", "AMR"]:
                    base_weight *= 2.0  # Wingers cut inside
                elif pos in ["CAM", "AMC"]:
                    base_weight *= 1.5
                elif pos in ["ST", "CF"]:
                    base_weight *= 0.8  # Strikers wait for better chance
                elif pos in ["CM", "LM", "RM"]:
                    base_weight *= 1.2  # Mids try long shots
                    
            elif zone == PitchZone.MIDFIELD:
                # Long range - mids only
                if pos in ["CM", "CAM", "CDM", "LM", "RM"]:
                    base_weight *= 1.5
                else:
                    base_weight *= 0.1  # Others don't shoot from here
            
            # Build-up type adjustments
            if build_up_type == "wing":
                if pos in ["LW", "RW", "AML", "AMR", "LWB", "RWB"]:
                    base_weight *= 1.5
            elif build_up_type == "through":
                if pos in ["ST", "CF", "CAM"]:
                    base_weight *= 1.5

            # Fatigue factor (tired players less likely to shoot)
            fatigue_factor = 1.0 - (player_stat.fatigue / 300)  # 0.67 to 1.0

            # Shooting ability factor - 使用射门属性而不是综合能力
            # 射门高的球员更容易被选中射门
            shooting = getattr(player_stat.player, 'shooting', None) or player_stat.player.current_ability
            # 增强射门属性影响：1.0-2.2倍范围（之前是1.0-2.0）
            shooting_factor = 1.0 + (shooting / 82.0)  # Elite(90) = 2.1x, Avg(68) = 1.83x, Poor(50) = 1.61x

            # 方案E: 增加随机性和波动因素
            # 模拟比赛状态的不确定性：球员状态波动、关键时刻等
            form_factor = 1.0 + (self.rng.random() - 0.5) * 0.3  # ±15% random form fluctuation

            # 应用关键时刻加成
            final_weight = base_weight * fatigue_factor * shooting_factor * form_factor * clutch_factor
            weights.append(max(0.1, final_weight))
        
        # Weighted random choice
        total = sum(weights)
        if total == 0:
            return candidates[0] if candidates else None
            
        r = self.rng.random() * total
        cumulative = 0
        for player, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return player
        
        return candidates[-1]
    
    def _select_player(
        self,
        match_state: MatchState,
        team: str,
        role: str,  # "gk", "def", "mid", "att"
    ) -> Optional[PlayerMatchState]:
        """Select a player based on role (for non-shot actions)."""
        stats = match_state.home_player_stats if team == "home" else match_state.away_player_stats
        
        # Filter by role
        if role == "gk":
            candidates = [s for s in stats.values() if s.player.position.value == "GK"]
        elif role == "def":
            candidates = [s for s in stats.values() if s.player.position.value in ["CB", "LB", "RB", "LWB", "RWB", "DC", "DL", "DR"]]
        elif role == "mid":
            candidates = [s for s in stats.values() if s.player.position.value in ["CM", "CDM", "LM", "RM", "CAM", "MC", "ML", "MR", "AMC", "DM"]]
        elif role == "att":
            candidates = [s for s in stats.values() if s.player.position.value in ["ST", "CF", "LW", "RW", "AML", "AMR"]]
        else:
            candidates = list(stats.values())
        
        if not candidates:
            return None

        # Weight by passing ability and freshness
        weights = []
        for c in candidates:
            freshness = 1.0 - (c.fatigue / 200)
            # 使用传球属性而不是综合能力
            passing = getattr(c.player, 'passing', None) or c.player.current_ability
            weight = passing * freshness
            weights.append(max(1, weight))

        # Weighted random choice
        total = sum(weights)
        r = self.rng.random() * total
        cumulative = 0
        for player, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return player

        return candidates[-1]
    
    def _update_stats(self, match_state: MatchState, event: MatchEvent, game_state: GameState):
        """Update match statistics after event."""
        # Update player minutes
        for stats in match_state.home_player_stats.values():
            stats.minutes_played = game_state.minute
        for stats in match_state.away_player_stats.values():
            stats.minutes_played = game_state.minute
    
    def _update_fatigue(self, match_state: MatchState, minute: int):
        """Update player fatigue every minute."""
        # Base fatigue increase every minute
        for stats in list(match_state.home_player_stats.values()) + list(match_state.away_player_stats.values()):
            stats.update_fatigue(0.2)
    
    def _check_substitutions(self, match_state: MatchState, minute: int):
        """Check and make substitutions."""
        # Simple substitution logic - replace tired players
        for team in ["home", "away"]:
            stats_dict = match_state.home_player_stats if team == "home" else match_state.away_player_stats
            
            for name, stats in list(stats_dict.items()):
                if stats.fatigue > 75 and self.rng.random() < 0.3:  # 30% chance if tired
                    # Would substitute here in full implementation
                    pass
    
    def _handle_injury(self, match_state: MatchState, minute: int):
        """Handle a player injury."""
        team = self.rng.choice(["home", "away"])
        stats_dict = match_state.home_player_stats if team == "home" else match_state.away_player_stats
        
        if stats_dict:
            player = self.rng.choice(list(stats_dict.keys()))
            match_state.events.append(MatchEvent(
                minute=minute,
                event_type=MatchEventType.INJURY,
                team=team,
                player=player,
                description=f"{player} is injured and needs treatment"
            ))
