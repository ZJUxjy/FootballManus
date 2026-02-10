"""Youth attribute generator for FM Manager.

Generates complete and realistic player attributes for youth players based on:
- CA/PA (Current Ability / Potential Ability)
- Position-specific priorities
- Age factors (younger players more variable)
- Country-specific modifiers
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from fm_manager.core.models.player import Position


@dataclass
class AttributeRange:
    """Defines min/max bounds for an attribute."""

    min_val: int = 1
    max_val: int = 100

    def clamp(self, value: int) -> int:
        """Clamp value to valid range."""
        return max(self.min_val, min(self.max_val, value))


@dataclass
class PositionModifier:
    """Attribute modifiers for a specific position."""

    # Technical attributes
    shooting: int = 0
    passing: int = 0
    dribbling: int = 0
    crossing: int = 0
    first_touch: int = 0
    technique: int = 0
    tackling: int = 0
    marking: int = 0
    positioning: int = 0
    vision: int = 0
    decisions: int = 0

    # Physical attributes
    pace: int = 0
    acceleration: int = 0
    stamina: int = 0
    strength: int = 0
    agility: int = 0
    jumping: int = 0
    balance: int = 0

    # Mental attributes
    work_rate: int = 0
    determination: int = 0
    leadership: int = 0
    teamwork: int = 0
    aggression: int = 0
    composure: int = 0
    concentration: int = 0
    anticipation: int = 0

    # Goalkeeping (GK only)
    reflexes: int = 0
    handling: int = 0
    kicking: int = 0
    one_on_one: int = 0


@dataclass
class CountryModifier:
    """Country-specific attribute biases."""

    name: str
    # Technical focus
    technical_bonus: int = 0
    passing_bonus: int = 0
    dribbling_bonus: int = 0

    # Physical focus
    physical_bonus: int = 0
    pace_bonus: int = 0
    strength_bonus: int = 0
    jumping_bonus: int = 0
    agility_bonus: int = 0

    # Mental focus
    mental_bonus: int = 0
    determination_bonus: int = 0
    aggression_bonus: int = 0
    work_rate_bonus: int = 0

    # Tactical/Other
    tactical_bonus: int = 0

    # Goalkeeping tradition
    gk_tradition: int = 0


class YouthAttributeGenerator:
    """Generate complete player attributes for youth players."""

    # Position modifiers - defining what each position needs
    POSITION_MODIFIERS: Dict[Position, PositionModifier] = {
        Position.GK: PositionModifier(
            # GKs don't need outfield skills
            shooting=-30,
            passing=-5,
            dribbling=-30,
            crossing=-30,
            tackling=-20,
            marking=-10,
            # Physical
            jumping=10,
            agility=5,
            # Mental
            concentration=15,
            composure=10,
            # GK specific
            reflexes=25,
            handling=25,
            kicking=15,
            one_on_one=20,
        ),
        Position.CB: PositionModifier(
            # Technical
            tackling=20,
            marking=20,
            positioning=15,
            first_touch=5,
            passing=0,
            shooting=-5,
            dribbling=-10,
            crossing=-5,
            # Physical
            strength=15,
            jumping=15,
            pace=-5,
            acceleration=-5,
            # Mental
            concentration=10,
            anticipation=10,
            aggression=10,
            work_rate=5,
        ),
        Position.LB: PositionModifier(
            # Technical
            tackling=10,
            marking=10,
            positioning=5,
            crossing=15,
            dribbling=5,
            passing=5,
            # Physical
            stamina=10,
            pace=5,
            # Mental
            work_rate=10,
            teamwork=10,
        ),
        Position.RB: PositionModifier(
            # Technical
            tackling=10,
            marking=10,
            positioning=5,
            crossing=15,
            dribbling=5,
            passing=5,
            # Physical
            stamina=10,
            pace=5,
            # Mental
            work_rate=10,
            teamwork=10,
        ),
        Position.LWB: PositionModifier(
            # Technical
            crossing=20,
            dribbling=10,
            passing=10,
            tackling=5,
            # Physical
            stamina=15,
            pace=10,
            acceleration=5,
            # Mental
            work_rate=15,
            teamwork=10,
        ),
        Position.RWB: PositionModifier(
            # Technical
            crossing=20,
            dribbling=10,
            passing=10,
            tackling=5,
            # Physical
            stamina=15,
            pace=10,
            acceleration=5,
            # Mental
            work_rate=15,
            teamwork=10,
        ),
        Position.CDM: PositionModifier(
            # Technical
            tackling=15,
            marking=10,
            positioning=10,
            passing=10,
            vision=5,
            shooting=-5,
            # Physical
            strength=10,
            stamina=10,
            # Mental
            work_rate=15,
            concentration=10,
            decisions=10,
            aggression=10,
        ),
        Position.CM: PositionModifier(
            # Technical
            passing=20,
            vision=15,
            first_touch=10,
            technique=10,
            positioning=5,
            tackling=5,
            shooting=-5,
            # Physical
            stamina=15,
            # Mental
            decisions=15,
            teamwork=15,
            concentration=10,
            work_rate=10,
        ),
        Position.LM: PositionModifier(
            # Technical
            crossing=15,
            dribbling=10,
            passing=10,
            # Physical
            pace=10,
            stamina=10,
            # Mental
            work_rate=10,
            teamwork=10,
        ),
        Position.RM: PositionModifier(
            # Technical
            crossing=15,
            dribbling=10,
            passing=10,
            # Physical
            pace=10,
            stamina=10,
            # Mental
            work_rate=10,
            teamwork=10,
        ),
        Position.CAM: PositionModifier(
            # Technical
            vision=20,
            passing=15,
            dribbling=15,
            technique=15,
            first_touch=10,
            shooting=5,
            tackling=-10,
            # Mental
            decisions=15,
            composure=10,
        ),
        Position.LW: PositionModifier(
            # Technical
            dribbling=15,
            crossing=10,
            passing=5,
            shooting=5,
            # Physical
            pace=15,
            acceleration=15,
            agility=10,
            # Mental
            decisions=5,
        ),
        Position.RW: PositionModifier(
            # Technical
            dribbling=15,
            crossing=10,
            passing=5,
            shooting=5,
            # Physical
            pace=15,
            acceleration=15,
            agility=10,
            # Mental
            decisions=5,
        ),
        Position.CF: PositionModifier(
            # Technical
            shooting=15,
            positioning=15,
            first_touch=10,
            dribbling=5,
            passing=-5,
            # Physical
            pace=5,
            strength=10,
            jumping=10,
            balance=10,
            # Mental
            composure=15,
            anticipation=15,
            decisions=5,
        ),
        Position.ST: PositionModifier(
            # Technical
            shooting=20,
            positioning=15,
            first_touch=10,
            dribbling=5,
            passing=-10,
            crossing=-15,
            tackling=-15,
            # Physical
            pace=10,
            strength=10,
            jumping=10,
            balance=10,
            acceleration=5,
            # Mental
            composure=15,
            anticipation=15,
            determination=10,
            aggression=5,
        ),
    }

    # Country modifiers - football traditions
    COUNTRY_MODIFIERS: Dict[str, CountryModifier] = {
        # Technical nations (with GK traditions where applicable)
        "Spain": CountryModifier(
            "Spain", technical_bonus=5, passing_bonus=5, mental_bonus=3, gk_tradition=5
        ),
        "Brazil": CountryModifier("Brazil", technical_bonus=8, dribbling_bonus=5, agility_bonus=3),
        "Argentina": CountryModifier(
            "Argentina", technical_bonus=5, determination_bonus=5, mental_bonus=3
        ),
        "Portugal": CountryModifier("Portugal", technical_bonus=5, dribbling_bonus=3),
        "Italy": CountryModifier(
            "Italy", technical_bonus=3, mental_bonus=5, tactical_bonus=5, gk_tradition=8
        ),
        "Netherlands": CountryModifier(
            "Netherlands", passing_bonus=5, technical_bonus=3, mental_bonus=3
        ),
        # Physical nations (with GK traditions where applicable)
        "England": CountryModifier(
            "England", physical_bonus=5, strength_bonus=3, pace_bonus=3, determination_bonus=3
        ),
        "Germany": CountryModifier(
            "Germany",
            physical_bonus=5,
            mental_bonus=5,
            determination_bonus=5,
            gk_tradition=10,
        ),
        "France": CountryModifier("France", physical_bonus=5, pace_bonus=5, technical_bonus=3),
        "Sweden": CountryModifier("Sweden", strength_bonus=5, jumping_bonus=3, physical_bonus=3),
        "Norway": CountryModifier("Norway", strength_bonus=5, physical_bonus=3),
        # Balanced/Mixed
        "Belgium": CountryModifier("Belgium", technical_bonus=3, physical_bonus=3, mental_bonus=3),
        "Croatia": CountryModifier(
            "Croatia", technical_bonus=5, mental_bonus=3, determination_bonus=3
        ),
        "Uruguay": CountryModifier(
            "Uruguay", determination_bonus=8, physical_bonus=3, aggression_bonus=3
        ),
        # Other notable nations
        "Mexico": CountryModifier("Mexico", technical_bonus=3, agility_bonus=3),
        "USA": CountryModifier("USA", physical_bonus=5, pace_bonus=3, strength_bonus=3),
        "Nigeria": CountryModifier("Nigeria", pace_bonus=10, physical_bonus=5, strength_bonus=3),
        "Ghana": CountryModifier("Ghana", physical_bonus=5, pace_bonus=5),
        "Ivory Coast": CountryModifier("Ivory Coast", physical_bonus=5, strength_bonus=5),
        "Senegal": CountryModifier("Senegal", physical_bonus=5, strength_bonus=5, pace_bonus=3),
        "Colombia": CountryModifier("Colombia", technical_bonus=3, agility_bonus=3),
        "Chile": CountryModifier("Chile", determination_bonus=5, work_rate_bonus=3),
    }

    # Default modifier for unknown countries
    DEFAULT_COUNTRY_MODIFIER = CountryModifier("Default")

    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator with optional seed for reproducibility."""
        self.rng = random.Random(seed)
        self.attr_range = AttributeRange(1, 100)

    def generate_attributes(
        self,
        ca: float,
        pa: float,
        position: str,
        age: int,
        country: str = "",
    ) -> Dict[str, int]:
        """Generate all attributes for a youth player.

        Args:
            ca: Current Ability (0-200 scale, will be converted to 0-100)
            pa: Potential Ability (0-200 scale, will be converted to 0-100)
            position: Player position (e.g., "ST", "CM", "GK")
            age: Player age (affects variance)
            country: Country of origin (for modifiers)

        Returns:
            Dictionary with all generated attributes
        """
        # Normalize CA/PA to 0-100 scale
        ca_100 = min(100, max(1, ca / 2)) if ca > 100 else ca
        pa_100 = min(100, max(1, pa / 2)) if pa > 100 else pa

        # Get position enum
        pos = self._parse_position(position)

        # Calculate age factor (younger = more variable)
        age_factor = self._calculate_age_factor(age)

        # Get modifiers
        pos_modifier = self.POSITION_MODIFIERS.get(pos, PositionModifier())
        country_modifier = self.COUNTRY_MODIFIERS.get(country, self.DEFAULT_COUNTRY_MODIFIER)

        # Generate attribute groups
        technical = self._generate_technical(
            ca_100, pos, pos_modifier, country_modifier, age_factor
        )
        physical = self._generate_physical(
            ca_100, age, pos, pos_modifier, country_modifier, age_factor
        )
        mental = self._generate_mental(ca_100, age, pos_modifier, country_modifier, age_factor)

        # Combine all attributes
        attributes = {**technical, **physical, **mental}

        # Add goalkeeping attributes for GKs
        if pos == Position.GK:
            gk_attrs = self._generate_goalkeeping(
                ca_100, pos_modifier, country_modifier, age_factor
            )
            attributes.update(gk_attrs)
        else:
            # Set GK attributes to low values for outfield players
            attributes.update(
                {
                    "reflexes": self.rng.randint(5, 25),
                    "handling": self.rng.randint(5, 25),
                    "kicking": self.rng.randint(20, 50),
                    "one_on_one": self.rng.randint(5, 25),
                }
            )

        return attributes

    def _parse_position(self, position: str) -> Position:
        """Parse position string to Position enum."""
        position_map = {
            "GK": Position.GK,
            "CB": Position.CB,
            "LB": Position.LB,
            "RB": Position.RB,
            "LWB": Position.LWB,
            "RWB": Position.RWB,
            "CDM": Position.CDM,
            "CM": Position.CM,
            "LM": Position.LM,
            "RM": Position.RM,
            "CAM": Position.CAM,
            "LW": Position.LW,
            "RW": Position.RW,
            "CF": Position.CF,
            "ST": Position.ST,
        }
        return position_map.get(position.upper(), Position.CM)

    def _calculate_age_factor(self, age: int) -> float:
        """Calculate age factor affecting attribute variance.

        Younger players have more variable attributes (more potential range).
        """
        if age <= 15:
            return 1.4  # Very high variance
        elif age <= 17:
            return 1.2  # High variance
        elif age <= 19:
            return 1.0  # Normal
        elif age <= 21:
            return 0.9  # Lower variance
        else:
            return 0.8  # More consistent

    def _generate_base_value(
        self, ca: float, variance: float, modifier: int = 0, age_factor: float = 1.0
    ) -> int:
        """Generate a base attribute value with random factor."""
        # Base from CA with random factor 0.7-1.3
        random_factor = self.rng.uniform(0.7, 1.3)
        base_value = ca * random_factor

        # Apply position/country modifier
        modified = base_value + modifier

        # Apply variance based on age
        variance_amount = variance * age_factor
        noise = self.rng.gauss(0, variance_amount)

        final_value = modified + noise
        return self.attr_range.clamp(int(final_value))

    def _generate_technical(
        self,
        ca: float,
        position: Position,
        pos_modifier: PositionModifier,
        country_modifier: CountryModifier,
        age_factor: float,
    ) -> Dict[str, int]:
        """Generate technical attributes."""
        base_variance = 15

        # Country bonus for technical attributes
        country_bonus = country_modifier.technical_bonus
        passing_bonus = country_modifier.passing_bonus

        attributes = {
            "shooting": self._generate_base_value(
                ca, base_variance, pos_modifier.shooting + country_bonus, age_factor
            ),
            "passing": self._generate_base_value(
                ca, base_variance, pos_modifier.passing + country_bonus + passing_bonus, age_factor
            ),
            "dribbling": self._generate_base_value(
                ca, base_variance, pos_modifier.dribbling + country_bonus, age_factor
            ),
            "crossing": self._generate_base_value(
                ca, base_variance, pos_modifier.crossing + country_bonus, age_factor
            ),
            "first_touch": self._generate_base_value(
                ca, base_variance, pos_modifier.first_touch + country_bonus, age_factor
            ),
            "technique": self._generate_base_value(
                ca, base_variance, pos_modifier.technique + country_bonus, age_factor
            ),
            "tackling": self._generate_base_value(
                ca, base_variance, pos_modifier.tackling, age_factor
            ),
            "marking": self._generate_base_value(
                ca, base_variance, pos_modifier.marking, age_factor
            ),
            "positioning": self._generate_base_value(
                ca, base_variance, pos_modifier.positioning, age_factor
            ),
            "vision": self._generate_base_value(
                ca, base_variance, pos_modifier.vision + country_bonus, age_factor
            ),
            "decisions": self._generate_base_value(
                ca, base_variance, pos_modifier.decisions, age_factor
            ),
        }

        return attributes

    def _generate_physical(
        self,
        ca: float,
        age: int,
        position: Position,
        pos_modifier: PositionModifier,
        country_modifier: CountryModifier,
        age_factor: float,
    ) -> Dict[str, int]:
        """Generate physical attributes with age considerations."""
        base_variance = 12

        # Age affects physical development
        age_physical_factor = self._calculate_age_physical_factor(age)

        # Country bonus
        country_bonus = country_modifier.physical_bonus
        pace_bonus = country_modifier.pace_bonus
        strength_bonus = country_modifier.strength_bonus

        attributes = {
            "pace": self._generate_base_value(
                ca, base_variance, pos_modifier.pace + country_bonus + pace_bonus, age_factor
            ),
            "acceleration": self._generate_base_value(
                ca,
                base_variance,
                pos_modifier.acceleration + country_bonus + pace_bonus,
                age_factor,
            ),
            "stamina": self._generate_base_value(
                ca, base_variance, pos_modifier.stamina + country_bonus, age_factor
            ),
            "strength": self._generate_base_value(
                ca * age_physical_factor,
                base_variance,
                pos_modifier.strength + country_bonus + strength_bonus,
                age_factor,
            ),
            "agility": self._generate_base_value(
                ca, base_variance, pos_modifier.agility + country_bonus, age_factor
            ),
            "jumping": self._generate_base_value(
                ca, base_variance, pos_modifier.jumping, age_factor
            ),
            "balance": self._generate_base_value(
                ca, base_variance, pos_modifier.balance, age_factor
            ),
        }

        return attributes

    def _calculate_age_physical_factor(self, age: int) -> float:
        """Calculate physical development factor based on age.

        Very young players may not have fully developed physically.
        """
        if age <= 16:
            return 0.85  # Not fully developed
        elif age <= 18:
            return 0.92  # Developing
        elif age <= 21:
            return 0.97  # Nearly there
        else:
            return 1.0  # Fully developed

    def _generate_mental(
        self,
        ca: float,
        age: int,
        pos_modifier: PositionModifier,
        country_modifier: CountryModifier,
        age_factor: float,
    ) -> Dict[str, int]:
        """Generate mental attributes with age considerations."""
        base_variance = 10

        # Mental attributes improve with age/experience
        age_mental_factor = self._calculate_age_mental_factor(age)
        effective_ca = ca * age_mental_factor

        # Country bonus
        country_bonus = country_modifier.mental_bonus
        determination_bonus = country_modifier.determination_bonus

        attributes = {
            "work_rate": self._generate_base_value(
                effective_ca, base_variance, pos_modifier.work_rate + country_bonus, age_factor
            ),
            "determination": self._generate_base_value(
                effective_ca,
                base_variance,
                pos_modifier.determination + country_bonus + determination_bonus,
                age_factor,
            ),
            "leadership": self._generate_base_value(
                effective_ca * 0.9,
                base_variance,  # Leadership is rare
                pos_modifier.leadership,
                age_factor,
            ),
            "teamwork": self._generate_base_value(
                effective_ca, base_variance, pos_modifier.teamwork + country_bonus, age_factor
            ),
            "aggression": self._generate_base_value(
                effective_ca, base_variance, pos_modifier.aggression, age_factor
            ),
            "composure": self._generate_base_value(
                effective_ca, base_variance, pos_modifier.composure, age_factor
            ),
            "concentration": self._generate_base_value(
                effective_ca, base_variance, pos_modifier.concentration, age_factor
            ),
            "anticipation": self._generate_base_value(
                effective_ca, base_variance, pos_modifier.anticipation, age_factor
            ),
        }

        return attributes

    def _calculate_age_mental_factor(self, age: int) -> float:
        """Calculate mental attribute factor based on age.

        Older players generally have better mental attributes due to experience.
        """
        if age <= 17:
            return 0.85  # Still learning
        elif age <= 20:
            return 0.92  # Developing
        elif age <= 25:
            return 0.98  # Nearly mature
        else:
            return 1.0  # Mentally mature

    def _generate_goalkeeping(
        self,
        ca: float,
        pos_modifier: PositionModifier,
        country_modifier: CountryModifier,
        age_factor: float,
    ) -> Dict[str, int]:
        """Generate goalkeeping attributes."""
        base_variance = 12

        # Country GK tradition bonus
        gk_bonus = country_modifier.gk_tradition

        attributes = {
            "reflexes": self._generate_base_value(
                ca, base_variance, pos_modifier.reflexes + gk_bonus, age_factor
            ),
            "handling": self._generate_base_value(
                ca, base_variance, pos_modifier.handling + gk_bonus, age_factor
            ),
            "kicking": self._generate_base_value(
                ca, base_variance, pos_modifier.kicking + gk_bonus, age_factor
            ),
            "one_on_one": self._generate_base_value(
                ca, base_variance, pos_modifier.one_on_one + gk_bonus, age_factor
            ),
        }

        return attributes

    def generate_player_summary(
        self,
        attributes: Dict[str, int],
        position: str,
    ) -> Dict[str, Any]:
        """Generate a summary of player attributes by category.

        Args:
            attributes: Generated attributes dictionary
            position: Player position

        Returns:
            Dictionary with category averages and key strengths
        """
        # Group attributes by category
        technical_attrs = [
            "shooting",
            "passing",
            "dribbling",
            "crossing",
            "first_touch",
            "technique",
            "tackling",
            "marking",
            "positioning",
            "vision",
            "decisions",
        ]
        physical_attrs = [
            "pace",
            "acceleration",
            "stamina",
            "strength",
            "agility",
            "jumping",
            "balance",
        ]
        mental_attrs = [
            "work_rate",
            "determination",
            "leadership",
            "teamwork",
            "aggression",
            "composure",
            "concentration",
            "anticipation",
        ]
        gk_attrs = ["reflexes", "handling", "kicking", "one_on_one"]

        # Calculate averages
        def avg_attrs(attr_list):
            values = [attributes.get(a, 50) for a in attr_list]
            return sum(values) / len(values) if values else 0

        summary = {
            "position": position,
            "technical_average": round(avg_attrs(technical_attrs), 1),
            "physical_average": round(avg_attrs(physical_attrs), 1),
            "mental_average": round(avg_attrs(mental_attrs), 1),
        }

        if position.upper() == "GK":
            summary["goalkeeping_average"] = round(avg_attrs(gk_attrs), 1)

        # Find top 3 strengths
        all_attrs = {k: v for k, v in attributes.items()}
        sorted_attrs = sorted(all_attrs.items(), key=lambda x: x[1], reverse=True)
        summary["top_strengths"] = sorted_attrs[:3]

        # Find top 3 weaknesses
        summary["top_weaknesses"] = sorted_attrs[-3:]

        return summary


# Convenience function for quick generation
def generate_youth_attributes(
    ca: float,
    pa: float,
    position: str,
    age: int,
    country: str = "",
    seed: Optional[int] = None,
) -> Dict[str, int]:
    """Convenience function to generate youth attributes.

    Args:
        ca: Current Ability
        pa: Potential Ability
        position: Player position
        age: Player age
        country: Country of origin
        seed: Random seed for reproducibility

    Returns:
        Dictionary with all attributes
    """
    generator = YouthAttributeGenerator(seed=seed)
    return generator.generate_attributes(ca, pa, position, age, country)
