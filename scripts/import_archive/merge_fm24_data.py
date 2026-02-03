"""Merge FM24 data (players.csv + teams.csv) into FootballManus database.

This script:
1. Loads teams from teams.csv
2. Loads players from players.csv
3. Creates leagues based on teams
4. Maps players to clubs and leagues
5. Imports everything into the database
"""

import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re


class FM24DataMerger:
    """Merge FM24 CSV data into SQLite database."""

    # Chinese position to English
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

    def __init__(self, players_csv: str, teams_csv: str, db_path: str):
        self.players_csv = Path(players_csv)
        self.teams_csv = Path(teams_csv)
        self.db_path = Path(db_path)

        self.teams: List[Dict] = []
        self.players: List[Dict] = []
        self.leagues: Dict[str, int] = {}  # league_name -> league_id
        self.clubs: Dict[str, int] = {}  # club_name -> club_id

    def load_teams(self):
        """Load teams from teams.csv (GBK encoding)."""
        print(f"📂 加载球队数据: {self.teams_csv}")

        with open(self.teams_csv, "r", encoding="gbk") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                self.teams.append(row)

        print(f"✓ 加载了 {len(self.teams)} 个俱乐部")

    def load_players(self):
        """Load players from players.csv (GBK encoding)."""
        print(f"📂 加载球员数据: {self.players_csv}")

        with open(self.players_csv, "r", encoding="gbk") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                self.players.append(row)

        print(f"✓ 加载了 {len(self.players)} 名球员")

    def _parse_rating(self, rating_str: str) -> int:
        """Parse rating from string like '69.9% (中场)' to 1-200 scale."""
        if not rating_str:
            return 50

        match = re.search(r"(\d+\.?\d*)%", rating_str)
        if match:
            percentage = float(match.group(1))
            return int(percentage * 2)  # 0-100% to 1-200

        return 50

    def _parse_number(self, num_str: str) -> int:
        """Parse number string like '162,630' to integer."""
        if not num_str:
            return 0
        return int(num_str.replace(",", "").strip()) if num_str.replace(",", "").strip().isdigit() else 0

    def _parse_birth_date(self, date_str: str) -> Optional[str]:
        """Parse birth date from format 'DD.MM.YYYY' to YYYY-MM-DD."""
        if not date_str or date_str == "-":
            return None

        try:
            parts = date_str.split(".")
            if len(parts) == 3:
                day, month, year = map(int, parts)
                return f"{year}-{month:02d}-{day:02d}"
        except Exception:
            pass

        return None

    def _infer_attributes(self, overall_rating: int, position: str) -> Dict[str, int]:
        """Infer player attributes from overall rating and position."""
        base = overall_rating // 2  # 200 scale to 100 scale

        if position == "GK":
            return {
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
                "determination": int(base * 0.8),
                "leadership": int(base * 0.6),
                "teamwork": int(base * 0.7),
                "aggression": int(base * 0.6),
            }
        elif position in ["CB", "LB", "RB", "LWB", "RWB"]:
            return {
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
                "determination": int(base * 0.8),
                "leadership": int(base * 0.6),
                "teamwork": int(base * 0.7),
                "aggression": int(base * 0.6),
            }
        elif position in ["CDM", "CM", "LM", "RM"]:
            return {
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
                "determination": int(base * 0.8),
                "leadership": int(base * 0.6),
                "teamwork": int(base * 0.7),
                "aggression": int(base * 0.6),
            }
        else:  # Attackers
            return {
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
                "determination": int(base * 0.8),
                "leadership": int(base * 0.6),
                "teamwork": int(base * 0.7),
                "aggression": int(base * 0.6),
            }

    def import_to_database(self, replace: bool = False):
        """Import all data to SQLite database."""
        print(f"\n📦 导入数据到: {self.db_path}")

        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if replace:
            print("⚠️  清除现有数据...")
            cursor.execute("DELETE FROM players")
            cursor.execute("DELETE FROM clubs")
            cursor.execute("DELETE FROM leagues")
            conn.commit()

        # Step 1: Import leagues
        print("\n=== 步骤 1: 导入联赛 ===")
        self._import_leagues(cursor)
        conn.commit()

        # Step 2: Import clubs
        print("\n=== 步骤 2: 导入俱乐部 ===")
        self._import_clubs(cursor)
        conn.commit()

        # Step 3: Import players
        print("\n=== 步骤 3: 导入球员 ===")
        self._import_players(cursor)
        conn.commit()

        conn.close()
        print("\n✅ 导入完成!")

    def _import_leagues(self, cursor):
        """Import unique leagues from teams data."""
        # Get unique leagues
        leagues_set = set()
        for team in self.teams:
            league = team.get("联赛", "").strip()
            if league:
                leagues_set.add((league, team.get("国家", "Unknown")))

        # Insert leagues
        for league_name, country in sorted(leagues_set):
            # Check if exists
            cursor.execute(
                "SELECT id FROM leagues WHERE name = ?",
                (league_name,)
            )
            existing = cursor.fetchone()

            if existing:
                self.leagues[league_name] = existing[0]
            else:
                cursor.execute(
                    """INSERT INTO leagues (name, short_name, country, tier, format, teams_count,
                                          promotion_count, relegation_count, has_promotion_playoff,
                                          has_relegation_playoff, season_start_month, season_end_month,
                                          has_winter_break, matches_on_weekdays, typical_match_days,
                                          champions_league_spots, europa_league_spots, conference_league_spots,
                                          prize_money_first, prize_money_last, tv_rights_base)
                       VALUES (?, ?, ?, 1, 'double_round_robin', 20, 3, 3, 0, 0, 8, 5,
                               0, 1, 'Saturday,Sunday', 4, 2, 1, 100000000, 10000000, 50000000)""",
                    (league_name, league_name[:20], country)
                )
                self.leagues[league_name] = cursor.lastrowid
                print(f"  ✓ 创建联赛: {league_name} ({country})")

        print(f"✓ 导入了 {len(self.leagues)} 个联赛")

    def _import_clubs(self, cursor):
        """Import clubs from teams data."""
        for team in self.teams:
            name = team.get("名字", "").strip()
            if not name:
                continue

            # Parse fields
            country = team.get("国家", "Unknown")
            league_name = team.get("联赛", "")
            reputation = self._parse_number(team.get("声望", "5000"))
            balance = self._parse_number(team.get("收支结余", "50000000"))
            transfer_budget = self._parse_number(team.get("转会预算", "10000000"))
            wage_budget = self._parse_number(team.get("工资预算", "1000000"))
            stadium_capacity = self._parse_number(team.get("球场容量", "0"))
            avg_attendance = self._parse_number(team.get("平均上座", "0"))
            training_facility = int(team.get("TF", "50").strip())
            youth_facility = int(team.get("YF", "50").strip())
            medical_facility = int(team.get("JC", "50").strip())

            # Get league_id
            league_id = self.leagues.get(league_name)
            if not league_id:
                print(f"  ⚠️  跳过 {name}: 联赛 '{league_name}' 不存在")
                continue

            # Check if exists
            cursor.execute(
                "SELECT id FROM clubs WHERE name = ?",
                (name,)
            )
            existing = cursor.fetchone()

            if existing:
                self.clubs[name] = existing[0]
            else:
                cursor.execute(
                    """INSERT INTO clubs (name, short_name, founded_year, city, country,
                                      stadium_name, stadium_capacity, reputation, reputation_level,
                                      primary_color, secondary_color, league_id,
                                      balance, transfer_budget, wage_budget,
                                      weekly_wage_bill, ticket_price, average_attendance, commercial_income,
                                      training_facility_level, youth_facility_level, youth_academy_country,
                                      owner_user_id, llm_config, is_ai_controlled,
                                      season_objective)
                       VALUES (?, ?, 1900, '', ?, ?, ?, ?, '#FF0000', '#FFFFFF', ?,
                                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, name[:20], country, f"{name} Stadium", stadium_capacity,
                     reputation, 'Respectable', league_id, balance, transfer_budget, wage_budget,
                     0, 50, avg_attendance, 0,
                     training_facility, youth_facility, country,
                     None, None, 1, 'mid_table')
                )
                self.clubs[name] = cursor.lastrowid

        print(f"✓ 导入了 {len(self.clubs)} 个俱乐部")

    def _import_players(self, cursor):
        """Import players from players data."""
        imported = 0
        skipped = 0

        for player in self.players:
            name = player.get("姓名", "").strip()
            if not name or name == "-":
                skipped += 1
                continue

            # Parse name
            name_parts = name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else "Unknown"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Parse fields
            age_str = player.get("年龄", "").strip()
            age = int(age_str) if age_str and age_str.isdigit() else 25

            nationality = player.get("国籍", "Unknown")
            if "/" in nationality:
                nationality = nationality.split("/")[0].strip()

            club = player.get("俱乐部", "").strip()
            if not club or club == "-":
                skipped += 1
                continue

            # Get club_id
            club_id = self.clubs.get(club)
            if not club_id:
                skipped += 1
                continue

            # Parse position
            position_str = player.get("位置", "").strip()
            position = self.POSITION_MAP.get(position_str.split(",")[0], "CM")

            # Parse ratings
            current_rating = self._parse_rating(player.get("当前评分", ""))
            potential_rating = self._parse_rating(player.get("最高潜力评分", ""))

            # Parse wage and value
            wage = self._parse_number(player.get("工资", "0"))
            value = self._parse_number(player.get("身价", "0"))

            # Parse birth date
            birth_date = self._parse_birth_date(player.get("生日", ""))

            # Infer attributes
            attributes = self._infer_attributes(current_rating, position)

            # Insert player
            cursor.execute(
                """INSERT INTO players (first_name, last_name, birth_date, nationality,
                                      position, preferred_foot,
                                      pace, acceleration, stamina, strength,
                                      shooting, passing, dribbling, crossing, first_touch,
                                      tackling, marking, positioning, vision, decisions,
                                      reflexes, handling, kicking, one_on_one,
                                      determination, leadership, teamwork, aggression,
                                      work_rate,
                                      current_ability, potential_ability,
                                      club_id, salary, market_value,
                                      fitness, morale, form)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (first_name, last_name, birth_date, nationality,
                 position, "Right",
                 attributes["pace"], attributes["acceleration"], attributes["stamina"], attributes["strength"],
                 attributes["shooting"], attributes["passing"], attributes["dribbling"], attributes["crossing"], attributes["first_touch"],
                 attributes["tackling"], attributes["marking"], attributes["positioning"], attributes["vision"], attributes["decisions"],
                 attributes["reflexes"], attributes["handling"], attributes["kicking"], attributes["one_on_one"],
                 attributes["determination"], attributes["leadership"], attributes["teamwork"], attributes["aggression"],
                 "Medium",
                 current_rating, potential_rating,
                 club_id, wage, value,
                 100, 50, 50)
            )

            imported += 1
            if imported % 10000 == 0:
                cursor.connection.commit()
                print(f"  已导入 {imported} 名球员...")

        print(f"✓ 导入了 {imported} 名球员")
        if skipped > 0:
            print(f"⚠️  跳过了 {skipped} 名球员")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="合并 FM24 数据到数据库")
    parser.add_argument("--players", default="/home/xu/code/FootballManus/data/players.csv",
                       help="球员 CSV 文件路径")
    parser.add_argument("--teams", default="/home/xu/code/FootballManus/data/teams.csv",
                       help="球队 CSV 文件路径")
    parser.add_argument("--db", default="/home/xu/code/FootballManus/data/fm_manager.db",
                       help="输出数据库路径")
    parser.add_argument("--replace", action="store_true",
                       help="替换现有数据")

    args = parser.parse_args()

    # Check files exist
    if not Path(args.players).exists():
        print(f"❌ 文件不存在: {args.players}")
        return
    if not Path(args.teams).exists():
        print(f"❌ 文件不存在: {args.teams}")
        return

    # Load data
    merger = FM24DataMerger(args.players, args.teams, args.db)
    merger.load_teams()
    merger.load_players()

    # Import to database
    merger.import_to_database(replace=args.replace)


if __name__ == "__main__":
    main()
