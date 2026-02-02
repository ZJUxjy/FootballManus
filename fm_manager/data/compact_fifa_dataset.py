"""
Compact FIFA-style player dataset for immediate use.

This module provides a way to generate a large dataset of realistic player data
without requiring external downloads. Useful for:
- Quick testing
- Demo purposes  
- Offline development

For production use with real data, see:
- scripts/download_data.py
- fifa_importer.py
- transfermarkt_scraper.py
"""

import csv
import random
from dataclasses import dataclass, asdict
from pathlib import Path

from fm_manager.data.generators import (
    FIRST_NAMES, LAST_NAMES, NATIONALITIES, calculate_market_value
)
from fm_manager.core.models import Position


# Top clubs by league
CLUBS_BY_LEAGUE = {
    "Premier League": [
        ("Manchester City", 9500, 150000000, 53400),
        ("Arsenal", 9000, 100000000, 60704),
        ("Liverpool", 9200, 120000000, 53394),
        ("Manchester United", 9000, 100000000, 74310),
        ("Chelsea", 8800, 200000000, 40343),
        ("Tottenham", 8500, 80000000, 62850),
        ("Newcastle United", 8200, 70000000, 52305),
        ("Aston Villa", 7800, 50000000, 42682),
        ("Brighton", 7500, 40000000, 31876),
        ("West Ham", 7600, 45000000, 62500),
        ("Brentford", 7000, 30000000, 17250),
        ("Crystal Palace", 7200, 35000000, 25486),
        ("Everton", 7400, 40000000, 39572),
        ("Fulham", 6800, 25000000, 22384),
        ("Wolves", 7300, 35000000, 32050),
        ("Burnley", 6500, 20000000, 21944),
        ("Sheffield United", 6400, 15000000, 32050),
        ("Luton Town", 6000, 10000000, 10356),
        ("Nottingham Forest", 6700, 25000000, 30445),
        ("Bournemouth", 6900, 28000000, 11307),
    ],
    "La Liga": [
        ("Real Madrid", 9800, 150000000, 81044),
        ("Barcelona", 9600, 80000000, 56000),
        ("Atletico Madrid", 8800, 80000000, 68456),
        ("Real Sociedad", 8000, 50000000, 39500),
        ("Sevilla", 8200, 40000000, 43883),
        ("Villarreal", 7900, 40000000, 23500),
        ("Real Betis", 7800, 35000000, 60721),
        ("Athletic Bilbao", 8100, 45000000, 53289),
        ("Valencia", 7500, 30000000, 55000),
        ("Celta Vigo", 7200, 25000000, 29000),
        ("Getafe", 7000, 20000000, 17393),
        ("Osasuna", 6800, 18000000, 23516),
        ("Rayo Vallecano", 6700, 15000000, 14708),
        ("Mallorca", 6600, 15000000, 23142),
        ("Las Palmas", 6400, 12000000, 33111),
        ("Alaves", 6300, 12000000, 19840),
        ("Granada", 6200, 10000000, 19336),
        ("Cadiz", 6100, 10000000, 20724),
        ("Almeria", 6000, 10000000, 15000),
    ],
    "Bundesliga": [
        ("Bayern Munich", 9500, 120000000, 75000),
        ("Borussia Dortmund", 8500, 60000000, 81365),
        ("RB Leipzig", 8200, 70000000, 47069),
        ("Bayer Leverkusen", 8000, 60000000, 30210),
        ("Eintracht Frankfurt", 7800, 45000000, 51500),
        ("Wolfsburg", 7600, 40000000, 30000),
        ("Freiburg", 7500, 35000000, 34700),
        ("Union Berlin", 7400, 30000000, 22012),
        ("Monchengladbach", 7700, 40000000, 54057),
        ("Mainz", 7200, 25000000, 34000),
        ("Werder Bremen", 7300, 30000000, 42100),
        ("Augsburg", 7000, 25000000, 30660),
        ("Hoffenheim", 7100, 28000000, 30150),
        ("Stuttgart", 7500, 35000000, 60449),
        ("Bochum", 6800, 20000000, 27599),
        ("Heidenheim", 6500, 15000000, 15000),
        ("Darmstadt", 6400, 12000000, 17810),
        ("Koln", 6900, 22000000, 50000),
    ],
    "Serie A": [
        ("Inter Milan", 8800, 70000000, 80018),
        ("AC Milan", 8600, 60000000, 80018),
        ("Juventus", 8900, 80000000, 41507),
        ("Napoli", 8400, 60000000, 54726),
        ("Roma", 8300, 50000000, 70634),
        ("Lazio", 8100, 45000000, 63292),
        ("Atalanta", 7900, 45000000, 24950),
        ("Fiorentina", 7800, 40000000, 43147),
        ("Bologna", 7500, 35000000, 36348),
        ("Torino", 7400, 30000000, 27958),
        ("Monza", 7000, 25000000, 16917),
        ("Genoa", 7200, 28000000, 36685),
        ("Sassuolo", 7300, 30000000, 21584),
        ("Udinese", 7100, 25000000, 25144),
        ("Lecce", 6800, 20000000, 31533),
        ("Empoli", 6900, 22000000, 16284),
        ("Verona", 7000, 25000000, 39311),
        ("Cagliari", 6700, 18000000, 16416),
        ("Frosinone", 6500, 15000000, 16227),
        ("Salernitana", 6600, 15000000, 31300),
    ],
    "Ligue 1": [
        ("Paris Saint-Germain", 9000, 200000000, 47929),
        ("Monaco", 8200, 80000000, 18523),
        ("Marseille", 8100, 60000000, 67394),
        ("Rennes", 7800, 45000000, 29778),
        ("Lille", 7900, 50000000, 50229),
        ("Nice", 7700, 40000000, 35624),
        ("Lyon", 8000, 50000000, 59186),
        ("Lens", 7600, 35000000, 38223),
        ("Strasbourg", 7400, 30000000, 26109),
        ("Nantes", 7300, 28000000, 35322),
        ("Reims", 7200, 25000000, 21127),
        ("Montpellier", 7100, 25000000, 32900),
        ("Brest", 7000, 20000000, 15220),
        ("Toulouse", 6900, 20000000, 33150),
        ("Le Havre", 6500, 15000000, 25178),
        ("Metz", 6800, 18000000, 28686),
        ("Clermont", 6700, 15000000, 11980),
        ("Lorient", 6600, 15000000, 18110),
    ],
}


