"""Player Development System for FM Manager.

Comprehensive player development including:
- Youth academy player generation with realistic potential
- Player growth curves based on age, playing time, and training
- Physical and mental attribute development
- Age-related decline for older players
- Post-injury recovery and permanent effects
- Position-specific development patterns
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum, auto

from fm_manager.core.models import Club, Player, Position, WorkRate


class DevelopmentPhase(Enum):
    """Player development phases based on age."""

    YOUTH = auto()  # 15-17: Rapid growth, high potential
    DEVELOPMENT = auto()  # 18-21: Peak growth years
    PRIME = auto()  # 22-26: Solid growth, reaching peak
    LATE_PRIME = auto()  # 27-29: Minimal growth, maintaining ability
    DECLINE = auto()  # 30-33: Gradual decline begins
    LATE_DECLINE = auto()  # 34+: Significant decline


class InjuryImpact(Enum):
    """Long-term impact of serious injuries."""

    NONE = 0  # No permanent effect
    MINOR = 1  # Slight reduction in specific attributes
    MODERATE = 2  # Noticeable reduction, potential capped
    SEVERE = 3  # Significant reduction, early retirement risk
    CAREER_ENDING = 4  # Career ended or severely limited


@dataclass
class AttributeDevelopment:
    """Track development of specific attributes."""

    attribute_name: str
    current_value: int
    potential_value: int
    growth_rate: float = 0.0

    def can_grow(self) -> bool:
        return self.current_value < self.potential_value

    def growth_potential(self) -> int:
        return self.potential_value - self.current_value


@dataclass
class PlayerDevelopmentProfile:
    """Complete development profile for a player."""

    player_id: int

    # Development tracking
    development_phase: DevelopmentPhase = DevelopmentPhase.YOUTH

    # Growth factors (0.0 - 2.0)
    natural_talent: float = 1.0  # Innate ability to develop
    work_ethic: float = 1.0  # Training attitude
    adaptability: float = 1.0  # How well they adapt to new roles

    # Playing history
    total_minutes_played: int = 0
    minutes_by_age: Dict[int, int] = field(default_factory=dict)

    # Development history
    ability_history: List[Tuple[date, int]] = field(default_factory=list)

    # Injury history
    serious_injuries: int = 0
    injury_impact: InjuryImpact = InjuryImpact.NONE
    reduced_attributes: List[str] = field(default_factory=list)

    # Position development
    primary_position: Optional[Position] = None
    secondary_positions: List[Position] = field(default_factory=list)

    # Mental attributes development
    leadership_growth: float = 0.0
    determination_growth: float = 0.0

    def record_ability(self, ability: int, date_recorded: date) -> None:
        """Record ability at a specific date."""
        self.ability_history.append((date_recorded, ability))

    def get_growth_last_season(self) -> int:
        """Get ability growth in the last season."""
        if len(self.ability_history) < 2:
            return 0
        return self.ability_history[-1][1] - self.ability_history[-2][1]


@dataclass
class YouthIntakeConfig:
    """Configuration for youth academy intake."""

    # Academy quality (0-100)
    academy_level: int = 50

    # Recruitment settings
    recruitment_radius: int = 100  # km
    international_recruitment: bool = False

    # Output quality
    min_potential: int = 50
    max_potential: int = 100

    # Number of players per intake
    players_per_intake: int = 3

    # Age range
    min_age: int = 15
    max_age: int = 17

    def get_quality_multiplier(self) -> float:
        """Calculate quality multiplier based on academy level."""
        return 0.5 + (self.academy_level / 100) * 0.5  # 0.5 to 1.0


class YouthAcademyGenerator:
    """Generate realistic youth players with proper development potential."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def generate_youth_intake(
        self,
        club_id: int,
        club_reputation: int,
        config: YouthIntakeConfig,
        intake_date: date,
    ) -> List[Player]:
        """Generate a youth intake for a club."""
        players = []

        for _ in range(config.players_per_intake):
            player = self._generate_youth_player(
                club_id=club_id,
                club_reputation=club_reputation,
                config=config,
                intake_date=intake_date,
            )
            players.append(player)

        return players

    def _generate_youth_player(
        self,
        club_id: int,
        club_reputation: int,
        config: YouthIntakeConfig,
        intake_date: date,
    ) -> Player:
        """Generate a single youth player."""
        # Age
        age = self.rng.randint(config.min_age, config.max_age)
        birth_year = intake_date.year - age
        birth_month = self.rng.randint(1, 12)
        birth_day = self.rng.randint(1, 28)
        birth_date = date(birth_year, birth_month, birth_day)

        # Position (weighted towards club needs)
        position = self.rng.choice(list(Position))

        # Potential based on academy level and club reputation
        # Better clubs attract better youth
        reputation_factor = min(1.0, club_reputation / 10000)
        academy_factor = config.academy_level / 100

        base_potential = 50 + int(30 * reputation_factor) + int(20 * academy_factor)
        potential_variance = int(self.rng.gauss(0, 10))
        potential_ability = max(
            config.min_potential, min(config.max_potential, base_potential + potential_variance)
        )

        # Current ability (15-40 points below potential for youth)
        ability_gap = self.rng.randint(15, 40)
        current_ability = max(20, potential_ability - ability_gap)

        # Create player with realistic attributes
        player = Player(
            first_name=self._generate_first_name(),
            last_name=self._generate_last_name(),
            birth_date=birth_date,
            nationality="England",  # Simplified
            position=position,
            current_ability=current_ability,
            potential_ability=potential_ability,
            club_id=club_id,
            salary=self.rng.randint(500, 2000),
            market_value=self._calculate_youth_value(current_ability, potential_ability, age),
        )

        # Set position-appropriate attributes
        self._set_youth_attributes(player, position, current_ability)

        return player

    def _generate_first_name(self) -> str:
        """Generate a random first name."""
        names = [
            "James",
            "Jack",
            "Harry",
            "Oliver",
            "Benjamin",
            "William",
            "Lucas",
            "Henry",
            "Alexander",
            "Daniel",
            "Matthew",
            "Samuel",
            "Thomas",
            "Joseph",
            "David",
            "Michael",
            "George",
            "Charlie",
        ]
        return self.rng.choice(names)

    def _generate_last_name(self) -> str:
        """Generate a random last name."""
        names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
            "Hernandez",
            "Lopez",
            "Wilson",
            "Anderson",
            "Thomas",
            "Taylor",
            "Moore",
            "Jackson",
        ]
        return self.rng.choice(names)

    def _calculate_youth_value(self, current: int, potential: int, age: int) -> int:
        """Calculate market value for youth player."""
        base = current * 1000
        potential_bonus = (potential - current) * 500
        age_factor = 1.0 if age <= 16 else 0.8
        return int((base + potential_bonus) * age_factor)

    def _set_youth_attributes(self, player: Player, position: Position, ability: int) -> None:
        """Set appropriate attributes for youth player."""
        variance = 15
        base = ability

        # Physical attributes
        player.pace = self._clamp_attribute(base + self.rng.gauss(0, variance))
        player.acceleration = self._clamp_attribute(base + self.rng.gauss(0, variance))
        player.stamina = self._clamp_attribute(base + self.rng.gauss(0, variance))
        player.strength = self._clamp_attribute(base + self.rng.gauss(0, variance))

        # Position-specific
        if position == Position.GK:
            player.reflexes = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.handling = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.positioning = self._clamp_attribute(base + self.rng.gauss(0, variance))
        elif position in {Position.CB, Position.LB, Position.RB}:
            player.tackling = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.marking = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.positioning = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
        elif position in {Position.CM, Position.CDM, Position.CAM}:
            player.passing = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.vision = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.decisions = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
        elif position in {Position.LW, Position.RW, Position.ST, Position.CF}:
            player.shooting = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.dribbling = self._clamp_attribute(base + 5 + self.rng.gauss(0, 10))
            player.positioning = self._clamp_attribute(base + self.rng.gauss(0, variance))

        # Mental attributes
        player.determination = self.rng.randint(40, 80)
        work_rates = [WorkRate.LOW, WorkRate.MEDIUM, WorkRate.HIGH]
        player.work_rate = self.rng.choice(work_rates)
        player.teamwork = self.rng.randint(40, 80)
        player.leadership = self.rng.randint(30, 70)

        # Fitness
        player.fitness = 100
        player.form = 50
        player.morale = 60

    def _clamp_attribute(self, value: float) -> int:
        """Clamp attribute value to valid range."""
        return max(1, min(99, int(value)))


