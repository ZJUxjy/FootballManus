#!/usr/bin/env python3
"""重新清洗数据，保留更多属性字段.

Usage:
    python scripts/rebuild_cleaned_data.py
"""

import pandas as pd
import numpy as np
import json
import re
from collections import defaultdict
from pathlib import Path


def parse_percentage(value):
    """解析百分比字符串为浮点数."""
    if pd.isna(value):
        return 0.0
    value_str = str(value)
    match = re.search(r'([\d.]+)%', value_str)
    if match:
        return float(match.group(1))
    try:
        return float(value_str)
    except:
        return 0.0


def parse_money(value):
    """解析金额字符串为整数."""
    if pd.isna(value):
        return 0
    value_str = str(value).replace(',', '').replace('$', '').replace('€', '')
    try:
        return int(float(value_str))
    except:
        return 0


def clean_players_data():
    """清洗球员数据，保留更多属性."""
    print("=" * 80)
    print("🔄 重新清洗球员数据")
    print("=" * 80)
    
    # 读取原始数据
    df = pd.read_csv('data/players.csv', encoding='gbk', sep=';')
    print(f"\n原始数据: {len(df)} 行, {len(df.columns)} 列")
    
    # 位置评分映射（中文列名 -> 英文属性名）
    position_ratings_map = {
        'GK 评分': 'rating_gk',
        'SW 评分': 'rating_sw',
        'DL 评分': 'rating_dl',
        'DC 评分': 'rating_dc',
        'DR 评分': 'rating_dr',
        'WBL 评分': 'rating_wbl',
        'WBR 评分': 'rating_wbr',
        'DM 评分': 'rating_dm',
        'ML 评分': 'rating_ml',
        'MC 评分': 'rating_mc',
        'MR 评分': 'rating_mr',
        'AML 评分': 'rating_aml',
        'AMC 评分': 'rating_amc',
        'AMR 评分': 'rating_amr',
        'FS 评分': 'rating_fs',
        'TS 评分': 'rating_ts',
        # 潜力评分
        'GK 潜力评分': 'potential_gk',
        'SW 潜力评分': 'potential_sw',
        'DL 潜力评分': 'potential_dl',
        'DC 潜力评分': 'potential_dc',
        'DR 潜力评分': 'potential_dr',
        'WBL 潜力评分': 'potential_wbl',
        'WBR 潜力评分': 'potential_wbr',
        'DM 潜力评分': 'potential_dm',
        'ML 潜力评分': 'potential_ml',
        'MC 潜力评分': 'potential_mc',
        'MR 潜力评分': 'potential_mr',
        'AML 潜力评分': 'potential_aml',
        'AMC 潜力评分': 'potential_amc',
        'AMR 潜力评分': 'potential_amr',
        'FS 潜力评分': 'potential_fs',
        'TS 潜力评分': 'potential_ts',
    }
    
    # 创建新的DataFrame
    cleaned = pd.DataFrame()
    
    # 1. 基本信息
    print("\n【1】处理基本信息...")
    cleaned['player_id'] = df['UNIQUE ID']
    cleaned['name'] = df['姓名']
    cleaned['nationality'] = df['国籍']
    cleaned['age'] = df['年龄']
    cleaned['birth_date'] = df['生日']
    cleaned['position'] = df['位置']
    cleaned['location'] = df['所在地']
    
    # 2. 能力值
    print("【2】处理能力值...")
    cleaned['current_ability'] = df['当前评分'].apply(parse_percentage)
    cleaned['potential_ability'] = df['最高潜力评分'].apply(parse_percentage)
    cleaned['player_role'] = df['球员定位']
    cleaned['estimated_role'] = df['预估球员定位']
    
    # 3. 位置评分（32个字段）
    print("【3】处理位置评分（32个字段）...")
    for col_zh, col_en in position_ratings_map.items():
        if col_zh in df.columns:
            cleaned[col_en] = df[col_zh].apply(parse_percentage)
        else:
            cleaned[col_en] = 0.0
    
    # 4. 状态属性
    print("【4】处理状态属性...")
    cleaned['fatigue'] = df['疲劳'].apply(lambda x: int(x) if pd.notna(x) else 0)
    cleaned['stamina'] = df['体力'].apply(parse_percentage)
    cleaned['match_shape'] = df['竞技状态'].apply(parse_percentage)
    cleaned['happiness'] = df['满意程度'].apply(lambda x: int(x) if pd.notna(x) else 50)
    
    # 5. 财务信息
    print("【5】处理财务信息...")
    cleaned['wage'] = df['工资'].apply(parse_money)
    cleaned['value'] = df['身价'].apply(parse_money)
    
    # 6. 经验数据
    print("【6】处理经验数据...")
    cleaned['match_experience'] = df['比赛经验'].apply(parse_percentage)
    cleaned['intl_caps'] = df['国家队出场数'].apply(lambda x: int(x) if pd.notna(x) else 0)
    cleaned['intl_goals'] = df['国家队进球数'].apply(lambda x: int(x) if pd.notna(x) else 0)
    
    # 7. 俱乐部信息
    print("【7】处理俱乐部信息...")
    cleaned['club_name'] = df['俱乐部']
    cleaned['club_id'] = df['Club ID']
    cleaned['club_reputation'] = df['球队声望'].apply(parse_money)
    cleaned['squad_status'] = df['所属球队']
    cleaned['league'] = df['联赛']
    
    # 过滤无效俱乐部ID
    print("\n【8】过滤无效数据...")
    valid_mask = (cleaned['club_id'] != -1) & (cleaned['club_id'].notna())
    cleaned = cleaned[valid_mask].copy()
    
    print(f"有效数据: {len(cleaned)} 行")
    
    # 保存
    output_path = 'data/cleaned/players_full.csv'
    cleaned.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n✅ 已保存: {output_path}")
    print(f"   字段数: {len(cleaned.columns)}")
    
    return cleaned


