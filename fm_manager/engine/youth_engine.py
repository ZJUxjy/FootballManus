"""Youth development engine for FM Manager.

Handles youth academy functionality:
- Youth player generation
- Player development curves
- Scouting network
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from fm_manager.core.models import Club, Player, Position, Foot
from fm_manager.data.generators import FIRST_NAMES, LAST_NAMES, NATIONALITIES


@dataclass
class YouthAcademy:
    """Youth academy configuration for a club."""
    club_id: int
    
    # Academy level (0-100)
    level: int = 50
    
    # Youth recruitment
    recruitment_range: int = 50  # km radius for scouting
    international_recruitment: bool = False
    
    # Facilities
    coaching_quality: int = 50
    facilities_quality: int = 50
    
    # Output
    players_per_intake: int = 3  # New players per year
    next_intake_date: date = field(default_factory=date.today)
    
    # History
    notable_graduates: list[int] = field(default_factory=list)  # Player IDs
    
    def get_intake_quality(self) -> float:
        """Calculate expected quality of youth intake."""
        return (self.level * 0.5 + self.coaching_quality * 0.3 + self.facilities_quality * 0.2) / 100


@dataclass
class PlayerDevelopment:
    """Track a player's development over time."""
    player_id: int
    
    # Development factors
    current_ability_history: list[tuple[date, int]] = field(default_factory=list)
    potential_ability: int = 0
    
    # Training focus
    training_focus: str = "balanced"  # balanced, physical, technical, mental
    
    # Playing time
    minutes_played_season: int = 0
    matches_played_season: int = 0
    
    # Form
    recent_ratings: list[float] = field(default_factory=list)
    
    def calculate_growth_rate(self) -> float:
        """Calculate current growth rate based on various factors."""
        base_rate = 1.0
        
        # Playing time bonus
        if self.minutes_played_season > 2000:
            base_rate += 0.3
        elif self.minutes_played_season > 1000:
            base_rate += 0.15
        
        # Form bonus
        if self.recent_ratings:
            avg_rating = sum(self.recent_ratings) / len(self.recent_ratings)
            if avg_rating > 7.0:
                base_rate += 0.2
        
        return base_rate


@dataclass
class ScoutingAssignment:
    """A scouting assignment."""
    id: int = 0
    region: str = ""  # Country or region name
    focus_position: Position | None = None
    min_potential: int = 60
    max_age: int = 21
    
    # Progress
    days_remaining: int = 30
    progress: float = 0.0  # 0-100
    
    # Results
    players_found: list[int] = field(default_factory=list)  # Player IDs


@dataclass
class ScoutingReport:
    """A scouting report on a player."""
    player_id: int
    scout_id: int
    
    # Assessment
    current_ability_estimate: int = 50
    potential_ability_estimate: int = 70
    confidence: int = 50  # How confident the scout is (0-100)
    
    # Detailed ratings
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    
    # Recommendation
    recommendation: str = "monitor"  # sign, monitor, avoid
    estimated_cost: int = 0
    
    report_date: date = field(default_factory=date.today)