class PlayerDevelopmentEngine:
    """Main engine for player development and growth."""

    # Age curve multipliers for development
    AGE_CURVE = {
        15: 1.5,
        16: 1.4,
        17: 1.3,  # Youth: Rapid growth
        18: 1.2,
        19: 1.1,
        20: 1.0,
        21: 0.95,  # Development: Peak growth
        22: 0.9,
        23: 0.85,
        24: 0.8,
        25: 0.75,
        26: 0.7,  # Prime: Solid growth
        27: 0.6,
        28: 0.5,
        29: 0.4,  # Late prime: Minimal growth
        30: -0.1,
        31: -0.2,
        32: -0.3,
        33: -0.4,  # Decline: Gradual
        34: -0.6,
        35: -0.8,
        36: -1.0,
        37: -1.2,  # Late decline: Significant
    }

    # Playing time thresholds (minutes per season)
    PLAYING_TIME_BONUS = {
        0: 0.0,  # No playing time: No growth
        500: 0.3,  # Minimal: Reduced growth
        1000: 0.6,  # Moderate: Some growth
        1500: 0.8,  # Regular: Good growth
        2000: 1.0,  # Starter: Full growth
        2500: 1.1,  # Key player: Bonus
        3000: 1.2,  # Star: Maximum bonus
    }

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.youth_generator = YouthAcademyGenerator(seed)

    def get_development_phase(self, age: int) -> DevelopmentPhase:
        """Determine development phase based on age."""
        if age <= 17:
            return DevelopmentPhase.YOUTH
        elif age <= 21:
            return DevelopmentPhase.DEVELOPMENT
        elif age <= 26:
            return DevelopmentPhase.PRIME
        elif age <= 29:
            return DevelopmentPhase.LATE_PRIME
        elif age <= 33:
            return DevelopmentPhase.DECLINE
        else:
            return DevelopmentPhase.LATE_DECLINE

    def calculate_season_development(
        self,
        player: Player,
        minutes_played: int,
        training_quality: int = 50,
        match_ratings: Optional[List[float]] = None,
    ) -> Dict:
        """Calculate development for a full season.

        Returns dict with development details.
        """
        age = player.age or 25
        old_ability = player.current_ability
        old_potential = player.potential_ability

        # Get base growth rate from age curve
        age_multiplier = self.AGE_CURVE.get(age, -0.5 if age > 37 else 0.0)

        # Get playing time bonus
        playing_bonus = self._get_playing_time_bonus(minutes_played)

        # Training quality factor (0.5 to 1.5)
        training_factor = 0.5 + (training_quality / 100)

        # Form bonus from match ratings
        form_bonus = 0.0
        if match_ratings:
            avg_rating = sum(match_ratings) / len(match_ratings)
            if avg_rating > 7.5:
                form_bonus = 0.2
            elif avg_rating > 7.0:
                form_bonus = 0.1
            elif avg_rating < 6.0:
                form_bonus = -0.1

        # Calculate total growth
        if age_multiplier > 0:  # Growing phase
            base_growth = 5 * age_multiplier * playing_bonus * training_factor
            base_growth += form_bonus * 2

            # Cap at potential
            potential_gap = old_potential - old_ability
            growth = min(base_growth, potential_gap)

            # Random variation
            growth = max(0, int(self.rng.gauss(growth, growth * 0.2)))

        else:
            decline = abs(age_multiplier) * 5

            if minutes_played > 2000:
                decline *= 0.8
            elif minutes_played > 1000:
                decline *= 0.9

            decline *= 1.0 - (training_quality / 300)

            growth = -max(1, int(decline))

        # Apply growth
        new_ability = max(1, min(99, old_ability + growth))
        actual_growth = new_ability - old_ability

        # Update player
        player.current_ability = new_ability

        # Update physical attributes for older players
        attribute_changes = {}
        if age > 30:
            attribute_changes = self._apply_age_decline(player, age)

        return {
            "old_ability": old_ability,
            "new_ability": new_ability,
            "growth": actual_growth,
            "age": age,
            "minutes_played": minutes_played,
            "age_multiplier": age_multiplier,
            "playing_bonus": playing_bonus,
            "training_factor": training_factor,
            "form_bonus": form_bonus,
            "attribute_changes": attribute_changes,
        }

    def _get_playing_time_bonus(self, minutes: int) -> float:
        """Get development bonus based on playing time."""
        thresholds = sorted(self.PLAYING_TIME_BONUS.keys())
        for threshold in reversed(thresholds):
            if minutes >= threshold:
                return self.PLAYING_TIME_BONUS[threshold]
        return 0.0

    def _apply_age_decline(self, player: Player, age: int) -> Dict[str, int]:
        """Apply physical attribute decline for older players."""
        changes = {}

        # Decline rate increases with age
        decline_rate = max(1, (age - 29) // 2)

        # Physical attributes decline
        physical_attrs = ["pace", "acceleration", "stamina", "strength"]
        for attr in physical_attrs:
            old_val = getattr(player, attr, None)
            if old_val is None:
                old_val = 50
            if old_val > 1:
                decline = self.rng.randint(0, decline_rate)
                new_val = max(1, old_val - decline)
                setattr(player, attr, new_val)
                if decline > 0:
                    changes[attr] = -decline

        # Technical attributes decline slower
        if age > 33:
            technical_attrs = ["dribbling", "pace"]  # Pace goes first
            for attr in technical_attrs:
                old_val = getattr(player, attr, None)
                if old_val is None:
                    old_val = 50
                if old_val > 1 and attr not in changes:
                    decline = self.rng.randint(0, 1)
                    new_val = max(1, old_val - decline)
                    setattr(player, attr, new_val)
                    if decline > 0:
                        changes[attr] = -decline

        return changes

    def apply_injury_recovery(
        self,
        player: Player,
        injury_severity: int,  # 1-5
        recovery_weeks: int,
    ) -> Dict:
        """Apply effects after injury recovery.

        Returns dict with permanent changes.
        """
        changes = {
            "permanent_reduction": False,
            "reduced_attributes": [],
            "potential_capped": False,
            "old_potential": player.potential_ability,
        }

        # Only serious injuries have permanent effects
        if injury_severity >= 3:
            reduction_chance = (injury_severity - 2) * 0.25 + 0.2

            if self.rng.random() < reduction_chance:
                changes["permanent_reduction"] = True

                # Reduce specific attributes based on injury type
                attrs_to_reduce = self.rng.sample(
                    ["pace", "acceleration", "stamina", "strength"], k=self.rng.randint(1, 2)
                )

                for attr in attrs_to_reduce:
                    old_val = getattr(player, attr, None)
                    if old_val is None:
                        old_val = 50
                    reduction = self.rng.randint(1, 3)
                    new_val = max(1, old_val - reduction)
                    setattr(player, attr, new_val)
                    changes["reduced_attributes"].append(
                        {
                            "attribute": attr,
                            "old": old_val,
                            "new": new_val,
                            "reduction": reduction,
                        }
                    )

                # May cap potential
                if injury_severity >= 4 and self.rng.random() < 0.3:
                    old_potential = player.potential_ability
                    new_potential = max(player.current_ability, old_potential - 5)
                    player.potential_ability = new_potential
                    changes["potential_capped"] = True
                    changes["new_potential"] = new_potential

        return changes

    def check_retirement(self, player: Player) -> Tuple[bool, str]:
        """Check if player should retire.

        Returns (should_retire, reason).
        """
        age = player.age or 25
        ability = player.current_ability

        # Base retirement age probabilities
        if age < 33:
            return False, ""

        # Calculate retirement probability
        base_prob = 0.0
        if age == 33:
            base_prob = 0.05
        elif age == 34:
            base_prob = 0.15
        elif age == 35:
            base_prob = 0.35
        elif age == 36:
            base_prob = 0.60
        elif age >= 37:
            base_prob = 0.85

        # Good players play longer
        if ability > 80:
            base_prob *= 0.5
        elif ability > 70:
            base_prob *= 0.7
        elif ability < 50:
            base_prob *= 1.5

        if self.rng.random() < base_prob:
            reason = f"Retired at age {age}"
            if ability > 75:
                reason += " (legend)"
            return True, reason

        return False, ""

    def develop_mental_attributes(
        self,
        player: Player,
        matches_played: int,
    ) -> Dict[str, int]:
        """Develop mental attributes based on experience."""
        changes = {}

        # Leadership can grow with experience
        if matches_played > 20 and player.leadership < 80:
            if self.rng.random() < 0.3:  # 30% chance per season
                old = player.leadership
                player.leadership = min(99, old + self.rng.randint(1, 3))
                changes["leadership"] = player.leadership - old

        # Determination can improve with good performances
        if player.determination < 85:
            if self.rng.random() < 0.2:
                old = player.determination
                player.determination = min(99, old + self.rng.randint(1, 2))
                changes["determination"] = player.determination - old

        return changes


class DevelopmentTracker:
    """Track development across multiple seasons."""

    def __init__(self):
        self.profiles: Dict[int, PlayerDevelopmentProfile] = {}

    def get_or_create_profile(self, player: Player) -> PlayerDevelopmentProfile:
        """Get or create development profile for player."""
        if player.id not in self.profiles:
            self.profiles[player.id] = PlayerDevelopmentProfile(
                player_id=player.id,
                development_phase=PlayerDevelopmentEngine().get_development_phase(player.age or 25),
                primary_position=player.position,
            )
        return self.profiles[player.id]

    def record_season(
        self,
        player: Player,
        minutes_played: int,
        development_result: Dict,
    ) -> None:
        """Record a season's development."""
        profile = self.get_or_create_profile(player)

        # Update phase
        profile.development_phase = PlayerDevelopmentEngine().get_development_phase(
            player.age or 25
        )

        # Record ability
        profile.record_ability(player.current_ability, date.today())

        # Update playing time
        profile.total_minutes_played += minutes_played
        age = player.age or 25
        if age not in profile.minutes_by_age:
            profile.minutes_by_age[age] = 0
        profile.minutes_by_age[age] += minutes_played

    def get_development_summary(self, player_id: int) -> Optional[Dict]:
        """Get development summary for a player."""
        if player_id not in self.profiles:
            return None

        profile = self.profiles[player_id]

        if not profile.ability_history:
            return None

        first_ability = profile.ability_history[0][1]
        current_ability = profile.ability_history[-1][1]
        total_growth = current_ability - first_ability

        return {
            "player_id": player_id,
            "development_phase": profile.development_phase.name,
            "total_growth": total_growth,
            "seasons_tracked": len(profile.ability_history),
            "total_minutes": profile.total_minutes_played,
            "serious_injuries": profile.serious_injuries,
            "injury_impact": profile.injury_impact.name,
        }