def clean_teams_data():
    """清洗俱乐部数据."""
    print("\n" + "=" * 80)
    print("🔄 清洗俱乐部数据")
    print("=" * 80)
    
    df = pd.read_csv('data/teams.csv', encoding='gbk', sep=';')
    print(f"原始数据: {len(df)} 行")
    
    cleaned = pd.DataFrame()
    cleaned['club_id'] = df['Unique ID'].astype(str).str.replace(',', '').astype(np.int64)
    cleaned['name'] = df['名字']
    cleaned['country'] = df['国家']
    cleaned['league'] = df['联赛']
    cleaned['reputation'] = df['声望'].astype(str).str.replace(',', '').astype(np.int64)
    cleaned['avg_age'] = df['平均年龄']
    cleaned['balance'] = df['收支结余'].astype(str).str.replace(',', '').astype(np.int64)
    cleaned['transfer_budget'] = df['转会预算'].astype(str).str.replace(',', '').astype(np.int64)
    cleaned['wage_budget'] = df['工资预算'].astype(str).str.replace(',', '').astype(np.int64)
    cleaned['stadium_capacity'] = df['球场容量'].astype(str).str.replace(',', '').astype(np.int64)
    cleaned['avg_attendance'] = df['平均上座'].astype(str).str.replace(',', '').astype(np.int64)
    
    output_path = 'data/cleaned/teams_full.csv'
    cleaned.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n✅ 已保存: {output_path}")
    
    return cleaned


def reorganize_leagues(teams_df):
    """重组联赛（按国家拆分）."""
    print("\n" + "=" * 80)
    print("🔄 重组联赛结构")
    print("=" * 80)
    
    # 按联赛和国家分组
    league_country = teams_df.groupby(['league', 'country']).size().reset_index(name='count')
    
    # 决定如何重组
    new_leagues = {}
    
    for league_name in teams_df['league'].unique():
        league_teams = teams_df[teams_df['league'] == league_name]
        total_clubs = len(league_teams)
        
        # 按国家分组
        by_country = league_teams.groupby('country').size().to_dict()
        
        # 如果联赛俱乐部数>30或有多个国家，则拆分
        if total_clubs > 30 or len(by_country) > 1:
            for country, count in by_country.items():
                if count >= 5:  # 至少5个俱乐部才独立成联赛
                    new_name = f"{country} {league_name}"
                    new_leagues[new_name] = {
                        'league_name': new_name,
                        'original_league': league_name,
                        'country': country,
                        'club_count': count,
                        'clubs': league_teams[league_teams['country'] == country][['name', 'country', 'reputation', 'club_id']].rename(
                            columns={'name': 'club_name', 'club_id': 'unique_id'}
                        ).to_dict('records')
                    }
        else:
            # 保持原样
            country = league_teams['country'].iloc[0] if len(league_teams) > 0 else 'Unknown'
            new_leagues[league_name] = {
                'league_name': league_name,
                'country': country,
                'club_count': total_clubs,
                'clubs': league_teams[['name', 'country', 'reputation', 'club_id']].rename(
                    columns={'name': 'club_name', 'club_id': 'unique_id'}
                ).to_dict('records')
            }
    
    # 保存
    with open('data/cleaned/leagues_full.json', 'w', encoding='utf-8') as f:
        json.dump(new_leagues, f, ensure_ascii=False, indent=2)
    
    print(f"联赛总数: {len(new_leagues)}")
    print(f"✅ 已保存: data/cleaned/leagues_full.json")
    
    return new_leagues


