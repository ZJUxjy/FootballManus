"""Data generators for creating game content."""

import json
import random
from datetime import date, timedelta
from pathlib import Path

from fm_manager.core.models import Player, Position, Foot, WorkRate


# Data paths
SEEDS_DIR = Path(__file__).parent / "seeds"

# Common names by nationality
FIRST_NAMES = {
    "England": ["James", "William", "Oliver", "Jack", "Harry", "George", "Thomas", "Charlie"],
    "Spain": ["Hugo", "Martín", "Lucas", "Leo", "Mateo", "Daniel", "Alejandro", "Pablo"],
    "Germany": ["Max", "Paul", "Ben", "Finn", "Jonas", "Felix", "Noah", "Elias"],
    "Italy": ["Leonardo", "Francesco", "Alessandro", "Lorenzo", "Mattia", "Andrea", "Gabriele", "Riccardo"],
    "France": ["Gabriel", "Léo", "Raphaël", "Louis", "Lucas", "Jules", "Adam", "Arthur"],
    "Brazil": ["Miguel", "Arthur", "Gael", "Heitor", "Theo", "Davi", "Pedro", "Gabriel"],
    "Argentina": ["Mateo", "Bautista", "Juan", "Felipe", "Bruno", "Noah", "Benicio", "Thiago"],
    "Portugal": ["Afonso", "Lourenço", "Miguel", "Santiago", "Rodrigo", "Martim", "Dinis", "Tomás"],
    "Netherlands": ["Noah", "Daan", "Lucas", "Levi", "Sem", "Milan", "James", "Noud"],
    "Belgium": ["Arthur", "Noah", "Adam", "Louis", "Liam", "Lucas", "Jules", "Victor"],
}

LAST_NAMES = {
    "England": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson"],
    "Spain": ["García", "Rodríguez", "González", "Fernández", "López", "Martínez", "Sánchez", "Pérez"],
    "Germany": ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker"],
    "Italy": ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci"],
    "France": ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand"],
    "Brazil": ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira"],
    "Argentina": ["González", "Rodríguez", "Gómez", "Fernández", "López", "Martínez", "Pérez", "García"],
    "Portugal": ["Silva", "Santos", "Ferreira", "Costa", "Oliveira", "Pereira", "Martins", "Rodrigues"],
    "Netherlands": ["De Jong", "De Vries", "Van den Berg", "Van Dijk", "Bakker", "Jansen", "Smit", "Van der Meer"],
    "Belgium": ["Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Willems", "Claes", "Goossens"],
}

NATIONALITIES = list(FIRST_NAMES.keys())


def generate_youth_player(
    club_id: int | None = None,
    min_age: int = 16,
    max_age: int = 18,
    position: Position | None = None,
    nationality: str | None = None,
) -> Player:
    """Generate a youth player with potential."""
    
    # Random nationality if not specified
    if nationality is None:
        nationality = random.choice(NATIONALITIES)
    
    # Generate name
    first_name = random.choice(FIRST_NAMES.get(nationality, FIRST_NAMES["England"]))
    last_name = random.choice(LAST_NAMES.get(nationality, LAST_NAMES["England"]))
    
    # Generate birth date
    age = random.randint(min_age, max_age)
    birth_year = date.today().year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    birth_date = date(birth_year, birth_month, birth_day)
    
    # Position
    if position is None:
        position = random.choice(list(Position))
    
    # Base attributes for youth player (lower than senior players)
    base_ability = random.randint(30, 60)
    potential = min(100, base_ability + random.randint(10, 40))
    
    # Position-specific attributes
    player = Player(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        nationality=nationality,
        position=position,
        current_ability=base_ability,
        potential_ability=potential,
        club_id=club_id,
        salary=random.randint(500, 5000),  # Youth wages
        market_value=calculate_market_value(base_ability, age, potential),
    )
    
    # Set position-specific attributes
    _set_position_attributes(player, position, base_ability)
    
    return player


