"""Convert FM24 Chinese CSV export to FootballManus database.

This script handles the specific format of FM24 Chinese CSV exports:
- GBK encoding
- Semicolon delimiter
- Percentage-based ratings (0-100%)
- Chinese position names
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core.database import SessionLocal
from fm_manager.core.models import Player, Club, League, Position, Foot, WorkRate


class FM24ChineseImporter:
    """Import FM24 Chinese CSV export data."""

    # Chinese position mapping to Position enum
    POSITION_MAP = {
        "门将": Position.GK,
        "中后卫": Position.CB,
        "左后卫": Position.LB,
        "右后卫": Position.RB,
        "左翼卫": Position.LWB,
        "右翼卫": Position.RWB,
        "后腰": Position.CDM,
        "中前卫": Position.CM,
        "左前卫": Position.LM,
        "右前卫": Position.RM,
        "前腰": Position.CAM,
        "左边锋": Position.LW,
        "右边锋": Position.RW,
        "中锋": Position.ST,
        "前锋": Position.ST,
        "攻击型中场": Position.CAM,
        "边锋": Position.LW,  # Default to left winger
        "中场": Position.CM,
        "后卫": Position.CB,
        "清道夫": Position.CB,
    }

    def __init__(self, csv_file: str | Path):
        self.csv_file = Path(csv_file)
        self.players = []
        self.clubs = {}

    def parse_csv(self) -> list[dict]:
        """Parse FM24 Chinese CSV file."""
        self.players = []

        with open(self.csv_file, "r", encoding="gbk") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                player = self._parse_row(row)
                if player:
                    self.players.append(player)

        print(f"✓ 解析了 {len(self.players)} 名球员")
        return self.players

    def _parse_row(self, row: dict) -> Optional[dict]:
        """Parse a single CSV row."""
        try:
            name = row.get("姓名", "").strip()
            if not name or name == "-":
                return None

            # Parse age
            age_str = row.get("年龄", "").strip()
            age = int(age_str) if age_str and age_str.isdigit() else 25

            # Parse nationality
            nationality = row.get("国籍", "Unknown")
            # Handle dual nationality like "Faroe Islands / Scotland"
            if "/" in nationality:
                nationality = nationality.split("/")[0].strip()

            # Parse club
            club = row.get("俱乐部", "").strip()
            if not club or club == "-":
                club = "Free Agent"

            # Parse position
            position_str = row.get("位置", "").strip()
            position = self._map_position(position_str)

            # Parse ratings (percentage to 1-200 scale)
            current_rating_str = row.get("当前评分", "").strip()
            current_rating = self._parse_rating(current_rating_str)

            potential_rating_str = row.get("最高潜力评分", "").strip()
            potential_rating = self._parse_rating(potential_rating_str)

            # Parse wage and value
            wage_str = row.get("工资", "0").strip()
            wage = self._parse_number(wage_str)

            value_str = row.get("身价", "0").strip()
            value = self._parse_number(value_str)

            # Parse birth date (format: DD.MM.YYYY)
            birth_date_str = row.get("生日", "").strip()
            birth_date = self._parse_birth_date(birth_date_str)

            # Parse unique ID
            uid = row.get("UNIQUE ID", "").strip()
            uid = int(uid) if uid and uid.isdigit() else None

            # Parse club ID
            club_id_fm = row.get("Club ID", "").strip()
            club_id_fm = int(club_id_fm) if club_id_fm and club_id_fm.isdigit() else None

            # Extract position ratings for attribute inference
            position_ratings = self._extract_position_ratings(row)

            # Infer attributes from position ratings and overall rating
            attributes = self._infer_attributes(current_rating, position, position_ratings)

            player = {
                "uid": uid,
                "fm_club_id": club_id_fm,
                "name": name,
                "age": age,
                "nationality": nationality,
                "club": club,
                "position": position,
                "position_str": position_str,
                "current_ability": current_rating,
                "potential_ability": potential_rating,
                "wage": wage,
                "market_value": value,
                "birth_date": birth_date,
                **attributes,
            }

            return player

        except Exception as e:
            print(f"Error parsing row: {e}")
            return None

    def _parse_rating(self, rating_str: str) -> int:
        """Parse rating from string like '69.9% (中场)' to 1-200 scale."""
        if not rating_str:
            return 50

        # Extract percentage
        import re
        match = re.search(r"(\d+\.?\d*)%", rating_str)
        if match:
            percentage = float(match.group(1))
            # Convert 0-100% to 1-200 scale
            return int(percentage * 2)

        return 50

    def _parse_number(self, num_str: str) -> int:
        """Parse number string like '162,630' to integer."""
        if not num_str:
            return 0

        # Remove commas and other non-numeric characters
        num_str = num_str.replace(",", "").strip()

        if num_str.isdigit():
            return int(num_str)

        return 0

    def _parse_birth_date(self, date_str: str) -> Optional[datetime]:
        """Parse birth date from format 'DD.MM.YYYY'."""
        if not date_str or date_str == "-":
            return None

        try:
            # Format: DD.MM.YYYY
            parts = date_str.split(".")
            if len(parts) == 3:
                day, month, year = map(int, parts)
                return datetime(year, month, day)
        except Exception:
            pass

        return None

    def _map_position(self, position_str: str) -> Position:
        """Map Chinese position string to Position enum."""
        # Handle multiple positions like "攻击型中场 右左, 前锋"
        # Take the first one
        positions = [p.strip() for p in position_str.split(",")]
        first_pos = positions[0] if positions else position_str

        # Try exact match
        if first_pos in self.POSITION_MAP:
            return self.POSITION_MAP[first_pos]

        # Try fuzzy match
        for chinese_pos, enum_pos in self.POSITION_MAP.items():
            if chinese_pos in first_pos or first_pos in chinese_pos:
                return enum_pos

        # Default
        return Position.CM

    def _extract_position_ratings(self, row: dict) -> dict:
        """Extract position ratings from row."""
        ratings = {}
        position_fields = [
            "GK 评分", "SW 评分", "DL 评分", "DC 评分", "DR 评分",
            "WBL 评分", "WBR 评分", "DM 评分", "ML 评分", "MC 评分",
            "MR 评分", "AML 评分", "AMC 评分", "AMR 评分", "FS 评分", "TS 评分"
        ]

        for field in position_fields:
            if field in row and row[field]:
                rating = self._parse_rating(row[field])
                # Map field name to position
                pos_key = field.replace(" 评分", "")
                ratings[pos_key] = rating

        return ratings

    def _infer_attributes(self, overall_rating: int, position: Position, position_ratings: dict) -> dict:
        """Infer player attributes from overall rating and position ratings.

        Since the CSV doesn't have detailed attributes, we infer them:
        1. Base attributes on overall rating
        2. Adjust based on position
        3. Add some variation for realism
        """
        # Base all attributes on overall rating with slight variation
        base = overall_rating // 2  # 200 scale to 100 scale

        # Position-specific adjustments
        if position == Position.GK:
            attributes = {
                "pace": int(base * 0.7),
                "acceleration": int(base * 0.7),
                "stamina": int(base * 0.8),
                "strength": int(base * 0.8),
                "shooting": int(base * 0.3),
                "passing": int(base * 0.6),
                "dribbling": int(base * 0.4),
                "crossing": int(base * 0.4),
                "first_touch": int(base * 0.5),
                "tackling": int(base * 0.3),
                "marking": int(base * 0.3),
                "positioning": int(base * 0.7),
                "vision": int(base * 0.6),
                "decisions": int(base * 0.7),
                # GK-specific
                "reflexes": int(base * 1.0),
                "handling": int(base * 0.9),
                "kicking": int(base * 0.7),
                "one_on_one": int(base * 0.8),
            }
        elif position in [Position.CB, Position.LB, Position.RB, Position.LWB, Position.RWB]:
            # Defenders
            attributes = {
                "pace": int(base * 0.8),
                "acceleration": int(base * 0.8),
                "stamina": int(base * 0.85),
                "strength": int(base * 0.9),
                "shooting": int(base * 0.4),
                "passing": int(base * 0.65),
                "dribbling": int(base * 0.6),
                "crossing": int(base * 0.6),
                "first_touch": int(base * 0.65),
                "tackling": int(base * 0.9),
                "marking": int(base * 0.9),
                "positioning": int(base * 0.85),
                "vision": int(base * 0.6),
                "decisions": int(base * 0.7),
                "reflexes": int(base * 0.4),
                "handling": int(base * 0.3),
                "kicking": int(base * 0.4),
                "one_on_one": int(base * 0.4),
            }
        elif position in [Position.CDM, Position.CM, Position.LM, Position.RM]:
            # Midfielders
            attributes = {
                "pace": int(base * 0.8),
                "acceleration": int(base * 0.8),
                "stamina": int(base * 0.9),
                "strength": int(base * 0.75),
                "shooting": int(base * 0.6),
                "passing": int(base * 0.85),
                "dribbling": int(base * 0.8),
                "crossing": int(base * 0.7),
                "first_touch": int(base * 0.8),
                "tackling": int(base * 0.75),
                "marking": int(base * 0.7),
                "positioning": int(base * 0.8),
                "vision": int(base * 0.85),
                "decisions": int(base * 0.8),
                "reflexes": int(base * 0.4),
                "handling": int(base * 0.3),
                "kicking": int(base * 0.4),
                "one_on_one": int(base * 0.4),
            }
        elif position in [Position.CAM, Position.LW, Position.RW, Position.CF, Position.ST]:
            # Attackers
            attributes = {
                "pace": int(base * 0.85),
                "acceleration": int(base * 0.85),
                "stamina": int(base * 0.8),
                "strength": int(base * 0.7),
                "shooting": int(base * 0.9),
                "passing": int(base * 0.75),
                "dribbling": int(base * 0.9),
                "crossing": int(base * 0.7),
                "first_touch": int(base * 0.85),
                "tackling": int(base * 0.5),
                "marking": int(base * 0.5),
                "positioning": int(base * 0.85),
                "vision": int(base * 0.8),
                "decisions": int(base * 0.75),
                "reflexes": int(base * 0.4),
                "handling": int(base * 0.3),
                "kicking": int(base * 0.4),
                "one_on_one": int(base * 0.4),
            }
        else:
            # Default
            attributes = {
                "pace": base,
                "acceleration": base,
                "stamina": base,
                "strength": base,
                "shooting": base,
                "passing": base,
                "dribbling": base,
                "crossing": base,
                "first_touch": base,
                "tackling": base,
                "marking": base,
                "positioning": base,
                "vision": base,
                "decisions": base,
                "reflexes": base,
                "handling": base,
                "kicking": base,
                "one_on_one": base,
            }

        # Add mental attributes (default values)
        attributes.update({
            "work_rate": WorkRate.MEDIUM,
            "determination": int(base * 0.8),
            "leadership": int(base * 0.6),
            "teamwork": int(base * 0.7),
            "aggression": int(base * 0.6),
        })

        # Ensure attributes are in 0-100 range
        for key, value in attributes.items():
            if isinstance(value, int):
                attributes[key] = max(1, min(100, value))

        return attributes

    def to_db_player(self, player_data: dict, club_id: Optional[int] = None) -> Player:
        """Convert parsed player data to database Player model."""
        # Parse name
        name_parts = player_data["name"].split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Unknown"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        player = Player(
            first_name=first_name,
            last_name=last_name,
            birth_date=player_data["birth_date"],
            nationality=player_data["nationality"],
            position=player_data["position"],
            preferred_foot=Foot.RIGHT,  # Default

            # Physical
            pace=player_data["pace"],
            acceleration=player_data["acceleration"],
            stamina=player_data["stamina"],
            strength=player_data["strength"],

            # Technical
            shooting=player_data["shooting"],
            passing=player_data["passing"],
            dribbling=player_data["dribbling"],
            crossing=player_data["crossing"],
            first_touch=player_data["first_touch"],

            # Mental/Defensive
            tackling=player_data["tackling"],
            marking=player_data["marking"],
            positioning=player_data["positioning"],
            vision=player_data["vision"],
            decisions=player_data["decisions"],

            # GK
            reflexes=player_data["reflexes"],
            handling=player_data["handling"],
            kicking=player_data["kicking"],
            one_on_one=player_data["one_on_one"],

            # Mental
            work_rate=player_data["work_rate"],
            determination=player_data["determination"],
            leadership=player_data["leadership"],
            teamwork=player_data["teamwork"],
            aggression=player_data["aggression"],

            # Overall
            current_ability=player_data["current_ability"],
            potential_ability=player_data["potential_ability"],

            # Contract
            club_id=club_id,
            salary=player_data["wage"],
            market_value=player_data["market_value"],
        )

        return player

    def get_unique_clubs(self) -> list[str]:
        """Get list of unique clubs."""
        clubs = set()
        for player in self.players:
            club = player.get("club", "")
            if club and club != "Free Agent":
                clubs.add(club)
        return sorted(clubs)


def import_players(csv_file: str, limit: Optional[int] = None, club_filter: Optional[str] = None):
    """Import players from FM24 Chinese CSV."""
    print(f"📂 读取 FM24 中文 CSV: {csv_file}")

    # Parse CSV
    importer = FM24ChineseImporter(csv_file)
    players = importer.parse_csv()

    # Apply filters
    if club_filter:
        players = [p for p in players if club_filter.lower() in p["club"].lower()]
        print(f"✓ 筛选俱乐部 '{club_filter}': {len(players)} 名球员")

    if limit:
        players = sorted(players, key=lambda p: p["current_ability"], reverse=True)[:limit]
        print(f"✓ 限制数量: {len(players)} 名球员")

    # Get unique clubs
    unique_clubs = importer.get_unique_clubs()
    print(f"✓ 发现 {len(unique_clubs)} 个俱乐部")

    # Create database session
    db = SessionLocal()

    try:
        # Create clubs
        club_map = {}
        for club_name in unique_clubs:
            club = db.query(Club).filter(Club.name == club_name).first()
            if not club:
                club = Club(
                    name=club_name,
                    league_id=1,  # Default
                    reputation=50,
                    balance=50_000_000,
                )
                db.add(club)
                db.commit()
                db.refresh(club)
                print(f"  ✓ 创建俱乐部: {club_name}")
            club_map[club_name] = club

        # Import players
        imported_count = 0
        for player_data in players:
            club_name = player_data["club"]
            club_id = club_map.get(club_name)
            if not club_id:
                continue

            # Check if player exists
            name_parts = player_data["name"].split(maxsplit=1)
            first_name = name_parts[0] if name_parts else "Unknown"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            existing = db.query(Player).filter(
                Player.first_name == first_name,
                Player.last_name == last_name
            ).first()

            if existing:
                # Update
                db_player = importer.to_db_player(player_data, club_id)
                existing.current_ability = db_player.current_ability
                existing.potential_ability = db_player.potential_ability
                existing.market_value = db_player.market_value
                existing.salary = db_player.salary
                db.commit()
                imported_count += 1
            else:
                # Create new
                db_player = importer.to_db_player(player_data, club_id)
                db.add(db_player)
                imported_count += 1

            if imported_count % 100 == 0:
                db.commit()
                print(f"  已导入 {imported_count} 名球员...")

        db.commit()
        print(f"\n✅ 成功导入 {imported_count} 名球员!")

        # Show statistics
        total_players = db.query(Player).count()
        print(f"\n📊 数据库中总球员数: {total_players}")

        top_players = db.query(Player).order_by(Player.current_ability.desc()).limit(5).all()
        print(f"\n🏆 能力最高的 5 名球员:")
        for p in top_players:
            print(f"  {p.full_name} (CA: {p.current_ability}, PA: {p.potential_ability}, 俱乐部: {p.club.name if p.club else 'N/A'})")

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导入 FM24 中文 CSV 数据")
    parser.add_argument("csv_file", help="FM24 CSV 文件路径")
    parser.add_argument("--limit", type=int, help="限制导入的球员数量")
    parser.add_argument("--club", help="只导入特定俱乐部的球员")

    args = parser.parse_args()

    if not Path(args.csv_file).exists():
        print(f"❌ 文件不存在: {args.csv_file}")
        sys.exit(1)

    import_players(args.csv_file, args.limit, args.club)
