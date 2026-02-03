"""Realistic match engine based on individual player attributes.

Key improvements:
1. Goal creation based on team buildup (midfield + attack)
2. Goal scoring based on shooter vs goalkeeper duel
3. Individual player quality matters
4. Proper shot-based system with realistic conversion rates
"""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional


class MatchEventType(Enum):
    GOAL = auto()
    SHOT_SAVED = auto()
    SHOT_MISSED = auto()
    YELLOW_CARD = auto()
    RED_CARD = auto()
    FULL_TIME = auto()


@dataclass
class MatchEvent:
    minute: int
    event_type: MatchEventType
    team: str
    player: str | None = None
    description: str = ""


@dataclass
class MatchState:
    match_id: int = 0
    minute: int = 0
    home_score: int = 0
    away_score: int = 0
    
    events: list[MatchEvent] = field(default_factory=list)
    
    # Lineups
    home_lineup: list = field(default_factory=list)
    away_lineup: list = field(default_factory=list)
    
    # Match stats
    home_possession: float = 50.0
    home_shots: int = 0
    home_shots_on_target: int = 0
    home_shots_saved: int = 0
    home_shots_missed: int = 0
    
    away_shots: int = 0
    away_shots_on_target: int = 0
    away_shots_saved: int = 0
    away_shots_missed: int = 0
    
    def score_string(self) -> str:
        return f"{self.home_score}-{self.away_score}"
    
    def winning_team(self) -> str | None:
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        return None
    
    def get_shot_accuracy(self, team: str) -> float:
        if team == "home":
            return (self.home_shots_on_target / self.home_shots * 100) if self.home_shots > 0 else 0
        else:
            return (self.away_shots_on_target / self.away_shots * 100) if self.away_shots > 0 else 0
    
    def get_conversion_rate(self, team: str) -> float:
        if team == "home":
            return (self.home_score / self.home_shots_on_target * 100) if self.home_shots_on_target > 0 else 0
        else:
            return (self.away_score / self.away_shots_on_target * 100) if self.away_shots_on_target > 0 else 0


