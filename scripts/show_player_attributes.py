#!/usr/bin/env python3
"""显示清洗后球员数据的各项属性能力.

Usage:
    python scripts/show_player_attributes.py <球员名>
    python scripts/show_player_attributes.py "Haaland"
    python scripts/show_player_attributes.py --id 29179241
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


def format_money(value: int) -> str:
    """格式化金额显示."""
    if value >= 1_000_000_000:
        return f"€{value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"€{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"€{value/1_000:.0f}K"
    return f"€{value}"


def show_player_from_csv(player_name: str = None, player_id: int = None):
    """从CSV直接显示球员原始数据."""
    players = pd.read_csv('data/cleaned/players_cleaned.csv')
    
    # 查找球员
    if player_id:
        player = players[players['player_id'] == player_id]
    elif player_name:
        player = players[players['name'].str.contains(player_name, case=False, na=False)]
    else:
        print("❌ 请提供球员名或ID")
        return
    
    if len(player) == 0:
        print(f"❌ 未找到球员: {player_name or player_id}")
        return
    
    # 如果找到多个，显示列表让用户选择
    if len(player) > 1:
        print(f"\n找到 {len(player)} 名匹配的球员:\n")
        print(f"{'ID':<12} {'姓名':<30} {'俱乐部':<25} {'能力':<15}")
        print("-" * 85)
        for _, row in player.head(10).iterrows():
            ability = f"{row['current_ability']:.1f}%"
            print(f"{row['player_id']:<12} {row['name']:<30} {row['club_name']:<25} {ability:<15}")
        print()
        return player.head(10)
    
    # 显示单个球员的详细信息
    row = player.iloc[0]
    
    print("\n" + "=" * 70)
    print(f"👤 {row['name']}")
    print("=" * 70)
    
    # 基本信息
    print("\n【基本信息】")
    print(f"  ID:          {row['player_id']}")
    print(f"  国籍:        {row['nationality']}")
    print(f"  年龄:        {row['age']}")
    print(f"  生日:        {row['birth_date']}")
    print(f"  位置:        {row['position']}")
    print(f"  所在地:      {row['location']}")
    
    # 能力值
    print("\n【能力总评】")
    print(f"  当前能力:    {row['current_ability']:.1f}/100")
    print(f"  潜力值:      {row['potential_ability']:.1f}/100")
    print(f"  球员角色:    {row['player_role']}")
    print(f"  预估角色:    {row['estimated_role']}")
    
    # 主要位置评分
    print("\n【主要位置评分】")
    rating_cols = [
        ('rating_gk', '门将'),
        ('rating_dc', '中后卫'),
        ('rating_dl', '左后卫'),
        ('rating_dr', '右后卫'),
        ('rating_dm', '后腰'),
        ('rating_mc', '中场'),
        ('rating_ml', '左中场'),
        ('rating_mr', '右中场'),
        ('rating_amc', '攻击中场'),
        ('rating_aml', '左边锋'),
        ('rating_amr', '右边锋'),
        ('rating_ts', '前锋'),
    ]
    for col, name in rating_cols:
        if col in row and row[col] > 0:
            print(f"  {name:<12} {row[col]:>6.1f}")
    
    # 状态属性
    print("\n【状态属性】")
    print(f"  疲劳:        {row['fatigue']}")
    print(f"  体力:        {row['stamina']:.1f}%")
    print(f"  竞技状态:    {row['match_shape']:.1f}%")
    print(f"  满意度:      {row['happiness']}")
    
    # 经验数据
    print("\n【经验数据】")
    print(f"  比赛经验:    {row['match_experience']:.1f}%")
    print(f"  国家队出场:  {row['intl_caps']}场")
    print(f"  国家队进球:  {row['intl_goals']}球")
    
    # 财务
    print("\n【财务信息】")
    print(f"  身价:        {format_money(row['value'])}")
    print(f"  周薪:        {format_money(row['wage'])}/周")
    
    # 俱乐部
    print("\n【俱乐部信息】")
    print(f"  俱乐部:      {row['club_name']}")
    print(f"  联赛:        {row['club_league']}")
    print(f"  声望:        {row['club_reputation']}")
    print(f"  队内角色:    {row['squad_status']}")
    
    print("=" * 70)
    
    return player


def list_sample_players():
    """显示一些示例球员."""
    players = pd.read_csv('data/cleaned/players_cleaned.csv')
    
    print("\n=== 知名球员示例 ===\n")
    
    # 按能力值排序
    top_players = players.nlargest(20, 'current_ability')
    
    print(f"{'排名':<4} {'姓名':<30} {'俱乐部':<25} {'能力':<10}")
    print("-" * 75)
    
    for i, (_, row) in enumerate(top_players.iterrows(), 1):
        print(f"{i:<4} {row['name']:<30} {row['club_name']:<25} {row['current_ability']:.1f}")
    
    print("\n使用示例:")
    print(f'  python scripts/show_player_attributes.py "Haaland"')
    print(f'  python scripts/show_player_attributes.py --id 29179241')


def main():
    parser = argparse.ArgumentParser(
        description="显示清洗后球员数据的各项属性能力",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "Haaland"              # 搜索Haaland
  %(prog)s --id 29179241          # 通过ID查询
  %(prog)s --list                 # 显示示例球员列表
        """
    )
    
    parser.add_argument("name", nargs="?", help="球员名（支持部分匹配）")
    parser.add_argument("--id", type=int, help="球员唯一ID")
    parser.add_argument("--list", action="store_true", help="显示示例球员列表")
    
    args = parser.parse_args()
    
    if args.list:
        list_sample_players()
    elif args.name or args.id:
        show_player_from_csv(args.name, args.id)
    else:
        parser.print_help()
        list_sample_players()


if __name__ == "__main__":
    main()
