"""Import data from FIFA game files or exported datasets.

FIFA player data can be obtained from:
1. Kaggle datasets (FIFA 20-24 complete player datasets)
2. Futbin/Futhead exports
3. Community CSV exports

Data format typically includes:
- Name, Age, Nationality, Club, Position
- Overall Rating, Potential
- Physical attributes (Pace, Shooting, Passing, etc.)
- Height, Weight, Preferred Foot
"""

import csv
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from fm_manager.core.models import Player, Club, League, Position, Foot, WorkRate


@dataclass
class FIFAPlayer:
    """FIFA player data structure."""
    # Required fields (no defaults)
    name: str
    age: int
    nationality: str
    club: str
    position: str
    overall: int
    potential: int
    value: int  # Market value in euros
    wage: int   # Weekly wage
    
    # Physical
    height: int  # cm
    weight: int  # kg
    preferred_foot: str
    
    # Attributes (0-100)
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int
    
    # Optional fields (with defaults)
    league: str = ""  # League name
    
    # Detailed (optional)
    crossing: int | None = None
    finishing: int | None = None
    heading: int | None = None
    short_passing: int | None = None
    volleys: int | None = None
    dribbling_skill: int | None = None
    curve: int | None = None
    free_kick: int | None = None
    long_passing: int | None = None
    ball_control: int | None = None
    acceleration: int | None = None
    sprint_speed: int | None = None
    agility: int | None = None
    reactions: int | None = None
    balance: int | None = None
    shot_power: int | None = None
    jumping: int | None = None
    stamina: int | None = None
    strength: int | None = None
    long_shots: int | None = None
    aggression: int | None = None
    interceptions: int | None = None
    positioning: int | None = None
    vision: int | None = None
    penalties: int | None = None
    marking: int | None = None
    standing_tackle: int | None = None
    sliding_tackle: int | None = None
    gk_diving: int | None = None
    gk_handling: int | None = None
    gk_kicking: int | None = None
    gk_positioning: int | None = None
    gk_reflexes: int | None = None