class YouthPlayerGenerator:
    """Generate realistic youth players."""
    
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
    
    def generate_youth_player(
        self,
        club_id: int,
        academy_level: int = 50,
        nationality: str | None = None,
        position: Position | None = None,
        min_age: int = 15,
        max_age: int = 17,
    ) -> Player:
        """Generate a youth player for a club."""
        # Age
        age = self.rng.randint(min_age, max_age)
        birth_year = date.today().year - age
        birth_month = self.rng.randint(1, 12)
        birth_day = self.rng.randint(1, 28)
        birth_date = date(birth_year, birth_month, birth_day)
        
        # Nationality
        if nationality is None:
            nationality = self.rng.choice(NATIONALITIES)
        
        # Name
        first_name = self.rng.choice(FIRST_NAMES.get(nationality, FIRST_NAMES["England"]))
        last_name = self.rng.choice(LAST_NAMES.get(nationality, LAST_NAMES["England"]))
        
        # Position
        if position is None:
            position = self.rng.choice(list(Position))
        
        # Potential based on academy level
        # Better academies produce higher potential players
        base_potential = 50 + (academy_level // 2)  # 50-100
        potential_variance = self.rng.gauss(0, 15)
        potential_ability = int(base_potential + potential_variance)
        potential_ability = max(40, min(100, potential_ability))
        
        # Current ability (lower than potential for youth)
        potential_gap = self.rng.randint(10, 40)  # 10-40 points below potential
        current_ability = max(20, potential_ability - potential_gap)
        
        # Create player
        player = Player(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            nationality=nationality,
            position=position,
            current_ability=current_ability,
            potential_ability=potential_ability,
            club_id=club_id,
            salary=self.rng.randint(500, 3000),  # Youth wages
            market_value=self.rng.randint(50_000, 500_000),
        )
        
        # Set attributes based on position and ability
        self._set_youth_attributes(player, position, current_ability)
        
        return player
    
    def _set_youth_attributes(self, player: Player, position: Position, ability: int) -> None:
        """Set appropriate attributes for a youth player."""
        base = ability
        variance = 15
        
        # Physical attributes (all positions need these)
        player.pace = max(1, min(99, int(base + self.rng.gauss(0, variance))))
        player.acceleration = max(1, min(99, int(base + self.rng.gauss(0, variance))))
        player.stamina = max(1, min(99, int(base + self.rng.gauss(0, variance))))
        player.strength = max(1, min(99, int(base + self.rng.gauss(0, variance))))
        
        # Position-specific attributes
        if position == Position.GK:
            player.reflexes = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.handling = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.positioning = max(1, min(99, int(base + self.rng.gauss(0, variance))))
            player.shooting = self.rng.randint(10, 30)
            player.passing = self.rng.randint(30, 60)
        elif position in {Position.CB, Position.LB, Position.RB}:
            player.tackling = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.marking = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.positioning = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.shooting = self.rng.randint(20, 50)
            player.passing = self.rng.randint(30, 60)
        elif position in {Position.CM, Position.CDM, Position.CAM}:
            player.passing = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.vision = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.decisions = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.tackling = max(1, min(99, int(base + self.rng.gauss(0, variance))))
        elif position in {Position.LW, Position.RW, Position.ST, Position.CF}:
            player.shooting = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.dribbling = max(1, min(99, int(base + 5 + self.rng.gauss(0, 10))))
            player.positioning = max(1, min(99, int(base + self.rng.gauss(0, variance))))
            player.passing = max(1, min(99, int(base - 5 + self.rng.gauss(0, variance))))
        
        # Mental attributes
        player.determination = self.rng.randint(40, 80)
        player.work_rate = self.rng.choice([40, 50, 60, 70])
        player.teamwork = self.rng.randint(40, 80)
        
        # Set fitness high for youth
        player.fitness = 100
        player.form = 50
        player.morale = 60


class DevelopmentCalculator:
    """Calculate player development and growth."""
    
    def __init__(self):
        pass
    
    def calculate_growth_potential(
        self,
        player: Player,
        age: int,
        training_quality: int = 50,
        playing_time: int = 0,  # Minutes per season
    ) -> dict:
        """Calculate how much a player can grow this season.
        
        Returns:
            dict with growth estimates for different attributes
        """
        # Age curve - peak development at 18-22
        if age < 18:
            age_factor = 1.2  # Rapid growth
        elif age <= 22:
            age_factor = 1.0  # Peak growth
        elif age <= 26:
            age_factor = 0.6  # Slowing down
        elif age <= 30:
            age_factor = 0.3  # Minimal growth
        else:
            age_factor = -0.2  # Decline
        
        # Playing time factor
        if playing_time > 2000:
            playing_factor = 1.3
        elif playing_time > 1000:
            playing_factor = 1.0
        elif playing_time > 500:
            playing_factor = 0.7
        else:
            playing_factor = 0.4
        
        # Training factor
        training_factor = 0.5 + (training_quality / 100)  # 0.5 to 1.5
        
        # Calculate potential growth
        base_growth = 5 * age_factor * playing_factor * training_factor
        
        # Cap at potential
        potential_gap = player.potential_ability - player.current_ability
        max_growth = min(base_growth, potential_gap)
        
        return {
            "max_growth": max(0, int(max_growth)),
            "likely_growth": max(0, int(max_growth * 0.7)),
            "age_factor": age_factor,
            "playing_factor": playing_factor,
            "potential_gap": potential_gap,
        }
    
    def apply_season_development(
        self,
        player: Player,
        playing_time: int,
        training_quality: int,
        match_ratings: list[float],
    ) -> dict:
        """Apply development for a completed season.
        
        Returns:
            dict with development results
        """
        age = player.age or 25
        
        growth_info = self.calculate_growth_potential(
            player, age, training_quality, playing_time
        )
        
        # Random variation
        import random
        actual_growth = random.gauss(
            growth_info["likely_growth"],
            growth_info["likely_growth"] * 0.3
        )
        actual_growth = max(0, min(growth_info["max_growth"], int(actual_growth)))
        
        # Apply growth
        old_ability = player.current_ability
        player.current_ability = min(player.potential_ability, player.current_ability + actual_growth)
        
        # Age-related physical decline for older players
        if age > 30:
            decline = (age - 30) * random.choice([0, 0, 1, 1, 2])  # Random decline
            player.pace = max(1, player.pace - decline)
            player.acceleration = max(1, player.acceleration - decline)
            player.stamina = max(1, player.stamina - decline)
        
        return {
            "old_ability": old_ability,
            "new_ability": player.current_ability,
            "growth": player.current_ability - old_ability,
            "growth_info": growth_info,
        }


class ScoutingNetwork:
    """Manage scouting network and assignments."""
    
    def __init__(self):
        self.rng = random.Random()
        self.assignments: list[ScoutingAssignment] = []
    
    def create_assignment(
        self,
        region: str,
        focus_position: Position | None = None,
        min_potential: int = 60,
        max_age: int = 21,
        duration_days: int = 30,
    ) -> ScoutingAssignment:
        """Create a new scouting assignment."""
        assignment = ScoutingAssignment(
            id=len(self.assignments) + 1,
            region=region,
            focus_position=focus_position,
            min_potential=min_potential,
            max_age=max_age,
            days_remaining=duration_days,
        )
        self.assignments.append(assignment)
        return assignment
    
    def progress_assignments(self, days: int = 1) -> list[ScoutingAssignment]:
        """Progress all scouting assignments.
        
        Returns:
            List of completed assignments
        """
        completed = []
        
        for assignment in self.assignments:
            if assignment.days_remaining > 0:
                assignment.days_remaining -= days
                assignment.progress = min(100, assignment.progress + (days / 30 * 100))
                
                # Random chance to find players
                if self.rng.random() < 0.1:  # 10% chance per day
                    # Would add player to found list in real implementation
                    pass
                
                if assignment.days_remaining <= 0:
                    assignment.days_remaining = 0
                    assignment.progress = 100
                    completed.append(assignment)
        
        return completed
    
    def generate_scouting_report(
        self,
        player: Player,
        scout_quality: int = 50,
    ) -> ScoutingReport:
        """Generate a scouting report for a player."""
        # Confidence based on scout quality
        confidence = 30 + (scout_quality // 2) + self.rng.randint(-10, 10)
        confidence = max(20, min(95, confidence))
        
        # Ability estimates (with error based on confidence)
        error_margin = (100 - confidence) / 2
        current_estimate = max(1, min(99, int(
            player.current_ability + self.rng.gauss(0, error_margin)
        )))
        potential_estimate = max(1, min(99, int(
            player.potential_ability + self.rng.gauss(0, error_margin)
        )))
        
        # Strengths and weaknesses
        strengths = []
        weaknesses = []
        
        attributes = {
            "pace": player.pace or 50,
            "shooting": player.shooting or 50,
            "passing": player.passing or 50,
            "dribbling": player.dribbling or 50,
            "defending": player.tackling or 50,
            "physical": player.strength or 50,
        }
        
        for attr_name, value in attributes.items():
            if value > 70:
                strengths.append(attr_name.replace("_", " ").title())
            elif value < 40:
                weaknesses.append(attr_name.replace("_", " ").title())
        
        # Recommendation
        if potential_estimate > 80 and current_estimate > 70:
            recommendation = "sign"
        elif potential_estimate > 65:
            recommendation = "monitor"
        else:
            recommendation = "avoid"
        
        return ScoutingReport(
            player_id=player.id,
            scout_id=1,  # Would use actual scout ID
            current_ability_estimate=current_estimate,
            potential_ability_estimate=potential_estimate,
            confidence=confidence,
            strengths=strengths[:3],  # Top 3
            weaknesses=weaknesses[:3],  # Bottom 3
            recommendation=recommendation,
            estimated_cost=player.market_value or 1000000,
        )


class YouthEngine:
    """Main youth development engine."""
    
    def __init__(self):
        self.player_generator = YouthPlayerGenerator()
        self.development_calculator = DevelopmentCalculator()
        self.scouting_network = ScoutingNetwork()
    
    def generate_youth_intake(
        self,
        club: Club,
        academy: YouthAcademy,
        intake_date: date,
    ) -> list[Player]:
        """Generate youth intake for a club.
        
        Returns:
            List of new youth players
        """
        new_players = []
        
        num_players = academy.players_per_intake
        quality_factor = academy.get_intake_quality()
        
        for _ in range(num_players):
            # Higher level academies produce better players
            effective_level = int(academy.level * quality_factor)
            
            player = self.player_generator.generate_youth_player(
                club_id=club.id,
                academy_level=effective_level,
                nationality=club.country or None,
            )
            
            new_players.append(player)
        
        # Update next intake date
        academy.next_intake_date = date(intake_date.year + 1, 3, 1)  # Next March
        
        return new_players
    
    def process_yearly_development(
        self,
        player: Player,
        playing_time: int,
        training_quality: int,
        match_ratings: list[float],
    ) -> dict:
        """Process one year of development for a player."""
        return self.development_calculator.apply_season_development(
            player, playing_time, training_quality, match_ratings
        )
    
    def scout_region(
        self,
        region: str,
        duration_days: int = 30,
        focus_position: Position | None = None,
    ) -> ScoutingAssignment:
        """Start scouting a region."""
        return self.scouting_network.create_assignment(
            region=region,
            focus_position=focus_position,
            duration_days=duration_days,
        )