@dataclass
class CompactPlayer:
    """Simplified player data structure."""
    name: str
    age: int
    nationality: str
    club: str
    league: str
    position: str
    overall: int
    potential: int
    value: int
    wage: int
    height: int
    weight: int
    preferred_foot: str
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int


def generate_compact_dataset(
    output_file: Path | None = None,
    players_per_club: int = 25,
) -> Path:
    """Generate a compact FIFA-style dataset with realistic data.
    
    This generates ~2000 players (5 leagues × 20 clubs × 25 players)
    without requiring external downloads.
    """
    if output_file is None:
        output_file = Path(__file__).parent / "seeds" / "compact_players.csv"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    players = []
    random.seed(42)  # Reproducible
    
    for league_name, clubs in CLUBS_BY_LEAGUE.items():
        for club_info in clubs:
            club_name, reputation, transfer_budget, stadium = club_info
            
            # Calculate average quality based on club reputation
            avg_quality = _reputation_to_quality(reputation)
            
            # Generate players for this club
            for i in range(players_per_club):
                player = _generate_player(
                    club_name=club_name,
                    league_name=league_name,
                    avg_quality=avg_quality,
                    squad_index=i,
                )
                players.append(player)
    
    # Write to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        if players:
            writer = csv.DictWriter(f, fieldnames=asdict(players[0]).keys())
            writer.writeheader()
            for player in players:
                writer.writerow(asdict(player))
    
    print(f"✅ Generated {len(players)} players to {output_file}")
    return output_file


def _reputation_to_quality(reputation: int) -> int:
    """Convert club reputation to average player quality."""
    if reputation >= 9500:
        return 82
    elif reputation >= 9000:
        return 78
    elif reputation >= 8500:
        return 75
    elif reputation >= 8000:
        return 72
    elif reputation >= 7500:
        return 68
    elif reputation >= 7000:
        return 64
    elif reputation >= 6500:
        return 60
    else:
        return 56


