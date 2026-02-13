"""Tactics engine for calculating tactical impact on match simulation.

This module provides the TacticsEngine class that calculates how tactical
decisions affect match outcomes, including passing bonuses, defensive bonuses,
attacking bonuses, and player role performance.
"""

from typing import Dict, Optional, Tuple, Any
from enum import Enum

from fm_manager.core.models.tactics import (
    TacticalFormation,
    TacticalInstructions,
    PlayerRole,
    PlayStyle,
    DefensiveLine,
    PressingIntensity,
    PassingStyle,
    RoleManager,
)
from fm_manager.core.models.player import Player, Position


class TacticsEngine:
    """Calculate tactical impact on match outcomes.
    
    This engine computes various bonuses and modifiers based on tactical
    settings, translating high-level tactical decisions into match-level
    probability adjustments.
    """
    
    # 逼抢强度 -> 拦截概率加成
    PRESSING_INTERCEPTION_BONUS = {
        PressingIntensity.EXTREME: 1.30,
        PressingIntensity.HIGH: 1.15,
        PressingIntensity.MEDIUM: 1.00,
        PressingIntensity.LOW: 0.85,
        PressingIntensity.MINIMAL: 0.70,
    }
    
    # 防线高度 -> 反击风险加成
    COUNTER_ATTACK_RISK = {
        DefensiveLine.VERY_HIGH: 1.40,  # 高位容易被反击
        DefensiveLine.HIGH: 1.20,
        DefensiveLine.MEDIUM: 1.00,
        DefensiveLine.LOW: 0.80,
        DefensiveLine.VERY_LOW: 0.60,
    }
    
    # 防线高度 -> 防线紧凑度 (影响防守效率)
    DEFENSIVE_COMPACTNESS = {
        DefensiveLine.VERY_HIGH: 0.85,  # 高位防线空间较大
        DefensiveLine.HIGH: 0.90,
        DefensiveLine.MEDIUM: 1.00,
        DefensiveLine.LOW: 1.10,
        DefensiveLine.VERY_LOW: 1.15,  # 低位防线更紧凑
    }
    
    # 传球风格 -> 传球成功率加成
    PASSING_STYLE_BONUS = {
        PassingStyle.VERY_SHORT: 1.12,   # 极短传成功率高
        PassingStyle.SHORT: 1.06,        # 短传成功率高
        PassingStyle.MIXED: 1.00,        # 混合标准
        PassingStyle.LONG: 0.94,         # 长传成功率较低
        PassingStyle.VERY_LONG: 0.88,    # 极长传成功率低
    }
    
    # 传球风格 -> 向前传球倾向
    PASSING_FORWARD_TENDENCY = {
        PassingStyle.VERY_SHORT: 0.70,   # 倾向于安全传球
        PassingStyle.SHORT: 0.80,
        PassingStyle.MIXED: 1.00,
        PassingStyle.LONG: 1.25,         # 倾向于向前长传
        PassingStyle.VERY_LONG: 1.40,
    }
    
    # 比赛风格 -> 整体战术加成
    PLAYSTYLE_MODIFIERS = {
        PlayStyle.POSSESSION: {
            "passing": 1.08,
            "defensive": 0.95,
            "attacking": 0.95,
            "counter_attack": 0.70,
        },
        PlayStyle.TIKI_TAKA: {
            "passing": 1.12,
            "defensive": 0.90,
            "attacking": 0.92,
            "counter_attack": 0.60,
        },
        PlayStyle.HIGH_PRESS: {
            "passing": 0.98,
            "defensive": 1.10,
            "attacking": 1.05,
            "counter_attack": 1.10,
        },
        PlayStyle.GEGENPRESSING: {
            "passing": 0.95,
            "defensive": 1.15,
            "attacking": 1.08,
            "counter_attack": 1.15,
        },
        PlayStyle.COUNTER_ATTACK: {
            "passing": 0.92,
            "defensive": 1.05,
            "attacking": 1.12,
            "counter_attack": 1.25,
        },
        PlayStyle.DIRECT: {
            "passing": 0.95,
            "defensive": 1.00,
            "attacking": 1.08,
            "counter_attack": 1.15,
        },
        PlayStyle.ROUTE_ONE: {
            "passing": 0.88,
            "defensive": 1.02,
            "attacking": 1.05,
            "counter_attack": 1.10,
        },
        PlayStyle.LOW_BLOCK: {
            "passing": 0.95,
            "defensive": 1.12,
            "attacking": 0.88,
            "counter_attack": 1.05,
        },
        PlayStyle.PARK_BUS: {
            "passing": 0.88,
            "defensive": 1.18,
            "attacking": 0.75,
            "counter_attack": 0.80,
        },
        PlayStyle.FLUID: {
            "passing": 1.05,
            "defensive": 0.98,
            "attacking": 1.05,
            "counter_attack": 1.00,
        },
    }
    
    def __init__(self):
        """Initialize the tactics engine."""
        self.role_manager = RoleManager()
    
    def calculate_passing_bonus(self, tactics) -> float:
        """Calculate passing success rate bonus based on tactics.
        
        Args:
            tactics: Team's tactical formation or TacticalInstructions
            
        Returns:
            Multiplier for passing success rate (0.7 - 1.3)
        """
        if not tactics:
            return 1.0
        
        # Support both TacticalFormation and TacticalInstructions
        if hasattr(tactics, 'instructions'):
            instructions = tactics if not hasattr(tactics, "instructions") else tactics.instructions
        else:
            instructions = tactics
        
        if not instructions:
            return 1.0
        bonus = 1.0
        
        # 传球风格影响
        bonus *= self.PASSING_STYLE_BONUS.get(instructions.passing_style, 1.0)
        
        # 逼抢强度影响 (高强度逼抢下传球更匆忙)
        pressing_factor = 1.0 - (instructions.pressing.value - 3) * 0.02
        bonus *= max(0.92, pressing_factor)
        
        # 比赛风格影响
        if hasattr(tactics, 'play_style') and tactics.play_style and tactics.play_style in self.PLAYSTYLE_MODIFIERS:
            bonus *= self.PLAYSTYLE_MODIFIERS[tactics.play_style]["passing"]
        
        # 节奏影响 (快节奏降低传球精度)
        tempo_factor = 1.0 - (instructions.tempo.value - 3) * 0.015
        bonus *= max(0.94, tempo_factor)
        
        return round(max(0.70, min(1.30, bonus)), 3)
    
    def calculate_defensive_bonus(self, tactics) -> float:
        """Calculate defensive effectiveness bonus based on tactics.
        
        Args:
            tactics: Team's tactical formation
            
        Returns:
            Multiplier for defensive effectiveness (0.8 - 1.25)
        """
        if not tactics:
            return 1.0
        
        instructions = tactics if not hasattr(tactics, "instructions") else tactics.instructions
        bonus = 1.0
        
        # 逼抢强度加成 (高强度逼抢增加拦截概率)
        bonus *= self.PRESSING_INTERCEPTION_BONUS.get(instructions.pressing, 1.0)
        
        # 防线高度影响防线紧凑度
        bonus *= self.DEFENSIVE_COMPACTNESS.get(instructions.defensive_line, 1.0)
        
        # 宽度影响 (窄阵型更紧凑)
        if instructions.width.value <= 2:
            bonus *= 1.05
        elif instructions.width.value >= 5:
            bonus *= 0.95
        
        # 比赛风格影响
        if hasattr(tactics, "play_style") and tactics.play_style and tactics.play_style in self.PLAYSTYLE_MODIFIERS:
            bonus *= self.PLAYSTYLE_MODIFIERS[tactics.play_style]["defensive"]
        
        return round(max(0.80, min(1.25, bonus)), 3)
    
    def calculate_attacking_bonus(self, tactics: TacticalFormation) -> float:
        """Calculate attacking effectiveness bonus based on tactics.
        
        Args:
            tactics: Team's tactical formation
            
        Returns:
            Multiplier for attacking effectiveness (0.75 - 1.20)
        """
        if not tactics:
            return 1.0
        
        instructions = tactics if not hasattr(tactics, "instructions") else tactics.instructions
        bonus = 1.0
        
        # 宽度影响进攻宽度
        if instructions.width.value >= 4:
            bonus *= 1.06  # 宽阵型增加进攻威胁
        elif instructions.width.value <= 2:
            bonus *= 0.95  # 窄阵型降低进攻威胁
        
        # 防线高度风险 (高位防线增加进攻球员数量)
        if instructions.defensive_line.value >= 4:
            bonus *= 1.04
        
        # 传球风格影响进攻流畅度
        bonus *= self.PASSING_FORWARD_TENDENCY.get(instructions.passing_style, 1.0)
        
        # 比赛风格影响
        if hasattr(tactics, "play_style") and tactics.play_style and tactics.play_style in self.PLAYSTYLE_MODIFIERS:
            bonus *= self.PLAYSTYLE_MODIFIERS[tactics.play_style]["attacking"]
        
        return round(max(0.75, min(1.20, bonus)), 3)
    
    def calculate_counter_attack_risk(self, tactics: TacticalFormation) -> float:
        """Calculate vulnerability to counter-attacks based on defensive line.
        
        Args:
            tactics: Team's tactical formation
            
        Returns:
            Risk multiplier for counter-attacks (0.6 - 1.4)
        """
        if not tactics:
            return 1.0
        
        return self.COUNTER_ATTACK_RISK.get(tactics.instructions.defensive_line, 1.0)
    
    def calculate_role_bonus(
        self, 
        player: Any, 
        role: Optional[PlayerRole],
        action_type: str = "general"
    ) -> float:
        """Calculate player performance bonus in a specific role.
        
        Args:
            player: Player object with attributes
            role: Assigned player role
            action_type: Type of action (passing, shooting, defending, etc.)
            
        Returns:
            Performance multiplier (0.8 - 1.3)
        """
        if not role:
            return 1.0
        
        # 获取角色档案
        profile = self.role_manager.get_role_profile(role)
        if not profile:
            return 1.0
        
        # 获取球员属性
        player_attrs = self._extract_player_attributes(player)
        
        # 计算角色适配度分数
        score, details = self.role_manager.calculate_role_score(
            role, player_attrs, getattr(player, 'position', None)
        )
        
        # 将分数转换为加成 (60分=0.95, 80分=1.05, 100分=1.15)
        base_bonus = 0.85 + (score / 100.0) * 0.30
        
        # 根据行动类型调整
        action_modifier = self._get_action_modifier(role, action_type)
        
        return round(max(0.80, min(1.30, base_bonus * action_modifier)), 3)
    
    def _extract_player_attributes(self, player: Any) -> Dict[str, float]:
        """Extract player attributes for role evaluation.
        
        Args:
            player: Player object
            
        Returns:
            Dictionary of attribute names to values
        """
        attrs = {}
        
        # 标准属性映射
        attribute_mapping = {
            # 技术属性
            "passing": ["passing", "传球"],
            "vision": ["vision", "视野"],
            "technique": ["technique", "技术", "dribbling"],
            "finishing": ["finishing", "射门"],
            "crossing": ["crossing", "传中"],
            "first_touch": ["first_touch", "停球"],
            # 身体属性
            "pace": ["pace", "速度"],
            "acceleration": ["acceleration", "加速"],
            "stamina": ["stamina", "耐力", "体能"],
            "strength": ["strength", "强壮"],
            "jumping": ["jumping", "弹跳"],
            # 防守属性
            "tackling": ["tackling", "抢断"],
            "marking": ["marking", "盯人"],
            "positioning": ["positioning", "位置感"],
            # 精神属性
            "decisions": ["decisions", "决断"],
            "creativity": ["creativity", "想象力", "flair"],
            "off_the_ball": ["off_the_ball", "无球跑"],
            "anticipation": ["anticipation", "预判"],
            "work_rate": ["work_rate", "工作投入"],
            "teamwork": ["teamwork", "团队合作"],
            "aggression": ["aggression", "侵略性"],
            "composure": ["composure", "镇定"],
            "concentration": ["concentration", "集中"],
            "bravery": ["bravery", "勇敢"],
            # 门将属性
            "command_of_area": ["command_of_area", "指挥防守"],
            "rushing_out": ["rushing_out", "出击"],
            "reflexes": ["reflexes", "反应"],
            "handling": ["handling", "手抛球"],
            "one_on_one": ["one_on_one", "一对一"],
            "communication": ["communication", "沟通"],
        }
        
        for standard_name, possible_names in attribute_mapping.items():
            for name in possible_names:
                value = getattr(player, name, None)
                if value is not None:
                    try:
                        attrs[standard_name] = float(value)
                        break
                    except (ValueError, TypeError):
                        continue
        
        return attrs
    
    def _get_action_modifier(self, role: PlayerRole, action_type: str) -> float:
        """Get modifier for specific action type based on role.
        
        Args:
            role: Player role
            action_type: Type of action
            
        Returns:
            Modifier multiplier
        """
        # 角色-行动加成映射
        role_action_bonus = {
            # 传球相关
            (PlayerRole.PLAYMAKER, "passing"): 1.15,
            (PlayerRole.DEEP_LYING_PLAYMAKER, "passing"): 1.12,
            (PlayerRole.WIDE_PLAYMAKER, "passing"): 1.10,
            (PlayerRole.REGISTA, "passing"): 1.15,
            
            # 射门相关
            (PlayerRole.POACHER, "shooting"): 1.15,
            (PlayerRole.COMPLETE_FORWARD, "shooting"): 1.08,
            (PlayerRole.INSIDE_FORWARD, "shooting"): 1.10,
            (PlayerRole.TREQUARTISTA, "shooting"): 1.08,
            
            # 防守相关
            (PlayerRole.BALL_WINNING_MIDFIELDER, "defending"): 1.15,
            (PlayerRole.ANCHOR_MAN, "defending"): 1.12,
            (PlayerRole.STOPPER, "defending"): 1.10,
            (PlayerRole.COVER, "defending"): 1.08,
            (PlayerRole.PRESSING_FORWARD, "defending"): 1.12,
            
            # 盘带相关
            (PlayerRole.TREQUARTISTA, "dribbling"): 1.12,
            (PlayerRole.INSIDE_FORWARD, "dribbling"): 1.10,
            (PlayerRole.MEZZALA, "dribbling"): 1.08,
            (PlayerRole.WINGER, "dribbling"): 1.08,
        }
        
        return role_action_bonus.get((role, action_type), 1.0)
    
    def calculate_tactical_matchup(
        self, 
        att_tactics: TacticalFormation, 
        def_tactics: TacticalFormation
    ) -> Dict[str, float]:
        """Calculate tactical matchup effects between two teams.
        
        Args:
            att_tactics: Attacking team's tactics
            def_tactics: Defending team's tactics
            
        Returns:
            Dictionary of matchup effects
        """
        effects = {
            "attacking_bonus": 1.0,
            "defensive_bonus": 1.0,
            "counter_attack_risk": 1.0,
        }
        
        if not att_tactics or not def_tactics:
            return effects
        
        # 进攻方宽度 vs 防守方宽度
        if (att_tactics.instructions and def_tactics.instructions):
            att_width = att_tactics.instructions.width.value
            def_width = def_tactics.instructions.width.value
            
            # 宽进攻 vs 窄防守 = 边路优势
            if att_width > def_width + 1:
                effects["attacking_bonus"] *= 1.06
            # 窄进攻 vs 宽防守 = 中路优势 (较小)
            elif def_width > att_width + 1:
                effects["attacking_bonus"] *= 1.03
        
        # 高位逼抢 vs 从后场组织
        if (att_tactics.instructions and def_tactics.instructions):
            if (att_tactics.instructions.pressing.value >= 4 and 
                def_tactics.instructions.play_out_of_defence):
                effects["defensive_bonus"] *= 1.08
        
        # 反击战术 vs 高位防线
        if (att_tactics.play_style == PlayStyle.COUNTER_ATTACK and 
            def_tactics.instructions and 
            def_tactics.instructions.defensive_line.value >= 4):
            effects["counter_attack_risk"] *= 1.15
        
        return effects
    
    def get_zone_transition_modifier(
        self, 
        tactics: TacticalFormation,
        current_zone: str,
        target_zone: str
    ) -> float:
        """Get probability modifier for zone transitions based on tactics.
        
        Args:
            tactics: Team's tactical formation
            current_zone: Current pitch zone
            target_zone: Target pitch zone
            
        Returns:
            Probability modifier
        """
        if not tactics:
            return 1.0
        
        modifier = 1.0
        instructions = tactics if not hasattr(tactics, "instructions") else tactics.instructions
        
        # 宽度影响边路进攻倾向
        is_wide_move = any(x in target_zone for x in ["THIRD", "BOX"])
        
        if instructions.width.value >= 4 and is_wide_move:
            # 宽阵型鼓励边路进攻
            modifier *= 1.10
        elif instructions.width.value <= 2 and is_wide_move:
            # 窄阵型减少边路进攻
            modifier *= 0.90
        
        # 传球风格影响向前传球
        if "AWAY" in target_zone and "HOME" in current_zone:
            # 向前进攻
            modifier *= self.PASSING_FORWARD_TENDENCY.get(
                instructions.passing_style, 1.0
            )
        
        # 比赛风格影响
        if tactics.play_style == PlayStyle.COUNTER_ATTACK:
            # 反击风格更快向前
            if "AWAY" in target_zone:
                modifier *= 1.15
        elif tactics.play_style == PlayStyle.POSSESSION:
            # 控球风格更谨慎
            if "AWAY" in target_zone:
                modifier *= 0.92
        
        return round(modifier, 3)


