#!/usr/bin/env python3

import sqlite3
import csv
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class TransfermarktConverter:
    def __init__(self, data_dir="data/football-datasets", db_path="fm_manager.db"):
        self.data_dir = Path(data_dir)
        self.db_path = db_path

        self.player_profiles_file = self.data_dir / "player_profiles" / "player_profiles.csv"
        self.team_details_file = self.data_dir / "team_details" / "team_details.csv"
        self.player_performances_file = (
            self.data_dir / "player_performances" / "player_performances.csv"
        )
        self.player_market_value_file = (
            self.data_dir / "player_latest_market_value" / "player_latest_market_value.csv"
        )

    def connect_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def load_market_values(self):
        print("\n加载市场价值数据...")

        market_values = {}

        if self.player_market_value_file.exists():
            with open(self.player_market_value_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                next(reader)

                for row in reader:
                    player_id = row.get("player_id", "")
                    if player_id:
                        try:
                            player_id = int(player_id)
                            value_str = row.get("value", "0")
                            value = self.parse_market_value(value_str)
                            if value > 0:
                                market_values[player_id] = value
                        except ValueError:
                            continue

            print(f"  ✓ 加载了 {len(market_values)} 条市场价值记录")

        return market_values

    def load_player_stats(self):
        print("\n加载球员统计数据...")

        stats = {}

        if self.player_performances_file.exists():
            with open(self.player_performances_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                next(reader)

                for row in reader:
                    player_id = row.get("player_id", "")
                    if player_id:
                        try:
                            player_id = int(player_id)

                            if player_id not in stats:
                                stats[player_id] = {
                                    "goals": 0,
                                    "assists": 0,
                                    "yellow_cards": 0,
                                    "red_cards": 0,
                                    "minutes_played": 0,
                                    "appearances": 0,
                                }

                            try:
                                stats[player_id]["goals"] += int(row.get("goals", 0) or 0)
                            except ValueError:
                                pass

                            try:
                                stats[player_id]["assists"] += int(row.get("assists", 0) or 0)
                            except ValueError:
                                pass

                            try:
                                stats[player_id]["yellow_cards"] += int(
                                    row.get("yellow_cards", 0) or 0
                                )
                            except ValueError:
                                pass

                            try:
                                red_cards = int(row.get("direct_red_cards", 0) or 0) + int(
                                    row.get("second_yellow_cards", 0) or 0
                                )
                                stats[player_id]["red_cards"] += red_cards
                            except ValueError:
                                pass

                            try:
                                stats[player_id]["minutes_played"] += int(
                                    row.get("minutes_played", 0) or 0
                                )
                            except ValueError:
                                pass

                            try:
                                stats[player_id]["appearances"] += int(
                                    row.get("nb_on_pitch", 0) or 0
                                )
                            except ValueError:
                                pass

                        except ValueError:
                            continue

            print(f"  ✓ 加载了 {len(stats)} 名球员的统计数据")

        return stats

    def import_clubs(self):
        print("\n=== 导入俱乐部数据 ===")

        if not self.team_details_file.exists():
            print(f"✗ 文件不存在: {self.team_details_file}")
            return False

        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            count = 0
            with open(self.team_details_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    club_id = row.get("club_id", "")

                    if not club_id or club_id == "":
                        continue

                    try:
                        club_id = int(club_id)
                        club_name = row.get("club_name", "")

                        values = (
                            club_id,
                            club_name[:100],
                            club_name[:20],
                            "Unknown",
                            1900,
                            row.get("country_name", "")[:100],
                            club_name[:100] + " Stadium",
                            20000,
                            50,
                            "World Class",
                            "#FF0000",
                            "#FFFFFF",
                            None,
                            50000000,
                            20000000,
                            1000000,
                            500000,
                            100,
                            25000,
                            500000,
                            10,
                            "Unknown",
                            5,
                            True,
                            "Win" + " " + "the" + " " + "league",
                            0,
                            0,
                            0,
                            0,
                            0,
                            0,
                            None,
                        )

                        cursor.execute(
                            "INSERT OR REPLACE INTO clubs (id, name, short_name, city, founded_year, country, stadium_name, stadium_capacity, reputation, reputation_level, primary_color, secondary_color, league_id, balance, transfer_budget, wage_budget, weekly_wage_bill, ticket_price, average_attendance, commercial_income, youth_facility_level, youth_academy_country, training_facility_level, is_ai_controlled, season_objective, matches_played, matches_won, matches_drawn, matches_lost, goals_for, goals_against, points, league_position) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            values,
                        )

                        count += 1
                        if count % 100 == 0:
                            conn.commit()
                            print(f"  已导入 {count} 家俱乐部...")

                    except ValueError as e:
                        continue

            conn.commit()
            print(f"✓ 成功导入 {count} 家俱乐部")
            return True

        except Exception as e:
            print(f"✗ 导入失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def import_players(self):
        print("\n=== 导入球员数据 ===")

        if not self.player_profiles_file.exists():
            print(f"✗ 文件不存在: {self.player_profiles_file}")
            return False

        market_values = self.load_market_values()
        player_stats = self.load_player_stats()

        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            count = 0
            with open(self.player_profiles_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    player_id = row.get("player_id", "")

                    if not player_id or player_id == "":
                        continue

                    try:
                        player_id = int(player_id)

                        full_name = row.get("player_name", "")
                        names = self.parse_name(full_name)

                        position = self.map_position(
                            row.get("main_position", row.get("position", ""))
                        )
                        birth_date = self.parse_date(row.get("date_of_birth"))

                        current_club_id = row.get("current_club_id", "")
                        if current_club_id and current_club_id != "":
                            try:
                                current_club_id = int(current_club_id)
                            except ValueError:
                                current_club_id = None
                        else:
                            current_club_id = None

                        contract_until = self.parse_date(row.get("contract_expires"))

                        market_value = market_values.get(player_id, 1000000)
                        stats = player_stats.get(player_id, {})

                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO players (
                                id, first_name, last_name, birth_date, nationality, position,
                                height, weight, preferred_foot,
                                pace, acceleration, stamina, strength,
                                shooting, passing, dribbling, crossing, first_touch,
                                tackling, marking, positioning, vision, decisions,
                                reflexes, handling, kicking, one_on_one,
                                work_rate, determination, leadership, teamwork, aggression,
                                current_ability, potential_ability,
                                club_id, contract_until, salary, market_value, release_clause,
                                fitness, morale, form,
                                appearances, goals, assists, yellow_cards, red_cards, minutes_played,
                                career_goals, career_appearances
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                player_id,
                                names["first_name"],
                                names["last_name"],
                                birth_date,
                                row.get("country_of_birth", "")[:100],
                                position,
                                self.parse_height(row.get("height")),
                                70,
                                row.get("foot", "Right")[:5],
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                60,
                                40,
                                40,
                                40,
                                40,
                                40,
                                "MEDIUM",
                                60,
                                60,
                                60,
                                60,
                                60,
                                self.estimate_ability(market_value),
                                75,
                                current_club_id,
                                contract_until,
                                10000,
                                market_value,
                                int(market_value * 1.5),
                                100,
                                80,
                                75,
                                stats.get("appearances", 0),
                                stats.get("goals", 0),
                                stats.get("assists", 0),
                                stats.get("yellow_cards", 0),
                                stats.get("red_cards", 0),
                                stats.get("minutes_played", 0),
                                stats.get("goals", 0),
                                stats.get("appearances", 0),
                            ),
                        )

                        count += 1
                        if count % 100 == 0:
                            conn.commit()
                            print(f"  已导入 {count} 名球员...")

                    except ValueError as e:
                        continue

            conn.commit()
            print(f"✓ 成功导入 {count} 名球员")
            return True

        except Exception as e:
            print(f"✗ 导入失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def parse_name(self, full_name):
        parts = full_name.split(" ", 1)
        if len(parts) == 2:
            return {"first_name": parts[0], "last_name": parts[1]}
        return {"first_name": full_name, "last_name": ""}

    def parse_height(self, height_str):
        try:
            if height_str:
                height_cm = float(height_str.replace("m", "").replace(",", ".").strip())
                return int(height_cm * 100) if height_cm < 3 else int(height_cm)
        except:
            pass
        return 175

    def parse_date(self, date_str):
        try:
            if date_str and date_str != "":
                for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%Y/%m/%d"]:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        return date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
        except Exception:
            pass
        return None

    def parse_market_value(self, value_str):
        try:
            value = float(value_str)
            return int(value)
        except:
            return 1000000

    def map_position(self, position):
        if not position:
            return "CM"

        position = position.upper()

        position_map = {
            "GK": "GK",
            "GOALKEEPER": "GK",
            "CB": "CB",
            "CENTRE-BACK": "CB",
            "CENTER-BACK": "CB",
            "RB": "RB",
            "RIGHT-BACK": "RB",
            "LB": "LB",
            "LEFT-BACK": "LB",
            "CDM": "CDM",
            "DEFENSIVE-MIDFIELD": "CDM",
            "CM": "CM",
            "CENTRAL-MIDFIELD": "CM",
            "CAM": "CAM",
            "ATTACKING-MIDFIELD": "CAM",
            "RM": "RM",
            "RIGHT-MIDFIELD": "RM",
            "LM": "LM",
            "LEFT-MIDFIELD": "LM",
            "RW": "RW",
            "RIGHT-WINGER": "RW",
            "LW": "LW",
            "LEFT-WINGER": "LW",
            "CF": "CF",
            "CENTRE-FORWARD": "CF",
            "ST": "ST",
            "STRIKER": "ST",
            "AM": "CAM",
        }

        for key, value in position_map.items():
            if key in position:
                return value

        return "CM"

    def estimate_ability(self, market_value):
        if market_value < 100000:
            return 50
        elif market_value < 500000:
            return 55
        elif market_value < 1000000:
            return 60
        elif market_value < 5000000:
            return 65
        elif market_value < 10000000:
            return 70
        elif market_value < 20000000:
            return 75
        elif market_value < 40000000:
            return 80
        elif market_value < 70000000:
            return 85
        elif market_value < 100000000:
            return 90
        else:
            return 95

    def show_menu(self):
        print("\n" + "=" * 50)
        print("    Transfermarkt 数据转换器")
        print("=" * 50)
        print(f"数据源: {self.data_dir.absolute()}")
        print(f"数据库: {self.db_path}")
        print("\n选项:")
        print("1. 导入俱乐部数据")
        print("2. 导入球员数据")
        print("3. 导入所有数据")
        print("0. 退出")
        print("=" * 50)

        choice = input("\n请选择 (0-3): ").strip()

        if choice == "1":
            self.import_clubs()
        elif choice == "2":
            self.import_players()
        elif choice == "3":
            self.import_clubs()
            self.import_players()
        elif choice == "0":
            print("退出")
            return False
        else:
            print("无效选择")

        return True

    def run(self):
        print("\n🔄 Transfermarkt 数据转换器")
        print("将真实世界足球数据转换为 FM Manager 格式\n")

        if not self.data_dir.exists():
            print(f"✗ 数据目录不存在: {self.data_dir}")
            print("请先下载数据集到该目录")
            return

        if not Path(self.db_path).exists():
            print(f"✗ 数据库不存在: {self.db_path}")
            print("请先运行 init_db.py 创建数据库")
            return

        while True:
            if not self.show_menu():
                break


if __name__ == "__main__":
    import sys

    converter = TransfermarktConverter()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--clubs":
            converter.import_clubs()
        elif command == "--players":
            converter.import_players()
        elif command == "--all":
            converter.import_clubs()
            converter.import_players()
        elif command == "--help" or command == "-h":
            print("Transfermarkt 数据转换器")
            print("\n用法:")
            print("  python transfermarkt_converter.py              # 交互式菜单")
            print("  python transfermarkt_converter.py --clubs     # 导入俱乐部")
            print("  python transfermarkt_converter.py --players    # 导入球员")
            print("  python transfermarkt_converter.py --all       # 导入所有")
        else:
            print(f"未知命令: {command}")
            print("使用 --help 查看帮助")
    else:
        converter.run()
