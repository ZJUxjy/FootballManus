"""Final working FM24 data merger - tested and working."""

import csv
import sqlite3
import re

def parse_number(num_str):
    if not num_str:
        return 0
    clean = num_str.replace(",", "").strip()
    return int(clean) if clean.isdigit() else 0

def parse_rating(rating_str):
    if not rating_str:
        return 50
    match = re.search(r"(\d+\.?\d*)%", rating_str)
    if match:
        return int(float(match.group(1)) * 2)  # 0-100% to 1-200
    return 50

def parse_birth_date(date_str):
    if not date_str or date_str == "-":
        return None
    try:
        parts = date_str.split(".")
        if len(parts) == 3:
            day, month, year = map(int, parts)
            return f"{year}-{month:02d}-{day:02d}"
    except Exception:
        return None

def infer_attributes(overall_rating, position):
    base = overall_rating // 2  # Convert 1-200 to 0-100
    
    if position == "GK":
        return (int(base*0.7), int(base*0.7), int(base*0.8), int(base*0.8),
                int(base*0.3), int(base*0.6), int(base*0.4), int(base*0.4), int(base*0.5),
                int(base*0.3), int(base*0.3), int(base*0.7), int(base*0.6), int(base*0.7),
                int(base*1.0), int(base*0.9), int(base*0.7), int(base*0.8))
    elif position in ["CB", "LB", "RB", "LWB", "RWB"]:
        return (int(base*0.8), int(base*0.8), int(base*0.85), int(base*0.9),
                int(base*0.4), int(base*0.65), int(base*0.6), int(base*0.6), int(base*0.65),
                int(base*0.9), int(base*0.9), int(base*0.85), int(base*0.6), int(base*0.7),
                int(base*0.4), int(base*0.3), int(base*0.4), int(base*0.4))
    elif position in ["CDM", "CM", "LM", "RM"]:
        return (int(base*0.8), int(base*0.8), int(base*0.9), int(base*0.75),
                int(base*0.6), int(base*0.85), int(base*0.8), int(base*0.7), int(base*0.8),
                int(base*0.75), int(base*0.7), int(base*0.8), int(base*0.85), int(base*0.8),
                int(base*0.4), int(base*0.3), int(base*0.4), int(base*0.4))
    else:
        # Attackers
        return (int(base*0.85), int(base*0.85), int(base*0.8), int(base*0.7),
                int(base*0.9), int(base*0.75), int(base*0.9), int(base*0.85), int(base*0.7),
                int(base*0.5), int(base*0.5), int(base*0.85), int(base*0.8), int(base*0.75),
                int(base*0.4), int(base*0.3), int(base*0.4), int(base*0.4))

# Load data
print("Loading FM24 data...")
teams = []
with open('/home/xu/code/FootballManus/data/teams.csv', 'r', encoding='gbk') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        teams.append(row)

players = []
with open('/home/xu/code/FootballManus/data/players.csv', 'r', encoding='gbk') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        players.append(row)

print(f"✓ Loaded {len(teams)} teams, {len(players)} players")

# Connect to database
db_path = '/home/xu/code/FootballManus/data/fm_manager_fm24.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Clear existing data
print("\nClearing existing data...")
cursor.execute("DELETE FROM players")
cursor.execute("DELETE FROM clubs")
cursor.execute("DELETE FROM leagues")
conn.commit()

# Step 1: Import Leagues
print("\n=== Step 1: Importing Leagues ===")
leagues = {}
for team in teams:
    league_name = team.get("联赛", "").strip()
    country = team.get("国家", "Unknown")

    league_key = (league_name, country)

    if league_name and league_key not in leagues:
        cursor.execute(
            """INSERT INTO leagues (name, short_name, country, tier, format, teams_count,
                                          promotion_count, relegation_count, has_promotion_playoff,
                                          has_relegation_playoff, season_start_month, season_end_month,
                                          has_winter_break, matches_on_weekdays, typical_match_days,
                                          champions_league_spots, europa_league_spots, conference_league_spots,
                                          prize_money_first, prize_money_last, tv_rights_base)
                   VALUES (?, ?, ?, 1, 'DOUBLE_ROUND_ROBIN', 20, 3, 3, 0, 0, 8, 5,
                           0, 1, 'Saturday,Sunday', 4, 2, 1,
                           100000000, 10000000, 50000000)""",
            (league_name, league_name[:20], country)
        )
        leagues[league_key] = cursor.lastrowid

