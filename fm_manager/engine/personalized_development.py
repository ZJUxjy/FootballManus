"""Personalized Player Development System for FM Manager.

Each player has a unique development trajectory based on:
- Player archetype (early peak, standard, late bloomer, consistent)
- Position-specific development patterns
- Personality traits affecting growth
- Dynamic potential adjustments
"""

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto

from fm_manager.core.models import Player, Position


class PlayerArchetype(Enum):
    """Player development archetypes - determines career trajectory."""

    EARLY_PEAKER = auto()  # Peak at 20-24, rapid decline (pace-based players)
    STANDARD = auto()  # Peak at 24-28 (most players)
    LATE_BLOOMER = auto()  # Peak at 27-31 (technical players, GKs)
    CONSISTENT = auto()  # Long peak, slow decline (legendary players)
    INJURY_PRONE = auto()  # High potential but injury risk
    WORKHORSE = auto()  # Lower peak but very consistent


class PersonalityTrait(Enum):
    """Personality traits affecting development."""

    PROFESSIONAL = auto()  # Better training, slower decline
    AMBITIOUS = auto()  # Faster growth with playing time
    DETERMINED = auto()  # Better recovery from setbacks
    LAZY = auto()  # Slower growth, faster decline
    FRAGILE = auto()  # Higher injury risk
    RESILIENT = auto()  # Lower injury risk, better recovery


@dataclass
class DevelopmentProfile:
    """Complete development profile for a player."""

    # Core archetype
    archetype: PlayerArchetype = PlayerArchetype.STANDARD

    # Personality traits (can have multiple)
    traits: List[PersonalityTrait] = field(default_factory=list)

    # Peak years
    peak_start_age: int = 24
    peak_end_age: int = 28

    # Growth characteristics
    early_growth_rate: float = 1.0  # Multiplier for ages 15-21
    prime_growth_rate: float = 1.0  # Multiplier for peak years
    decline_rate: float = 1.0  # Multiplier for decline speed

    # Position-specific modifiers
    position_growth_modifiers: Dict[str, float] = field(default_factory=dict)

    # Career longevity
    expected_retirement_age: int = 35

    # Development history
    breakthrough_year: Optional[int] = None  # Age when player broke through

    def get_age_multiplier(self, age: int) -> float:
        """Get growth multiplier for specific age."""
        if age <= 21:
            return self.early_growth_rate * self._base_youth_multiplier(age)
        elif age < self.peak_start_age:
            return self._base_development_multiplier(age)
        elif age <= self.peak_end_age:
            return self.prime_growth_rate * 0.8
        else:
            return -self.decline_rate * self._base_decline_multiplier(age)

    def _base_youth_multiplier(self, age: int) -> float:
        """Base multiplier for youth years."""
        multipliers = {15: 1.5, 16: 1.4, 17: 1.3, 18: 1.2, 19: 1.1, 20: 1.0, 21: 0.95}
        return multipliers.get(age, 1.0)

    def _base_development_multiplier(self, age: int) -> float:
        """Base multiplier for development years."""
        return 0.9 - (age - 22) * 0.05

    def _base_decline_multiplier(self, age: int) -> float:
        """Base multiplier for decline years."""
        years_past_peak = age - self.peak_end_age
        return 0.2 + years_past_peak * 0.15