# ============================================================================
# 便捷函数
# ============================================================================

def get_tactics_engine() -> TacticsEngine:
    """Get a tactics engine instance."""
    return TacticsEngine()


def calculate_match_tactics_impact(
    home_tactics: TacticalFormation,
    away_tactics: TacticalFormation,
) -> Dict[str, Dict[str, float]]:
    """Calculate complete tactical impact for a match.
    
    Args:
        home_tactics: Home team's tactical formation
        away_tactics: Away team's tactical formation
        
    Returns:
        Dictionary with tactical impacts for both teams
    """
    engine = TacticsEngine()
    
    return {
        "home": {
            "passing_bonus": engine.calculate_passing_bonus(home_tactics),
            "defensive_bonus": engine.calculate_defensive_bonus(home_tactics),
            "attacking_bonus": engine.calculate_attacking_bonus(home_tactics),
            "counter_attack_risk": engine.calculate_counter_attack_risk(home_tactics),
        },
        "away": {
            "passing_bonus": engine.calculate_passing_bonus(away_tactics),
            "defensive_bonus": engine.calculate_defensive_bonus(away_tactics),
            "attacking_bonus": engine.calculate_attacking_bonus(away_tactics),
            "counter_attack_risk": engine.calculate_counter_attack_risk(away_tactics),
        },
        "matchup": engine.calculate_tactical_matchup(home_tactics, away_tactics),
    }


__all__ = [
    "TacticsEngine",
    "get_tactics_engine",
    "calculate_match_tactics_impact",
]