conn.commit()
print(f"✓ Created {len(leagues)} leagues")

# Step 2: Import Clubs
print("\n=== Step 2: Importing Clubs ===")
clubs_map = {}
club_count = 0

for team in teams:
    name = team.get("名字", "").strip()
    if not name:
        continue
    
    # Check for duplicates
    cursor.execute("SELECT id FROM clubs WHERE name = ?", (name,))
    if cursor.fetchone():
        continue
    
    country = team.get("国家", "Unknown")
    league_name = team.get("联赛", "")
    reputation = parse_number(team.get("声望", "5000"))
    balance = parse_number(team.get("收支结余", "50000000"))
    transfer_budget = parse_number(team.get("转会预算", "10000000"))
    wage_budget = parse_number(team.get("工资预算", "1000000"))
    stadium_capacity = parse_number(team.get("球场容量", "0"))
    avg_attendance = parse_number(team.get("平均上座", "0"))
    training_facility = int(team.get("TF", "50").strip())
    youth_facility = int(team.get("YF", "50").strip())

    league_key = (league_name, country)
    league_id = leagues.get(league_key)
    if not league_id:
        continue
    
    # Insert club
    cursor.execute(
        """INSERT INTO clubs (name, short_name, founded_year, city, country,
                                  stadium_name, stadium_capacity, reputation, reputation_level,
                                  primary_color, secondary_color, league_id,
                                  balance, transfer_budget, wage_budget,
                                  weekly_wage_bill, ticket_price, average_attendance, commercial_income,
                                  training_facility_level, youth_facility_level, youth_academy_country,
                                  owner_user_id, llm_config, is_ai_controlled,
                                  matches_played, matches_won, matches_drawn, matches_lost,
                                  goals_for, goals_against, points, league_position,
                                  season_objective)
               VALUES (?, ?, 1900, '', ?, ?, ?, ?, 'RESPECTABLE', '#FF0000', '#FFFFFF', ?,
                           ?, ?, ?, 0, 50, ?, 0, ?, ?, ?, NULL, NULL, 1,
                           0, 0, 0, 0, 0, 0, 0, 0, 'mid_table')""",
        (name, name[:20], country, f"{name} Stadium", stadium_capacity,
         reputation, league_id, balance, transfer_budget, wage_budget,
         avg_attendance, training_facility, youth_facility, country)
    )
    clubs_map[name] = cursor.lastrowid
    club_count += 1

conn.commit()
print(f"✓ Imported {club_count} clubs")

# Position mapping
POSITION_MAP = {
    "门将": "GK", "中后卫": "CB", "左后卫": "LB", "右后卫": "RB",
    "左翼卫": "LWB", "右翼卫": "RWB", "后腰": "CDM", "中前卫": "CM",
    "左前卫": "LM", "右前卫": "RM", "前腰": "CAM", "左边锋": "LW",
    "右边锋": "RW", "中锋": "ST", "前锋": "ST", "攻击型中场": "CAM",
    "边锋": "LW", "中场": "CM", "后卫": "CB", "清道夫": "CB",
    "中": "CM", "左": "LB", "右": "RB",
}

# Step 3: Import Players
print("\n=== Step 3: Importing Players (this may take a few minutes) ===")

imported = 0
skipped = 0

