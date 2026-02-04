"""Additional enums for player development system."""

from enum import Enum as PyEnum


class PlayerDevelopmentType(PyEnum):
    """球员发展类型 - 决定成长和衰退的时机"""
    EARLY_BLOOMER = "early_bloomer"    # 18-22巅峰，后快速下滑
    STANDARD = "standard"              # 24-28巅峰，最常见
    LATE_BLOOMER = "late_bloomer"      # 27-31巅峰
    CONSISTENT = "consistent"          # 巅峰期长，下滑缓慢


class PlayerSubType(PyEnum):
    """球员子类型 - 基于位置和风格"""
    # 边锋类型
    PACING_WINGER = "pacing_winger"    # 速度型边锋
    TECHNICAL_WINGER = "technical_winger"  # 技术型边锋
    
    # 中场类型
    CREATIVE_PLAYMAKER = "creative_playmaker"  # 组织型中场
    BOX_TO_BOX = "box_to_box"          # 全能型中场
    DEFENSIVE_MIDFIELDER = "defensive_midfielder"  # 防守型中场
    
    # 后卫类型
    BALL_PLAYING_DEFENDER = "ball_playing_defender"  # 出球型后卫
    PURE_DEFENDER = "pure_defender"    # 纯防守型后卫
    
    # 前锋类型
    TARGET_MAN = "target_man"          # 高点型前锋
    POACHER = "poacher"                # 抢点型前锋
    
    # 门将
    SWEEP_KEEPER = "sweep_keeper"      # 门将-出球型
    TRADITIONAL_KEEPER = "traditional_keeper"  # 门将-传统型
