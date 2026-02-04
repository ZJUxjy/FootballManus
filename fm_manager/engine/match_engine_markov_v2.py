"""Enhanced Markov Chain match engine with advanced tactical and psychological factors.

Key improvements over v1:
- Dynamic xG model with match stage pressure
- Advanced fatigue system with stamina and age factors
- Tactical formation impact
- Momentum and psychology system
- More realistic event flow
- Intelligent substitution logic
- Injury and chemistry integration
"""

import random
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, Dict, List, Tuple

# Import base engine structures
from fm_manager.engine.match_engine_markov import (
    PitchZone,
    Possession,
    MatchEventType,
    GameState,
    MatchEvent,
    PlayerMatchState,
    MatchState,
    compute_shot_xg,
    MarkovMatchEngine,
)

from fm_manager.engine.injury_chemistry_engine import InjuryEngine, ChemistryEngine


class MatchStage(Enum):
    """Different stages of a match with different psychological impacts."""

    OPENING = "opening"  # 0-15 min: Testing the waters
    ESTABLISHED = "established"  # 16-45 min: Settling in
    FIRST_HALF_END = "first_half_end"  # 46-60 min: Post-halftime
    CRUCIAL = "crucial"  # 61-75 min: Game taking shape
    CLIMAX = "climax"  # 76-90 min: Final push


# Home advantage factor: 15% boost for home team in all events
HOME_ADVANTAGE_FACTOR = 1.15


@dataclass
class TeamMomentum:
    """Tracks team momentum and psychological state."""

    club_id: int

    # Momentum
    attacking_momentum: float = 0.0  # -10 to 10, positive = attacking flow
    defensive_stability: float = 0.0  # -10 to 10, positive = solid defense

    # Psychology
    morale: float = 50.0  # 0-100
    confidence: float = 50.0  # 0-100

    # Recent performance
    shots_conceded_last_10: int = 0
    chances_created_last_10: int = 0

    def update_after_event(self, event_type: MatchEventType, is_own_team: bool) -> None:
        """Update momentum based on events."""
        if is_own_team:
            if event_type in [MatchEventType.GOAL_HOME, MatchEventType.GOAL_AWAY]:
                self.attacking_momentum += 3.0
                self.morale = min(100, self.morale + 10.0)
                self.confidence = min(100, self.confidence + 8.0)
            elif event_type == MatchEventType.SHOT_ON_TARGET:
                self.attacking_momentum = min(10, self.attacking_momentum + 0.5)
                self.chances_created_last_10 += 1
            elif event_type == MatchEventType.CLEARANCE:
                self.defensive_stability = min(10, self.defensive_stability + 0.5)
        else:
            # Opponent event - negative impact
            if event_type in [MatchEventType.GOAL_HOME, MatchEventType.GOAL_AWAY]:
                self.attacking_momentum = max(-10, self.attacking_momentum - 4.0)
                self.morale = max(0, self.morale - 15.0)
                self.confidence = max(0, self.confidence - 10.0)
            elif event_type == MatchEventType.SHOT_ON_TARGET:
                self.defensive_stability = max(-10, self.defensive_stability - 0.5)
                self.shots_conceded_last_10 += 1

        # Clamp momentum values
        self.attacking_momentum = max(-10, min(10, self.attacking_momentum))
        self.defensive_stability = max(-10, min(10, self.defensive_stability))

        # Decay recent stats
        if self.chances_created_last_10 > 10:
            self.chances_created_last_10 -= 1
        if self.shots_conceded_last_10 > 10:
            self.shots_conceded_last_10 -= 1

    def get_overall_momentum(self) -> float:
        """Get overall momentum factor (0.8 to 1.2)."""
        base = (self.attacking_momentum + self.defensive_stability) / 2.0
        return 1.0 + (base / 20.0)  # Map -10 to 10 => 0.5 to 1.5


@dataclass
class TacticalFormation:
    """Represents a team's tactical formation."""

    formation: str = "4-3-3"

    # Formation characteristics
    width: float = 1.0  # 0.8 = narrow, 1.2 = wide
    tempo: float = 1.0  # 0.7 = slow possession, 1.3 = fast counter
    risk_level: float = 1.0  # 0.7 = defensive, 1.3 = all-out attack

    def get_width_modifier(self, zone: PitchZone) -> float:
        """Get width modifier based on formation and pitch zone."""
        base = self.width
        # Wide formations better in wide areas
        if zone in [PitchZone.AWAY_THIRD, PitchZone.HOME_THIRD]:
            return base * 1.1
        return base

    def get_pressing_modifier(self, minute: int, score_diff: int) -> float:
        """Get pressing intensity modifier based on situation."""
        base = self.tempo
        # Late game adjustments
        if minute > 75:
            if score_diff > 0:  # Winning
                return base * 0.8  # Slow down, control
            elif score_diff < 0:  # Losing
                return base * 1.2  # Press high
        return base


