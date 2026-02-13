#!/usr/bin/env python3
"""青训和球员发展系统完善

新增功能:
1. 球员月度成长报告
2. 青训营具体产出机制
3. 球员潜力波动模拟
4. 教练对特定属性提升的影响
"""

import random
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum

from fm_manager.core.models.player import Player, Position
from fm_manager.core.models.staff import Staff, StaffRole
from fm_manager.core.models.facility import Facility, FacilityType


class DevelopmentFocus(Enum):
    """发展重点"""
    BALANCED = "balanced"
    TECHNICAL = "technical"
    PHYSICAL = "physical"
    MENTAL = "mental"
    DEFENSIVE = "defensive"
    ATTACKING = "attacking"


@dataclass
class PlayerDevelopmentReport:
    """球员发展报告"""
    player_id: int
    player_name: str
    month: str
    
    # 属性变化
    attribute_changes: Dict[str, float]
    
    # 总体发展
    ca_change: int
    pa_change: int
    
    # 发展评价
    development_rating: str  # excellent, good, average, poor
    
    # 影响因素
    training_quality: float
    match_experience: float
    coach_bonus: float
    
    # 建议
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "month": self.month,
            "attribute_changes": self.attribute_changes,
            "ca_change": self.ca_change,
            "pa_change": self.pa_change,
            "development_rating": self.development_rating,
            "training_quality": self.training_quality,
            "recommendations": self.recommendations
        }


