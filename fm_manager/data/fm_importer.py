"""Import data from Football Manager 2024 database exports.

FM24 player data can be obtained from:
1. FM Editor exports (CSV/XML) - Recommended
2. Sortitoutsi database downloads
3. FM Scout data exports
4. FMInside API

FM24 data typically includes:
- Name, Age, Nationality, Club, Position
- Current Ability (CA), Potential Ability (PA)
- 50+ attributes (Technical, Mental, Physical)
- Contract details, Market value, Wage
"""

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fm_manager.core.models import Player, Club, League, Position, Foot, WorkRate


@dataclass
class FM24Player:
    """Football Manager 2024 player data structure."""
    # Required fields
    uid: int  # Unique ID in FM database
    name: str
    age: int
    nationality: str
    club: str
    position: str

    # Ability ratings
    current_ability: int  # Current Ability (CA)
    potential_ability: int  # Potential Ability (PA)

    # Contract
    contract_until: str | None = None  # Date string
    wage: int = 0  # Weekly wage
    market_value: int = 0
    release_clause: int | None = None

    # Physical
    height: int = 0  # cm
    weight: int = 0  # kg
    preferred_foot: str = "Right"

    # Technical Attributes (FM24 has 14 technical attributes)
    corners: int = 10
    crossing: int = 10
    dribbling: int = 10
    finishing: int = 10
    first_touch: int = 10
    free_kicks: int = 10
    heading: int = 10
    long_shots: int = 10
    marking: int = 10
    passing: int = 10
    penalty_taking: int = 10
    tackling: int = 10
    technique: int = 10

    # Mental Attributes (FM24 has 14 mental attributes)
    aggression: int = 10
    anticipation: int = 10
    bravery: int = 10
    composure: int = 10
    concentration: int = 10
    decisions: int = 10
    determination: int = 10
    flair: int = 10
    leadership: int = 10
    off_the_ball: int = 10
    positioning: int = 10
    teamwork: int = 10
    vision: int = 10
    work_rate: int = 10

    # Physical Attributes (FM24 has 8 physical attributes)
    acceleration: int = 10
    agility: int = 10
    balance: int = 10
    jumping: int = 10
    natural_fitness: int = 10
    pace: int = 10
    stamina: int = 10
    strength: int = 10

    # Goalkeeper-specific (optional)
    aerial_reach: int | None = None
    command_of_area: int | None = None
    communication: int | None = None
    eccentricity: int | None = None
    handling: int | None = None
    kicking: int | None = None
    one_on_ones: int | None = None
    reflexes: int | None = None
    rushing_out: int | None = None
    throwing: int | None = None