for player in players:
    name = player.get("姓名", "").strip()
    if not name or name == "-":
        skipped += 1
        continue
    
    name_parts = name.split(maxsplit=1)
    first_name = name_parts[0] if name_parts else "Unknown"
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    nationality = player.get("国籍", "Unknown")
    if "/" in nationality:
        nationality = nationality.split("/")[0].strip()
    
    club = player.get("俱乐部", "").strip()
    if not club or club == "-" or club not in clubs_map:
        skipped += 1
        continue
    
    club_id = clubs_map[club]
    
    position_str = player.get("位置", "").strip()
    position = "CM"
    for pos_part in position_str.replace("/", " ").split():
        if pos_part in POSITION_MAP:
            position = POSITION_MAP[pos_part]
            break
    
    # Parse ratings
    current_rating = parse_rating(player.get("当前评分", ""))
    potential_rating = parse_rating(player.get("最高潜力评分", ""))
    
    # Parse wage and value
    wage = parse_number(player.get("工资", "0"))
    value = parse_number(player.get("身价", "0"))
    
    # Parse birth date
    birth_date = parse_birth_date(player.get("生日", ""))
    
    # Infer attributes
    (pace, acc, stam, str, shoot, pass_, drib, cross, ftouch,
     tackle, mark, pos, vision, decis, refl, hand, kick, onev) = infer_attributes(current_rating, position)
    
    params = (
        first_name, last_name, birth_date, nationality, position, "RIGHT",
        pace, acc, stam, str, shoot, pass_, drib, cross, ftouch,
        tackle, mark, pos, vision, decis, refl, hand, kick, onev,
        int(current_rating*0.8), int(current_rating*0.6), int(current_rating*0.7), int(current_rating*0.6), "MEDIUM",
        current_rating, potential_rating, club_id, wage, value,
        None, None, None, None, None,
        100, 50, 50,
        0, 0, 0, 0, 0, 0, 0, 0
    )

    cursor.execute(
        """INSERT INTO players (first_name, last_name, birth_date, nationality, position, preferred_foot,
                                   pace, acceleration, stamina, strength, shooting, passing, dribbling,
                                   crossing, first_touch, tackling, marking, positioning, vision, decisions,
                                   reflexes, handling, kicking, one_on_one,
                                   determination, leadership, teamwork, aggression, work_rate,
                                   current_ability, potential_ability, club_id, salary, market_value,
                                   secondary_position, height, weight, contract_until, release_clause,
                                   fitness, morale, form,
                                   appearances, goals, assists, yellow_cards, red_cards, minutes_played, career_goals, career_appearances)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        params
    )
    
    imported += 1
    if imported % 10000 == 0:
        conn.commit()
        print(f"  Progress: {imported:,} players imported...")

conn.commit()
print(f"✓ Imported {imported} players")
print(f"⚠️  Skipped {skipped} players (no club match)")

# Final summary
print(f"\n" + "="*60)
print(f"🎉 FM24 Data Import Complete!")
print(f"=" *60)

# Statistics
cursor.execute("SELECT COUNT(*) FROM leagues")
leagues_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM clubs")
clubs_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM players")
players_count = cursor.fetchone()[0]

print(f"\n📊 Database Statistics:")
print(f"  🏆 Leagues: {leagues_count}")
print(f"  ⚽ Clubs: {clubs_count}")
print(f"  ⚽ Players: {players_count}")

# Sample data
print(f"\n🏆 Top 10 Players by Current Ability:")
cursor.execute(
    """SELECT p.first_name, p.last_name, c.name as club, p.current_ability as ca, p.potential_ability as pa
       FROM players p
       JOIN clubs c ON p.club_id = c.id
       ORDER BY p.current_ability DESC LIMIT 10"""
)
for i, row in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {row[0]:<25} {row[1]:<25} ({row[2]}) - CA: {row[3]}, PA: {row[4]}")

# Sample clubs
print(f"\n⚽ Sample Clubs:")
cursor.execute(
    """SELECT name, reputation, balance FROM clubs ORDER BY reputation DESC LIMIT 5"""
)
for i, row in enumerate(cursor.fetchall(), 1):
    print(f"  {i}. {row[0]} - Rep: {row[1]}, Balance: €{row[2]:,}")

conn.close()
print(f"\n💾 Database saved to: {db_path}")
print(f"\n📁 You can now use this database with:")
print(f"   - Match engine tests: python scripts/demo_match.py")
print(f"   - Season simulation: python scripts/simulate_season.py")
print(f"   - Test your imports: python scripts/test_match_engine.py")
