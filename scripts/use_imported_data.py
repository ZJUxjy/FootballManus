#!/usr/bin/env python3
"""
展示如何使用导入的 FM 中文数据
从 SQLite 数据库查询和使用数据
"""

import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_db_connection():
    """获取数据库连接"""
    db_path = Path(__file__).parent.parent / "data" / "fm_manager.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def list_top_leagues(limit=10):
    """列出顶级联赛"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print("顶级联赛（按球队数量排序）")
    print(f"{'='*60}")
    
    cursor.execute("""
        SELECT l.name, l.country, COUNT(c.id) as team_count
        FROM leagues l
        LEFT JOIN clubs c ON l.id = c.league_id
        GROUP BY l.id
        ORDER BY team_count DESC
        LIMIT ?
    """, (limit,))
    
    for row in cursor.fetchall():
        print(f"  {row['name']} ({row['country']}): {row['team_count']} 支球队")
    
    conn.close()


def list_top_clubs(limit=10):
    """列出顶级球队（按声望）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print("顶级球队（按声望排序）")
    print(f"{'='*60}")
    
    cursor.execute("""
        SELECT c.name, c.country, c.reputation, c.balance, l.name as league
        FROM clubs c
        LEFT JOIN leagues l ON c.league_id = l.id
        ORDER BY c.reputation DESC
        LIMIT ?
    """, (limit,))
    
    print(f"{'球队':<25} {'联赛':<25} {'声望':<8} {'资金':>12}")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"{row['name']:<25} {row['league'] or 'N/A':<25} {row['reputation']:<8} €{row['balance']:>10,}")
    
    conn.close()


def list_top_players(limit=15):
    """列出顶级球员（按能力值）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print("顶级球员（按能力值排序）")
    print(f"{'='*80}")
    
    cursor.execute("""
        SELECT p.first_name, p.last_name, p.position, p.current_ability, 
               p.potential_ability, p.market_value, c.name as club
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        ORDER BY p.current_ability DESC
        LIMIT ?
    """, (limit,))
    
    print(f"{'排名':<4} {'姓名':<25} {'位置':<5} {'CA':<4} {'PA':<4} {'身价':>12} {'球队':<20}")
    print("-" * 100)
    for i, row in enumerate(cursor.fetchall(), 1):
        name = f"{row['first_name']} {row['last_name']}"
        print(f"{i:<4} {name:<25} {row['position']:<5} {row['current_ability']:<4} "
              f"{row['potential_ability']:<4} €{row['market_value']:>10,} {row['club'] or '自由球员':<20}")
    
    conn.close()


def get_club_squad(club_name):
    """查看指定球队的阵容"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查找球队（优先匹配完整名称，按声望排序）
    cursor.execute("""
        SELECT c.*, l.name as league_name
        FROM clubs c
        LEFT JOIN leagues l ON c.league_id = l.id
        WHERE c.name LIKE ?
        ORDER BY c.reputation DESC
    """, (f"%{club_name}%",))
    
    clubs = cursor.fetchall()
    if not clubs:
        print(f"未找到球队: {club_name}")
        conn.close()
        return
    
    # 如果有多个匹配，显示选择列表
    club = clubs[0]
    if len(clubs) > 1:
        print(f"\n找到 {len(clubs)} 个匹配的球队:")
        for i, c in enumerate(clubs[:5], 1):
            print(f"  {i}. {c['name']} ({c['reputation']} 声望)")
        print(f"\n显示: {club['name']}")
    
    print(f"\n{'='*80}")
    print(f"球队: {club['name']}")
    print(f"{'='*80}")
    print(f"联赛: {club['league_name'] or '未知'}")
    print(f"声望: {club['reputation']}")
    print(f"资金: €{club['balance']:,}")
    print(f"转会预算: €{club['transfer_budget']:,}")
    print(f"工资预算: €{club['wage_budget']:,}")
    print(f"球场容量: {club['stadium_capacity']:,}")
    
    # 获取球员
    cursor.execute("""
        SELECT p.* 
        FROM players p
        WHERE p.club_id = ?
        ORDER BY p.current_ability DESC
    """, (club['id'],))
    
    players = cursor.fetchall()
    print(f"\n阵容 ({len(players)} 人):")
    print("-" * 80)
    print(f"{'姓名':<25} {'位置':<6} {'CA':<4} {'PA':<4} {'年龄':<4} {'身价':>12}")
    print("-" * 80)
    
    for p in players:
        name = f"{p['first_name']} {p['last_name']}"
        age = p['birth_date'][:4] if p['birth_date'] else 'N/A'
        print(f"{name:<25} {p['position']:<6} {p['current_ability']:<4} "
              f"{p['potential_ability']:<4} {age:<4} €{p['market_value']:>10,}")
    
    conn.close()


def search_player(name):
    """搜索球员"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.*, c.name as club_name
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        WHERE p.first_name LIKE ? OR p.last_name LIKE ?
        LIMIT 20
    """, (f"%{name}%", f"%{name}%"))
    
    players = cursor.fetchall()
    
    print(f"\n{'='*80}")
    print(f"搜索 '{name}' 找到 {len(players)} 名球员")
    print(f"{'='*80}")
    
    print(f"{'姓名':<30} {'位置':<6} {'CA':<4} {'PA':<4} {'球队':<25}")
    print("-" * 80)
    for p in players:
        full_name = f"{p['first_name']} {p['last_name']}"
        print(f"{full_name:<30} {p['position']:<6} {p['current_ability']:<4} "
              f"{p['potential_ability']:<4} {p['club_name'] or '自由球员':<25}")
    
    conn.close()


def show_stats():
    """显示数据统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print("数据统计")
    print(f"{'='*60}")
    
    cursor.execute("SELECT COUNT(*) FROM leagues")
    print(f"联赛总数: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM clubs")
    print(f"球队总数: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM players")
    print(f"球员总数: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM players WHERE club_id IS NOT NULL")
    print(f"有球队的球员: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT AVG(current_ability), MAX(current_ability) FROM players")
    row = cursor.fetchone()
    print(f"球员平均能力值: {row[0]:.1f}")
    print(f"球员最高能力值: {row[1]}")
    
    cursor.execute("SELECT SUM(market_value) FROM players")
    total_value = cursor.fetchone()[0] or 0
    print(f"球员总身价: €{total_value:,.0f}")
    
    conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="使用导入的 FM 数据")
    parser.add_argument("--stats", action="store_true", help="显示数据统计")
    parser.add_argument("--leagues", action="store_true", help="列出顶级联赛")
    parser.add_argument("--clubs", action="store_true", help="列出顶级球队")
    parser.add_argument("--players", action="store_true", help="列出顶级球员")
    parser.add_argument("--squad", type=str, help="查看指定球队阵容")
    parser.add_argument("--search", type=str, help="搜索球员")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        # 默认显示所有概览
        show_stats()
        list_top_leagues()
        list_top_clubs(5)
        list_top_players(10)
    else:
        if args.stats:
            show_stats()
        if args.leagues:
            list_top_leagues()
        if args.clubs:
            list_top_clubs()
        if args.players:
            list_top_players()
        if args.squad:
            get_club_squad(args.squad)
        if args.search:
            search_player(args.search)


if __name__ == "__main__":
    main()
