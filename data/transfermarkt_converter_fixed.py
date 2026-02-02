#!/usr/bin/env python3

import sqlite3
import csv
from pathlib import Path
from datetime import datetime


def import_clubs():
    print("\n=== 导入俱乐部数据 ===")

    db_path = "fm_manager.db"
    csv_path = "data/football-datasets/team_details/team_details.csv"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        count = 0
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                club_id = row.get("club_id", "")

                if not club_id or club_id == "":
                    continue

                try:
                    club_id = int(club_id)
                    club_name = row.get("club_name", "")

                    values = [
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
                        "Win_the_league",
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        None,
                    ]

                    if len(values) != 33:
                        print(f"  ERROR: Got {len(values)} values, need 33")
                        continue

                    cursor.execute(
                        "INSERT OR REPLACE INTO clubs (id, name, short_name, city, founded_year, country, stadium_name, stadium_capacity, reputation, reputation_level, primary_color, secondary_color, league_id, balance, transfer_budget, wage_budget, weekly_wage_bill, ticket_price, average_attendance, commercial_income, youth_facility_level, youth_academy_country, training_facility_level, is_ai_controlled, season_objective, matches_played, matches_won, matches_drawn, matches_lost, goals_for, goals_against, points, league_position) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        values,
                    )

                    count += 1
                    if count % 100 == 0:
                        conn.commit()
                        print(f"  已导入 {count} 家俱乐部...")

                    if count >= 1000:
                        print("  测试导入前1000条后停止")
                        break

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


if __name__ == "__main__":
    import_clubs()
