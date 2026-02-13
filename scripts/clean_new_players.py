#!/usr/bin/env python3
"""清洗新的球员数据文件 data/new_players.csv

Usage:
    python scripts/clean_new_players.py
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path


def parse_percentage(value):
    """解析百分比字符串为浮点数."""
    if pd.isna(value):
        return 0.0
    value_str = str(value)
    match = re.search(r"([\d.]+)%", value_str)
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
    value_str = str(value).replace(",", "").replace("$", "").replace("€", "").replace("-", "")
    try:
        return int(float(value_str))
    except:
        return 0


def parse_int(value):
    """解析整数，处理各种格式."""
    if pd.isna(value):
        return 0
    value_str = str(value).replace(",", "").replace("-", "")
    try:
        return int(float(value_str))
    except:
        return 0


def clean_new_players_data():
    """清洗新球员数据."""
    print("=" * 80)
    print("🔄 清洗新球员数据")
    print("=" * 80)

    # 读取原始数据 (GBK编码，分号分隔)
    df = pd.read_csv("data/new_players.csv", encoding="gbk", sep=";")
    print(f"\n原始数据: {len(df)} 行, {len(df.columns)} 列")

    # 位置评分映射（中文列名 -> 英文属性名）
    position_ratings_map = {
        "GK 评分": "rating_gk",
        "SW 评分": "rating_sw",
        "DL 评分": "rating_dl",
        "DC 评分": "rating_dc",
        "DR 评分": "rating_dr",
        "WBL 评分": "rating_wbl",
        "WBR 评分": "rating_wbr",
        "DM 评分": "rating_dm",
        "ML 评分": "rating_ml",
        "MC 评分": "rating_mc",
        "MR 评分": "rating_mr",
        "AML 评分": "rating_aml",
        "AMC 评分": "rating_amc",
        "AMR 评分": "rating_amr",
        "FS 评分": "rating_fs",
        "TS 评分": "rating_ts",
        # 潜力评分
        "GK 潜力评分": "potential_gk",
        "SW 潜力评分": "potential_sw",
        "DL 潜力评分": "potential_dl",
        "DC 潜力评分": "potential_dc",
        "DR 潜力评分": "potential_dr",
        "WBL 潜力评分": "potential_wbl",
        "WBR 潜力评分": "potential_wbr",
        "DM 潜力评分": "potential_dm",
        "ML 潜力评分": "potential_ml",
        "MC 潜力评分": "potential_mc",
        "MR 潜力评分": "potential_mr",
        "AML 潜力评分": "potential_aml",
        "AMC 潜力评分": "potential_amc",
        "AMR 潜力评分": "potential_amr",
        "FS 潜力评分": "potential_fs",
        "TS 潜力评分": "potential_ts",
    }

    # 创建新的DataFrame
    cleaned = pd.DataFrame()

    # 1. 基本信息
    print("\n【1】处理基本信息...")
    cleaned["player_id"] = df["UNIQUE ID"]
    cleaned["name"] = df["姓名"]
    cleaned["nationality"] = df["国籍"]
    cleaned["age"] = df["年龄"]
    cleaned["birth_date"] = df["生日"]
    cleaned["position"] = df["位置"]
    cleaned["location"] = df["所在地"]

    # 2. 能力值
    print("【2】处理能力值...")
    cleaned["current_ability"] = df["当前评分"].apply(parse_percentage)
    cleaned["potential_ability"] = df["最高潜力评分"].apply(parse_percentage)
    cleaned["player_role"] = df["球员定位"]
    cleaned["estimated_role"] = df["预估球员定位"]

    # 3. 位置评分（32个字段）- 如果列存在则处理，不存在则填0
    print("【3】处理位置评分（32个字段）...")
    for col_zh, col_en in position_ratings_map.items():
        if col_zh in df.columns:
            cleaned[col_en] = df[col_zh].apply(parse_percentage)
        else:
            print(f"   警告: 列 '{col_zh}' 不存在，填充为0")
            cleaned[col_en] = 0.0

    # 4. 状态属性
    print("【4】处理状态属性...")
    cleaned["fatigue"] = df["疲劳"].apply(parse_int)
    cleaned["stamina"] = df["体力"].apply(parse_percentage)
    cleaned["match_shape"] = df["竞技状态"].apply(parse_percentage)
    cleaned["happiness"] = df["满意程度"].apply(parse_int)

    # 5. 财务信息
    print("【5】处理财务信息...")
    cleaned["wage"] = df["工资"].apply(parse_money)
    cleaned["value"] = df["身价"].apply(parse_money)

    # 6. 经验数据
    print("【6】处理经验数据...")
    cleaned["match_experience"] = df["比赛经验"].apply(parse_percentage)
    cleaned["intl_caps"] = df["国家队出场数"].apply(parse_int)
    cleaned["intl_goals"] = df["国家队进球数"].apply(parse_int)

    # 7. 俱乐部信息
    print("【7】处理俱乐部信息...")
    cleaned["club_name"] = df["俱乐部"]
    cleaned["club_id"] = df["Club ID"]
    cleaned["club_reputation"] = df["球队声望"].apply(parse_money)
    cleaned["squad_status"] = df["所属球队"]
    cleaned["league"] = df["联赛"]

    # 8. 新增字段 - 转会状况（如果存在）
    if "转会状况" in df.columns:
        print("【8】处理转会状况...")
        cleaned["transfer_status"] = df["转会状况"].fillna("")
    else:
        cleaned["transfer_status"] = ""

    # 9. 新增字段 - 合同信息（如果存在）
    if "合同类型" in df.columns:
        print("【9】处理合同信息...")
        cleaned["contract_type"] = df["合同类型"].fillna("")
    else:
        cleaned["contract_type"] = ""

    if "加入的俱乐部" in df.columns:
        cleaned["joined_date"] = df["加入的俱乐部"].fillna("")
    else:
        cleaned["joined_date"] = ""

    if "合同到期日" in df.columns:
        cleaned["contract_end"] = df["合同到期日"].fillna("")
    else:
        cleaned["contract_end"] = ""

    if "最低解约金" in df.columns:
        cleaned["release_clause"] = df["最低解约金"].apply(parse_money)
    else:
        cleaned["release_clause"] = 0

    # 过滤无效俱乐部ID（保留club_id=-1的球员，但标记为自由球员）
    print("\n【10】处理俱乐部数据...")
    invalid_club_mask = (cleaned["club_id"] == -1) | (cleaned["club_id"].isna())
    free_agents = cleaned[invalid_club_mask].copy()
    valid_players = cleaned[~invalid_club_mask].copy()

    print(f"   有效俱乐部球员: {len(valid_players)} 行")
    print(f"   自由球员: {len(free_agents)} 行")

    # 合并回一起，自由球员的club_name标记为"Free Agent"
    cleaned.loc[invalid_club_mask, "club_name"] = "Free Agent"
    cleaned.loc[invalid_club_mask, "squad_status"] = "Free Agent"

    # 保存
    output_path = "data/cleaned/players_cleaned.csv"
    cleaned.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\n✅ 已保存: {output_path}")
    print(f"   总行数: {len(cleaned)}")
    print(f"   字段数: {len(cleaned.columns)}")

    return cleaned


def show_summary(df):
    """显示数据摘要."""
    print("\n" + "=" * 80)
    print("📊 数据摘要")
    print("=" * 80)

    print(f"\n球员数据: {len(df)} 行, {len(df.columns)} 列")
    print("字段分类:")

    fields = {
        "基本信息": [
            "player_id",
            "name",
            "nationality",
            "age",
            "birth_date",
            "position",
            "location",
        ],
        "能力总评": ["current_ability", "potential_ability", "player_role", "estimated_role"],
        "位置评分": [c for c in df.columns if c.startswith("rating_")],
        "位置潜力": [c for c in df.columns if c.startswith("potential_")],
        "状态属性": ["fatigue", "stamina", "match_shape", "happiness"],
        "经验数据": ["match_experience", "intl_caps", "intl_goals"],
        "财务信息": ["wage", "value", "release_clause"],
        "合同信息": ["contract_type", "joined_date", "contract_end"],
        "俱乐部信息": [
            "club_name",
            "club_id",
            "club_reputation",
            "squad_status",
            "league",
            "transfer_status",
        ],
    }

    for category, cols in fields.items():
        existing = [c for c in cols if c in df.columns]
        if existing:
            print(f"  {category}: {len(existing)} 个字段")

    print(f"\n联赛数: {df['league'].nunique()}")
    print(f"俱乐部数: {df['club_id'].nunique()}")

    # 自由球员数
    free_count = len(df[df["club_id"] == -1])
    print(f"自由球员: {free_count} 人")

    # 显示一些示例数据
    print("\n示例球员数据（前3行）:")
    sample_cols = ["player_id", "name", "age", "position", "current_ability", "club_name"]
    print(df[sample_cols].head(3).to_string())


def main():
    """主函数."""
    # 创建输出目录
    Path("data/cleaned").mkdir(parents=True, exist_ok=True)

    # 清洗数据
    players_df = clean_new_players_data()

    # 显示摘要
    show_summary(players_df)

    print("\n" + "=" * 80)
    print("✅ 数据清洗完成!")
    print("=" * 80)
    print(f"\n输出文件: data/cleaned/players_cleaned.csv")


if __name__ == "__main__":
    main()