class FIFAImporter:
    """Import FIFA player data into the database."""
    
    # Position mapping from FIFA to our Position enum
    POSITION_MAP = {
        "GK": Position.GK,
        "CB": Position.CB,
        "LB": Position.LB,
        "LWB": Position.LWB,
        "RB": Position.RB,
        "RWB": Position.RWB,
        "CDM": Position.CDM,
        "CM": Position.CM,
        "CAM": Position.CAM,
        "LM": Position.LM,
        "RM": Position.RM,
        "LW": Position.LW,
        "RW": Position.RW,
        "CF": Position.CF,
        "ST": Position.ST,
        # Alternative names
        "LCB": Position.CB,
        "RCB": Position.CB,
        "LDM": Position.CDM,
        "RDM": Position.CDM,
        "LAM": Position.CAM,
        "RAM": Position.CAM,
        "LF": Position.CF,
        "RF": Position.CF,
        "RS": Position.ST,
        "LS": Position.ST,
    }
    
    def __init__(self, csv_file: str | Path):
        self.csv_file = Path(csv_file)
        self.players: list[FIFAPlayer] = []
    
    def parse_csv(self) -> list[FIFAPlayer]:
        """Parse FIFA CSV file."""
        self.players = []
        
        with open(self.csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                player = self._parse_row(row)
                if player:
                    self.players.append(player)
        
        return self.players
    
    def _parse_row(self, row: dict[str, str]) -> FIFAPlayer | None:
        """Parse a single CSV row into FIFAPlayer."""
        try:
            # Handle different column naming conventions
            name = self._get_column(row, ["Name", "Player Name", "LongName", "long_name"])
            if not name:
                return None
            
            age = int(self._get_column(row, ["Age", "age"]) or 25)
            nationality = self._get_column(row, ["Nationality", "NationalTeam", "nationality"]) or "Unknown"
            club = self._get_column(row, ["Club", "Team", "club_name"]) or "Free Agent"
            position = self._get_column(row, ["Position", "player_positions"]) or "CM"
            league = self._get_column(row, ["League", "league"]) or ""
            
            overall = int(self._get_column(row, ["Overall", "overall"]) or 60)
            potential = int(self._get_column(row, ["Potential", "potential"]) or overall)
            
            # Parse value (e.g., "€110.5M" or "110500000")
            value_str = self._get_column(row, ["Value", "value_eur"]) or "0"
            value = self._parse_money(value_str)
            
            # Parse wage
            wage_str = self._get_column(row, ["Wage", "wage_eur"]) or "0"
            wage = self._parse_money(wage_str) // 52  # Annual to weekly
            
            height = int(self._get_column(row, ["Height", "height_cm"]) or 180)
            weight = int(self._get_column(row, ["Weight", "weight_kg"]) or 75)
            
            foot_str = self._get_column(row, ["Preferred Foot", "preferred_foot"]) or "Right"
            preferred_foot = "Right" if "right" in foot_str.lower() else "Left"
            
            # Attributes
            pace = int(self._get_column(row, ["Pace", "pace"]) or 50)
            shooting = int(self._get_column(row, ["Shooting", "shooting"]) or 50)
            passing = int(self._get_column(row, ["Passing", "passing"]) or 50)
            dribbling = int(self._get_column(row, ["Dribbling", "dribbling"]) or 50)
            defending = int(self._get_column(row, ["Defending", "defending"]) or 50)
            physical = int(self._get_column(row, ["Physical", "physic"]) or 50)
            
            return FIFAPlayer(
                name=name,
                age=age,
                nationality=nationality,
                club=club,
                position=position,
                league=league,
                overall=overall,
                potential=potential,
                value=value,
                wage=max(1000, wage),
                height=height,
                weight=weight,
                preferred_foot=preferred_foot,
                pace=pace,
                shooting=shooting,
                passing=passing,
                dribbling=dribbling,
                defending=defending,
                physical=physical,
                # Detailed attributes
                crossing=self._get_int(row, "Crossing"),
                finishing=self._get_int(row, "Finishing"),
                heading=self._get_int(row, "HeadingAccuracy"),
                short_passing=self._get_int(row, "ShortPassing"),
                volleys=self._get_int(row, "Volleys"),
                dribbling_skill=self._get_int(row, "Dribbling"),
                curve=self._get_int(row, "Curve"),
                free_kick=self._get_int(row, "FKAccuracy"),
                long_passing=self._get_int(row, "LongPassing"),
                ball_control=self._get_int(row, "BallControl"),
                acceleration=self._get_int(row, "Acceleration"),
                sprint_speed=self._get_int(row, "SprintSpeed"),
                agility=self._get_int(row, "Agility"),
                reactions=self._get_int(row, "Reactions"),
                balance=self._get_int(row, "Balance"),
                shot_power=self._get_int(row, "ShotPower"),
                jumping=self._get_int(row, "Jumping"),
                stamina=self._get_int(row, "Stamina"),
                strength=self._get_int(row, "Strength"),
                long_shots=self._get_int(row, "LongShots"),
                aggression=self._get_int(row, "Aggression"),
                interceptions=self._get_int(row, "Interceptions"),
                positioning=self._get_int(row, "Positioning"),
                vision=self._get_int(row, "Vision"),
                penalties=self._get_int(row, "Penalties"),
                marking=self._get_int(row, "Marking"),
                standing_tackle=self._get_int(row, "StandingTackle"),
                sliding_tackle=self._get_int(row, "SlidingTackle"),
                gk_diving=self._get_int(row, "GKDiving"),
                gk_handling=self._get_int(row, "GKHandling"),
                gk_kicking=self._get_int(row, "GKKicking"),
                gk_positioning=self._get_int(row, "GKPositioning"),
                gk_reflexes=self._get_int(row, "GKReflexes"),
            )
        except Exception as e:
            print(f"Error parsing row: {e}")
            return None
    
    def _get_column(self, row: dict[str, str], alternatives: list[str]) -> str | None:
        """Try to get value from multiple possible column names."""
        for alt in alternatives:
            if alt in row and row[alt]:
                return row[alt].strip()
        # Try case-insensitive match
        row_lower = {k.lower(): v for k, v in row.items()}
        for alt in alternatives:
            if alt.lower() in row_lower:
                return row_lower[alt.lower()].strip()
        return None
    
    def _get_int(self, row: dict[str, str], column: str) -> int | None:
        """Get integer value from row."""
        val = row.get(column)
        if val and val.isdigit():
            return int(val)
        return None
    
    def _parse_money(self, value: str) -> int:
        """Parse money string like '€110.5M' or '500K' to integer."""
        value = value.replace("€", "").replace(",", "").strip()
        
        if not value:
            return 0
        
        # Already a number
        if value.isdigit():
            return int(value)
        
        # Parse with suffix
        multiplier = 1
        if "M" in value.upper():
            multiplier = 1_000_000
            value = value.upper().replace("M", "")
        elif "K" in value.upper():
            multiplier = 1_000
            value = value.upper().replace("K", "")
        
        try:
            return int(float(value) * multiplier)
        except ValueError:
            return 0
    
    def to_db_player(self, fifa_player: FIFAPlayer, club_id: int | None = None) -> Player:
        """Convert FIFAPlayer to database Player model."""
        # Parse name
        name_parts = fifa_player.name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Unknown"
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Map position
        position = self.POSITION_MAP.get(fifa_player.position.upper(), Position.CM)
        
        # Map foot
        foot = Foot.RIGHT if fifa_player.preferred_foot == "Right" else Foot.LEFT
        
        # Calculate birth date from age
        from datetime import date, timedelta
        birth_year = date.today().year - fifa_player.age
        birth_date = date(birth_year, 1, 1)  # Default to Jan 1
        
        player = Player(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            nationality=fifa_player.nationality,
            position=position,
            height=fifa_player.height,
            weight=fifa_player.weight,
            preferred_foot=foot,
            
            # FIFA attributes mapped to our model
            pace=fifa_player.pace,
            acceleration=fifa_player.acceleration or fifa_player.pace,
            stamina=fifa_player.stamina or fifa_player.physical,
            strength=fifa_player.strength or fifa_player.physical,
            
            shooting=fifa_player.shooting,
            passing=fifa_player.passing,
            dribbling=fifa_player.dribbling,
            crossing=fifa_player.crossing or fifa_player.passing,
            first_touch=fifa_player.ball_control or fifa_player.dribbling,
            
            tackling=fifa_player.standing_tackle or fifa_player.defending,
            marking=fifa_player.marking or fifa_player.defending,
            positioning=fifa_player.positioning or fifa_player.defending,
            vision=fifa_player.vision or fifa_player.passing,
            decisions=fifa_player.reactions or fifa_player.overall,
            
            # GK attributes
            reflexes=fifa_player.gk_reflexes or 50,
            handling=fifa_player.gk_handling or 50,
            kicking=fifa_player.gk_kicking or 50,
            one_on_one=fifa_player.gk_positioning or 50,
            
            # Mental
            work_rate=WorkRate.MEDIUM,
            determination=fifa_player.aggression or 50,
            leadership=50,
            teamwork=50,
            aggression=fifa_player.aggression or 50,
            
            # Overall
            current_ability=fifa_player.overall,
            potential_ability=fifa_player.potential,
            
            # Contract
            club_id=club_id,
            salary=fifa_player.wage,
            market_value=fifa_player.value,
        )
        
        return player
    
    def get_unique_clubs(self) -> list[str]:
        """Get list of unique clubs in the dataset."""
        if not self.players:
            self.parse_csv()
        
        clubs = set()
        for player in self.players:
            if player.club and player.club != "Free Agent":
                clubs.add(player.club)
        
        return sorted(clubs)
    
    def get_players_by_club(self, club_name: str) -> list[FIFAPlayer]:
        """Get all players for a specific club."""
        return [p for p in self.players if p.club == club_name]


def download_fifa_dataset_from_kaggle() -> None:
    """Instructions for downloading FIFA dataset from Kaggle.
    
    1. Install kaggle: pip install kaggle
    2. Set up API credentials: https://www.kaggle.com/docs/api
    3. Download dataset:
       kaggle datasets download -d stefanoleone992/fifa-22-complete-player-dataset
    4. Unzip and place CSV in data/raw/
    """
    print("""
To download FIFA dataset from Kaggle:

1. Install kaggle CLI:
   pip install kaggle

2. Get API credentials from https://www.kaggle.com/account
   Download kaggle.json and place in ~/.kaggle/

3. Download FIFA dataset:
   kaggle datasets download -d stefanoleone992/fifa-22-complete-player-dataset
   # OR for FIFA 23:
   kaggle datasets download -d bryanb/fifa-player-stats-database
   # OR for FIFA 24:
   kaggle datasets download -d sagy6t9/fifa-24-player-stats

4. Unzip the downloaded file:
   unzip fifa-*.zip -d data/raw/

5. Update the path in the import script
""")


# Alternative data sources
DATA_SOURCE_URLS = {
    "fifa_22_kaggle": "https://www.kaggle.com/datasets/stefanoleone992/fifa-22-complete-player-dataset",
    "fifa_23_kaggle": "https://www.kaggle.com/datasets/bryanb/fifa-player-stats-database",
    "fifa_24_kaggle": "https://www.kaggle.com/datasets/sagy6t9/fifa-24-player-stats",
    "european_soccer_db": "https://www.kaggle.com/datasets/hugomathien/soccer",
    "football_manager_2024": "https://sortitoutsi.net/downloads/view/66832/football-manager-2024-database",
}


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fifa_importer.py <fifa_csv_file>")
        download_fifa_dataset_from_kaggle()
        sys.exit(1)
    
    csv_file = sys.argv[1]
    importer = FIFAImporter(csv_file)
    players = importer.parse_csv()
    
    print(f"Parsed {len(players)} players")
    print(f"Unique clubs: {len(importer.get_unique_clubs())}")
    
    # Show top 10 players by overall rating
    top_players = sorted(players, key=lambda p: p.overall, reverse=True)[:10]
    print("\nTop 10 players:")
    for p in top_players:
        print(f"  {p.name} ({p.club}) - OVR: {p.overall}, POT: {p.potential}, Value: €{p.value:,}")
