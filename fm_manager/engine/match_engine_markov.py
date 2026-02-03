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


# ============================================================================
# SHOOTING PROBABILITY MODEL
# Advanced shooter vs goalkeeper duel calculation
# ============================================================================

# Probability parameters (k controls curve steepness)
FRAME_K = 0.08    # On-target smoothness (reduced for more realistic rates)
SAVE_K = 0.12     # Save probability smoothness

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
    
    # Stats
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
            
            # Each minute can have multiple events (a "phase of play")
            # Continue until possession changes or shot taken
            max_events_per_minute = 2
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
        
        return match_state
    
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
        
        # Get event probabilities based on zone
        zone_probs = self.BASE_EVENT_PROBS[game_state.zone].copy()
        
        # Adjust probabilities based on team strengths
        zone_probs = self._adjust_probs_for_strengths(
            zone_probs, att_strength, def_strength, game_state.zone
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
        
        # Success probability based on midfield battle
        passer_rating = att_strength["mid"] if passer is None else passer.player.current_ability
        defender_rating = def_strength["mid"]
        
        success_prob = 0.70 + (passer_rating - defender_rating) / 200
        success_prob = max(0.50, min(0.90, success_prob))
        
        success = self.rng.random() < success_prob
        
        if success:
            # Move forward or sideways
            new_zone = self._advance_zone(game_state.zone, team)
            game_state.zone = new_zone
            game_state.consecutive_passes += 1
            
            if passer:
                passer.passes_completed += 1
            
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
        
        # Success based on attack vs defense
        dribbler_rating = att_strength["att"] if dribbler is None else dribbler.player.current_ability
        defender_rating = def_strength["def"]
        
        success_prob = 0.55 + (dribbler_rating - defender_rating) / 150
        success_prob = max(0.35, min(0.75, success_prob))
        
        success = self.rng.random() < success_prob
        
        if success:
            new_zone = self._advance_zone(game_state.zone, attacking_team)
            game_state.zone = new_zone
            
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
        shooter = self._select_shooter(match_state, attacking_team, game_state.zone)
        if shooter:
            shooter.shots += 1
            shooter.update_fatigue(0.7)
        
        shooter_rating = att_strength["att"] if shooter is None else shooter.player.current_ability
        gk_rating = def_strength["gk"]
        
        # ========================================================================
        # ADVANCED SHOOTING MODEL
        # Using shooter vs goalkeeper duel calculation
        # ========================================================================
        # Compute outcome probabilities
        probs = compute_shot_probabilities(shooter_rating, gk_rating)
        
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
            
            if attacking_team == "home":
                match_state.home_shots += 1
                match_state.home_shots_on_target += 1
            else:
                match_state.away_shots += 1
                match_state.away_shots_on_target += 1
            
            # 50% chance for rebound after save
            rebound_prob = 0.50
            if self.rng.random() < rebound_prob:
                # Rebound opportunity
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_ON_TARGET,
                    team=attacking_team,
                    player=shooter.player.full_name if shooter else None,
                    description="Great save! - REBOUND! scramble in the box",
                    zone=game_state.zone
                )
            else:
                # Keeper holds the ball
                game_state.possession = Possession.AWAY if attacking_team == "home" else Possession.HOME
                game_state.zone = PitchZone.HOME_BOX if attacking_team == "away" else PitchZone.AWAY_BOX
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.SHOT_ON_TARGET,
                    team=attacking_team,
                    player=shooter.player.full_name if shooter else None,
                    description="Shot saved by goalkeeper",
                    zone=game_state.zone
                )
        
        else:
            # =====================================================================
            # OUTCOME: GOAL (进球！)
            # =====================================================================
            if shooter:
                shooter.shots += 1
                shooter.shots_on_target += 1
            
            if attacking_team == "home":
                match_state.home_shots += 1
                match_state.home_shots_on_target += 1
                match_state.home_score += 1
                game_state.home_score += 1
                event_type = MatchEventType.GOAL_HOME
            else:
                match_state.away_shots += 1
                match_state.away_shots_on_target += 1
                match_state.away_score += 1
                game_state.away_score += 1
                event_type = MatchEventType.GOAL_AWAY
            
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
            description="Defensive clearance",
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
        zone: PitchZone,
        build_up_type: str = "mixed",  # "mixed", "wing", "through", "long"
    ) -> Optional[PlayerMatchState]:
        """
        Select shooter based on zone and build-up type.
        
        Different zones favor different positions:
        - AWAY_BOX (attacking box): ST/CF highest priority, wingers from sides
        - AWAY_THIRD: Wingers and attacking mids shoot from distance
        - MIDFIELD: Central mids shoot long range
        """
        stats = match_state.home_player_stats if team == "home" else match_state.away_player_stats
        candidates = list(stats.values())
        
        if not candidates:
            return None
        
        # Calculate weights based on position and zone
        weights = []
        for player_stat in candidates:
            pos = player_stat.player.position.value
            base_weight = self.POSITION_SHOT_WEIGHTS.get(pos, 0.20)
            
            # Zone-based adjustments
            if zone == PitchZone.AWAY_BOX:
                # In the box - central positions preferred
                if pos in ["ST", "CF"]:
                    base_weight *= 2.5  # Strikers get 2.5x boost
                elif pos in ["CAM", "AMC"]:
                    base_weight *= 1.8
                elif pos in ["LW", "RW", "AML", "AMR"]:
                    base_weight *= 1.2  # Wingers from tight angles
                elif pos in ["CM", "CDM", "DM"]:
                    base_weight *= 0.3  # Mids rarely shoot in box
                    
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
            
            # Ability factor (good finishers more likely)
            ability = player_stat.player.current_ability
            
            final_weight = base_weight * fatigue_factor * (ability / 50)
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
        
        # Weight by ability and freshness
        weights = []
        for c in candidates:
            freshness = 1.0 - (c.fatigue / 200)
            weight = c.player.current_ability * freshness
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
