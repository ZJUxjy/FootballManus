#!/usr/bin/env python3
"""
导入 Football Manager 中文导出数据 (players.csv, teams.csv)
处理重名球队（通过联赛区分）
"""

import sqlite3
import csv
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class FMChineseDataImporter:
    def __init__(self, data_dir=".", db_path="fm_manager.db"):
        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path)
        self.players_file = self.data_dir / "players.csv"
        self.teams_file = self.data_dir / "teams.csv"
        
        # 联赛映射缓存
        self.league_cache = {}
        # 球队映射缓存：key = (联赛名, 球队名), value = club_id
        self.club_cache = {}
        # 球队ID计数器
        self.next_club_id = 1
        self.next_league_id = 1

    def connect_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_leagues_table(self):
        """创建联赛表（如果不存在）"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                tier INTEGER DEFAULT 1,
                UNIQUE(name, country)
            )
        """)
        
        conn.commit()
        conn.close()
        
    def load_existing_data(self):
        """加载已存在的联赛和球队数据"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # 加载现有联赛
        try:
            cursor.execute("SELECT id, name, country FROM leagues")
            for row in cursor.fetchall():
                self.league_cache[(row['name'], row['country'])] = row['id']
                self.next_league_id = max(self.next_league_id, row['id'] + 1)
        except sqlite3.OperationalError:
            pass
        
        # 加载现有球队
        cursor.execute("SELECT id, name, country, league_id FROM clubs")
        for row in cursor.fetchall():
            # 使用 (联赛ID, 球队名) 作为唯一键
            league_key = row['league_id'] if row['league_id'] else 0
            self.club_cache[(league_key, row['name'])] = row['id']
            self.next_club_id = max(self.next_club_id, row['id'] + 1)
            
        conn.close()
        print(f"已加载 {len(self.league_cache)} 个联赛, {len(self.club_cache)} 个球队")

    def parse_percentage(self, value_str):
        """解析百分比字符串为整数"""
        if not value_str:
            return 50
        # 移除 % 和括号内容
        clean = value_str.replace('%', '').strip()
        # 处理 "48.4% (速度型前锋)" 格式
        clean = re.sub(r'\s*\([^)]*\)', '', clean)
        try:
            val = float(clean)
            return int(val)
        except (ValueError, TypeError):
            return 50

    def parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str or date_str == '-':
            return None
        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def parse_money(self, money_str):
        """解析金额字符串"""
        if not money_str or money_str == '-':
            return 0
        # 移除逗号、空格和货币符号
        clean = money_str.replace(',', '').replace(' ', '').replace('€', '').replace('$', '')
        try:
            # 处理 "1,000" 或 "1000"
            return int(float(clean))
        except (ValueError, TypeError):
            return 0

    def map_position(self, position_str):
        """将中文位置映射到标准位置代码"""
        if not position_str:
            return "CM"
        
        position_str = position_str.upper()
        
        # 中文位置映射
        mapping = {
            "门将": "GK", "守门员": "GK", "GK": "GK",
            "清道夫": "SW", "拖后": "SW", "SW": "SW",
            "左后卫": "DL", "左边卫": "DL", "DL": "DL",
            "中后卫": "DC", "中卫": "DC", "DC": "DC", "CB": "DC",
            "右后卫": "DR", "右边卫": "DR", "DR": "DR",
            "左翼卫": "WBL", "WBL": "WBL", "LWB": "WBL",
            "右翼卫": "WBR", "WBR": "WBR", "RWB": "WBR",
            "防守型中场": "DM", "后腰": "DM", "DM": "DM", "CDM": "DM",
            "左中场": "ML", "左边锋": "ML", "ML": "ML", "LM": "ML",
            "中前卫": "MC", "中场": "MC", "MC": "MC", "CM": "MC",
            "右中场": "MR", "右边锋": "MR", "MR": "MR", "RM": "MR",
            "左攻击型中场": "AML", "左前腰": "AML", "AML": "AML", "LW": "AML",
            "攻击型中场": "AMC", "前腰": "AMC", "AMC": "AMC", "CAM": "AMC",
            "右攻击型中场": "AMR", "右前腰": "AMR", "AMR": "AMR", "RW": "AMR",
            "影锋": "FS", "二前锋": "FS", "FS": "FS", "CF": "FS",
            "前锋": "ST", "中锋": "ST", "TS": "ST", "ST": "ST",
        }
        
        # 尝试部分匹配
        for key, value in mapping.items():
            if key in position_str:
                return value
        
        return "CM"

    def get_best_position(self, row):
        """根据各位置评分确定最佳位置"""
        positions = {
            'GK': self.parse_percentage(row.get('GK 评分', '0')),
            'SW': self.parse_percentage(row.get('SW 评分', '0')),
            'DL': self.parse_percentage(row.get('DL 评分', '0')),
            'DC': self.parse_percentage(row.get('DC 评分', '0')),
            'DR': self.parse_percentage(row.get('DR 评分', '0')),
            'WBL': self.parse_percentage(row.get('WBL 评分', '0')),
            'WBR': self.parse_percentage(row.get('WBR 评分', '0')),
            'DM': self.parse_percentage(row.get('DM 评分', '0')),
            'ML': self.parse_percentage(row.get('ML 评分', '0')),
            'MC': self.parse_percentage(row.get('MC 评分', '0')),
            'MR': self.parse_percentage(row.get('MR 评分', '0')),
            'AML': self.parse_percentage(row.get('AML 评分', '0')),
            'AMC': self.parse_percentage(row.get('AMC 评分', '0')),
            'AMR': self.parse_percentage(row.get('AMR 评分', '0')),
            'FS': self.parse_percentage(row.get('FS 评分', '0')),
            'ST': self.parse_percentage(row.get('TS 评分', '0')),
        }
        
        # 找到评分最高的位置
        best_pos = max(positions, key=positions.get)
        return best_pos, positions[best_pos]

    def get_best_potential_position(self, row):
        """根据各位置潜力评分确定最佳潜力位置"""
        positions = {
            'GK': self.parse_percentage(row.get('GK 潜力评分', '0')),
            'SW': self.parse_percentage(row.get('SW 潜力评分', '0')),
            'DL': self.parse_percentage(row.get('DL 潜力评分', '0')),
            'DC': self.parse_percentage(row.get('DC 潜力评分', '0')),
            'DR': self.parse_percentage(row.get('DR 潜力评分', '0')),
            'WBL': self.parse_percentage(row.get('WBL 潜力评分', '0')),
            'WBR': self.parse_percentage(row.get('WBR 潜力评分', '0')),
            'DM': self.parse_percentage(row.get('DM 潜力评分', '0')),
            'ML': self.parse_percentage(row.get('ML 潜力评分', '0')),
            'MC': self.parse_percentage(row.get('MC 潜力评分', '0')),
            'MR': self.parse_percentage(row.get('MR 潜力评分', '0')),
            'AML': self.parse_percentage(row.get('AML 潜力评分', '0')),
            'AMC': self.parse_percentage(row.get('AMC 潜力评分', '0')),
            'AMR': self.parse_percentage(row.get('AMR 潜力评分', '0')),
            'FS': self.parse_percentage(row.get('FS 潜力评分', '0')),
            'ST': self.parse_percentage(row.get('TS 潜力评分', '0')),
        }
        
        best_pos = max(positions, key=positions.get)
        return best_pos, positions[best_pos]

    def estimate_attributes(self, position, ability):
        """根据位置和能力估算各项属性"""
        base = ability
        
        # 位置属性权重
        if position == 'GK':
            return {
                'pace': base - 20, 'acceleration': base - 20, 'stamina': base - 10,
                'strength': base, 'shooting': base - 30, 'passing': base - 15,
                'dribbling': base - 25, 'crossing': base - 30, 'first_touch': base - 10,
                'tackling': base - 10, 'marking': base, 'positioning': base + 5,
                'vision': base - 15, 'decisions': base + 5,
                'reflexes': base + 15, 'handling': base + 15, 'kicking': base, 'one_on_one': base + 10,
                'determination': base, 'leadership': base, 'teamwork': base, 'aggression': base
            }
        elif position in ['CB', 'SW']:
            return {
                'pace': base - 10, 'acceleration': base - 10, 'stamina': base,
                'strength': base + 10, 'shooting': base - 15, 'passing': base - 5,
                'dribbling': base - 10, 'crossing': base - 10, 'first_touch': base,
                'tackling': base + 10, 'marking': base + 15, 'positioning': base + 10,
                'vision': base - 5, 'decisions': base + 5,
                'reflexes': 20, 'handling': 20, 'kicking': base - 10, 'one_on_one': base - 5,
                'determination': base, 'leadership': base + 5, 'teamwork': base + 5, 'aggression': base + 5
            }
        elif position in ['DL', 'DR', 'WBL', 'WBR']:
            return {
                'pace': base + 5, 'acceleration': base + 5, 'stamina': base + 5,
                'strength': base, 'shooting': base - 10, 'passing': base + 5,
                'dribbling': base + 5, 'crossing': base + 10, 'first_touch': base,
                'tackling': base + 5, 'marking': base + 5, 'positioning': base,
                'vision': base, 'decisions': base,
                'reflexes': 20, 'handling': 20, 'kicking': base, 'one_on_one': base - 10,
                'determination': base, 'leadership': base, 'teamwork': base, 'aggression': base
            }
        elif position == 'DM':
            return {
                'pace': base - 5, 'acceleration': base - 5, 'stamina': base + 5,
                'strength': base + 5, 'shooting': base - 5, 'passing': base + 10,
                'dribbling': base, 'crossing': base - 5, 'first_touch': base + 5,
                'tackling': base + 10, 'marking': base + 5, 'positioning': base + 10,
                'vision': base + 5, 'decisions': base + 10,
                'reflexes': 20, 'handling': 20, 'kicking': base, 'one_on_one': 30,
                'determination': base, 'leadership': base + 5, 'teamwork': base + 10, 'aggression': base + 5
            }
        elif position in ['ML', 'MR']:
            return {
                'pace': base + 10, 'acceleration': base + 10, 'stamina': base + 5,
                'strength': base - 5, 'shooting': base, 'passing': base + 5,
                'dribbling': base + 10, 'crossing': base + 15, 'first_touch': base + 5,
                'tackling': base - 5, 'marking': base - 10, 'positioning': base - 5,
                'vision': base, 'decisions': base,
                'reflexes': 20, 'handling': 20, 'kicking': base, 'one_on_one': 30,
                'determination': base, 'leadership': base, 'teamwork': base, 'aggression': base - 5
            }
        elif position == 'MC':
            return {
                'pace': base, 'acceleration': base, 'stamina': base + 5,
                'strength': base, 'shooting': base, 'passing': base + 15,
                'dribbling': base + 5, 'crossing': base, 'first_touch': base + 10,
                'tackling': base, 'marking': base - 5, 'positioning': base + 5,
                'vision': base + 10, 'decisions': base + 10,
                'reflexes': 20, 'handling': 20, 'kicking': base + 5, 'one_on_one': 30,
                'determination': base, 'leadership': base + 5, 'teamwork': base + 10, 'aggression': base
            }
        elif position in ['AML', 'AMR', 'AMC']:
            return {
                'pace': base + 5, 'acceleration': base + 10, 'stamina': base,
                'strength': base - 5, 'shooting': base + 10, 'passing': base + 10,
                'dribbling': base + 15, 'crossing': base + 5, 'first_touch': base + 10,
                'tackling': base - 10, 'marking': base - 15, 'positioning': base,
                'vision': base + 10, 'decisions': base + 5,
                'reflexes': 20, 'handling': 20, 'kicking': base, 'one_on_one': 40,
                'determination': base + 5, 'leadership': base, 'teamwork': base, 'aggression': base - 5
            }
        elif position in ['FS', 'ST']:
            return {
                'pace': base + 5, 'acceleration': base + 5, 'stamina': base,
                'strength': base + 5, 'shooting': base + 15, 'passing': base - 5,
                'dribbling': base + 5, 'crossing': base - 10, 'first_touch': base + 10,
                'tackling': base - 15, 'marking': base - 20, 'positioning': base + 15,
                'vision': base, 'decisions': base + 5,
                'reflexes': 20, 'handling': 20, 'kicking': base - 10, 'one_on_one': base + 10,
                'determination': base + 5, 'leadership': base, 'teamwork': base - 5, 'aggression': base + 5
            }
        
        return {k: base for k in ['pace', 'acceleration', 'stamina', 'strength', 'shooting', 
                                   'passing', 'dribbling', 'crossing', 'first_touch', 'tackling',
                                   'marking', 'positioning', 'vision', 'decisions', 'reflexes',
                                   'handling', 'kicking', 'one_on_one', 'determination', 
                                   'leadership', 'teamwork', 'aggression']}

    def import_teams(self):
        """导入球队数据，处理重名问题"""
        print("\n=== 导入球队数据 ===")
        
        if not self.teams_file.exists():
            print(f"✗ 球队文件不存在: {self.teams_file}")
            return False
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        new_leagues = 0
        new_clubs = 0
        
        try:
            with open(self.teams_file, "r", encoding="gbk", errors="ignore") as f:
                reader = csv.DictReader(f, delimiter=';')
                
                for row in reader:
                    team_name = row.get('名字', '').strip()
                    country = row.get('国家', '').strip()
                    league_name = row.get('联赛', '').strip()
                    
                    if not team_name or not league_name:
                        continue
                    
                    # 创建/获取联赛
                    league_key = (league_name, country)
                    if league_key not in self.league_cache:
                        cursor.execute("""
                            INSERT OR IGNORE INTO leagues (id, name, country, tier)
                            VALUES (?, ?, ?, ?)
                        """, (self.next_league_id, league_name, country, 1))
                        self.league_cache[league_key] = self.next_league_id
                        self.next_league_id += 1
                        new_leagues += 1
                    
                    league_id = self.league_cache[league_key]
                    
                    # 检查球队是否已存在（同一联赛下）
                    club_key = (league_id, team_name)
                    if club_key in self.club_cache:
                        continue
                    
                    # 处理重名球队：添加联赛后缀
                    display_name = team_name
                    cursor.execute("SELECT id FROM clubs WHERE name = ?", (team_name,))
                    existing = cursor.fetchone()
                    if existing:
                        # 球队名已存在，检查是否是同一联赛
                        cursor.execute("SELECT league_id FROM clubs WHERE id = ?", (existing[0],))
                        existing_league = cursor.fetchone()[0]
                        if existing_league == league_id:
                            # 同一联赛下的重复，跳过
                            continue
                        # 不同联赛，添加联赛后缀
                        display_name = f"{team_name} ({league_name})"
                        # 再次检查新名称是否已存在
                        cursor.execute("SELECT id FROM clubs WHERE name = ?", (display_name,))
                        if cursor.fetchone():
                            continue
                    
                    # 解析数据
                    reputation = self.parse_money(row.get('声望', '1000'))
                    balance = self.parse_money(row.get('收支结余', '0'))
                    transfer_budget = self.parse_money(row.get('转会预算', '0'))
                    wage_budget = self.parse_money(row.get('工资预算', '0'))
                    stadium_capacity = self.parse_money(row.get('球场容量', '5000'))
                    
                    # 计算球队评分作为 reputation
                    rating = self.parse_percentage(row.get('评分', '50%'))
                    
                    cursor.execute("""
                        INSERT INTO clubs (
                            id, name, short_name, founded_year, city, country,
                            stadium_name, stadium_capacity, reputation, reputation_level,
                            primary_color, secondary_color, league_id, balance,
                            transfer_budget, wage_budget, weekly_wage_bill, ticket_price,
                            average_attendance, commercial_income, youth_facility_level,
                            youth_academy_country, training_facility_level, is_ai_controlled,
                            season_objective, matches_played, matches_won, matches_drawn,
                            matches_lost, goals_for, goals_against, points, league_position
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.next_club_id,
                        display_name,
                        team_name[:20] if len(team_name) > 20 else team_name,
                        1900,  # founded_year
                        country,
                        country,
                        f"{team_name[:50]} Stadium",
                        stadium_capacity,
                        min(reputation, 10000),
                        "Professional",
                        "#FF0000",
                        "#FFFFFF",
                        league_id,
                        balance,
                        transfer_budget,
                        wage_budget,
                        int(wage_budget / 52) if wage_budget else 10000,
                        50,
                        self.parse_money(row.get('平均上座', '1000')),
                        100000,
                        5,
                        country,
                        5,
                        True,
                        "Avoid Relegation",
                        0, 0, 0, 0, 0, 0, 0, 1
                    ))
                    
                    self.club_cache[club_key] = self.next_club_id
                    self.next_club_id += 1
                    new_clubs += 1
                    
                    if new_clubs % 100 == 0:
                        conn.commit()
                        print(f"  已导入 {new_clubs} 支球队...")
            
            conn.commit()
            print(f"✓ 成功导入 {new_clubs} 支新球队, {new_leagues} 个新联赛")
            return True
            
        except Exception as e:
            print(f"✗ 导入球队失败: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False
        finally:
            conn.close()

    def import_players(self, limit=None):
        """导入球员数据"""
        print("\n=== 导入球员数据 ===")
        
        if not self.players_file.exists():
            print(f"✗ 球员文件不存在: {self.players_file}")
            return False
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        count = 0
        skipped = 0
        
        try:
            with open(self.players_file, "r", encoding="gbk", errors="ignore") as f:
                reader = csv.DictReader(f, delimiter=';')
                
                for row in reader:
                    if limit and count >= limit:
                        break
                    
                    player_name = row.get('姓名', '').strip()
                    if not player_name:
                        skipped += 1
                        continue
                    
                    # 解析名字
                    name_parts = player_name.split(', ')
                    if len(name_parts) == 2:
                        # "á Lakjuni, Báreur" 格式
                        last_name = name_parts[0].strip()
                        first_name = name_parts[1].strip()
                    else:
                        name_parts = player_name.split(' ', 1)
                        if len(name_parts) == 2:
                            first_name = name_parts[0]
                            last_name = name_parts[1]
                        else:
                            first_name = player_name
                            last_name = ""
                    
                    # 获取球队
                    team_name = row.get('俱乐部', '').strip()
                    league_name = row.get('联赛', '').strip()
                    country = row.get('所在地', row.get('国籍', '')).strip()
                    
                    # 查找球队ID
                    club_id = None
                    if team_name and team_name != '-':
                        # 先尝试精确匹配
                        for (lid, name), cid in self.club_cache.items():
                            if name == team_name:
                                club_id = cid
                                break
                        
                        # 如果没有找到，尝试模糊匹配
                        if club_id is None:
                            for (lid, name), cid in self.club_cache.items():
                                if team_name in name or name in team_name:
                                    club_id = cid
                                    break
                        
                        # 如果仍然没有找到，创建新俱乐部
                        if club_id is None and team_name:
                            # 获取或创建联赛
                            league_key = (league_name, country)
                            if league_key not in self.league_cache:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO leagues (id, name, country, tier)
                                    VALUES (?, ?, ?, ?)
                                """, (self.next_league_id, league_name, country, 1))
                                self.league_cache[league_key] = self.next_league_id
                                self.next_league_id += 1
                            
                            league_id = self.league_cache.get(league_key)
                            
                            # 检查是否有重名
                            display_name = team_name
                            cursor.execute("SELECT id FROM clubs WHERE name = ?", (team_name,))
                            if cursor.fetchone():
                                display_name = f"{team_name} ({league_name})"
                            
                            # 创建新俱乐部
                            club_id = self.next_club_id
                            cursor.execute("""
                                INSERT INTO clubs (
                                    id, name, short_name, founded_year, city, country,
                                    stadium_name, stadium_capacity, reputation, reputation_level,
                                    primary_color, secondary_color, league_id, balance,
                                    transfer_budget, wage_budget, weekly_wage_bill, ticket_price,
                                    average_attendance, commercial_income, youth_facility_level,
                                    youth_academy_country, training_facility_level, is_ai_controlled,
                                    season_objective, matches_played, matches_won, matches_drawn,
                                    matches_lost, goals_for, goals_against, points, league_position
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                club_id, display_name, team_name[:20], 1900, country, country,
                                f"{team_name[:50]} Stadium", 5000, 1000, "Professional",
                                "#FF0000", "#FFFFFF", league_id, 1000000, 0, 0, 1000, 20, 1000, 10000,
                                5, country, 5, True, "Avoid Relegation", 0, 0, 0, 0, 0, 0, 0, 1
                            ))
                            
                            self.club_cache[(league_id, team_name)] = club_id
                            self.next_club_id += 1
                    
                    # 确定位置和评分
                    position, ca = self.get_best_position(row)
                    _, pa = self.get_best_potential_position(row)
                    
                    # 解析当前评分和最高潜力评分（如果单独字段有值）
                    current_rating = self.parse_percentage(row.get('当前评分', '0%'))
                    potential_rating = self.parse_percentage(row.get('最高潜力评分', '0%'))
                    
                    if current_rating > ca:
                        ca = current_rating
                    if potential_rating > pa:
                        pa = potential_rating
                    
                    # 确保 PA > CA
                    if pa <= ca:
                        pa = min(ca + 10, 100)
                    
                    # 估算属性
                    attrs = self.estimate_attributes(position, ca)
                    
                    # 解析其他数据
                    age = self.parse_money(row.get('年龄', '20'))
                    salary = self.parse_money(row.get('工资', '0'))
                    market_value = self.parse_money(row.get('身价', '0'))
                    birth_date = self.parse_date(row.get('生日', ''))
                    
                    # 使用 FM 的 UNIQUE ID
                    unique_id = row.get('UNIQUE ID', '')
                    try:
                        player_id = int(unique_id) if unique_id else self.next_club_id + count
                    except ValueError:
                        player_id = self.next_club_id + count
                    
                    cursor.execute("""
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
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        player_id,
                        first_name[:100],
                        last_name[:100],
                        birth_date,
                        row.get('国籍', 'Unknown')[:100],
                        position,
                        175,  # height (default)
                        70,   # weight (default)
                        'RIGHT',
                        max(1, min(99, attrs['pace'])),
                        max(1, min(99, attrs['acceleration'])),
                        max(1, min(99, attrs['stamina'])),
                        max(1, min(99, attrs['strength'])),
                        max(1, min(99, attrs['shooting'])),
                        max(1, min(99, attrs['passing'])),
                        max(1, min(99, attrs['dribbling'])),
                        max(1, min(99, attrs['crossing'])),
                        max(1, min(99, attrs['first_touch'])),
                        max(1, min(99, attrs['tackling'])),
                        max(1, min(99, attrs['marking'])),
                        max(1, min(99, attrs['positioning'])),
                        max(1, min(99, attrs['vision'])),
                        max(1, min(99, attrs['decisions'])),
                        max(1, min(99, attrs['reflexes'])),
                        max(1, min(99, attrs['handling'])),
                        max(1, min(99, attrs['kicking'])),
                        max(1, min(99, attrs['one_on_one'])),
                        'MEDIUM',
                        max(1, min(99, attrs['determination'])),
                        max(1, min(99, attrs['leadership'])),
                        max(1, min(99, attrs['teamwork'])),
                        max(1, min(99, attrs['aggression'])),
                        ca,
                        pa,
                        club_id,
                        None,  # contract_until
                        salary,
                        market_value,
                        int(market_value * 1.5) if market_value else None,
                        100,  # fitness
                        80,   # morale
                        75,   # form
                        0, 0, 0, 0, 0, 0, 0, 0  # stats (appearances, goals, assists, yellow_cards, red_cards, minutes_played, career_goals, career_appearances)
                    ))
                    
                    count += 1
                    if count % 1000 == 0:
                        conn.commit()
                        print(f"  已导入 {count} 名球员...")
            
            conn.commit()
            print(f"✓ 成功导入 {count} 名球员 (跳过 {skipped} 条无效记录)")
            return True
            
        except Exception as e:
            print(f"✗ 导入球员失败: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False
        finally:
            conn.close()

    def show_summary(self):
        """显示导入摘要"""
        print("\n=== 导入摘要 ===")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # 统计
        cursor.execute("SELECT COUNT(*) FROM leagues")
        leagues_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clubs")
        clubs_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM players")
        players_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT club_id) FROM players WHERE club_id IS NOT NULL")
        players_with_club = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"联赛总数: {leagues_count}")
        print(f"球队总数: {clubs_count}")
        print(f"球员总数: {players_count}")
        print(f"有所属球队的球员: {players_with_club}")

    def run(self, player_limit=None):
        """执行完整导入流程"""
        print("=" * 60)
        print("    Football Manager 中文数据导入器")
        print("=" * 60)
        print(f"数据文件: {self.players_file.absolute()}, {self.teams_file.absolute()}")
        print(f"目标数据库: {self.db_path.absolute()}")
        
        # 检查文件
        if not self.players_file.exists():
            print(f"\n✗ 球员文件不存在: {self.players_file}")
            return
        if not self.teams_file.exists():
            print(f"\n✗ 球队文件不存在: {self.teams_file}")
            return
        
        # 初始化
        self.init_leagues_table()
        self.load_existing_data()
        
        # 导入球队
        if not self.import_teams():
            print("\n✗ 球队导入失败")
            return
        
        # 导入球员
        if not self.import_players(limit=player_limit):
            print("\n✗ 球员导入失败")
            return
        
        # 显示摘要
        self.show_summary()
        
        print("\n✅ 导入完成！")


if __name__ == "__main__":
    import sys
    
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"测试模式：仅导入前 {limit} 名球员")
        except ValueError:
            pass
    
    importer = FMChineseDataImporter()
    importer.run(player_limit=limit)