def _generate_player(
    club_name: str,
    league_name: str,
    avg_quality: int,
    squad_index: int,
) -> CompactPlayer:
    """Generate a single player."""
    # Determine position based on squad index (for balanced squads)
    positions = [
        Position.GK, Position.GK,
        Position.CB, Position.CB, Position.CB, Position.CB,
        Position.LB, Position.LB, Position.RB, Position.RB,
        Position.CDM, Position.CDM,
        Position.CM, Position.CM, Position.CM,
        Position.CAM, Position.CAM,
        Position.LM, Position.RM,
        Position.LW, Position.RW,
        Position.CF, Position.ST, Position.ST, Position.ST,
    ]
    position = positions[squad_index % len(positions)]
    
    # Generate name
    nationality = random.choice(NATIONALITIES)
    first_name = random.choice(FIRST_NAMES[nationality])
    last_name = random.choice(LAST_NAMES[nationality])
    
    # Age based on position (GKs peak later, young attackers more common)
    if position == Position.GK:
        age = random.randint(23, 35)
    elif position in [Position.ST, Position.LW, Position.RW]:
        age = random.randint(20, 32)
    else:
        age = random.randint(21, 34)
    
    # Quality with some variation
    quality_variation = random.randint(-8, 8)
    overall = max(45, min(95, avg_quality + quality_variation))
    potential = min(99, overall + random.randint(-5, 15))
    
    # Physical attributes based on position
    height, weight = _generate_physique(position, age)
    foot = random.choice(["Left", "Right", "Right"])  # 2/3 right-footed
    
    # FIFA-style attributes
    attributes = _generate_attributes(position, overall)
    
    # Market value
    value = calculate_market_value(overall, age, potential)
    wage = max(1000, value // 50000)  # Rough wage estimation
    
    return CompactPlayer(
        name=f"{first_name} {last_name}",
        age=age,
        nationality=nationality,
        club=club_name,
        league=league_name,
        position=position.value,
        overall=overall,
        potential=potential,
        value=value,
        wage=wage,
        height=height,
        weight=weight,
        preferred_foot=foot,
        **attributes,
    )


def _generate_physique(position: Position, age: int) -> tuple[int, int]:
    """Generate height and weight based on position."""
    if position == Position.GK:
        height = random.randint(185, 200)
    elif position in [Position.CB, Position.CDM]:
        height = random.randint(183, 195)
    elif position in [Position.ST, Position.CF]:
        height = random.randint(178, 192)
    else:
        height = random.randint(170, 185)
    
    # Weight proportional to height
    weight = int((height - 100) * 0.9) + random.randint(-5, 10)
    return height, weight


def _generate_attributes(position: Position, overall: int) -> dict[str, int]:
    """Generate FIFA-style attributes based on position and overall."""
    base = overall
    variation = 12
    
    if position == Position.GK:
        return {
            "pace": random.randint(base - 25, base - 10),
            "shooting": random.randint(base - 30, base - 15),
            "passing": random.randint(base - 15, base + 5),
            "dribbling": random.randint(base - 20, base - 5),
            "defending": random.randint(base - 10, base + 10),
            "physical": random.randint(base - 10, base + 5),
        }
    elif position in [Position.CB, Position.LB, Position.RB]:
        return {
            "pace": random.randint(base - 10, base + 10),
            "shooting": random.randint(base - 25, base - 5),
            "passing": random.randint(base - 10, base + 10),
            "dribbling": random.randint(base - 15, base + 5),
            "defending": random.randint(base - 5, base + 15),
            "physical": random.randint(base - 5, base + 10),
        }
    elif position in [Position.CDM, Position.CM]:
        return {
            "pace": random.randint(base - 10, base + 5),
            "shooting": random.randint(base - 15, base + 5),
            "passing": random.randint(base - 5, base + 15),
            "dribbling": random.randint(base - 10, base + 10),
            "defending": random.randint(base - 10, base + 10),
            "physical": random.randint(base - 5, base + 15),
        }
    elif position in [Position.CAM, Position.LM, Position.RM]:
        return {
            "pace": random.randint(base - 5, base + 10),
            "shooting": random.randint(base - 10, base + 10),
            "passing": random.randint(base - 5, base + 15),
            "dribbling": random.randint(base - 5, base + 15),
            "defending": random.randint(base - 20, base - 5),
            "physical": random.randint(base - 15, base + 5),
        }
    else:  # Wingers and strikers
        return {
            "pace": random.randint(base - 5, base + 15),
            "shooting": random.randint(base - 10, base + 15),
            "passing": random.randint(base - 10, base + 10),
            "dribbling": random.randint(base - 5, base + 15),
            "defending": random.randint(base - 30, base - 10),
            "physical": random.randint(base - 10, base + 10),
        }


if __name__ == "__main__":
    # Generate compact dataset
    output = generate_compact_dataset()
    print(f"\nDataset saved to: {output}")
    
    # Show sample
    import pandas as pd
    df = pd.read_csv(output)
    print(f"\nTotal players: {len(df)}")
    print(f"\nTop 10 players by overall rating:")
    print(df.nlargest(10, "overall")[["name", "club", "overall", "value"]].to_string(index=False))
