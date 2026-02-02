#!/usr/bin/env python3
"""
从 Transfermarkt 数据集导入数据到新数据库
生成新数据库：fm_manager_transfermarkt.db
"""

import sqlite3
import csv
from pathlib import Path
from collections import defaultdict
import random


class TransfermarktImporter:
    def __init__(self, project_root=None, data_dir="data/data/football-datasets", db_path="fm_manager_transfermarkt.db"):
        # 获取项目根目录
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        self.data_dir = self.project_root / data_dir
        self.db_path = self.project_root / db_path
        self.player_stats = defaultdict(lambda: {
            'goals': 0,
            'assists': 0,
            'yellow_cards': 0,
            'red_cards': 0,
            'minutes_played': 0,
            'appearances': 0
        })
        self.player_market_values = {}

    def create_database(self):
        """创建数据库和表结构"""
        print("\n=== 创建数据库 ===")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建联赛表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                short_name TEXT NOT NULL,
                country TEXT NOT NULL,
                tier INTEGER NOT NULL,
                teams_count INTEGER NOT NULL
            )
        """)

        # 创建俱乐部表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                short_name TEXT,
                city TEXT,
                country TEXT,
                stadium_name TEXT,
                stadium_capacity INTEGER,
                founded_year INTEGER,
                reputation INTEGER DEFAULT 5000,
                balance INTEGER DEFAULT 50000000,
                transfer_budget INTEGER DEFAULT 20000000,
                wage_budget INTEGER DEFAULT 1000000,
                league_id INTEGER,
                is_ai_controlled BOOLEAN DEFAULT 1
            )
        """)

        # 创建球员表（简化版，基于ARCHITECTURE.md）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                age INTEGER,
                nationality TEXT,
                position TEXT,
                height INTEGER,
                weight INTEGER DEFAULT 70,
                preferred_foot TEXT DEFAULT 'RIGHT',

                -- 技术属性（基于位置和市场价值估算）
                pace INTEGER DEFAULT 60,
                shooting INTEGER DEFAULT 60,
                passing INTEGER DEFAULT 60,
                dribbling INTEGER DEFAULT 60,
                defending INTEGER DEFAULT 60,
                physical INTEGER DEFAULT 60,

                -- 精神属性
                mentality INTEGER DEFAULT 60,
                work_rate TEXT DEFAULT 'MEDIUM',

                -- 能力值
                current_ability INTEGER DEFAULT 60,
                potential_ability INTEGER DEFAULT 70,

                -- 合同
                club_id INTEGER,
                contract_until TEXT,
                salary INTEGER DEFAULT 50000,
                market_value INTEGER DEFAULT 0,

                -- 统计数据（职业生涯）
                career_goals INTEGER DEFAULT 0,
                career_assists INTEGER DEFAULT 0,
                career_appearances INTEGER DEFAULT 0,

                -- 状态
                fitness INTEGER DEFAULT 100,
                morale INTEGER DEFAULT 80,
                form INTEGER DEFAULT 75,

                FOREIGN KEY (club_id) REFERENCES clubs(id)
            )
        """)

        conn.commit()
        conn.close()
        print(f"✓ 数据库创建成功: {self.db_path}")

    def load_player_performances(self):
        """加载球员表现统计数据"""
        print("\n=== 加载球员表现数据 ===")

        csv_file = self.data_dir / "player_performances" / "player_performances.csv"

        if not csv_file.exists():
            print(f"✗ 文件不存在: {csv_file}")
            return False

        count = 0
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                player_id = row.get("player_id")
                if not player_id:
                    continue

                def safe_int(value, default=0):
                    """安全转换为整数，处理浮点数字符串"""
                    try:
                        return int(float(value)) if value else default
                    except (ValueError, TypeError):
                        return default

                stats = self.player_stats[player_id]
                stats['goals'] += safe_int(row.get("goals"))
                stats['assists'] += safe_int(row.get("assists"))
                stats['yellow_cards'] += safe_int(row.get("yellow_cards"))
                stats['red_cards'] += safe_int(row.get("direct_red_cards")) + safe_int(row.get("second_yellow_cards"))
                stats['minutes_played'] += safe_int(row.get("minutes_played"))
                stats['appearances'] += safe_int(row.get("nb_on_pitch"))

                count += 1
                if count % 100000 == 0:
                    print(f"  已处理 {count:,} 条表现记录...")

        print(f"✓ 已加载 {len(self.player_stats):,} 名球员的统计数据")
        return True

    def load_market_values(self):
        """加载球员市场价值"""
        print("\n=== 加载市场价值数据 ===")

        # 优先使用最新的市场价值
        csv_file = self.data_dir / "player_latest_market_value" / "player_latest_market_value.csv"

        if not csv_file.exists():
            print(f"✗ 文件不存在: {csv_file}")
            return False

        count = 0
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                player_id = row.get("player_id")
                value = row.get("value")
                if player_id and value:
                    try:
                        self.player_market_values[player_id] = int(float(value))
                        count += 1
                    except ValueError:
                        continue

        print(f"✓ 已加载 {count:,} 名球员的市场价值")
        return True

    def estimate_ability_from_value(self, market_value):
        """根据市场价值估算能力值"""
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

    def estimate_attributes_by_position(self, position, base_ability):
        """根据位置估算技术属性"""
        pos = position.upper() if position else "CM"

        # 默认值
        attrs = {
            'pace': base_ability,
            'shooting': base_ability,
            'passing': base_ability,
            'dribbling': base_ability,
            'defending': base_ability,
            'physical': base_ability
        }

        # 根据位置调整
        if 'GK' in pos:
            attrs['defending'] = min(base_ability + 15, 99)
            attrs['physical'] = min(base_ability + 10, 99)
            attrs['passing'] = max(base_ability - 10, 40)
            attrs['pace'] = max(base_ability - 5, 40)
        elif 'CB' in pos or 'RB' in pos or 'LB' in pos or 'RWB' in pos or 'LWB' in pos:
            attrs['defending'] = min(base_ability + 10, 99)
            attrs['physical'] = min(base_ability + 5, 99)
            attrs['passing'] = base_ability
            attrs['pace'] = base_ability + 2
        elif 'CDM' in pos or 'CM' in pos:
            attrs['passing'] = min(base_ability + 8, 99)
            attrs['defending'] = base_ability + 5
            attrs['dribbling'] = base_ability
            attrs['pace'] = base_ability
        elif 'CAM' in pos or 'RM' in pos or 'LM' in pos:
            attrs['passing'] = min(base_ability + 10, 99)
            attrs['dribbling'] = min(base_ability + 8, 99)
            attrs['pace'] = base_ability + 5
            attrs['shooting'] = base_ability
            attrs['defending'] = max(base_ability - 10, 40)
        elif 'RW' in pos or 'LW' in pos or 'ST' in pos or 'CF' in pos:
            attrs['pace'] = min(base_ability + 8, 99)
            attrs['shooting'] = min(base_ability + 10, 99)
            attrs['dribbling'] = min(base_ability + 8, 99)
            attrs['passing'] = base_ability
            attrs['defending'] = max(base_ability - 15, 30)

        # 添加随机变化
        for key in attrs:
            attrs[key] = max(40, min(99, attrs[key] + random.randint(-5, 5)))

        return attrs

    def map_position(self, position):
        """映射位置到标准格式"""
        if not position:
            return "CM"

        position_mapping = {
            "GK": "GK",
            "Goalkeeper": "GK",
            "CB": "CB",
            "Centre-Back": "CB",
            "RB": "RB",
            "Right-Back": "RB",
            "LB": "LB",
            "Left-Back": "LB",
            "RWB": "RWB",
            "LWB": "LWB",
            "CDM": "CDM",
            "Defensive Midfield": "CDM",
            "CM": "CM",
            "Central Midfield": "CM",
            "CAM": "CAM",
            "Attacking Midfield": "CAM",
            "RM": "RM",
            "LM": "LM",
            "RW": "RW",
            "LW": "LW",
            "CF": "CF",
            "ST": "ST",
            "Striker": "ST",
        }

        # 尝试精确匹配
        if position in position_mapping:
            return position_mapping[position]

        # 尝试部分匹配
        for key, value in position_mapping.items():
            if key.lower() in position.lower():
                return value

        # 默认
        return position[:3].upper() if len(position) >= 3 else "CM"

    def import_clubs(self):
        """导入俱乐部数据"""
        print("\n=== 导入俱乐部数据 ===")

        csv_file = self.data_dir / "team_details" / "team_details.csv"

        if not csv_file.exists():
            print(f"✗ 文件不存在: {csv_file}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            count = 0
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    club_id = row.get("club_id")
                    if not club_id:
                        continue

                    try:
                        club_id = int(club_id)
                        club_name = row.get("club_name", "")
                        country = row.get("country_name", "")

                        cursor.execute("""
                            INSERT OR REPLACE INTO clubs (
                                id, name, short_name, city, country,
                                stadium_name, stadium_capacity, founded_year,
                                reputation, balance, transfer_budget, wage_budget,
                                is_ai_controlled
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            club_id,
                            club_name[:100],
                            club_name[:20] if len(club_name) > 20 else club_name,
                            "Unknown",
                            country[:100],
                            f"{club_name[:50]} Stadium",
                            20000,
                            1900,
                            5000,
                            50000000,
                            20000000,
                            1000000,
                            1
                        ))

                        count += 1
                        if count % 100 == 0:
                            conn.commit()
                            print(f"  已导入 {count} 家俱乐部...")

                    except ValueError:
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

    def import_players(self, limit=None):
        """导入球员数据"""
        print("\n=== 导入球员数据 ===")

        csv_file = self.data_dir / "player_profiles" / "player_profiles.csv"

        if not csv_file.exists():
            print(f"✗ 文件不存在: {csv_file}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            count = 0
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    if limit and count >= limit:
                        break

                    player_id = row.get("player_id")
                    if not player_id:
                        continue

                    try:
                        player_id = int(player_id)
                        player_name = row.get("player_name", "")

                        # 分离姓名
                        name_parts = player_name.split(" ", 1)
                        first_name = name_parts[0]
                        last_name = name_parts[1] if len(name_parts) > 1 else ""

                        # 基本信息
                        position = self.map_position(row.get("position", ""))
                        height = row.get("height")
                        height_cm = int(float(height)) if height and height != "0.0" else 175

                        # 市场价值
                        market_value = self.player_market_values.get(str(player_id), 0)

                        # 根据市场价值估算能力
                        current_ability = self.estimate_ability_from_value(market_value)
                        potential_ability = min(current_ability + random.randint(5, 15), 99)

                        # 根据位置估算技术属性
                        attrs = self.estimate_attributes_by_position(position, current_ability)

                        # 统计数据
                        stats = self.player_stats.get(str(player_id), {})

                        cursor.execute("""
                            INSERT OR REPLACE INTO players (
                                id, name, first_name, last_name, nationality, position,
                                height, weight, preferred_foot,
                                pace, shooting, passing, dribbling, defending, physical,
                                current_ability, potential_ability,
                                club_id, contract_until, market_value,
                                career_goals, career_assists, career_appearances
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            player_id,
                            player_name[:100],
                            first_name[:50],
                            last_name[:50],
                            row.get("country_of_birth", "")[:100],
                            position,
                            height_cm,
                            70,  # 默认体重
                            row.get("foot", "RIGHT")[:10] or "RIGHT",
                            attrs['pace'],
                            attrs['shooting'],
                            attrs['passing'],
                            attrs['dribbling'],
                            attrs['defending'],
                            attrs['physical'],
                            current_ability,
                            potential_ability,
                            row.get("current_club_id") or None,
                            row.get("contract_expires") or None,
                            market_value,
                            stats.get('goals', 0),
                            stats.get('assists', 0),
                            stats.get('appearances', 0)
                        ))

                        count += 1
                        if count % 1000 == 0:
                            conn.commit()
                            print(f"  已导入 {count:,} 名球员...")

                    except (ValueError, KeyError) as e:
                        continue

            conn.commit()
            print(f"✓ 成功导入 {count:,} 名球员")
            return True

        except Exception as e:
            print(f"✗ 导入失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def show_summary(self):
        """显示数据库摘要"""
        print("\n=== 数据库摘要 ===")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 统计俱乐部
        cursor.execute("SELECT COUNT(*) FROM clubs")
        clubs_count = cursor.fetchone()[0]

        # 统计球员
        cursor.execute("SELECT COUNT(*) FROM players")
        players_count = cursor.fetchone()[0]

        # 有俱乐部的球员
        cursor.execute("SELECT COUNT(*) FROM players WHERE club_id IS NOT NULL")
        players_with_club = cursor.fetchone()[0]

        # 市场价值统计
        cursor.execute("SELECT AVG(market_value), MAX(market_value) FROM players WHERE market_value > 0")
        avg_value, max_value = cursor.fetchone()

        conn.close()

        print(f"俱乐部总数: {clubs_count:,}")
        print(f"球员总数: {players_count:,}")
        print(f"有俱乐部的球员: {players_with_club:,}")
        print(f"平均市场价值: €{avg_value:,.0f}" if avg_value else "平均市场价值: N/A")
        print(f"最高市场价值: €{max_value:,.0f}" if max_value else "最高市场价值: N/A")

    def run(self, players_limit=None):
        """执行完整的导入流程"""
        print("\n" + "=" * 60)
        print("    Transfermarkt 数据导入器")
        print("=" * 60)
        print(f"数据目录: {self.data_dir.absolute()}")
        print(f"数据库文件: {self.db_path}")

        if players_limit:
            print(f"球员导入限制: {players_limit:,}")

        # 创建数据库
        self.create_database()

        # 加载统计数据
        self.load_player_performances()

        # 加载市场价值
        self.load_market_values()

        # 导入俱乐部
        if not self.import_clubs():
            print("\n✗ 俱乐部导入失败，终止")
            return

        # 导入球员
        if not self.import_players(limit=players_limit):
            print("\n✗ 球员导入失败")
            return

        # 显示摘要
        self.show_summary()

        print("\n✅ 导入完成！")
        print(f"数据库位置: {self.db_path.absolute()}")


if __name__ == "__main__":
    import sys

    # 可以通过命令行参数限制导入的球员数量（用于测试）
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"测试模式：仅导入前 {limit:,} 名球员")
        except ValueError:
            pass

    importer = TransfermarktImporter()
    importer.run(players_limit=limit)