class EnhancedMarkovEngine:
    """Enhanced match engine with advanced tactical and psychological modeling."""

    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)

        # Enhanced state tracking
        self.home_momentum = TeamMomentum(club_id=0)
        self.away_momentum = TeamMomentum(club_id=0)
        self.home_tactics = TacticalFormation()
        self.away_tactics = TacticalFormation()

        self.injury_engine = InjuryEngine(random_seed)
        self.chemistry_engine = ChemistryEngine(random_seed)

        self.home_chemistry: float = 50.0
        self.away_chemistry: float = 50.0

        # Assist tracking
        self._last_passer: Dict[str, Tuple[PlayerMatchState, int]] = {}

        # Match stage
        self._match_stage: MatchStage = MatchStage.OPENING

        # Create base engine for helper methods
        self._base_engine = MarkovMatchEngine(random_seed)

    def simulate(
        self,
        home_lineup: list,
        away_lineup: list,
        home_formation: str = "4-3-3",
        away_formation: str = "4-3-3",
        callback: Optional[Callable[[MatchState], None]] = None,
    ) -> MatchState:
        """Simulate a full 90-minute match with enhanced realism."""

        # Initialize tactics
        self.home_tactics = self._get_formation_tactics(home_formation)
        self.away_tactics = self._get_formation_tactics(away_formation)

        # Calculate team strengths first (needed for initial possession)
        home_strength = self._calculate_team_strength(home_lineup)
        away_strength = self._calculate_team_strength(away_lineup)

        # === 基于球队实力的初始控球概率 ===
        # 强队更有可能开球后控制球权
        strength_diff = home_strength["overall"] - away_strength["overall"]
        home_possession_prob = 0.5 + (strength_diff / 200)  # 0.35 到 0.65 范围
        home_possession_prob = max(0.35, min(0.65, home_possession_prob))

        initial_possession = (
            Possession.HOME if random.random() < home_possession_prob else Possession.AWAY
        )

        # Initialize states
        game_state = GameState(minute=0, zone=PitchZone.MIDFIELD, possession=initial_possession)

        match_state = MatchState(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_player_stats={p.full_name: PlayerMatchState(p) for p in home_lineup},
            away_player_stats={p.full_name: PlayerMatchState(p) for p in away_lineup},
        )

        # Team strengths already calculated above for initial possession

        self.home_chemistry = self.chemistry_engine.get_team_chemistry_modifier(home_lineup) * 100
        self.away_chemistry = self.chemistry_engine.get_team_chemistry_modifier(away_lineup) * 100

        # Simulate each minute
        for minute in range(1, 91):
            game_state.minute = minute
            match_state.minute = minute

            # Update match stage
            self._match_stage = self._get_match_stage(minute)

            # Calculate score difference
            score_diff = game_state.home_score - game_state.away_score

            # Each minute can have multiple events
            max_events_per_minute = 2
            events_this_minute = 0

            while events_this_minute < max_events_per_minute:
                event = self._simulate_minute(
                    game_state, match_state, home_strength, away_strength, score_diff
                )

                if event:
                    match_state.events.append(event)
                    game_state.last_event = event.event_type

                    # Update momentum
                    self._update_momentum(event, game_state)

                    # Update stats using base engine
                    self._base_engine._update_stats(match_state, event, game_state)
                    events_this_minute += 1

                    # Stop conditions
                    if self._should_stop_sequence(event):
                        break
                else:
                    break

            # Update fatigue (enhanced)
            self._update_fatigue_enhanced(match_state, minute)

            # Check for intelligent substitutions
            if minute in [60, 65, 70, 75, 80, 85]:
                self._check_intelligent_substitutions(match_state, minute, score_diff)

            # Injury check
            if self.rng.random() < 0.0015:
                self._handle_injury_enhanced(match_state, minute, game_state)

            if callback:
                callback(match_state)

        # Final event
        match_state.events.append(
            MatchEvent(
                minute=90,
                event_type=MatchEventType.FULL_TIME,
                team="",
                description=f"Full Time: {match_state.score_string()}",
            )
        )

        # Calculate final possession
        total_passes = match_state.home_passes + match_state.away_passes
        if total_passes > 0:
            match_state.home_possession = (match_state.home_passes / total_passes) * 100

        # Calculate player ratings
        self._calculate_match_ratings_enhanced(match_state)

        return match_state

    def _get_match_stage(self, minute: int) -> MatchStage:
        """Determine current match stage."""
        if minute <= 15:
            return MatchStage.OPENING
        elif minute <= 45:
            return MatchStage.ESTABLISHED
        elif minute <= 60:
            return MatchStage.FIRST_HALF_END
        elif minute <= 75:
            return MatchStage.CRUCIAL
        else:
            return MatchStage.CLIMAX

    def _get_formation_tactics(self, formation: str) -> TacticalFormation:
        """Get tactical characteristics for a formation."""
        tactics = TacticalFormation(formation=formation)

        if formation == "4-3-3":
            tactics.width = 1.0
            tactics.tempo = 1.1
            tactics.risk_level = 1.1
        elif formation == "4-4-2":
            tactics.width = 1.0
            tactics.tempo = 1.0
            tactics.risk_level = 1.0
        elif formation == "3-5-2":
            tactics.width = 0.9
            tactics.tempo = 1.0
            tactics.risk_level = 1.0
        elif formation == "4-2-3-1":
            tactics.width = 1.1
            tactics.tempo = 1.2
            tactics.risk_level = 1.2

        return tactics

    def _simulate_minute(
        self,
        game_state: GameState,
        match_state: MatchState,
        home_strength: dict,
        away_strength: dict,
        score_diff: int,
    ) -> Optional[MatchEvent]:
        """Simulate one minute of play with enhanced factors."""

        # Get current team
        attacking_team = "home" if game_state.possession == Possession.HOME else "away"
        defending_team = "away" if attacking_team == "home" else "home"

        att_strength = home_strength if attacking_team == "home" else away_strength
        def_strength = away_strength if attacking_team == "home" else home_strength

        # Get tactics and momentum
        att_tactics = self.home_tactics if attacking_team == "home" else self.away_tactics
        att_momentum = self.home_momentum if attacking_team == "home" else self.away_momentum
        def_momentum = self.away_momentum if defending_team == "home" else self.home_momentum

        # Get event probabilities
        zone_probs = self._get_enhanced_zone_probs(
            game_state.zone,
            att_strength,
            def_strength,
            att_tactics,
            def_momentum,
            score_diff,
            game_state.minute,
            attacking_team,
        )

        # Select event type
        event_type = self._select_event(zone_probs)

        # Execute event
        return self._execute_event(
            event_type,
            game_state,
            match_state,
            attacking_team,
            defending_team,
            att_strength,
            def_strength,
            score_diff,
        )

    def _get_enhanced_zone_probs(
        self,
        zone: PitchZone,
        att_strength: dict,
        def_strength: dict,
        att_tactics: TacticalFormation,
        def_momentum: TeamMomentum,
        score_diff: int,
        minute: int,
        attacking_team: str = "",
    ) -> Dict[str, float]:
        """Get enhanced event probabilities based on zone and context.

        增强球队实力差距对事件概率的影响。
        """

        # Base probabilities
        base_probs = {
            PitchZone.HOME_BOX: {
                "clearance": 0.30,
                "pass": 0.45,
                "dribble": 0.10,
                "foul": 0.12,
                "shot": 0.02,
            },
            PitchZone.HOME_THIRD: {
                "pass": 0.55,
                "dribble": 0.24,
                "foul": 0.13,
                "clearance": 0.05,
                "shot": 0.03,
            },
            PitchZone.MIDFIELD: {
                "pass": 0.58,
                "dribble": 0.30,
                "foul": 0.09,
                "shot": 0.03,
                "clearance": 0.0,
            },
            PitchZone.AWAY_THIRD: {
                "pass": 0.48,
                "dribble": 0.27,
                "foul": 0.11,
                "shot": 0.12,
                "clearance": 0.0,
            },
            PitchZone.AWAY_BOX: {
                "shot": 0.18,
                "pass": 0.40,
                "dribble": 0.22,
                "foul": 0.11,
                "clearance": 0.0,
            },
        }

        probs = base_probs[zone].copy()

        # === 球队实力差距对进攻效率的影响 ===
        # 计算整体实力差距 (进攻方 vs 防守方)
        att_overall = att_strength["overall"]
        def_overall = def_strength["overall"]
        strength_diff = att_overall - def_overall  # 正值表示进攻方更强

        # 实力差距对事件概率的调整因子 - 增强效果
        # 差距 20 点能力值时，进攻方优势约 40%
        strength_factor = strength_diff / 80.0  # -0.75 到 +0.75 范围

        # Home advantage adjustment
        if attacking_team == "home":
            strength_factor += 0.05  # +5% base home advantage
        elif attacking_team == "away":
            strength_factor -= 0.05  # -5% penalty for away team

        # 强队更容易传球成功、创造射门机会
        # 弱队更容易被逼抢、被迫解围
        if "pass" in probs:
            probs["pass"] *= 1.0 + strength_factor * 0.20
        if "dribble" in probs:
            probs["dribble"] *= 1.0 + strength_factor * 0.15
        if "clearance" in probs:
            probs["clearance"] *= 1.0 - strength_factor * 0.30
        if "shot" in probs:
            probs["shot"] *= 1.0 + strength_factor * 0.20
        if "foul" in probs:
            probs["foul"] *= 1.0 - strength_factor * 0.10

        # Tactical modifiers
        tempo = att_tactics.get_pressing_modifier(minute, score_diff)
        width = att_tactics.get_width_modifier(zone)

        # Tempo affects pass/dribble balance
        if tempo > 1.1:  # Fast tempo
            probs["pass"] *= 0.9
            probs["dribble"] *= 1.2
        elif tempo < 0.9:  # Slow tempo
            probs["pass"] *= 1.2
            probs["dribble"] *= 0.8

        # Width affects zone progression
        if width > 1.0 and zone in [PitchZone.AWAY_THIRD, PitchZone.HOME_THIRD]:
            probs["dribble"] *= 1.3

        # Momentum modifiers
        momentum_factor = def_momentum.get_overall_momentum()
        if momentum_factor < 0.9:
            probs["shot"] *= 1.3
            probs["pass"] *= 0.9
        elif momentum_factor > 1.1:
            probs["shot"] *= 0.7
            probs["clearance"] *= 1.3

        # Late-game desperation
        if minute > 80 and abs(score_diff) >= 2:
            if (attacking_team == "home" and score_diff < 0) or (
                attacking_team == "away" and score_diff > 0
            ):
                probs["shot"] *= 1.15
                probs["pass"] *= 0.95

        # Normalize
        total = sum(probs.values())
        return {k: v / total for k, v in probs.items()}

    def _execute_event(
        self,
        event_type: str,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        att_strength: dict,
        def_strength: dict,
        score_diff: int,
    ) -> Optional[MatchEvent]:
        """Execute event with enhanced handling."""

        if event_type == "pass":
            return self._handle_enhanced_pass(
                game_state, match_state, attacking_team, att_strength, def_strength
            )
        elif event_type == "dribble":
            return self._base_engine._handle_dribble(
                game_state, match_state, attacking_team, defending_team, att_strength, def_strength
            )
        elif event_type == "shot":
            return self._handle_enhanced_shot(
                game_state,
                match_state,
                attacking_team,
                defending_team,
                att_strength,
                def_strength,
                score_diff,
            )
        elif event_type == "foul":
            return self._handle_enhanced_foul(
                game_state, match_state, attacking_team, defending_team
            )
        elif event_type == "clearance":
            return self._base_engine._handle_clearance(game_state, match_state, defending_team)

        return None

    def _handle_enhanced_foul(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
    ) -> MatchEvent:
        fouler = self._base_engine._select_player(match_state, defending_team, "def")
        if fouler:
            fouler.fouls += 1

        if defending_team == "home":
            match_state.home_fouls += 1
        else:
            match_state.away_fouls += 1

        card_roll = self.rng.random()

        momentum = self.home_momentum if defending_team == "home" else self.away_momentum
        if momentum.defensive_stability < -5:
            card_roll += 0.01

        if card_roll < 0.005:
            if fouler:
                fouler.red_cards += 1

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.RED_CARD,
                team=defending_team,
                player=getattr(fouler.player, "full_name", None) if fouler else None,
                description="Red card! Straight red",
                zone=game_state.zone,
            )
        elif card_roll < 0.025:
            if fouler:
                fouler.yellow_cards += 1

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.YELLOW_CARD,
                team=defending_team,
                player=getattr(fouler.player, "full_name", None) if fouler else None,
                description="Yellow card",
                zone=game_state.zone,
            )

        return MatchEvent(
            minute=game_state.minute,
            event_type=MatchEventType.FOUL,
            team=defending_team,
            player=getattr(fouler.player, "full_name", None) if fouler else None,
            description="Foul",
            zone=game_state.zone,
        )

    def _handle_enhanced_pass(
        self,
        game_state: GameState,
        match_state: MatchState,
        team: str,
        att_strength: dict,
        def_strength: dict,
    ) -> MatchEvent:
        """Handle pass with enhanced accuracy and decision making."""

        # Get passer
        passer = self._base_engine._select_player(match_state, team, "mid")
        if passer:
            passer.passes_attempted += 1
            passer.update_fatigue(0.3)

        # Calculate success probability
        if passer:
            ca = getattr(passer.player, "current_ability", 70)
            passing = getattr(passer.player, "passing", 70)
            positioning = getattr(passer.player, "positioning", 70)
            pace = getattr(passer.player, "pace", 70)

            # Enhanced calculation with momentum
            momentum = self.home_momentum if team == "home" else self.away_momentum
            momentum_mod = momentum.get_overall_momentum()

            attacker_score = (
                ca * 0.35 + passing * 0.35 + positioning * 0.20 + pace * 0.10
            ) * momentum_mod
        else:
            attacker_score = att_strength["mid"] * 0.9

        defender_score = def_strength["mid"]

        # Pressure from score
        if team == "home":
            score_diff = game_state.home_score - game_state.away_score
        else:
            score_diff = game_state.away_score - game_state.home_score

        # === 增强实力差距对传球成功率的影响 ===
        # 基础差距 + 整体实力差距
        overall_strength_diff = att_strength["overall"] - def_strength["overall"]

        if score_diff < 0 and game_state.minute > 70:
            success_prob = (
                0.65 + (attacker_score - defender_score) / 150 + overall_strength_diff / 100
            )
        else:
            success_prob = (
                0.65 + (attacker_score - defender_score) / 120 + overall_strength_diff / 80
            )

        if team == "home":
            success_prob += 0.03
        else:
            success_prob -= 0.03

        success_prob = max(0.40, min(0.98, success_prob))
        success = self.rng.random() < success_prob

        if success:
            new_zone = self._base_engine._advance_zone(game_state.zone, team)
            game_state.zone = new_zone
            game_state.consecutive_passes += 1

            if passer:
                passer.passes_completed += 1

                # Track assists
                if new_zone in [PitchZone.AWAY_BOX, PitchZone.AWAY_THIRD]:
                    self._last_passer[team] = (passer, game_state.minute)

                # Clean up old assists
                if team in self._last_passer:
                    _, pass_minute = self._last_passer[team]
                    if game_state.minute - pass_minute > 2.0:
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
                player=getattr(passer.player, "full_name", None) if passer else None,
                description=f"Pass completed to {new_zone.name}",
                zone=game_state.zone,
            )
        else:
            # Intercepted
            game_state.possession = Possession.AWAY if team == "home" else Possession.HOME
            game_state.consecutive_passes = 0

            # Second ball chance
            if self.rng.random() < 0.55:
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.PASS_FAIL,
                    team=team,
                    player=getattr(passer.player, "full_name", None) if passer else None,
                    description="Pass intercepted - loose ball",
                    zone=game_state.zone,
                )
            else:
                return MatchEvent(
                    minute=game_state.minute,
                    event_type=MatchEventType.PASS_FAIL,
                    team=team,
                    player=getattr(passer.player, "full_name", None) if passer else None,
                    description="Pass intercepted - defense control",
                    zone=game_state.zone,
                )

    def _handle_enhanced_shot(
        self,
        game_state: GameState,
        match_state: MatchState,
        attacking_team: str,
        defending_team: str,
        att_strength: dict,
        def_strength: dict,
        score_diff: int,
    ) -> MatchEvent:
        """Handle shot with enhanced xG model."""

        # Select shooter
        shooter = self._base_engine._select_shooter(match_state, attacking_team, game_state)
        if shooter:
            shooter.shots += 1
            shooter.update_fatigue(0.7)

        # Get shot location
        shot_distance, shot_angle, is_breakaway = self._base_engine._get_shot_location(
            game_state.zone, attacking_team
        )

        # Determine header probability
        is_header = False
        if shooter and game_state.zone == PitchZone.AWAY_BOX:
            position = getattr(shooter.player, "position", None)
            if position:
                pos_value = position.value if hasattr(position, "value") else str(position)
                header_chance = 0.20 if pos_value in ["ST", "CF"] else 0.10
                is_header = self.rng.random() < header_chance

        # Get shooter attributes
        if shooter:
            shooting = getattr(shooter.player, "shooting", 70)
            shooter_positioning = getattr(shooter.player, "positioning", 70)
            shooter_strength = getattr(shooter.player, "strength", 70)
            shooter_ca = getattr(shooter.player, "current_ability", 70)
        else:
            shooting = att_strength["att"]
            shooter_positioning = 70
            shooter_strength = 70
            shooter_ca = att_strength["att"]

        # Get goalkeeper
        goalkeeper = self._base_engine._select_player(match_state, defending_team, "gk")
        if goalkeeper:
            gk_positioning = getattr(goalkeeper.player, "positioning", 70)
            gk_reflexes = getattr(goalkeeper.player, "reflexes", 70)
            gk_ca = getattr(goalkeeper.player, "current_ability", 70)
        else:
            gk_positioning = def_strength["gk"]
            gk_reflexes = def_strength["gk"]
            gk_ca = def_strength["gk"]

        # Calculate momentum pressure
        momentum = self.home_momentum if attacking_team == "home" else self.away_momentum
        momentum_pressure = momentum.get_overall_momentum()

        # Match stage pressure
        if self._match_stage == MatchStage.CLIMAX:
            pressure = 0.4
        elif self._match_stage == MatchStage.CRUCIAL:
            pressure = 0.2
        else:
            pressure = 0.0

        # Defender pressure
        defensive_pressure = 0.0
        if not is_breakaway and self.rng.random() < 0.65:
            defender = self._base_engine._select_player(match_state, defending_team, "def")
            if defender:
                tackling = getattr(defender.player, "tackling", 70)
                marking = getattr(defender.player, "marking", 70)
                def_pos = getattr(defender.player, "positioning", 70)

                def_score = tackling * 0.40 + marking * 0.35 + def_pos * 0.25
                defensive_pressure = (def_score - 50) / 100.0
                defensive_pressure = max(0.0, min(0.8, defensive_pressure))

        # Score pressure (late game)
        score_pressure = 0.0
        if game_state.minute > 80 and abs(score_diff) <= 1:
            score_pressure = 0.3

        # === 增强球队整体实力差距对射门的影响 ===
        # 强队面对弱队时，射门质量更高
        overall_strength_diff = att_strength["overall"] - def_strength["overall"]
        # 调整射手和门将的有效能力值 - 增强效果
        shooter_ca += overall_strength_diff * 0.25  # 强队射手获得更大加成
        shooter_ca = max(45, min(100, shooter_ca))

        gk_ca -= overall_strength_diff * 0.20  # 弱队门将面对强队时表现下降更多
        gk_ca = max(35, min(100, gk_ca))

        # 强队在面对弱队时，防守压力更小（对方防守组织差）
        defensive_pressure *= max(0.5, 1.0 - overall_strength_diff / 100)

        # Calculate xG with all factors
        shot_result = compute_shot_xg(
            shooter_ca=shooter_ca,
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
            pressure=pressure + score_pressure,
            defensive_pressure=defensive_pressure,
        )

        # Momentum affects finishing
        final_goal_prob = shot_result["goal"] * momentum_pressure

        # Home advantage: +4% xG for home shots
        if attacking_team == "home":
            final_goal_prob *= 1.04

        # Determine outcome
        outcome_roll = self.rng.random()

        if outcome_roll < final_goal_prob:
            # GOAL!
            return self._record_goal(
                game_state, match_state, attacking_team, shooter, shot_distance, shot_angle
            )
        elif outcome_roll < shot_result["on_target"]:
            # Saved
            if goalkeeper:
                goalkeeper.saves += 1

            if attacking_team == "home":
                match_state.away_saves += 1
            else:
                match_state.home_saves += 1

            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.SHOT_ON_TARGET,
                team=attacking_team,
                player=getattr(shooter.player, "full_name", None) if shooter else None,
                description=f"Shot saved by GK (xG: {shot_result['xg']:.2f})",
                zone=game_state.zone,
            )
        else:
            # Missed
            return MatchEvent(
                minute=game_state.minute,
                event_type=MatchEventType.SHOT_OFF_TARGET,
                team=attacking_team,
                player=getattr(shooter.player, "full_name", None) if shooter else None,
                description=f"Shot off target (xG: {shot_result['xg']:.2f})",
                zone=game_state.zone,
            )

    def _record_goal(
        self,
        game_state: GameState,
        match_state: MatchState,
        scoring_team: str,
        scorer_state: Optional[PlayerMatchState],
        distance: float,
        angle: float,
    ) -> MatchEvent:
        """Record a goal with assist tracking."""

        # Update score
        if scoring_team == "home":
            game_state.home_score += 1
            match_state.home_score = game_state.home_score
            event_type = MatchEventType.GOAL_HOME
        else:
            game_state.away_score += 1
            match_state.away_score = game_state.away_score
            event_type = MatchEventType.GOAL_AWAY

        # Record goal
        if scorer_state:
            scorer_state.goals += 1

        # Check for assist
        assist_player = None
        if scoring_team in self._last_passer:
            assister, pass_minute = self._last_passer[scoring_team]
            if game_state.minute - pass_minute <= 2.0:
                assist_player = getattr(assister.player, "full_name", None) if assister else None
                if assist_player:
                    assister.assists += 1
                del self._last_passer[scoring_team]

        scorer_name = (
            getattr(scorer_state.player, "full_name", "Unknown") if scorer_state else "Unknown"
        )
        description = f"GOAL! {scorer_name}"
        if assist_player:
            description += f" (Assist: {assist_player})"
        description += f" from {distance:.1f}m, {angle:.1f}°"

        # Update goals conceded
        conceding_team = "away" if scoring_team == "home" else "home"
        conceding_gk = self._base_engine._select_player(match_state, conceding_team, "gk")
        if conceding_gk:
            conceding_gk.goals_conceded += 1

        if conceding_team == "home":
            match_state.home_goals_conceded += 1
        else:
            match_state.away_goals_conceded += 1

        # Update shots on target
        if scorer_state:
            scorer_state.shots_on_target += 1

        if scoring_team == "home":
            match_state.home_shots_on_target += 1
        else:
            match_state.away_shots_on_target += 1

        return MatchEvent(
            minute=game_state.minute,
            event_type=event_type,
            team=scoring_team,
            player=scorer_name,
            description=description,
            zone=game_state.zone,
        )

    def _update_momentum(self, event: MatchEvent, game_state: GameState) -> None:
        """Update team momentum after events."""
        if event.team == "home":
            self.home_momentum.update_after_event(event.event_type, True)
            self.away_momentum.update_after_event(event.event_type, False)
        elif event.team == "away":
            self.away_momentum.update_after_event(event.event_type, True)
            self.home_momentum.update_after_event(event.event_type, False)

    def _check_intelligent_substitutions(
        self,
        match_state: MatchState,
        minute: int,
        score_diff: int,
    ) -> None:
        """Make intelligent substitution decisions."""
        for team in ["home", "away"]:
            team_stats = (
                match_state.home_player_stats if team == "home" else match_state.away_player_stats
            )
            tactics = self.home_tactics if team == "home" else self.away_tactics

            # Find tired or underperforming players
            tired_players = [
                (name, stats)
                for name, stats in team_stats.items()
                if stats.minutes_played >= minute and stats.fatigue > 70
            ]

            # Find available substitutes
            available_subs = [
                (name, stats)
                for name, stats in team_stats.items()
                if stats.minutes_played == 0 or stats.minutes_played < 45
            ]

            if tired_players and available_subs:
                # Sort by fatigue (highest first)
                tired_players.sort(key=lambda x: x[1].fatigue, reverse=True)

                # Sort subs by ability (highest first)
                available_subs.sort(
                    key=lambda x: getattr(x[1].player, "current_ability", 50), reverse=True
                )

                # Make substitution based on situation
                if minute < 70:
                    # Early: Only if very tired
                    if tired_players[0][1].fatigue > 80:
                        self._make_substitution(
                            match_state, team, tired_players[0][0], available_subs[0][0], minute
                        )
                elif minute < 80:
                    # Mid-late: Tactical or tired
                    if score_diff < 0 and tactics.tempo < 1.1:
                        # Losing - bring on attackers
                        attackers = [
                            (n, s)
                            for n, s in available_subs
                            if getattr(s.player, "position", None)
                            and str(getattr(s.player.position, "value", "MID"))
                            in ["ST", "CF", "LW", "RW"]
                        ]
                        if attackers:
                            self._make_substitution(
                                match_state, team, tired_players[0][0], attackers[0][0], minute
                            )
                    elif tired_players[0][1].fatigue > 75:
                        self._make_substitution(
                            match_state, team, tired_players[0][0], available_subs[0][0], minute
                        )
                else:
                    # Late: Strategic
                    if tired_players[0][1].fatigue > 70:
                        self._make_substitution(
                            match_state, team, tired_players[0][0], available_subs[0][0], minute
                        )

    def _make_substitution(
        self,
        match_state: MatchState,
        team: str,
        player_out_name: str,
        player_in_name: str,
        minute: int,
    ) -> None:
        """Execute a substitution."""
        team_stats = (
            match_state.home_player_stats if team == "home" else match_state.away_player_stats
        )

        if player_out_name not in team_stats or player_in_name not in team_stats:
            return

        player_out = team_stats[player_out_name]
        player_in = team_stats[player_in_name]

        # Update stats
        player_in.minutes_played = player_out.minutes_played

        # Record substitution
        match_state.events.append(
            MatchEvent(
                minute=minute,
                event_type=MatchEventType.SUBSTITUTE,
                team=team,
                player=f"{player_out_name} -> {player_in_name}",
                description=f"Substitution: {getattr(player_out.player, 'full_name', player_out_name)} off, {getattr(player_in.player, 'full_name', player_in_name)} on",
                zone=None,
            )
        )

    def _update_fatigue_enhanced(self, match_state: MatchState, minute: int) -> None:
        """Update fatigue with enhanced rate calculation."""
        for team in ["home", "away"]:
            team_stats = (
                match_state.home_player_stats if team == "home" else match_state.away_player_stats
            )

            for stats in team_stats.values():
                if stats.minutes_played < minute:
                    continue

                # Base fatigue rate
                base_rate = 0.4

                # Stamina affects rate
                stamina = getattr(stats.player, "stamina", 70)
                stamina_factor = 1.0 - (stamina / 140.0)  # 0.5 to 1.0

                # Age affects rate
                age = getattr(stats.player, "age", 25)
                if age > 30:
                    age_factor = 1.3
                elif age > 27:
                    age_factor = 1.1
                elif age < 22:
                    age_factor = 0.8
                else:
                    age_factor = 1.0

                # Minute-based intensity
                if minute < 30:
                    intensity_factor = 0.8
                elif minute > 70:
                    intensity_factor = 1.2
                else:
                    intensity_factor = 1.0

                # Calculate fatigue increase
                fatigue_increase = base_rate * stamina_factor * age_factor * intensity_factor
                stats.fatigue = min(100.0, stats.fatigue + fatigue_increase)

    def _calculate_match_ratings_enhanced(self, match_state: MatchState) -> None:
        """Calculate match ratings with enhanced factors."""
        for team in ["home", "away"]:
            player_stats = (
                match_state.home_player_stats if team == "home" else match_state.away_player_stats
            )
            team_score = match_state.home_score if team == "home" else match_state.away_score
            opp_score = match_state.away_score if team == "home" else match_state.home_score

            is_winner = team_score > opp_score
            is_draw = team_score == opp_score

            for stats in player_stats.values():
                if stats.minutes_played == 0:
                    stats.match_rating = 0.0
                    continue

                # Base rating
                rating = 6.0

                # Position
                position_obj = getattr(stats.player, "position", None)
                position = (
                    position_obj.value if position_obj and hasattr(position_obj, "value") else "MID"
                )

                # Goals (position-weighted)
                if position in ["ST", "CF", "CAM", "LW", "RW"]:
                    rating += stats.goals * 0.8
                elif position in ["CM", "CDM", "LM", "RM"]:
                    rating += stats.goals * 0.9
                else:
                    rating += stats.goals * 1.2

                # Assists
                rating += stats.assists * 0.6

                # Key passes and dribbles
                rating += stats.key_passes * 0.10
                rating += stats.dribbles * 0.06
                rating -= stats.dribbles_failed * 0.04

                # Shot accuracy
                if stats.shots > 0:
                    accuracy = stats.shots_on_target / stats.shots
                    rating += (accuracy - 0.5) * 0.4

                # Pass accuracy
                if stats.passes_attempted > 0:
                    pass_accuracy = stats.passes_completed / stats.passes_attempted
                    if position in ["CB", "LB", "RB", "CDM", "CM"]:
                        rating += (pass_accuracy - 0.75) * 2.5
                    else:
                        rating += (pass_accuracy - 0.70) * 1.5

                # Defensive stats
                if position in ["CB", "LB", "RB", "LWB", "RWB", "CDM", "CM"]:
                    rating += stats.tackles * 0.10
                    rating += stats.interceptions * 0.10
                    rating += stats.blocks * 0.12
                    rating += stats.clearances * 0.06

                # Goalkeeper stats
                if position == "GK":
                    if stats.goals_conceded == 0 and stats.minutes_played >= 90:
                        rating = 8.0
                    else:
                        rating += stats.saves * 0.12
                        rating -= stats.goals_conceded * 1.2

                        # Penalties saved bonus
                        if stats.saves > 0 and stats.goals_conceded < 3:
                            rating += 0.3

                # Match result bonus
                if is_winner:
                    rating += 0.6
                elif is_draw:
                    rating += 0.1
                else:
                    rating -= 0.4

                # Minutes played
                if stats.minutes_played >= 90:
                    rating += 0.15
                elif stats.minutes_played >= 75:
                    rating += 0.10
                elif stats.minutes_played >= 60:
                    rating += 0.05

                # Cards penalty
                rating -= stats.yellow_cards * 0.4
                rating -= stats.red_cards * 1.8

                # Own goals
                rating -= stats.own_goals * 1.5

                # Clamp
                stats.match_rating = max(4.0, min(10.0, rating))

    def _should_stop_sequence(self, event: MatchEvent) -> bool:
        """Determine if event sequence should stop."""
        stop_events = [
            MatchEventType.GOAL_HOME,
            MatchEventType.GOAL_AWAY,
            MatchEventType.CORNER_HOME,
            MatchEventType.CORNER_AWAY,
            MatchEventType.FREE_KICK,
            MatchEventType.PENALTY,
            MatchEventType.CLEARANCE,
            MatchEventType.SHOT_OFF_TARGET,
            MatchEventType.YELLOW_CARD,
            MatchEventType.RED_CARD,
        ]
        return event.event_type in stop_events

    def _select_event(self, probs: dict) -> str:
        """Randomly select an event based on probabilities."""
        r = self.rng.random()
        cumulative = 0
        for event, prob in probs.items():
            cumulative += prob
            if r <= cumulative:
                return event
        return list(probs.keys())[-1]

    def _handle_injury_enhanced(
        self,
        match_state: MatchState,
        minute: int,
        game_state: GameState,
    ) -> None:
        """Handle injury using the injury engine."""

        for team in ["home", "away"]:
            team_stats = (
                match_state.home_player_stats if team == "home" else match_state.away_player_stats
            )
            team_lineup = match_state.home_lineup if team == "home" else match_state.away_lineup
            team_chemistry = self.home_chemistry if team == "home" else self.away_chemistry

            for stats in team_stats.values():
                player = stats.player

                fatigue = stats.fatigue if hasattr(stats, "fatigue") else 0.0

                risk = self.injury_engine.simulate_injury_risk(
                    player,
                    match_importance="normal",
                    fatigue=fatigue,
                    team_chemistry=team_chemistry,
                )

                if self.rng.random() < risk:
                    from datetime import date

                    injury = self.injury_engine.generate_injury(
                        player, player.club_id if player.club_id else 0, date.today()
                    )

                    match_state.events.append(
                        MatchEvent(
                            minute=minute,
                            event_type=MatchEventType.INJURY,
                            team=team,
                            player=player.full_name,
                            description=f"INJURY: {player.full_name} suffers {injury.injury_type.value} injury (out {injury.expected_return.day - injury.occurred_at.day} weeks)",
                            zone=game_state.zone,
                        )
                    )

                    if hasattr(stats, "is_injured"):
                        stats.is_injured = True
                    break

    def _select_shooter(
        self,
        match_state: MatchState,
        team: str,
        game_state: GameState,
        build_up_type: str = "mixed",
    ):
        """选择射手，带重点盯防机制。

        防守方会对进攻威胁大的球员进行重点盯防，降低他们获得射门机会的概率。
        """
        from fm_manager.engine.match_engine_markov import PitchZone

        zone = game_state.zone
        stats = match_state.home_player_stats if team == "home" else match_state.away_player_stats
        candidates = list(stats.values())

        if not candidates:
            return None

        # 计算每个球员的进攻威胁值（基于射门、位置感、能力）
        threat_scores = []
        for player_stat in candidates:
            player = player_stat.player
            shooting = getattr(player, "shooting", 70)
            positioning = getattr(player, "positioning", 70)
            ca = getattr(player, "current_ability", 70)

            # 进攻威胁 = 射门能力*0.4 + 位置感*0.3 + 当前能力*0.3
            threat = shooting * 0.4 + positioning * 0.3 + ca * 0.3
            threat_scores.append(threat)

        # 计算平均威胁和最大威胁
        avg_threat = sum(threat_scores) / len(threat_scores) if threat_scores else 70
        max_threat = max(threat_scores) if threat_scores else 90

        # 计算防守重点盯防因子
        # 威胁值高于平均的球员会受到盯防
        # 使用 sigmoid 函数平滑调整：威胁越高，被盯防越严
        def get_marking_factor(threat):
            if threat <= avg_threat:
                return 1.0  # 普通球员不受额外盯防

            # 威胁超过平均值的比例 (0 到 ~1.5)
            threat_ratio = (threat - avg_threat) / (max_threat - avg_threat + 1)

            # sigmoid 函数: 1.0 -> 0.5 平滑过渡
            # 顶级球员 (threat_ratio ~1.0) -> marking_factor ~0.5 (射门机会减半)
            # 中等威胁 (threat_ratio ~0.5) -> marking_factor ~0.75
            import math

            marking_factor = 1.0 - (1.0 / (1.0 + math.exp(-5 * (threat_ratio - 0.5)))) * 0.5

            return max(0.4, marking_factor)  # 最低保留 40% 权重

        marking_factors = [get_marking_factor(t) for t in threat_scores]

        # 调用基础引擎的射手选择，但修改权重
        # 重新实现基础逻辑并加入盯防因子
        weights = []
        for i, player_stat in enumerate(candidates):
            pos = player_stat.player.position.value
            base_weight = self._base_engine.POSITION_SHOT_WEIGHTS.get(pos, 0.20)

            # 区域调整
            if zone == PitchZone.AWAY_BOX:
                if pos in ["ST", "CF"]:
                    base_weight *= 1.8
                elif pos in ["CAM", "AMC"]:
                    base_weight *= 1.6
                elif pos in ["LW", "RW", "AML", "AMR"]:
                    base_weight *= 1.5
                elif pos in ["CM", "CDM", "DM"]:
                    base_weight *= 0.4

            elif zone == PitchZone.AWAY_THIRD:
                if pos in ["LW", "RW", "AML", "AMR"]:
                    base_weight *= 2.0
                elif pos in ["CAM", "AMC"]:
                    base_weight *= 1.5
                elif pos in ["ST", "CF"]:
                    base_weight *= 0.8
                elif pos in ["CM", "LM", "RM"]:
                    base_weight *= 1.2

            elif zone == PitchZone.MIDFIELD:
                if pos in ["CM", "CAM", "CDM", "LM", "RM"]:
                    base_weight *= 1.5
                else:
                    base_weight *= 0.1

            # 疲劳因素
            fatigue_factor = 1.0 - (player_stat.fatigue / 300)

            # 射门能力
            shooting = (
                getattr(player_stat.player, "shooting", None) or player_stat.player.current_ability
            )
            shooting_factor = 1.0 + (shooting / 82.0)

            # 随机波动
            form_factor = 1.0 + (self.rng.random() - 0.5) * 0.3

            # 关键时刻
            clutch_factor = 1.0
            if game_state.minute > 75:
                score_diff = abs(game_state.home_score - game_state.away_score)
                if score_diff <= 1:
                    clutch_factor = 1.3
                elif score_diff == 0:
                    clutch_factor = 1.4

            # 应用重点盯防因子！
            marking_factor = marking_factors[i]

            final_weight = (
                base_weight
                * fatigue_factor
                * shooting_factor
                * form_factor
                * clutch_factor
                * marking_factor
            )
            weights.append(max(0.1, final_weight))

        # 加权随机选择
        total = sum(weights)
        if total == 0:
            return candidates[0] if candidates else None

        r = self.rng.random() * total
        cumulative = 0
        for player, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return player

        return candidates[-1] if candidates else None

    def _calculate_team_strength(self, lineup: list) -> dict:
        """Calculate team strength in different areas."""
        # Group by position
        gk = [
            p
            for p in lineup
            if hasattr(p, "position") and str(getattr(p.position, "value", "")) == "GK"
        ]
        defs = [
            p
            for p in lineup
            if hasattr(p, "position")
            and str(getattr(p.position, "value", "")) in ["CB", "LB", "RB", "LWB", "RWB"]
        ]
        mids = [
            p
            for p in lineup
            if hasattr(p, "position")
            and str(getattr(p.position, "value", "")) in ["CM", "CDM", "LM", "RM", "CAM"]
        ]
        atts = [
            p
            for p in lineup
            if hasattr(p, "position")
            and str(getattr(p.position, "value", "")) in ["ST", "CF", "LW", "RW"]
        ]

        def avg_rating(players):
            if not players:
                return 50.0
            return sum(getattr(p, "current_ability", 50) for p in players) / len(players)

        return {
            "gk": avg_rating(gk),
            "def": avg_rating(defs),
            "mid": avg_rating(mids),
            "att": avg_rating(atts),
            "overall": avg_rating(lineup),
        }