def update_league_names(players_df, teams_df, leagues_dict):
    """更新联赛名称."""
    print("\n" + "=" * 80)
    print("🔄 更新联赛名称")
    print("=" * 80)
    
    # 构建俱乐部ID到新联赛名称的映射
    club_to_league = {}
    for league_name, info in leagues_dict.items():
        for club in info['clubs']:
            club_to_league[club['unique_id']] = league_name
    
    # 更新球员数据
    players_df['club_league'] = players_df['club_id'].map(club_to_league)
    
    # 更新俱乐部数据
    teams_df['league'] = teams_df['club_id'].map(club_to_league)
    
    # 保存
    players_df.to_csv('data/cleaned/players_full.csv', index=False, encoding='utf-8')
    teams_df.to_csv('data/cleaned/teams_full.csv', index=False, encoding='utf-8')
    
    print(f"✅ 联赛名称已更新")
    print(f"   球员数据: {len(players_df)} 行")
    print(f"   俱乐部数据: {len(teams_df)} 行")
    
    return players_df, teams_df


def show_summary(players_df, teams_df):
    """显示数据摘要."""
    print("\n" + "=" * 80)
    print("📊 数据摘要")
    print("=" * 80)
    
    print(f"\n球员数据: {len(players_df)} 行, {len(players_df.columns)} 列")
    print("字段分类:")
    
    fields = {
        '基本信息': ['player_id', 'name', 'nationality', 'age', 'birth_date', 'position', 'location'],
        '能力总评': ['current_ability', 'potential_ability', 'player_role', 'estimated_role'],
        '位置评分': [c for c in players_df.columns if c.startswith('rating_')],
        '位置潜力': [c for c in players_df.columns if c.startswith('potential_')],
        '状态属性': ['fatigue', 'stamina', 'match_shape', 'happiness'],
        '经验数据': ['match_experience', 'intl_caps', 'intl_goals'],
        '财务信息': ['wage', 'value'],
        '俱乐部信息': ['club_name', 'club_id', 'club_reputation', 'squad_status', 'club_league'],
    }
    
    for category, cols in fields.items():
        existing = [c for c in cols if c in players_df.columns]
        if existing:
            print(f"  {category}: {len(existing)} 个字段")
    
    print(f"\n俱乐部数据: {len(teams_df)} 行")
    print(f"联赛数: {players_df['club_league'].nunique()}")
    
    # 五大联赛球员数
    print("\n五大联赛球员分布:")
    top5 = [
        'England Premier League',
        'La Liga',
        'Italy Serie A',
        'Bundesliga',
        'France Ligue 1',
    ]
    for league in top5:
        count = len(players_df[players_df['club_league'] == league])
        if count > 0:
            print(f"  {league}: {count} 球员")


def main():
    """主函数."""
    # 创建输出目录
    Path('data/cleaned').mkdir(parents=True, exist_ok=True)
    
    # 清洗数据
    players_df = clean_players_data()
    teams_df = clean_teams_data()
    
    # 重组联赛
    leagues_dict = reorganize_leagues(teams_df)
    
    # 更新联赛名称
    players_df, teams_df = update_league_names(players_df, teams_df, leagues_dict)
    
    # 显示摘要
    show_summary(players_df, teams_df)
    
    print("\n" + "=" * 80)
    print("✅ 数据清洗完成!")
    print("=" * 80)
    print("\n输出文件:")
    print("  - data/cleaned/players_full.csv")
    print("  - data/cleaned/teams_full.csv")
    print("  - data/cleaned/leagues_full.json")


if __name__ == "__main__":
    main()
