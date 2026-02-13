#!/usr/bin/env python3
"""AI对手个性化系统

新增功能:
1. AI经理性格系统
2. AI战术适应性
3. AI转会策略个性化
4. AI与玩家互动
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from fm_manager.core.models.tactics import PlayStyle, Formation
from fm_manager.core.models.player import Position


class ManagerPersonality(Enum):
    """AI经理性格类型"""
    ATTACKING = "attacking"         # 进攻型 - 偏好进攻战术，高风险高回报
    DEFENSIVE = "defensive"         # 防守型 - 偏好稳固防守，谨慎保守
    BALANCED = "balanced"           # 平衡型 - 攻守均衡，灵活多变
    PRAGMATIC = "pragmatic"         # 务实型 - 根据对手调整，结果导向
    TIKI_TAKA = "tiki_taka"         # 传控型 - 偏好控球，技术流
    COUNTER_ATTACK = "counter"      # 反击型 - 偏好快速反击，效率优先


class RiskTolerance(Enum):
    """风险承受度"""
    VERY_LOW = 1    # 极低 - 从不冒险
    LOW = 2         # 低 - 很少冒险
    MEDIUM = 3      # 中等 - 适度冒险
    HIGH = 4        # 高 - 经常冒险
    VERY_HIGH = 5   # 极高 - 总是冒险


@dataclass
class AIManagerProfile:
    """AI经理档案"""
    manager_id: int
    name: str
    personality: ManagerPersonality
    risk_tolerance: RiskTolerance
    
    # 战术偏好
    preferred_style: PlayStyle
    preferred_formation: Formation
    alternative_formations: List[Formation] = field(default_factory=list)
    
    # 转会策略
    transfer_aggression: int  # 1-10
    youth_preference: int     # 1-10
    wage_tolerance: int       # 1-10
    
    # 比赛管理
    rotation_frequency: int   # 1-10
    sub_timing: str           # "early", "normal", "late"
    
    # 与玩家互动
    rivalry_level: int        # 0-10
    media_friendliness: int   # 1-10
    
    # 历史数据
    career_stats: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "manager_id": self.manager_id,
            "name": self.name,
            "personality": self.personality.value,
            "risk_tolerance": self.risk_tolerance.value,
            "preferred_style": self.preferred_style.value if hasattr(self.preferred_style, 'value') else str(self.preferred_style),
            "transfer_aggression": self.transfer_aggression,
            "youth_preference": self.youth_preference
        }


class AIPersonalityGenerator:
    """AI性格生成器"""
    
    PERSONALITY_TRAITS = {
        ManagerPersonality.ATTACKING: {
            "styles": [PlayStyle.HIGH_PRESS, PlayStyle.DIRECT, PlayStyle.FLUID],
            "formations": ["4-3-3", "4-2-4", "3-4-3"],
            "risk": RiskTolerance.HIGH,
            "transfer_aggression": (7, 10),
            "sub_timing": "early"
        },
        ManagerPersonality.DEFENSIVE: {
            "styles": [PlayStyle.LOW_BLOCK, PlayStyle.PARK_BUS, PlayStyle.COUNTER_ATTACK],
            "formations": ["5-4-1", "4-5-1", "5-3-2"],
            "risk": RiskTolerance.LOW,
            "transfer_aggression": (3, 6),
            "sub_timing": "late"
        },
        ManagerPersonality.BALANCED: {
            "styles": [PlayStyle.POSSESSION, PlayStyle.COUNTER_ATTACK],
            "formations": ["4-3-3", "4-2-3-1", "4-4-2"],
            "risk": RiskTolerance.MEDIUM,
            "transfer_aggression": (5, 7),
            "sub_timing": "normal"
        },
        ManagerPersonality.PRAGMATIC: {
            "styles": [PlayStyle.COUNTER_ATTACK, PlayStyle.DIRECT],
            "formations": ["4-4-2", "4-2-3-1", "4-1-4-1"],
            "risk": RiskTolerance.MEDIUM,
            "transfer_aggression": (5, 8),
            "sub_timing": "normal"
        },
        ManagerPersonality.TIKI_TAKA: {
            "styles": [PlayStyle.TIKI_TAKA, PlayStyle.POSSESSION],
            "formations": ["4-3-3", "4-1-4-1", "3-4-3"],
            "risk": RiskTolerance.MEDIUM,
            "transfer_aggression": (6, 9),
            "sub_timing": "early"
        },
        ManagerPersonality.COUNTER_ATTACK: {
            "styles": [PlayStyle.COUNTER_ATTACK, PlayStyle.LOW_BLOCK],
            "formations": ["4-4-2", "4-1-4-1", "3-5-2"],
            "risk": RiskTolerance.LOW,
            "transfer_aggression": (4, 7),
            "sub_timing": "late"
        }
    }
    
    MANAGER_NAMES = [
        "Guardiola", "Mourinho", "Klopp", "Ancelotti", "Conte",
        "Simeone", "Tuchel", "Arteta", "Ten Hag", "Pochettino",
        "Rodgers", "Potter", "Howe", "Emery", "Lampard",
        "Gerrard", "Rooney", "Nagelsmann", "Alonso", "Xavi"
    ]
    
    @classmethod
    def generate_random_profile(cls, manager_id: int) -> AIManagerProfile:
        """生成随机AI经理档案"""
        
        personality = random.choice(list(ManagerPersonality))
        traits = cls.PERSONALITY_TRAITS[personality]
        
        return AIManagerProfile(
            manager_id=manager_id,
            name=random.choice(cls.MANAGER_NAMES),
            personality=personality,
            risk_tolerance=traits["risk"],
            preferred_style=random.choice(traits["styles"]),
            preferred_formation=random.choice(traits["formations"]),
            alternative_formations=random.sample(traits["formations"], 
n                                                  min(2, len(traits["formations"]))),
            transfer_aggression=random.randint(*traits["transfer_aggression"]),
            youth_preference=random.randint(1, 10),
            wage_tolerance=random.randint(3, 8),
            rotation_frequency=random.randint(3, 8),
            sub_timing=traits["sub_timing"],
            rivalry_level=random.randint(0, 7),
            media_friendliness=random.randint(3, 9)
        )
    
    @classmethod
    def generate_profile_by_reputation(cls, manager_id: int, reputation: int) -> AIManagerProfile:
        """基于俱乐部声誉生成AI经理档案"""
        
        profile = cls.generate_random_profile(manager_id)
        
        # 高声誉俱乐部经理通常更有经验，更平衡
        if reputation >= 7000:
            profile.personality = ManagerPersonality.BALANCED
            profile.risk_tolerance = RiskTolerance.MEDIUM
            profile.transfer_aggression = max(5, profile.transfer_aggression)
        
        return profile


class AITacticalAdaptation:
    """AI战术适应性系统"""
    
    def __init__(self, ai_profile: AIManagerProfile):
        self.profile = ai_profile
    
    def decide_tactics_against_opponent(
        self,
        opponent_strength: float,  # 0.0 - 1.0
        opponent_style: Optional[PlayStyle] = None,
        is_home: bool = True
    ) -> Dict:
        """根据对手决定战术"""
        
        decision = {
            "formation": self.profile.preferred_formation,
            "style": self.profile.preferred_style,
            "risk_level": self.profile.risk_tolerance.value,
            "mentality": "balanced",
            "adaptations": []
        }
        
        # 根据对手强弱调整
        if opponent_strength > 0.7:  # 强队
            if self.profile.personality == ManagerPersonality.DEFENSIVE:
                decision["mentality"] = "defensive"
                decision["adaptations"].append("深度防守")
            elif self.profile.personality == ManagerPersonality.PRAGMATIC:
                decision["formation"] = self._get_defensive_formation()
                decision["mentality"] = "cautious"
            elif self.profile.risk_tolerance.value >= 4:
                decision["mentality"] = "attacking"
                decision["adaptations"].append("全力进攻")
        
        elif opponent_strength < 0.4:  # 弱队
            decision["mentality"] = "attacking"
            if self.profile.personality == ManagerPersonality.ATTACKING:
                decision["adaptations"].append("高位压迫")
        
        # 主场/客场调整
        if not is_home and opponent_strength > 0.6:
            decision["mentality"] = "cautious"
        
        # 针对特定风格的调整
        if opponent_style:
            counter_tactics = self._get_counter_tactics(opponent_style)
            decision["adaptations"].extend(counter_tactics)
        
        return decision
    
    def decide_in_game_adjustments(
        self,
        score_diff: int,  # 我方 - 对方
        minute: int,
        player_ratings: Dict[int, float]
    ) -> List[Dict]:
        """比赛中实时调整"""
        
        adjustments = []
        
        # 落后时的调整
        if score_diff < 0:
            if self.profile.personality == ManagerPersonality.ATTACKING:
                if minute > 60:
                    adjustments.append({
                        "type": "formation_change",
                        "change": "更加进攻",
                        "minute": minute
                    })
            
            if self.profile.risk_tolerance.value >= 4 and minute > 70:
                adjustments.append({
                    "type": "mentality",
                    "change": "全力进攻",
                    "minute": minute
                })
        
        # 领先时的调整
        elif score_diff > 0:
            if self.profile.personality == ManagerPersonality.DEFENSIVE:
                if minute > 70:
                    adjustments.append({
                        "type": "formation_change",
                        "change": "加强防守",
                        "minute": minute
                    })
        
        # 换人决策
        low_rated_players = [pid for pid, rating in player_ratings.items() if rating < 6.0]
        if low_rated_players and minute >= 60:
            sub_timing = self.profile.sub_timing
            if sub_timing == "early" or (sub_timing == "normal" and minute >= 65):
                adjustments.append({
                    "type": "substitution",
                    "players": low_rated_players[:2],
                    "minute": minute
                })
        
        return adjustments
    
    def _get_defensive_formation(self) -> str:
        """获取防守阵型"""
        defensive_formations = ["5-4-1", "5-3-2", "4-5-1"]
        return random.choice(defensive_formations)
    
    def _get_counter_tactics(self, opponent_style: PlayStyle) -> List[str]:
        """获取针对特定风格的反击战术"""
        
        counters = {
            PlayStyle.HIGH_PRESS: ["长传绕过", "快速转移"],
            PlayStyle.TIKI_TAKA: ["高位逼抢", "身体对抗"],
            PlayStyle.COUNTER_ATTACK: ["控球压制", "耐心等待"],
            PlayStyle.LOW_BLOCK: ["边路传中", "远射"],
            PlayStyle.POSSESSION: ["深度防守", "快速反击"]
        }
        
        return counters.get(opponent_style, ["保持平衡"])


class AITransferStrategy:
    """AI转会策略"""
    
    def __init__(self, ai_profile: AIManagerProfile, club_budget: int):
        self.profile = ai_profile
        self.budget = club_budget
    
    def evaluate_transfer_target(
        self,
        player,
        asking_price: int,
        wage_demands: int
    ) -> Dict:
        """评估转会目标"""
        
        evaluation = {
            "player_id": player.id,
            "player_name": player.full_name,
            "interest_level": 0,
            "max_offer": 0,
            "reasoning": []
        }
        
        # 价格评估
        price_factor = asking_price / max(self.budget * 0.5, 1000000)
        
        if price_factor > 1.5:
            if self.profile.transfer_aggression < 7:
                evaluation["reasoning"].append("价格过高")
                return evaluation
        
        # 工资评估
        wage_factor = wage_demands / max(self.budget * 0.01, 50000)
        if wage_factor > 2.0:
            evaluation["reasoning"].append("工资要求过高")
            return evaluation
        
        # 潜力评估
        potential_score = (player.potential_ability - player.current_ability) / 100
        age_factor = max(0, 1 - (player.age - 20) * 0.05)
        
        # 青年偏好
        if self.profile.youth_preference > 7 and player.age <= 21:
            evaluation["interest_level"] += 20
            evaluation["reasoning"].append("年轻有潜力")
        
        # 计算兴趣度
        interest = (
            potential_score * 30 +
            age_factor * 20 +
            player.current_ability / 200 * 30 +
            (10 - self.profile.transfer_aggression) * 2
        )
        
        evaluation["interest_level"] = min(100, int(interest))
        
        # 计算最高出价
        if evaluation["interest_level"] > 60:
            max_multiplier = 1.0 + (self.profile.transfer_aggression / 10) * 0.5
            evaluation["max_offer"] = int(asking_price * max_multiplier)
            evaluation["reasoning"].append("有意引进")
        
        return evaluation
    
    def decide_sell_player(
        self,
        player,
        offer_amount: int,
        player_importance: int  # 1-10
    ) -> Dict:
        """决定是否出售球员"""
        
        decision = {
            "accept": False,
            "counter_offer": None,
            "reason": ""
        }
        
        # 计算球员价值倍数
        player_value = player.market_value or player.current_ability * 1000
        offer_multiple = offer_amount / max(player_value, 1)
        
        # 根据重要性决定
        if player_importance >= 8:  # 核心球员
            if offer_multiple < 2.0:
                decision["reason"] = "核心球员，报价不够高"
            elif self.profile.transfer_aggression >= 8:
                decision["accept"] = True
                decision["reason"] = "高价出售核心球员"
            else:
                decision["counter_offer"] = int(offer_amount * 1.3)
        
        elif player_importance >= 5:  # 重要球员
            if offer_multiple >= 1.5:
                decision["accept"] = True
                decision["reason"] = "合理报价，可以接受"
            else:
                decision["counter_offer"] = int(player_value * 1.5)
        
        else:  # 边缘球员
            if offer_multiple >= 1.0:
                decision["accept"] = True
                decision["reason"] = "边缘球员，尽快出售"
        
        return decision


class AIInteractionSystem:
    """AI互动系统"""
    
    def __init__(self, ai_profile: AIManagerProfile):
        self.profile = ai_profile
    
    def generate_pre_match_comment(
        self,
        opponent_name: str,
        opponent_strength: float
    ) -> str:
        """生成赛前评论"""
        
        comments = {
            ManagerPersonality.ATTACKING: [
                f"我们会全力进攻，争取在{opponent_name}身上拿下三分。",
                "我们的目标就是进球，越多越好。"
            ],
            ManagerPersonality.DEFENSIVE: [
                f"{opponent_name}是强队，我们需要稳固防守。",
                "一场不失球的胜利是最好的结果。"
            ],
            ManagerPersonality.BALANCED: [
                f"这会是一场艰难的比赛，但我们准备好了。",
                "我们会根据场上形势调整战术。"
            ],
            ManagerPersonality.PRAGMATIC: [
                f"{opponent_name}有他们的优势，我们也有我们的。",
                "重要的是结果，不是过程。"
            ],
            ManagerPersonality.TIKI_TAKA: [
                "我们会控制比赛节奏，用传球撕开对手防线。",
                "控球就是我们的武器。"
            ],
            ManagerPersonality.COUNTER_ATTACK: [
                f"{opponent_name}会给我们留下空间。",
                "我们会抓住每一次反击机会。"
            ]
        }
        
        return random.choice(comments.get(self.profile.personality, ["祝我们好运。"]))
    
    def generate_post_match_comment(
        self,
        result: str,  # "win", "draw", "loss"
        score: str
    ) -> str:
        """生成赛后评论"""
        
        if result == "win":
            comments = [
                "球队表现很好，配得上这场胜利。",
                "这是全队努力的结果，继续保持！"
            ]
        elif result == "draw":
            comments = [
                "平局有些遗憾，但我们展现了韧性。",
                "一分总比没有好，我们会继续改进。"
            ]
        else:
            comments = [
                "失利让人失望，需要从错误中学习。",
                "我们不够好，下次必须做得更好。"
            ]
        
        return random.choice(comments)
    
    def respond_to_player_transfer_request(
        self,
        player_name: str,
        request_reason: str
    ) -> Dict:
        """回应球员转会申请"""
        
        responses = {
            "accept": {
                "response": f"我理解{player_name}的想法，我们会考虑合适的报价。",
                "willing_to_sell": True
            },
            "reject": {
                "response": f"{player_name}是球队重要一员，我们不会放人。",
                "willing_to_sell": False
            },
            "negotiate": {
                "response": f"让我们看看会收到什么报价。",
                "willing_to_sell": "depends_on_price"
            }
        }
        
        # 根据性格决定
        if self.profile.personality == ManagerPersonality.PRAGMATIC:
            return responses["negotiate"]
        elif self.profile.transfer_aggression > 7:
            return responses["accept"]
        else:
            return responses["reject"]


# 导出主要类
__all__ = [
    "ManagerPersonality",
    "RiskTolerance",
    "AIManagerProfile",
    "AIPersonalityGenerator",
    "AITacticalAdaptation",
    "AITransferStrategy",
    "AIInteractionSystem"
]
