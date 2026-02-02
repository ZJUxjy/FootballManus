#!/usr/bin/env python3

import sqlite3
import csv
import json
from pathlib import Path
from typing import List, Dict
import re


class FootballDataConverter:
    def __init__(self, data_dir="data", db_path="fm_manager.db"):
        self.data_dir = Path(data_dir)
        self.db_path = db_path

    def connect_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def import_transfermarkt_players(self):
        print("\n=== 导入 Transfermarkt 球员数据 ===")

        csv_file = self.data_dir / "transfermarkt_players.csv"

        if not csv_file.exists():
            print(f"✗ 文件不存在: {csv_file}")
            print("请先运行 download_football_data.py 下载数据")
            return False

        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            count = 0
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    player_id = row.get("player_id") or count + 1
                    first_name = row.get("name", "").split(" ")[0]
                    last_name = " ".join(row.get("name", "").split(" ")[1:]) or row.get("name", "")

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO players (
                            id, first_name, last_name, nationality, position,
                            height, weight, market_value, current_ability, potential_ability,
                            appearances, goals, assists, yellow_cards, red_cards,
                            minutes_played, career_goals, career_appearances,
                            preferred_foot, pace, shooting, passing, dribbling,
                            tackling, marking, reflexes, handling, work_rate,
                            determination, leadership, teamwork, aggression
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            player_id,
                            first_name,
                            last_name,
                            row.get("nationality", ""),
                            self.map_position(row.get("position", "")),
                            int(row.get("height_in_cm") or 170),
                            int(row.get("weight_in_kg") or 70),
                            self.parse_market_value(row.get("market_value_in_eur", "0")),
                            60,
                            75,
                            int(row.get("appearance") or 0),
                            int(row.get("goals") or 0),
                            int(row.get("assists") or 0),
                            int(row.get("yellow_cards") or 0),
                            int(row.get("red_cards") or 0),
                            int(row.get("minutes_played") or 0),
                            int(row.get("goals") or 0),
                            int(row.get("appearance") or 0),
                            "RIGHT",
                            60,
                            60,
                            60,
                            60,
                            50,
                            50,
                            40,
                            40,
                            "MEDIUM",
                            50,
                            50,
                            50,
                            50,
                        ),
                    )

                    count += 1
                    if count % 100 == 0:
                        conn.commit()
                        print(f"已导入 {count} 条记录...")

            conn.commit()
            print(f"✓ 成功导入 {count} 名球员")
            return True

        except Exception as e:
            print(f"✗ 导入失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def import_transfermarkt_clubs(self):
        print("\n=== 导入 Transfermarkt 俱乐部数据 ===")

        csv_file = self.data_dir / "transfermarkt_clubs.csv"

        if not csv_file.exists():
            print(f"✗ 文件不存在: {csv_file}")
            return False

        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            count = 0
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    club_id = row.get("club_id") or count + 1

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO clubs (
                            id, name, league, country, stadium,
                            founded, budget, reputation
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            club_id,
                            row.get("name", ""),
                            row.get("domestic_competition_id", ""),
                            row.get("country", ""),
                            "",
                            1900,
                            50000000,
                            50,
                        ),
                    )

                    count += 1

            conn.commit()
            print(f"✓ 成功导入 {count} 家俱乐部")
            return True

        except Exception as e:
            print(f"✗ 导入失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def import_kaggle_fc_players(self, csv_file="male_players.csv"):
        print(f"\n=== 导入 Kaggle FC 球员数据 ({csv_file}) ===")

        csv_path = self.data_dir / csv_file

        if not csv_path.exists():
            print(f"✗ 文件不存在: {csv_path}")
            print("请从 Kaggle 下载 EA Sports FC 数据集并放到 data/ 文件夹")
            return False

        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            count = 0
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    player_id = row.get("player_id") or count + 1

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO players (
                            id, first_name, last_name, nationality, position,
                            height, weight, preferred_foot,
                            pace, shooting, passing, dribbling, defending, physicality,
                            current_ability, potential_ability,
                            market_value, appearances, goals, assists,
                            yellow_cards, red_cards, minutes_played,
                            work_rate, determination, leadership, teamwork, aggression
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            player_id,
                            row.get("short_name", "").split(" ")[0],
                            " ".join(row.get("short_name", "").split(" ")[1:])
                            or row.get("short_name", ""),
                            row.get("nationality_name", ""),
                            self.map_position(row.get("club_position", "")),
                            int(row.get("height_cm") or 175),
                            int(row.get("weight_kg") or 72),
                            row.get("preferred_foot", "Right"),
                            int(row.get("pace") or 60),
                            int(row.get("shooting") or 60),
                            int(row.get("passing") or 60),
                            int(row.get("dribbling") or 60),
                            int(row.get("defending") or 60),
                            int(row.get("physicality") or 60),
                            int(row.get("overall") or 65),
                            int(row.get("potential") or 75),
                            self.parse_euro_value(row.get("value_eur", "0")),
                            int(row.get("club_jersey_number") or 0),
                            0,
                            0,
                            0,
                            0,
                            0,
                            row.get("work_rate", "Medium"),
                            50,
                            50,
                            50,
                            50,
                        ),
                    )

                    count += 1
                    if count % 100 == 0:
                        conn.commit()
                        print(f"已导入 {count} 条记录...")

            conn.commit()
            print(f"✓ 成功导入 {count} 名球员")
            return True

        except Exception as e:
            print(f"✗ 导入失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def map_position(self, position):
        position_mapping = {
            "GK": "GK",
            "Goalkeeper": "GK",
            "CB": "CB",
            "RB": "RB",
            "LB": "LB",
            "RWB": "RWB",
            "LWB": "LWB",
            "Centre-Back": "CB",
            "Right-Back": "RB",
            "Left-Back": "LB",
            "CDM": "CDM",
            "CM": "CM",
            "CAM": "CAM",
            "RM": "RM",
            "LM": "LM",
            "Central Midfield": "CM",
            "Defensive Midfield": "CDM",
            "Attacking Midfield": "CAM",
            "Right Midfield": "RM",
            "Left Midfield": "LM",
            "CF": "CF",
            "ST": "ST",
            "RW": "RW",
            "LW": "LW",
            "Centre-Forward": "CF",
            "Striker": "ST",
            "Right Winger": "RW",
            "Left Winger": "LW",
        }
        return position_mapping.get(position, position[:3].upper() if len(position) >= 3 else "CM")

    def parse_market_value(self, value_str):
        if not value_str or value_str == "0":
            return 0

        value_str = value_str.replace("€", "").replace(",", "").strip()

        if "Th" in value_str:
            return int(float(value_str.replace("Th.", "")) * 1000)
        elif "m" in value_str:
            return int(float(value_str.replace("m", "")) * 1000000)
        elif "bn" in value_str:
            return int(float(value_str.replace("bn", "")) * 1000000000)

        return int(float(value_str))

    def parse_euro_value(self, value_str):
        try:
            return int(float(value_str))
        except:
            return 0

    def show_menu(self):
        print("\n" + "=" * 50)
        print("    足球数据导入器 - 选择数据源")
        print("=" * 50)
        print("1. Transfermarkt 球员数据 (transfermarkt_players.csv)")
        print("2. Transfermarkt 俱乐部数据 (transfermarkt_clubs.csv)")
        print("3. Kaggle FC 球员数据 (male_players.csv)")
        print("4. 导入所有 Transfermarkt 数据")
        print("0. 退出")
        print("=" * 50)

        choice = input("\n请选择 (0-4): ").strip()

        if choice == "1":
            self.import_transfermarkt_players()
        elif choice == "2":
            self.import_transfermarkt_clubs()
        elif choice == "3":
            self.import_kaggle_fc_players()
        elif choice == "4":
            self.import_transfermarkt_clubs()
            self.import_transfermarkt_players()
        elif choice == "0":
            print("退出")
            return False
        else:
            print("无效选择")

        return True

    def run(self):
        print("\n🔄 足球数据导入器")
        print(f"数据库: {self.db_path}")
        print(f"数据目录: {self.data_dir.absolute()}")

        if not Path(self.db_path).exists():
            print(f"\n✗ 数据库不存在: {self.db_path}")
            print("请先运行 python init_db.py 创建数据库")
            return

        while True:
            if not self.show_menu():
                break


if __name__ == "__main__":
    converter = FootballDataConverter()
    converter.run()