class FM24Importer:
    """Import Football Manager 2024 player data into the database."""

    # Position mapping from FM24 to our Position enum
    # FM24 uses combined positions like "DL R, DC, DL C"
    POSITION_MAP = {
        "GK": Position.GK,
        "D C": Position.CB,
        "D L": Position.LB,
        "D R": Position.RB,
        "D/WB L": Position.LWB,
        "D/WB R": Position.RWB,
        "DM C": Position.CDM,
        "M C": Position.CM,
        "M L": Position.LM,
        "M R": Position.RM,
        "AM C": Position.CAM,
        "A L": Position.LW,
        "A R": Position.RW,
        "AM L": Position.LW,
        "AM R": Position.RW,
        "AM C, ST C": Position.CF,
        "ST C": Position.ST,
        # Alternative formats
        "DL C": Position.CB,
        "DL R": Position.RB,
        "DL L": Position.LB,
    }

    def __init__(self, csv_file: str | Path):
        self.csv_file = Path(csv_file)
        self.players: list[FM24Player] = []

    def parse_csv(self) -> list[FM24Player]:
        """Parse FM24 CSV export."""
        self.players = []

        with open(self.csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                player = self._parse_row(row)
                if player:
                    self.players.append(player)

        return self.players

    def _parse_row(self, row: dict[str, str]) -> FM24Player | None:
        """Parse a single CSV row into FM24Player."""
        try:
            # Try different column naming conventions
            uid = int(self._get_column(row, ["UID", "id", "player_id"]) or "0")
            name = self._get_column(row, ["Name", "name", "player_name"])
            if not name:
                return None

            age = int(self._get_column(row, ["Age", "age"]) or "25")
            nationality = self._get_column(row, ["Nation", "Nationality", "nationality"]) or "Unknown"
            club = self._get_column(row, ["Club", "club_name", "Team"]) or "Free Agent"
            position = self._get_column(row, ["Pos", "Position", "Best Pos", "best_position"]) or "M C"

            # Abilities
            ca = int(self._get_column(row, ["CA", "Current Ability", "cur_ab"]) or "50")
            pa = int(self._get_column(row, ["PA", "Potential Ability", "pot_ab"]) or str(ca))

            # Contract
            contract = self._get_column(row, ["Contract", "contract_until"])
            wage_str = self._get_column(row, ["Wage", "wage"]) or "0"
            wage = self._parse_wage(wage_str)

            value_str = self._get_column(row, ["Value", "market_value"]) or "0"
            value = self._parse_money(value_str)

            release_clause_str = self._get_column(row, ["Release Clause", "release_clause"])
            release_clause = int(self._parse_money(release_clause_str)) if release_clause_str else None

            # Physical
            height = int(self._get_column(row, ["Height", "height_cm"]) or "180")
            weight = int(self._get_column(row, ["Weight", "weight_kg"]) or "75")
            foot = self._get_column(row, ["Foot", "preferred_foot"]) or "Right"

            # Technical attributes
            corners = int(self._get_column(row, ["Corners", "corner"]) or "10")
            crossing = int(self._get_column(row, ["Crossing", "crossing"]) or "10")
            dribbling = int(self._get_column(row, ["Dribbling", "dribbling"]) or "10")
            finishing = int(self._get_column(row, ["Finishing", "finishing"]) or "10")
            first_touch = int(self._get_column(row, ["First Touch", "first_touch"]) or "10")
            free_kicks = int(self._get_column(row, ["Free Kicks", "free_kicks"]) or "10")
            heading = int(self._get_column(row, ["Heading", "heading"]) or "10")
            long_shots = int(self._get_column(row, ["Long Shots", "long_shots"]) or "10")
            marking = int(self._get_column(row, ["Marking", "marking"]) or "10")
            passing = int(self._get_column(row, ["Passing", "passing"]) or "10")
            penalty_taking = int(self._get_column(row, ["Penalties", "penalty"]) or "10")
            tackling = int(self._get_column(row, ["Tackling", "tackling"]) or "10")
            technique = int(self._get_column(row, ["Technique", "technique"]) or "10")

            # Mental attributes
            aggression = int(self._get_column(row, ["Aggression", "aggression"]) or "10")
            anticipation = int(self._get_column(row, ["Anticipation", "anticipation"]) or "10")
            bravery = int(self._get_column(row, ["Bravery", "bravery"]) or "10")
            composure = int(self._get_column(row, ["Composure", "composure"]) or "10")
            concentration = int(self._get_column(row, ["Concentration", "concentration"]) or "10")
            decisions = int(self._get_column(row, ["Decisions", "decisions"]) or "10")
            determination = int(self._get_column(row, ["Determination", "determination"]) or "10")
            flair = int(self._get_column(row, ["Flair", "flair"]) or "10")
            leadership = int(self._get_column(row, ["Leadership", "leadership"]) or "10")
            off_the_ball = int(self._get_column(row, ["Off the Ball", "off_the_ball"]) or "10")
            positioning = int(self._get_column(row, ["Positioning", "positioning"]) or "10")
            teamwork = int(self._get_column(row, ["Teamwork", "teamwork"]) or "10")
            vision = int(self._get_column(row, ["Vision", "vision"]) or "10")
            work_rate = int(self._get_column(row, ["Work Rate", "work_rate"]) or "10")

            # Physical attributes
            acceleration = int(self._get_column(row, ["Acceleration", "acceleration"]) or "10")
            agility = int(self._get_column(row, ["Agility", "agility"]) or "10")
            balance = int(self._get_column(row, ["Balance", "balance"]) or "10")
            jumping = int(self._get_column(row, ["Jumping", "jumping"]) or "10")
            natural_fitness = int(self._get_column(row, ["Natural Fitness", "natural_fitness"]) or "10")
            pace = int(self._get_column(row, ["Pace", "pace"]) or "10")
            stamina = int(self._get_column(row, ["Stamina", "stamina"]) or "10")
            strength = int(self._get_column(row, ["Strength", "strength"]) or "10")

            return FM24Player(
                uid=uid,
                name=name,
                age=age,
                nationality=nationality,
                club=club,
                position=position,
                current_ability=ca,
                potential_ability=pa,
                contract_until=contract,
                wage=wage,
                market_value=value,
                release_clause=release_clause,
                height=height,
                weight=weight,
                preferred_foot=foot,
                # Technical
                corners=corners,
                crossing=crossing,
                dribbling=dribbling,
                finishing=finishing,
                first_touch=first_touch,
                free_kicks=free_kicks,
                heading=heading,
                long_shots=long_shots,
                marking=marking,
                passing=passing,
                penalty_taking=penalty_taking,
                tackling=tackling,
                technique=technique,
                # Mental
                aggression=aggression,
                anticipation=anticipation,
                bravery=bravery,
                composure=composure,
                concentration=concentration,
                decisions=decisions,
                determination=determination,
                flair=flair,
                leadership=leadership,
                off_the_ball=off_the_ball,
                positioning=positioning,
                teamwork=teamwork,
                vision=vision,
                work_rate=work_rate,
                # Physical
                acceleration=acceleration,
                agility=agility,
                balance=balance,
                jumping=jumping,
                natural_fitness=natural_fitness,
                pace=pace,
                stamina=stamina,
                strength=strength,
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

    def _parse_wage(self, wage_str: str) -> int:
        """Parse wage string like '£150k p/w' or '150000' to weekly wage."""
        wage_str = wage_str.replace("£", "").replace("€", "").replace("$", "").replace(",", "").strip()
        wage_str = wage_str.replace("p/w", "").replace("per week", "").replace("/w", "").strip()

        if not wage_str:
            return 0

        if wage_str.isdigit():
            return int(wage_str)

        multiplier = 1
        if "k" in wage_str.lower():
            multiplier = 1000
            wage_str = wage_str.lower().replace("k", "")
        elif "m" in wage_str.lower():
            multiplier = 1_000_000
            wage_str = wage_str.lower().replace("m", "")

        try:
            return int(float(wage_str) * multiplier)
        except ValueError:
            return 0

    def _parse_money(self, value: str) -> int:
        """Parse money string like '£110.5M' or '500K' to integer."""
        if not value:
            return 0

        value = value.replace("£", "").replace("€", "").replace("$", "").replace(",", "").strip()

        if value.isdigit():
            return int(value)

        multiplier = 1
        if "m" in value.lower():
            multiplier = 1_000_000
            value = value.lower().replace("m", "")
        elif "k" in value.lower():
            multiplier = 1_000
            value = value.lower().replace("k", "")

        try:
            return int(float(value) * multiplier)
        except ValueError:
            return 0

    def to_db_player(self, fm_player: FM24Player, club_id: int | None = None) -> Player:
        """Convert FM24Player to database Player model."""
        # Parse name
        name_parts = fm_player.name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Unknown"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Map position
        position = self._map_position(fm_player.position)

        # Map foot
        foot = Foot.RIGHT if "right" in fm_player.preferred_foot.lower() else Foot.LEFT

        # Calculate birth date from age
        from datetime import date
        birth_year = date.today().year - fm_player.age
        birth_date = date(birth_year, 1, 1)

        # Map work rate from FM24 to our WorkRate enum
        work_rate_val = fm_player.work_rate
        if work_rate_val >= 15:
            work_rate = WorkRate.HIGH
        elif work_rate_val >= 7:
            work_rate = WorkRate.MEDIUM
        else:
            work_rate = WorkRate.LOW

        player = Player(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            nationality=fm_player.nationality,
            position=position,
            height=fm_player.height,
            weight=fm_player.weight,
            preferred_foot=foot,

            # Physical
            pace=fm_player.pace,
            acceleration=fm_player.acceleration,
            stamina=fm_player.stamina,
            strength=fm_player.strength,

            # Technical
            shooting=fm_player.finishing,
            passing=fm_player.passing,
            dribbling=fm_player.dribbling,
            crossing=fm_player.crossing,
            first_touch=fm_player.first_touch,

            # Mental/Defensive
            tackling=fm_player.tackling,
            marking=fm_player.marking,
            positioning=fm_player.positioning,
            vision=fm_player.vision,
            decisions=fm_player.decisions,

            # Mental
            work_rate=work_rate,
            determination=fm_player.determination,
            leadership=fm_player.leadership,
            teamwork=fm_player.teamwork,
            aggression=fm_player.aggression,

            # Overall
            current_ability=fm_player.current_ability,
            potential_ability=fm_player.potential_ability,

            # Contract
            club_id=club_id,
            salary=fm_player.wage,
            market_value=fm_player.market_value,
            release_clause=fm_player.release_clause,
        )

        return player

    def _map_position(self, fm_position: str) -> Position:
        """Map FM24 position string to our Position enum."""
        # Handle combined positions like "D C, DL R, DC"
        fm_position = fm_position.split(",")[0].strip()  # Take first position

        # Map exact match
        if fm_position in self.POSITION_MAP:
            return self.POSITION_MAP[fm_position]

        # Fuzzy match
        fm_upper = fm_position.upper()
        for key, value in self.POSITION_MAP.items():
            if key.upper() in fm_upper or fm_upper in key.upper():
                return value

        # Default
        return Position.CM

    def get_unique_clubs(self) -> list[str]:
        """Get list of unique clubs in the dataset."""
        if not self.players:
            self.parse_csv()

        clubs = set()
        for player in self.players:
            if player.club and player.club != "Free Agent":
                clubs.add(player.club)

        return sorted(clubs)

    def get_players_by_club(self, club_name: str) -> list[FM24Player]:
        """Get all players for a specific club."""
        return [p for p in self.players if p.club == club_name]


def download_fm24_dataset_instructions():
    """Print instructions for downloading FM24 dataset."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║   Football Manager 2024 数据导入指南                             ║
╚════════════════════════════════════════════════════════════════╝

方法 1: 使用 FM 编辑器导出 (推荐)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 打开 FM Editor
   - FM24 安装目录中找到 fm_editor.exe
   - 或在 Steam 中: 右键 FM24 → 管理工具 → FM Editor

2. 加载数据库
   - File → Load → 选择 FM24 数据库
   - 位置: documents/Sports Interactive/Football Manager 2024/db/

3. 导出数据
   - File → Export → 选择 CSV 格式
   - 选择要导出的表: players, clubs, leagues

4. 导入到项目
   python scripts/import_fm_data.py fm_players.csv


方法 2: 下载 Sortitoutsi 数据库 (最简单)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 访问: https://sortitoutsi.net/downloads/view/66832/football-manager-2024-database

2. 下载预览数据库 (Excel/CSV 格式)

3. 导入到项目
   python scripts/import_fm_data.py sortitoutsi_database.csv


方法 3: FM Scout 在线导出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 访问: https://www.fmscout.com/

2. 搜索 FM24 球员数据

3. 使用导出功能下载 CSV


方法 4: 直接使用 FM 数据库文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需要使用第三方解析库:
- fm-data-parser: https://github.com/yourusername/fm-data-parser
- fminside-api: pip install fminside-api


数据对比
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 数据源        | 数据量   | 质量 | 难度 |
|-------------|---------|------|------|
| FM Editor   | 50万+    | ⭐⭐⭐⭐⭐ | 中   |
| Sortitoutsi | 10万+    | ⭐⭐⭐⭐ | 低   |
| FM Scout    | 预览数据  | ⭐⭐⭐ | 低   |


推荐流程
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: 快速测试 (本周)
└─ 使用 Sortitoutsi 数据快速导入英超 5 大联赛

Phase 2: 完整数据 (下周)
└─ 使用 FM Editor 导出完整数据库

""")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fm_importer.py <fm24_csv_file>")
        download_fm24_dataset_instructions()
        sys.exit(1)

    csv_file = sys.argv[1]
    importer = FM24Importer(csv_file)
    players = importer.parse_csv()

    print(f"✓ 解析了 {len(players)} 名球员")
    print(f"✓ 独特俱乐部: {len(importer.get_unique_clubs())} 个")

    # Show top 10 players by CA
    top_players = sorted(players, key=lambda p: p.current_ability, reverse=True)[:10]
    print("\n🏆 能力最高的 10 名球员:")
    for i, p in enumerate(top_players, 1):
        print(f"  {i}. {p.name} ({p.club}) - CA: {p.current_ability}, PA: {p.potential_ability}, Value: €{p.market_value:,}")