class ArchetypeGenerator:
    """Generate development archetypes based on player characteristics."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def generate_archetype(
        self,
        position: Position,
        potential: int,
        personality_traits: Optional[List[PersonalityTrait]] = None,
    ) -> DevelopmentProfile:
        """Generate appropriate archetype for a player."""

        # Determine base archetype based on position
        archetype = self._determine_base_archetype(position)

        # Adjust based on potential (high potential = more likely to be consistent)
        if potential >= 85 and self.rng.random() < 0.3:
            archetype = PlayerArchetype.CONSISTENT

        # Generate traits if not provided
        if personality_traits is None:
            traits = self._generate_traits(archetype, potential)
        else:
            traits = personality_traits

        # Create profile based on archetype
        profile = self._create_profile(archetype, position, traits)

        return profile

    def _determine_base_archetype(self, position: Position) -> PlayerArchetype:
        """Determine base archetype from position."""
        archetype_weights = {
            # Speed-based positions tend to peak early
            Position.LW: [
                (PlayerArchetype.EARLY_PEAKER, 0.4),
                (PlayerArchetype.STANDARD, 0.4),
                (PlayerArchetype.CONSISTENT, 0.2),
            ],
            Position.RW: [
                (PlayerArchetype.EARLY_PEAKER, 0.4),
                (PlayerArchetype.STANDARD, 0.4),
                (PlayerArchetype.CONSISTENT, 0.2),
            ],
            Position.ST: [
                (PlayerArchetype.EARLY_PEAKER, 0.3),
                (PlayerArchetype.STANDARD, 0.5),
                (PlayerArchetype.LATE_BLOOMER, 0.2),
            ],
            # Technical midfielders can be late bloomers
            Position.CAM: [
                (PlayerArchetype.LATE_BLOOMER, 0.35),
                (PlayerArchetype.STANDARD, 0.45),
                (PlayerArchetype.CONSISTENT, 0.2),
            ],
            Position.CM: [
                (PlayerArchetype.STANDARD, 0.5),
                (PlayerArchetype.LATE_BLOOMER, 0.3),
                (PlayerArchetype.CONSISTENT, 0.2),
            ],
            Position.CDM: [
                (PlayerArchetype.LATE_BLOOMER, 0.4),
                (PlayerArchetype.STANDARD, 0.4),
                (PlayerArchetype.CONSISTENT, 0.2),
            ],
            # Defenders - standard to late bloomer
            Position.CB: [
                (PlayerArchetype.STANDARD, 0.4),
                (PlayerArchetype.LATE_BLOOMER, 0.4),
                (PlayerArchetype.CONSISTENT, 0.2),
            ],
            Position.LB: [
                (PlayerArchetype.EARLY_PEAKER, 0.25),
                (PlayerArchetype.STANDARD, 0.45),
                (PlayerArchetype.LATE_BLOOMER, 0.3),
            ],
            Position.RB: [
                (PlayerArchetype.EARLY_PEAKER, 0.25),
                (PlayerArchetype.STANDARD, 0.45),
                (PlayerArchetype.LATE_BLOOMER, 0.3),
            ],
            # Goalkeepers - always late bloomers
            Position.GK: [
                (PlayerArchetype.LATE_BLOOMER, 0.6),
                (PlayerArchetype.CONSISTENT, 0.3),
                (PlayerArchetype.STANDARD, 0.1),
            ],
        }

        weights = archetype_weights.get(position, [(PlayerArchetype.STANDARD, 1.0)])
        archetypes, probs = zip(*weights)
        return self.rng.choices(archetypes, weights=probs)[0]

    def _generate_traits(
        self,
        archetype: PlayerArchetype,
        potential: int,
    ) -> List[PersonalityTrait]:
        """Generate personality traits based on archetype."""
        traits = []

        # Archetype-specific traits
        trait_chances = {
            PlayerArchetype.EARLY_PEAKER: [
                (PersonalityTrait.AMBITIOUS, 0.4),
                (PersonalityTrait.PROFESSIONAL, 0.3),
                (PersonalityTrait.LAZY, 0.15),
            ],
            PlayerArchetype.LATE_BLOOMER: [
                (PersonalityTrait.DETERMINED, 0.5),
                (PersonalityTrait.PROFESSIONAL, 0.4),
                (PersonalityTrait.RESILIENT, 0.3),
            ],
            PlayerArchetype.CONSISTENT: [
                (PersonalityTrait.PROFESSIONAL, 0.6),
                (PersonalityTrait.DETERMINED, 0.4),
                (PersonalityTrait.RESILIENT, 0.3),
            ],
            PlayerArchetype.INJURY_PRONE: [
                (PersonalityTrait.FRAGILE, 0.7),
                (PersonalityTrait.DETERMINED, 0.3),
            ],
            PlayerArchetype.WORKHORSE: [
                (PersonalityTrait.PROFESSIONAL, 0.5),
                (PersonalityTrait.RESILIENT, 0.4),
                (PersonalityTrait.DETERMINED, 0.3),
            ],
            PlayerArchetype.STANDARD: [
                (PersonalityTrait.PROFESSIONAL, 0.3),
                (PersonalityTrait.AMBITIOUS, 0.3),
                (PersonalityTrait.DETERMINED, 0.2),
            ],
        }

        chances = trait_chances.get(archetype, [])
        for trait, chance in chances:
            if self.rng.random() < chance:
                traits.append(trait)

        # High potential players more likely to be professional/ambitious
        if potential >= 80 and self.rng.random() < 0.4:
            if PersonalityTrait.PROFESSIONAL not in traits:
                traits.append(PersonalityTrait.PROFESSIONAL)

        return traits

    def _create_profile(
        self,
        archetype: PlayerArchetype,
        position: Position,
        traits: List[PersonalityTrait],
    ) -> DevelopmentProfile:
        """Create development profile from archetype and traits."""

        # Base profile for each archetype
        archetype_configs = {
            PlayerArchetype.EARLY_PEAKER: {
                "peak_start_age": 20,
                "peak_end_age": 24,
                "early_growth_rate": 1.3,
                "prime_growth_rate": 1.1,
                "decline_rate": 1.5,
                "expected_retirement_age": 32,
            },
            PlayerArchetype.STANDARD: {
                "peak_start_age": 24,
                "peak_end_age": 28,
                "early_growth_rate": 1.0,
                "prime_growth_rate": 1.0,
                "decline_rate": 1.0,
                "expected_retirement_age": 35,
            },
            PlayerArchetype.LATE_BLOOMER: {
                "peak_start_age": 27,
                "peak_end_age": 31,
                "early_growth_rate": 0.8,
                "prime_growth_rate": 1.0,
                "decline_rate": 0.7,
                "expected_retirement_age": 37,
            },
            PlayerArchetype.CONSISTENT: {
                "peak_start_age": 25,
                "peak_end_age": 32,
                "early_growth_rate": 1.0,
                "prime_growth_rate": 1.1,
                "decline_rate": 0.6,
                "expected_retirement_age": 38,
            },
            PlayerArchetype.INJURY_PRONE: {
                "peak_start_age": 23,
                "peak_end_age": 27,
                "early_growth_rate": 1.2,
                "prime_growth_rate": 1.0,
                "decline_rate": 1.3,
                "expected_retirement_age": 32,
            },
            PlayerArchetype.WORKHORSE: {
                "peak_start_age": 25,
                "peak_end_age": 29,
                "early_growth_rate": 0.9,
                "prime_growth_rate": 0.95,
                "decline_rate": 0.8,
                "expected_retirement_age": 36,
            },
        }

        config = archetype_configs[archetype].copy()
        config["archetype"] = archetype
        config["traits"] = traits

        # Apply trait modifiers
        if PersonalityTrait.PROFESSIONAL in traits:
            config["decline_rate"] *= 0.85
            config["expected_retirement_age"] += 1

        if PersonalityTrait.AMBITIOUS in traits:
            config["early_growth_rate"] *= 1.15

        if PersonalityTrait.DETERMINED in traits:
            config["prime_growth_rate"] *= 1.1

        if PersonalityTrait.LAZY in traits:
            config["early_growth_rate"] *= 0.85
            config["decline_rate"] *= 1.2

        # Position-specific attribute modifiers
        position_modifiers = self._get_position_modifiers(position)
        config["position_growth_modifiers"] = position_modifiers

        return DevelopmentProfile(**config)

    def _get_position_modifiers(self, position: Position) -> Dict[str, float]:
        """Get attribute growth modifiers for position."""
        modifiers = {}

        if position in [Position.LW, Position.RW, Position.ST]:
            modifiers["pace"] = 1.2
            modifiers["acceleration"] = 1.2
            modifiers["shooting"] = 1.1
            modifiers["vision"] = 0.9
        elif position in [Position.CM, Position.CAM, Position.CDM]:
            modifiers["vision"] = 1.2
            modifiers["passing"] = 1.2
            modifiers["decisions"] = 1.1
            modifiers["pace"] = 0.9
        elif position in [Position.CB, Position.LB, Position.RB]:
            modifiers["positioning"] = 1.2
            modifiers["tackling"] = 1.1
            modifiers["marking"] = 1.1
            modifiers["pace"] = 0.95
        elif position == Position.GK:
            modifiers["reflexes"] = 1.3
            modifiers["positioning"] = 1.2
            modifiers["handling"] = 1.2

        return modifiers


class PersonalizedDevelopmentEngine:
    """Engine for personalized player development."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.archetype_generator = ArchetypeGenerator(seed)

    def create_player_profile(self, player: Player) -> DevelopmentProfile:
        """Create development profile for a player."""
        return self.archetype_generator.generate_archetype(
            position=player.position or Position.ST,
            potential=player.potential_ability or 70,
        )

    def calculate_season_growth(
        self,
        player: Player,
        profile: DevelopmentProfile,
        age: int,
        minutes_played: int,
        training_quality: int = 50,
    ) -> Dict:
        """Calculate growth for a season with personalized profile."""

        # Get age-based multiplier from profile
        age_multiplier = profile.get_age_multiplier(age)

        # Calculate playing time bonus
        playing_bonus = self._calculate_playing_bonus(minutes_played, profile)

        # Training factor
        training_factor = 0.5 + (training_quality / 100)

        # Trait bonuses
        trait_bonus = self._calculate_trait_bonus(profile.traits, minutes_played)

        if age_multiplier > 0:
            # Growing phase
            base_growth = 5 * age_multiplier * playing_bonus * training_factor
            base_growth += trait_bonus

            # Cap at potential
            potential_gap = player.potential_ability - player.current_ability
            growth = min(base_growth, potential_gap)

            # Random variation
            growth = max(0, int(self.rng.gauss(growth, growth * 0.2)))
        else:
            # Declining phase
            decline = abs(age_multiplier) * 5 * profile.decline_rate

            # Playing time slows decline
            if minutes_played > 2000:
                decline *= 0.8
            elif minutes_played > 1000:
                decline *= 0.9

            # Professional trait helps
            if PersonalityTrait.PROFESSIONAL in profile.traits:
                decline *= 0.9

            growth = -max(1, int(decline))

        # Apply position-specific modifiers to attributes
        attribute_changes = self._apply_position_development(player, profile, age, growth)

        # Update current ability
        old_ability = player.current_ability
        new_ability = max(1, min(99, old_ability + growth))
        player.current_ability = new_ability

        return {
            "old_ability": old_ability,
            "new_ability": new_ability,
            "growth": new_ability - old_ability,
            "age_multiplier": age_multiplier,
            "playing_bonus": playing_bonus,
            "trait_bonus": trait_bonus,
            "attribute_changes": attribute_changes,
            "archetype": profile.archetype.name,
        }

    def _calculate_playing_bonus(
        self,
        minutes: int,
        profile: DevelopmentProfile,
    ) -> float:
        """Calculate playing time bonus based on profile."""
        if minutes >= 3000:
            base = 1.2
        elif minutes >= 2000:
            base = 1.0
        elif minutes >= 1500:
            base = 0.8
        elif minutes >= 1000:
            base = 0.6
        elif minutes >= 500:
            base = 0.4
        else:
            base = 0.2

        # Workhorse archetype benefits more from playing time
        if profile.archetype == PlayerArchetype.WORKHORSE:
            base *= 1.15

        return base

    def _calculate_trait_bonus(
        self,
        traits: List[PersonalityTrait],
        minutes_played: int,
    ) -> float:
        """Calculate bonus from personality traits."""
        bonus = 0.0

        if PersonalityTrait.AMBITIOUS in traits and minutes_played > 2000:
            bonus += 0.5

        if PersonalityTrait.DETERMINED in traits:
            bonus += 0.3

        if PersonalityTrait.PROFESSIONAL in traits:
            bonus += 0.2

        if PersonalityTrait.LAZY in traits:
            bonus -= 0.5

        return bonus

    def _apply_position_development(
        self,
        player: Player,
        profile: DevelopmentProfile,
        age: int,
        ability_growth: int,
    ) -> Dict[str, int]:
        """Apply position-specific attribute development."""
        changes = {}

        # Only apply during growth years
        if ability_growth <= 0:
            return changes

        for attr, modifier in profile.position_growth_modifiers.items():
            old_val = getattr(player, attr, None)
            if old_val is None:
                continue

            # Calculate attribute growth
            attr_growth = int(ability_growth * modifier * self.rng.uniform(0.8, 1.2))

            if attr_growth > 0:
                new_val = min(99, old_val + attr_growth)
                setattr(player, attr, new_val)
                changes[attr] = new_val - old_val

        return changes

    def should_retire(
        self,
        player: Player,
        profile: DevelopmentProfile,
    ) -> Tuple[bool, str]:
        """Check if player should retire based on profile."""
        age = player.age or 25
        ability = player.current_ability

        # Base retirement age from profile
        expected_age = profile.expected_retirement_age

        if age < expected_age - 3:
            return False, ""

        # Calculate probability
        years_past_expected = age - expected_age

        if years_past_expected < 0:
            base_prob = 0.1
        elif years_past_expected == 0:
            base_prob = 0.3
        elif years_past_expected == 1:
            base_prob = 0.5
        elif years_past_expected == 2:
            base_prob = 0.75
        else:
            base_prob = 0.9

        # Ability affects retirement
        if ability > 80:
            base_prob *= 0.6
        elif ability > 70:
            base_prob *= 0.8
        elif ability < 50:
            base_prob *= 1.3

        # Professional players play longer
        if PersonalityTrait.PROFESSIONAL in profile.traits:
            base_prob *= 0.8

        if self.rng.random() < base_prob:
            reason = f"Retired at age {age}"
            if ability > 75:
                reason += " (legend)"
            elif years_past_expected > 2:
                reason += " (age caught up)"
            return True, reason

        return False, ""


class PlayerDevelopmentRegistry:
    """Registry to track all player development profiles."""

    def __init__(self):
        self.profiles: Dict[int, DevelopmentProfile] = {}
        self.engine = PersonalizedDevelopmentEngine()

    def get_or_create_profile(self, player: Player) -> DevelopmentProfile:
        """Get or create development profile for player."""
        if player.id not in self.profiles:
            self.profiles[player.id] = self.engine.create_player_profile(player)
        return self.profiles[player.id]

    def get_profile(self, player_id: int) -> Optional[DevelopmentProfile]:
        """Get profile by player ID."""
        return self.profiles.get(player_id)

    def simulate_season(
        self,
        player: Player,
        minutes_played: int,
        training_quality: int = 50,
    ) -> Dict:
        """Simulate one season for a player."""
        profile = self.get_or_create_profile(player)
        age = player.age or 25

        result = self.engine.calculate_season_growth(
            player=player,
            profile=profile,
            age=age,
            minutes_played=minutes_played,
            training_quality=training_quality,
        )

        return result