class YouthAcademyProduction:
    """青训营产出机制"""
    
    def __init__(self, facility_level: int, head_coach: Optional[Staff] = None):
        self.facility_level = facility_level
        self.head_coach = head_coach
    
    def generate_youth_player(self, age: int = 16) -> Dict:
        """生成青训球员"""
        
        # 基础质量由设施等级决定
        base_quality = 40 + (self.facility_level * 2)  # 42-80
        
        # 教练加成
        coach_bonus = 0
        if self.head_coach:
            coach_bonus = (self.head_coach.coaching_ability - 50) / 5  # -4 to +10
        
        # 随机波动
        random_variation = random.uniform(-10, 10)
        
        ca = int(base_quality + coach_bonus + random_variation)
        ca = max(30, min(90, ca))
        
        # PA基于CA + 潜力
        potential_gap = random.randint(10, 40)
        pa = min(200, ca + potential_gap)
        
        # 确定位置 (青训偏好某些位置)
        position_weights = {
            Position.ST: 15,
            Position.CF: 10,
            Position.LW: 10,
            Position.RW: 10,
            Position.CAM: 12,
            Position.CM: 15,
            Position.CDM: 12,
            Position.LB: 8,
            Position.RB: 8,
            Position.CB: 10
        }
        
        position = random.choices(
            list(position_weights.keys()),
            weights=list(position_weights.values())
        )[0]
        
        return {
            "age": age,
            "ca": ca,
            "pa": pa,
            "position": position,
            "potential_gap": potential_gap,
            "quality_rating": self._rate_quality(ca, pa)
        }
    
    def _rate_quality(self, ca: int, pa: int) -> str:
        """评价球员质量"""
        if pa >= 160:
            return "世界级潜力"
        elif pa >= 140:
            return "优秀潜力"
        elif pa >= 120:
            return "良好潜力"
        else:
            return "普通潜力"
    
    def calculate_monthly_output(self) -> int:
        """计算每月青训产出数量"""
        # Level 1: 0-1人, Level 20: 3-5人
        base_output = 1 + (self.facility_level // 10)
        random_bonus = random.randint(0, 1)
        return base_output + random_bonus


class PlayerDevelopmentSystem:
    """球员发展系统"""
    
    def __init__(self):
        self.focus_multipliers = {
            DevelopmentFocus.TECHNICAL: {
                "passing": 1.3, "dribbling": 1.3, "first_touch": 1.2,
                "pace": 0.9, "strength": 0.9
            },
            DevelopmentFocus.PHYSICAL: {
                "pace": 1.3, "strength": 1.3, "stamina": 1.2,
                "passing": 0.9, "vision": 0.9
            },
            DevelopmentFocus.MENTAL: {
                "vision": 1.3, "decisions": 1.3, "positioning": 1.2,
                "pace": 0.9, "dribbling": 0.9
            },
            DevelopmentFocus.DEFENSIVE: {
                "tackling": 1.3, "marking": 1.3, "positioning": 1.2,
                "shooting": 0.8, "dribbling": 0.9
            },
            DevelopmentFocus.ATTACKING: {
                "shooting": 1.3, "dribbling": 1.2, "passing": 1.1,
                "tackling": 0.8, "marking": 0.8
            },
            DevelopmentFocus.BALANCED: {
                # 所有属性1.0
            }
        }
    
    def generate_monthly_report(
        self,
        player: Player,
        training_facility_level: int,
        coaches: List[Staff],
        matches_played: int = 0,
        focus: DevelopmentFocus = DevelopmentFocus.BALANCED
    ) -> PlayerDevelopmentReport:
        """生成月度发展报告"""
        
        # 计算训练质量
        training_quality = self._calculate_training_quality(
            training_facility_level, coaches
        )
        
        # 计算属性变化
        attribute_changes = self._calculate_attribute_changes(
            player, training_quality, matches_played, focus
        )
        
        # 计算CA变化
        ca_change = self._calculate_ca_change(
            player, attribute_changes, training_quality
        )
        
        # 计算PA变化 (潜力可能上下波动)
        pa_change = self._calculate_pa_change(player, training_quality)
        
        # 评价发展
        development_rating = self._rate_development(ca_change, training_quality)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            player, attribute_changes, focus
        )
        
        return PlayerDevelopmentReport(
            player_id=player.id,
            player_name=player.full_name,
            month=datetime.now().strftime("%Y-%m"),
            attribute_changes=attribute_changes,
            ca_change=ca_change,
            pa_change=pa_change,
            development_rating=development_rating,
            training_quality=training_quality,
            match_experience=min(matches_played * 0.1, 1.0),
            coach_bonus=self._calculate_coach_bonus(coaches),
            recommendations=recommendations
        )
    
    def _calculate_training_quality(
        self,
        facility_level: int,
        coaches: List[Staff]
    ) -> float:
        """计算训练质量 (0.0 - 1.0)"""
        
        # 设施贡献 (40%)
        facility_contribution = facility_level / 20 * 0.4
        
        # 教练贡献 (60%)
        if coaches:
            avg_coaching = sum(c.coaching_ability for c in coaches) / len(coaches)
            coach_contribution = (avg_coaching / 100) * 0.6
        else:
            coach_contribution = 0.3  # 默认教练
        
        return min(1.0, facility_contribution + coach_contribution)
    
    def _calculate_attribute_changes(
        self,
        player: Player,
        training_quality: float,
        matches_played: int,
        focus: DevelopmentFocus
    ) -> Dict[str, float]:
        """计算属性变化"""
        
        changes = {}
        
        # 基础成长率 (年轻长得快)
        age_factor = max(0.2, 1.0 - (player.age - 16) * 0.05)
        
        # 比赛经验加成
        match_bonus = min(matches_played * 0.02, 0.2)
        
        # 潜力空间 (接近PA时成长慢)
        potential_room = (player.potential_ability - player.current_ability) / 100
        potential_factor = max(0.1, potential_room)
        
        # 各属性成长
        focus_multipliers = self.focus_multipliers.get(focus, {})
        
        attributes = ["pace", "shooting", "passing", "dribbling", "defending", "physical"]
        for attr in attributes:
            base_growth = random.uniform(0.1, 0.5)
            multiplier = focus_multipliers.get(attr, 1.0)
            
            change = (
                base_growth *
                training_quality *
                age_factor *
                potential_factor *
                multiplier +
                match_bonus
            )
            
            changes[attr] = round(change, 2)
        
        return changes
    
    def _calculate_ca_change(
        self,
        player: Player,
        attribute_changes: Dict[str, float],
        training_quality: float
    ) -> int:
        """计算CA变化"""
        
        avg_change = sum(attribute_changes.values()) / len(attribute_changes)
        ca_change = int(avg_change * training_quality * 2)
        
        # 确保不超过PA
        max_ca = player.potential_ability
        if player.current_ability + ca_change > max_ca:
            ca_change = max_ca - player.current_ability
        
        return max(0, ca_change)
    
    def _calculate_pa_change(self, player: Player, training_quality: float) -> int:
        """计算PA变化 (潜力可能重新评估)"""
        
        # 小幅波动 (-2 to +2)
        if random.random() < 0.1 * training_quality:  # 10%概率重新评估
            return random.randint(-2, 2)
        return 0
    
    def _rate_development(self, ca_change: int, training_quality: float) -> str:
        """评价发展水平"""
        
        if ca_change >= 3 and training_quality >= 0.8:
            return "excellent"
        elif ca_change >= 2 and training_quality >= 0.6:
            return "good"
        elif ca_change >= 1:
            return "average"
        else:
            return "poor"
    
    def _calculate_coach_bonus(self, coaches: List[Staff]) -> float:
        """计算教练加成"""
        
        if not coaches:
            return 0.0
        
        avg_ability = sum(c.coaching_ability for c in coaches) / len(coaches)
        return (avg_ability - 50) / 100  # -0.5 to +0.5
    
    def _generate_recommendations(
        self,
        player: Player,
        attribute_changes: Dict[str, float],
        current_focus: DevelopmentFocus
    ) -> List[str]:
        """生成发展建议"""
        
        recommendations = []
        
        # 找出成长最慢的属性
        weakest_attr = min(attribute_changes.items(), key=lambda x: x[1])
        if weakest_attr[1] < 0.2:
            recommendations.append(f"建议加强{weakest_attr[0]}训练")
        
        # 年龄相关建议
        if player.age < 20:
            recommendations.append("年轻球员，成长潜力大，建议多给比赛机会")
        elif player.age > 28:
            recommendations.append("球员进入成熟期，重点保持状态")
        
        # 潜力相关
        if player.potential_ability - player.current_ability > 30:
            recommendations.append("潜力尚未完全开发，建议增加训练强度")
        
        return recommendations[:3]  # 最多3条建议


