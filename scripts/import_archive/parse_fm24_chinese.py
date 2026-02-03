"""Convert FM24 Chinese CSV to FootballManus format (standalone version).

This script parses the FM24 Chinese CSV and converts it to our format,
without requiring database connection for testing.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class FM24ChineseParser:
    """Parse FM24 Chinese CSV export."""

    POSITION_MAP = {
        "门将": "GK",
        "中后卫": "CB",
        "左后卫": "LB",
        "右后卫": "RB",
        "左翼卫": "LWB",
        "右翼卫": "RWB",
        "后腰": "CDM",
        "中前卫": "CM",
        "左前卫": "LM",
        "右前卫": "RM",
        "前腰": "CAM",
        "左边锋": "LW",
        "右边锋": "RW",
        "中锋": "ST",
        "前锋": "ST",
        "攻击型中场": "CAM",
        "边锋": "LW",
        "中场": "CM",
        "后卫": "CB",
        "清道夫": "CB",
    }

    def __init__(self, csv_file: str | Path):
        self.csv_file = Path(csv_file)
        self.players = []

    def parse(self) -> list[dict]:
        """Parse FM24 Chinese CSV file."""
        self.players = []

        print(f"📂 读取文件: {self.csv_file}")

        with open(self.csv_file, "r", encoding="gbk") as f:
            reader = csv.DictReader(f, delimiter=";")
            for i, row in enumerate(reader):
                player = self._parse_row(row)
                if player:
                    self.players.append(player)

                if (i + 1) % 1000 == 0:
                    print(f"  已处理 {i + 1} 行...")

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
            if "/" in nationality:
                nationality = nationality.split("/")[0].strip()

            # Parse club
            club = row.get("俱乐部", "").strip()
            if not club or club == "-":
                club = "Free Agent"

            # Parse position
            position_str = row.get("位置", "").strip()
            position = self._map_position(position_str)

            # Parse ratings
            current_rating_str = row.get("当前评分", "").strip()
            current_rating = self._parse_rating(current_rating_str)

            potential_rating_str = row.get("最高潜力评分", "").strip()
            potential_rating = self._parse_rating(potential_rating_str)

            # Parse wage and value
            wage_str = row.get("工资", "0").strip()
            wage = self._parse_number(wage_str)

            value_str = row.get("身价", "0").strip()
            value = self._parse_number(value_str)

            # Parse birth date
            birth_date_str = row.get("生日", "").strip()
            birth_date = self._parse_birth_date(birth_date_str)

            # Parse unique ID
            uid = row.get("UNIQUE ID", "").strip()
            uid = int(uid) if uid and uid.isdigit() else None

            # Parse club ID
            club_id_fm = row.get("Club ID", "").strip()
            club_id_fm = int(club_id_fm) if club_id_fm and club_id_fm.isdigit() else None

            # Extract position ratings
            position_ratings = self._extract_position_ratings(row)

            # Infer attributes
            attributes = self._infer_attributes(current_rating, position, position_ratings)

            return {
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
                "birth_date": birth_date.isoformat() if birth_date else None,
                **attributes,
            }

        except Exception as e:
            print(f"Error parsing row: {e}")
            return None

    def _parse_rating(self, rating_str: str) -> int:
        """Parse rating from string like '69.9% (中场)' to 1-200 scale."""
        if not rating_str:
            return 50

        import re
        match = re.search(r"(\d+\.?\d*)%", rating_str)
        if match:
            percentage = float(match.group(1))
            return int(percentage * 2)  # 0-100% to 1-200

        return 50

    def _parse_number(self, num_str: str) -> int:
        """Parse number string like '162,630' to integer."""
        if not num_str:
            return 0

        num_str = num_str.replace(",", "").strip()

        if num_str.isdigit():
            return int(num_str)

        return 0

    def _parse_birth_date(self, date_str: str) -> Optional[datetime]:
        """Parse birth date from format 'DD.MM.YYYY'."""
        if not date_str or date_str == "-":
            return None

        try:
            parts = date_str.split(".")
            if len(parts) == 3:
                day, month, year = map(int, parts)
                return datetime(year, month, day)
        except Exception:
            pass

        return None

    def _map_position(self, position_str: str) -> str:
        """Map Chinese position string to English position code."""
        positions = [p.strip() for p in position_str.split(",")]
        first_pos = positions[0] if positions else position_str

        if first_pos in self.POSITION_MAP:
            return self.POSITION_MAP[first_pos]

        for chinese_pos, english_pos in self.POSITION_MAP.items():
            if chinese_pos in first_pos or first_pos in chinese_pos:
                return english_pos

        return "CM"

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
                pos_key = field.replace(" 评分", "")
                ratings[pos_key] = rating

        return ratings

    def _infer_attributes(self, overall_rating: int, position: str, position_ratings: dict) -> dict:
        """Infer player attributes from overall rating and position."""
        base = overall_rating // 2  # 200 scale to 100 scale

        if position == "GK":
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
                "reflexes": int(base * 1.0),
                "handling": int(base * 0.9),
                "kicking": int(base * 0.7),
                "one_on_one": int(base * 0.8),
            }
        elif position in ["CB", "LB", "RB", "LWB", "RWB"]:
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
        elif position in ["CDM", "CM", "LM", "RM"]:
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
        elif position in ["CAM", "LW", "RW", "ST"]:
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

        # Add mental attributes
        attributes.update({
            "determination": int(base * 0.8),
            "leadership": int(base * 0.6),
            "teamwork": int(base * 0.7),
            "aggression": int(base * 0.6),
        })

        # Clamp to 0-100
        for key, value in attributes.items():
            if isinstance(value, int):
                attributes[key] = max(1, min(100, value))

        return attributes

    def get_unique_clubs(self) -> list[str]:
        """Get list of unique clubs."""
        clubs = set()
        for player in self.players:
            club = player.get("club", "")
            if club and club != "Free Agent":
                clubs.add(club)
        return sorted(clubs)

    def export_json(self, output_file: str):
        """Export parsed players to JSON file."""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.players, f, ensure_ascii=False, indent=2)
        print(f"✓ 导出到: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("用法: python parse_fm24_chinese.py <csv文件> [输出JSON文件]")
        print("\n示例:")
        print("  python parse_fm24_chinese.py data/players.csv")
        print("  python parse_fm24_chinese.py data/players.csv output.json")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(csv_file).exists():
        print(f"❌ 文件不存在: {csv_file}")
        sys.exit(1)

    # Parse CSV
    parser = FM24ChineseParser(csv_file)
    players = parser.parse()

    # Show statistics
    print(f"\n📊 数据统计:")
    print(f"  总球员数: {len(players)}")
    print(f"  独特俱乐部: {len(parser.get_unique_clubs())}")

    # Show top 10 by CA
    top_players = sorted(players, key=lambda p: p["current_ability"], reverse=True)[:10]
    print(f"\n🏆 能力最高的 10 名球员:")
    for i, p in enumerate(top_players, 1):
        print(f"  {i}. {p['name']} ({p['club']}) - CA: {p['current_ability']}, PA: {p['potential_ability']}, Age: {p['age']}")

    # Export to JSON if requested
    if output_json:
        parser.export_json(output_json)


if __name__ == "__main__":
    main()