def _set_position_attributes(player: Player, position: Position, base: int) -> None:
    """Set attributes based on position."""
    variation = 15
    
    if position == Position.GK:
        player.reflexes = min(100, base + random.randint(-10, 20))
        player.handling = min(100, base + random.randint(-10, 15))
        player.positioning = min(100, base + random.randint(-5, 15))
        player.vision = random.randint(base - 20, base)
        player.pace = random.randint(base - 20, base)
    elif position in [Position.CB, Position.LB, Position.RB]:
        player.tackling = min(100, base + random.randint(0, 20))
        player.marking = min(100, base + random.randint(0, 20))
        player.positioning = min(100, base + random.randint(0, 15))
        player.strength = min(100, base + random.randint(0, 20))
        player.pace = random.randint(base - 10, base + 10)
        player.passing = random.randint(base - 10, base + 10)
    elif position in [Position.CDM, Position.CM, Position.CAM]:
        player.passing = min(100, base + random.randint(0, 20))
        player.vision = min(100, base + random.randint(0, 20))
        player.decisions = min(100, base + random.randint(0, 15))
        player.stamina = min(100, base + random.randint(0, 20))
        player.tackling = random.randint(base - 10, base + 15)
    elif position in [Position.LM, Position.RM, Position.LW, Position.RW]:
        player.pace = min(100, base + random.randint(5, 25))
        player.dribbling = min(100, base + random.randint(5, 25))
        player.crossing = min(100, base + random.randint(0, 20))
        player.shooting = random.randint(base - 5, base + 15)
    elif position in [Position.CF, Position.ST]:
        player.shooting = min(100, base + random.randint(5, 25))
        player.positioning = min(100, base + random.randint(0, 20))
        player.strength = min(100, base + random.randint(0, 15))
        player.pace = random.randint(base, base + 20)
    
    # General physical attributes
    player.stamina = random.randint(base - 10, base + 15)
    player.strength = random.randint(base - 10, base + 15)
    player.acceleration = random.randint(base - 10, base + 20)


def calculate_market_value(ability: int, age: int, potential: int) -> int:
    """Calculate player market value based on ability, age, and potential."""
    base_value = ability * 100_000
    
    # Age factor (peak at 25-28)
    if age < 21:
        age_factor = 0.8 + (age - 16) * 0.1  # 0.8 to 1.3
    elif age <= 28:
        age_factor = 1.3
    else:
        age_factor = max(0.3, 1.3 - (age - 28) * 0.1)
    
    # Potential premium for young players
    potential_factor = 1.0
    if age < 23:
        potential_gap = potential - ability
        potential_factor = 1.0 + (potential_gap / 100) * 0.5
    
    return int(base_value * age_factor * potential_factor)


class PlayerGenerator:
    """Generator for creating batches of players."""
    
    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
    
    def generate_squad(
        self,
        club_id: int,
        size: int = 25,
        avg_quality: int = 60,
    ) -> list[Player]:
        """Generate a full squad for a club."""
        players = []
        
        # Position distribution for a balanced squad
        positions = [
            Position.GK,
            Position.CB, Position.CB, Position.CB, Position.CB,
            Position.LB, Position.LB,
            Position.RB, Position.RB,
            Position.CDM, Position.CDM,
            Position.CM, Position.CM, Position.CM,
            Position.CAM, Position.CAM,
            Position.LM, Position.RM,
            Position.LW, Position.RW,
            Position.CF, Position.CF,
            Position.ST, Position.ST, Position.ST,
        ]
        
        # Generate senior players (age 22-32)
        for i in range(min(size, len(positions))):
            age = random.randint(22, 32)
            ability = max(40, min(95, avg_quality + random.randint(-15, 15)))
            potential = max(ability, min(100, ability + random.randint(-10, 10)))
            
            player = self._create_senior_player(
                club_id=club_id,
                position=positions[i],
                age=age,
                ability=ability,
                potential=potential,
            )
            players.append(player)
        
        # Generate youth players (age 16-20)
        youth_count = random.randint(3, 5)
        for _ in range(youth_count):
            player = generate_youth_player(
                club_id=club_id,
                min_age=16,
                max_age=20,
            )
            players.append(player)
        
        return players
    
    def _create_senior_player(
        self,
        club_id: int,
        position: Position,
        age: int,
        ability: int,
        potential: int,
    ) -> Player:
        """Create a senior player."""
        nationality = random.choice(NATIONALITIES)
        first_name = random.choice(FIRST_NAMES[nationality])
        last_name = random.choice(LAST_NAMES[nationality])
        
        birth_year = date.today().year - age
        birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
        
        player = Player(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            nationality=nationality,
            position=position,
            current_ability=ability,
            potential_ability=potential,
            club_id=club_id,
            salary=calculate_market_value(ability, age, potential) // 1000,  # Weekly wage
            market_value=calculate_market_value(ability, age, potential),
        )
        
        _set_position_attributes(player, position, ability)
        
        return player