class ContractNegotiationSystem:
    """合同谈判系统"""
    
    def __init__(self):
        self.wage_multipliers = {
            "star": 2.5,
            "first_team": 1.5,
            "squad": 1.0,
            "prospect": 0.6,
            "youth": 0.3
        }
    
    def calculate_wage_demand(
        self,
        player: Player,
        role: str = "squad",
        club_reputation: int = 3000
    ) -> Tuple[int, int]:
        """计算球员薪资要求 (周薪范围)"""
        
        # 基础薪资由CA决定
        base_wages = {
            (80, 100): 50000,
            (70, 80): 25000,
            (60, 70): 12000,
            (50, 60): 6000,
            (40, 50): 3000,
            (0, 40): 1500
        }
        
        ca = player.current_ability
        base_wage = 3000  # 默认值
        for (min_ca, max_ca), wage in base_wages.items():
            if min_ca <= ca <= max_ca:
                base_wage = wage
                break
        
        # 角色调整
        role_multiplier = self.wage_multipliers.get(role, 1.0)
        
        # 年龄调整 (巅峰期薪资要求高)
        if 25 <= player.age <= 30:
            age_multiplier = 1.2
        elif player.age < 22:
            age_multiplier = 0.8
        elif player.age > 32:
            age_multiplier = 0.7
        else:
            age_multiplier = 1.0
        
        # 俱乐部声誉调整
        reputation_multiplier = 0.8 + (club_reputation / 10000) * 0.4
        
        min_wage = int(base_wage * role_multiplier * age_multiplier * 0.9)
        max_wage = int(base_wage * role_multiplier * age_multiplier * 1.1 * reputation_multiplier)
        
        return min_wage, max_wage
    
    def negotiate_contract(
        self,
        player: Player,
        offered_wage: int,
        offered_years: int,
        release_clause: Optional[int] = None,
        player_loyalty: int = 50
    ) -> Dict:
        """模拟合同谈判"""
        
        min_wage, max_wage = self.calculate_wage_demand(player)
        
        # 计算满意度
        if offered_wage >= max_wage:
            satisfaction = 100
            acceptance = True
        elif offered_wage >= min_wage:
            satisfaction = 60 + (offered_wage - min_wage) / (max_wage - min_wage) * 40
            acceptance = satisfaction > 70 or random.random() < satisfaction / 100
        else:
            satisfaction = max(0, (offered_wage / min_wage) * 60)
            acceptance = False
        
        # 忠诚度影响
        if player_loyalty > 70:
            acceptance = acceptance or satisfaction > 50
        
        return {
            "accepted": acceptance,
            "satisfaction": int(satisfaction),
            "wage_range": (min_wage, max_wage),
            "counter_offer": None if acceptance else int(min_wage * 1.1),
            "message": self._generate_negotiation_message(acceptance, satisfaction)
        }
    
    def _generate_negotiation_message(self, accepted: bool, satisfaction: int) -> str:
        """生成谈判消息"""
        
        if accepted and satisfaction >= 80:
            return "非常高兴接受这份合同！"
        elif accepted:
            return "合同可以接受。"
        elif satisfaction >= 40:
            return "薪资需要再商量。"
        else:
            return "这份报价远低于我的期望。"


# 导出主要类
__all__ = [
    "YouthAcademyProduction",
    "PlayerDevelopmentSystem",
    "PlayerDevelopmentReport",
    "DevelopmentFocus",
    "ContractNegotiationSystem"
]
