#!/usr/bin/env python3

import sqlite3
import csv

DB_PATH = "fm_manager.db"
CSV_PATH = "players_export.csv"


def export_players_to_csv():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players")

        columns = [description[0] for description in cursor.description]

        with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)

            for row in cursor:
                writer.writerow(row)

        total_rows = cursor.rowcount
        print(f"✓ 成功导出 {total_rows} 条球员数据到: {CSV_PATH}")
        print(f"✓ 包含 {len(columns)} 个字段")

    except Exception as e:
        print(f"✗ 导出失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    export_players_to_csv()