class RealisticMatchSimulator:
    """
    Realistic match simulator based on individual player quality.
    
    How it works:
    1. Shot creation: Teams create chances based on midfield control and attack quality
    2. Shot conversion: Each shot is a duel between shooter and goalkeeper
    3. Player selection: Best attackers take more shots
    """
    
    HOME_ADVANTAGE = 1.15  # 15% home advantage
    MATCH_LENGTH = 90
    
    # Shot creation (tuned for ~10-12 shots per team per match)
    BASE_SHOTS_PER_TEAM = 15
    SHOT_VARIATION = 8  # +/- 4 shots based on quality
    
    # Shot conversion (realistic rates)
    # Premier League average is ~25-30% of shots on target result in goals
    # After considering all tactical factors, this is the final conversion rate
    BASE_CONVERSION_RATE = 0.15  # 15% of shots on target go in (with adjustments)
    
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
        """Simulate a match with realistic player-based mechanics."""
        
        state = MatchState(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
        )
        
        # Calculate team qualities
        home_attackers = self._get_attackers(home_lineup)
        home_defenders = self._get_defenders(home_lineup)
        home_gk = self._get_goalkeeper(home_lineup)
        home_midfield = self._get_midfielders(home_lineup)
        
        away_attackers = self._get_attackers(away_lineup)
        away_defenders = self._get_defenders(away_lineup)
        away_gk = self._get_goalkeeper(away_lineup)
        away_midfield = self._get_midfielders(away_lineup)
        
        # Calculate team strengths
        home_attack_strength = self._calculate_attack_strength(home_attackers, home_midfield)
        home_defense_strength = self._calculate_defense_strength(home_defenders, home_gk)
        
        away_attack_strength = self._calculate_attack_strength(away_attackers, away_midfield)
        away_defense_strength = self._calculate_defense_strength(away_defenders, away_gk)
        
        # Apply home advantage
        home_attack_strength *= self.HOME_ADVANTAGE
        home_defense_strength *= self.HOME_ADVANTAGE
        
        # Determine number of shots for each team
        home_shots = self._determine_shots(home_attack_strength, away_defense_strength)
        away_shots = self._determine_shots(away_attack_strength, home_defense_strength)
        
        # Simulate shots for home team
        for _ in range(home_shots):
            self._simulate_shot(
                state, "home", 
                home_attackers, home_midfield,
                away_defenders, away_gk, away_midfield
            )
        
        # Simulate shots for away team
        for _ in range(away_shots):
            self._simulate_shot(
                state, "away", 
                away_attackers, away_midfield,
                home_defenders, home_gk, home_midfield
            )
        
        # Calculate possession based on midfield battle
        home_mid_quality = sum(p.current_ability for p in home_midfield) / max(len(home_midfield), 1)
        away_mid_quality = sum(p.current_ability for p in away_midfield) / max(len(away_midfield), 1)
        total_mid = home_mid_quality + away_mid_quality
        if total_mid > 0:
            state.home_possession = 40 + (home_mid_quality / total_mid) * 20
        
        # Sort events by minute
        state.events.sort(key=lambda e: e.minute)
        
        # Add full time event
        state.events.append(MatchEvent(
            minute=90,
            event_type=MatchEventType.FULL_TIME,
            team="",
            description=f"Full Time: {state.score_string()}"
        ))
        
        return state
    
    def _get_attackers(self, lineup: list) -> list:
        """Get attacking players (ST, CF, LW, RW, CAM, AML, AMR, AMC, TS, FS, Winger)."""
        # Handle both Position enum values and raw position strings from _data
        # Position enum values that can score goals
        attack_pos_values = {"ST", "CF", "LW", "RW", "CAM"}  
        # Raw position strings from _data that can score goals
        attack_data_positions = {"ST", "CF", "LW", "RW", "AML", "AMR", "AMC", "TS", "FS", "CAM", "Winger"}
        
        result = []
        for p in lineup:
            # Check position enum value
            if hasattr(p, 'position') and hasattr(p.position, 'value') and p.position.value in attack_pos_values:
                result.append(p)
            # Check raw position string from _data
            elif hasattr(p, '_data') and p._data.position in attack_data_positions:
                result.append(p)
        return result
    
    def _get_defenders(self, lineup: list) -> list:
        """Get defensive players (CB, LB, RB, LWB, RWB, DL, DR, DC, WBL, WBR)."""
        defense_pos_values = {"CB", "LB", "RB", "LWB", "RWB"}  # Position enum values
        defense_data_positions = {"CB", "LB", "RB", "LWB", "RWB", "DL", "DR", "DC", "WBL", "WBR"}  # Raw position strings
        
        result = []
        for p in lineup:
            if hasattr(p, 'position') and hasattr(p.position, 'value') and p.position.value in defense_pos_values:
                result.append(p)
            elif hasattr(p, '_data') and p._data.position in defense_data_positions:
                result.append(p)
        return result
    
    def _get_goalkeeper(self, lineup: list) -> Optional:
        """Get goalkeeper."""
        for p in lineup:
            if hasattr(p, 'position') and hasattr(p.position, 'value') and p.position.value == "GK":
                return p
            if hasattr(p, '_data') and p._data.position == "GK":
                return p
        return None
    
    def _get_midfielders(self, lineup: list) -> list:
        """Get midfielders."""
        mid_pos_values = {"CM", "CDM", "LM", "RM", "CAM"}  # Position enum values
        mid_data_positions = {"CM", "CDM", "LM", "RM", "ML", "MR", "MC", "DM", "AML", "AMR", "AMC"}  # Raw position strings
        
        result = []
        for p in lineup:
            if hasattr(p, 'position') and hasattr(p.position, 'value') and p.position.value in mid_pos_values:
                result.append(p)
            elif hasattr(p, '_data') and p._data.position in mid_data_positions:
                result.append(p)
        return result
    
    def _calculate_attack_strength(self, attackers: list, midfielders: list) -> float:
        """Calculate attack strength based on individual players."""
        if not attackers:
            return 50.0
        
        # Get best attacker ratings (considering position-specific ratings)
        attack_ratings = []
        for p in attackers:
            if hasattr(p, '_data'):
                # Use position-specific rating if available
                pos_rating = p._data.get_rating_for_position(p._data.position)
                attack_ratings.append(pos_rating)
            else:
                attack_ratings.append(p.current_ability)
        
        # Top 3 attackers matter most
        top_attackers = sorted(attack_ratings, reverse=True)[:3]
        avg_attack = sum(top_attackers) / len(top_attackers) if top_attackers else 50
        
        # Midfield support (affects chance creation)
        if midfielders:
            mid_ratings = [p.current_ability for p in midfielders]
            avg_midfield = sum(sorted(mid_ratings, reverse=True)[:3]) / 3
        else:
            avg_midfield = 50
        
        # Combined: 60% attack, 40% midfield support
        return avg_attack * 0.6 + avg_midfield * 0.4
    
    def _calculate_defense_strength(self, defenders: list, goalkeeper: Optional) -> float:
        """Calculate defense strength."""
        if not defenders:
            return 50.0
        
        # Defenders' rating
        defense_ratings = [p.current_ability for p in defenders]
        top_defenders = sorted(defense_ratings, reverse=True)[:4]
        avg_defense = sum(top_defenders) / len(top_defenders)
        
        # Goalkeeper is crucial
        gk_rating = goalkeeper.current_ability if goalkeeper else 50
        
        # Combined: 60% defense, 40% goalkeeper
        return avg_defense * 0.6 + gk_rating * 0.4
    
    def _determine_shots(self, attack_strength: float, opponent_defense: float) -> int:
        """Determine number of shots based on quality difference."""
        # Base shots
        base = self.BASE_SHOTS_PER_TEAM
        
        # Quality difference affects shots
        quality_diff = attack_strength - opponent_defense
        
        # More attack quality = more shots, better defense = fewer shots
        adjustment = (quality_diff / 100) * self.SHOT_VARIATION
        
        expected_shots = base + adjustment
        
        # Add randomness
        shots = int(self.rng.gauss(expected_shots, 2))
        return max(0, min(25, shots))  # 0-25 shots range
    
    def _simulate_shot(
        self, 
        state: MatchState, 
        team: str, 
        attackers: list, 
        own_midfield: list,
        opponent_defenders: list,
        opponent_gk: Optional,
        opponent_midfield: list
    ) -> None:
        """Simulate a single shot attempt with realistic tactical factors.
        
        Factors affecting shot success:
        1. Shooter quality (finishing/shooting)
        2. Build-up quality (own midfield passing/support)
        3. Defensive pressure (opponent defenders' positioning/marking)
        4. Midfield protection (opponent DM's ability to shield defense)
        5. Goalkeeper quality
        """
        if not attackers:
            return
        
        # Select shooter (weighted by ability and position)
        shooter = self._select_shooter(attackers)
        if not shooter:
            return
        
        # Get shooter quality (position-specific rating)
        if hasattr(shooter, '_data'):
            shooter_rating = shooter._data.get_rating_for_position(shooter._data.position)
        else:
            shooter_rating = shooter.current_ability
        
        # Calculate build-up quality (own midfield support)
        # Better midfield = better quality chances
        buildup_quality = 50.0
        if own_midfield:
            # Use top 3 midfielders' average ability
            mid_ratings = sorted([p.current_ability for p in own_midfield], reverse=True)[:3]
            buildup_quality = sum(mid_ratings) / len(mid_ratings)
        
        # Calculate defensive pressure
        # Better defenders = harder to get a clear shot
        defensive_pressure = 50.0
        if opponent_defenders:
            # Use top 4 defenders' average
            def_ratings = sorted([p.current_ability for p in opponent_defenders], reverse=True)[:4]
            defensive_pressure = sum(def_ratings) / len(def_ratings)
        
        # Calculate midfield protection (DMs shielding defense)
        # DMs/CDMs reduce shot quality by intercepting/blocking
        dm_protection = 0.0
        if opponent_midfield:
            # Check for defensive midfielders (DM/CDM positions)
            dm_positions = {"DM", "CDM"}
            dm_ratings = []
            for p in opponent_midfield:
                pos = p._data.position if hasattr(p, '_data') else ""
                if pos in dm_positions or (hasattr(p, 'position') and p.position.value in dm_positions):
                    dm_ratings.append(p.current_ability)
            if dm_ratings:
                # Average of DMs' ratings
                dm_protection = sum(dm_ratings) / len(dm_ratings)
        
        # Get goalkeeper quality
        gk_rating = opponent_gk.current_ability if opponent_gk else 50
        
        # Calculate chance quality based on all factors
        # First calculate the attacking quality (shooter + build-up)
        # Build-up matters less than the shooter himself
        attack_quality = shooter_rating * 0.85 + buildup_quality * 0.30
        
        # Defensive factors affect the difficulty
        # We calculate how much the defense reduces the chance
        # Note: Defensive effect is dampened to allow more goals
        defense_effect = (
            defensive_pressure * 0.10 +  # Defenders have moderate impact
            dm_protection * 0.05 +       # DMs provide small additional protection
            gk_rating * 0.15             # Goalkeeper is important for saving
        ) / 200  # Normalize to 0-1 range (roughly)
        
        # Shot on target probability
        # Mainly depends on shooter quality, slightly affected by defense
        # Good shooters get shots on target 40-70% of the time
        base_accuracy = 0.40 + (shooter_rating - 50) / 150  # 40% to ~70%
        # Defense reduces accuracy slightly
        accuracy = base_accuracy * (1 - defense_effect * 0.3)  # Defense has 30% impact on accuracy
        accuracy = max(0.30, min(0.75, accuracy))
        is_on_target = self.rng.random() < accuracy
        
        # Update stats
        if team == "home":
            state.home_shots += 1
            if is_on_target:
                state.home_shots_on_target += 1
        else:
            state.away_shots += 1
            if is_on_target:
                state.away_shots_on_target += 1
        
        if not is_on_target:
            # Shot missed (blocked or off target due to pressure)
            if team == "home":
                state.home_shots_missed += 1
            else:
                state.away_shots_missed += 1
            return
        
        # Shot on target - calculate goal probability
        # This is where goalkeeper and defense matter most
        # Better shooter = more likely to beat the keeper
        # Better keeper = more likely to save
        
        # Shooter vs Goalkeeper duel
        shooter_advantage = (shooter_rating - gk_rating) / 100  # -1 to +1
        
        # Defensive pressure affects the shot power/quality
        # Under pressure, shots are weaker/easier to save
        pressure_factor = (defensive_pressure - 50) / 200  # -0.25 to +0.25
        
        base_conversion = self.BASE_CONVERSION_RATE
        # Shooter advantage has major impact (±20%)
        # Pressure has minor impact (±6%)
        conversion_rate = base_conversion + (shooter_advantage * 0.20) - (pressure_factor * 0.06)
        conversion_rate = max(0.12, min(0.65, conversion_rate))  # 12% to 65%
        
        is_goal = self.rng.random() < conversion_rate
        
        minute = self.rng.randint(1, 90)
        
        if is_goal:
            # GOAL!
            if team == "home":
                state.home_score += 1
            else:
                state.away_score += 1
            
            state.events.append(MatchEvent(
                minute=minute,
                event_type=MatchEventType.GOAL,
                team=team,
                player=shooter.full_name,
                description=f"GOAL! {shooter.full_name} scores!"
            ))
        else:
            # Saved by goalkeeper
            if team == "home":
                state.home_shots_saved += 1
            else:
                state.away_shots_saved += 1
    
    def _select_shooter(self, attackers: list) -> Optional:
        """Select shooter weighted by their scoring ability."""
        if not attackers:
            return None
        
        # Calculate weights based on position-specific ratings
        weights = []
        for p in attackers:
            if hasattr(p, '_data'):
                # Use TS (striker) or AML/AMR (wingers) rating
                rating = p._data.get_rating_for_position(p._data.position)
            else:
                rating = p.current_ability
            weights.append(max(1, rating))
        
        # Weighted random choice
        total = sum(weights)
        if total == 0:
            return self.rng.choice(attackers)
        
        r = self.rng.random() * total
        cumulative = 0
        for player, weight in zip(attackers, weights):
            cumulative += weight
            if r <= cumulative:
                return player
        
        return attackers[-1]


def quick_simulate(home_rating: int, away_rating: int, random_seed: Optional[int] = None) -> dict:
    """Quick simulation for testing."""
    from fm_manager.data.generators import PlayerGenerator
    
    generator = PlayerGenerator(seed=random_seed or 42)
    home_team = [generator.generate_player(home_rating) for _ in range(11)]
    away_team = [generator.generate_player(away_rating) for _ in range(11)]
    
    simulator = RealisticMatchSimulator(random_seed=random_seed)
    state = simulator.simulate(home_team, away_team)
    
    return {
        "home_goals": state.home_score,
        "away_goals": state.away_score,
        "score": state.score_string(),
        "home_shots": state.home_shots,
        "away_shots": state.away_shots,
        "home_on_target": state.home_shots_on_target,
        "away_on_target": state.away_shots_on_target,
    }
