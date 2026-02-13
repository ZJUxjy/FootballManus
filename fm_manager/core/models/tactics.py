"""Tactical system models for Football Manager simulation.

This module defines tactical formations, instructions, player roles, and related enums
for the match simulation engine.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
from copy import deepcopy

from fm_manager.core.models.player import Player


# ============================================================================
# 球员角色枚举 (Player Role Enums)
# ============================================================================

class PlayerRole(Enum):
    """球员角色枚举 - 定义球场上25+种专业角色.
    
    每个角色代表一种独特的踢球风格和职责，影响球员的行为模式、
    属性要求和场上表现。
    """
    
    # ==================== 进攻型角色 (Attackers) ====================
    PLAYMAKER = "playmaker"                     # 组织核心 - 创造机会
    FALSE_NINE = "false_nine"                   # 伪九号 - 回撤组织
    ADVANCED_PLAYMAKER = "advanced_playmaker"   # 进攻组织核心 - 前场组织
    TREQUARTISTA = "trequartista"               # 影子前锋 - 自由人
    COMPLETE_FORWARD = "complete_forward"       # 全能前锋 - 无短板
    POACHER = "poacher"                         # 抢点型前锋 - 门前嗅觉
    TARGET_MAN = "target_man"                   # 站桩中锋 - 桥头堡
    PRESSING_FORWARD = "pressing_forward"       # 逼抢型前锋 - 高位压迫
    
    # ==================== 中场角色 (Midfielders) ====================
    BOX_TO_BOX = "box_to_box"                   # 全能中场 - 攻防俱佳
    DEEP_LYING_PLAYMAKER = "deep_lying_playmaker"  # 拖后组织核心 - 后场指挥
    BALL_WINNING_MIDFIELDER = "ball_winning_midfielder"  # 抢球机器 - 破坏对方进攻
    MEZZALA = "mezzala"                         # 伪边锋 - 内切型中场
    SEGUNDO_VOLANTE = "segundo_volante"         # 自由人中场 - 后排插上
    ANCHOR_MAN = "anchor_man"                   # 锚人 - 后腰屏障
    REGISTA = "regista"                         # 古典后腰 - 皮尔洛式
    
    # ==================== 边路角色 (Wide Players) ====================
    WINGER = "winger"                           # 传统边锋 - 下底传中
    INSIDE_FORWARD = "inside_forward"           # 内切型边锋 - 内切射门
    WIDE_PLAYMAKER = "wide_playmaker"           # 边路组织核心
    DEFENSIVE_WINGER = "defensive_winger"       # 防守型边锋 - 协助防守
    
    # ==================== 防守型角色 (Defenders) ====================
    BALL_PLAYING_DEFENDER = "ball_playing_defender"  # 出球型中卫 - 组织进攻
    STOPPER = "stopper"                         # 上抢型中卫 - 主动出击
    COVER = "cover"                             # 拖后型中卫 - 补位保护
    WING_BACK = "wing_back"                     # 进攻型边后卫 - 助攻为主
    INVERTED_WING_BACK = "inverted_wing_back"   # 内切型边后卫 - 内收组织
    NO_NONSENSE_FULL_BACK = "no_nonsense_full_back"  # 务实型边后卫 - 安全第一
    LIBERO = "libero"                           # 清道夫 - 自由人后卫
    
    # ==================== 门将角色 (Goalkeepers) ====================
    SWEEPER_KEEPER = "sweeper_keeper"           # 清道夫门将 - 出击范围大
    GOALKEEPER = "goalkeeper"                   # 传统门将 - 门线技术
    
    @property
    def category(self) -> str:
        """获取角色所属类别."""
        category_map = {
            # 进攻
            PlayerRole.PLAYMAKER: "attack",
            PlayerRole.FALSE_NINE: "attack",
            PlayerRole.ADVANCED_PLAYMAKER: "attack",
            PlayerRole.TREQUARTISTA: "attack",
            PlayerRole.COMPLETE_FORWARD: "attack",
            PlayerRole.POACHER: "attack",
            PlayerRole.TARGET_MAN: "attack",
            PlayerRole.PRESSING_FORWARD: "attack",
            # 中场
            PlayerRole.BOX_TO_BOX: "midfield",
            PlayerRole.DEEP_LYING_PLAYMAKER: "midfield",
            PlayerRole.BALL_WINNING_MIDFIELDER: "midfield",
            PlayerRole.MEZZALA: "midfield",
            PlayerRole.SEGUNDO_VOLANTE: "midfield",
            PlayerRole.ANCHOR_MAN: "midfield",
            PlayerRole.REGISTA: "midfield",
            # 边路
            PlayerRole.WINGER: "wide",
            PlayerRole.INSIDE_FORWARD: "wide",
            PlayerRole.WIDE_PLAYMAKER: "wide",
            PlayerRole.DEFENSIVE_WINGER: "wide",
            # 防守
            PlayerRole.BALL_PLAYING_DEFENDER: "defense",
            PlayerRole.STOPPER: "defense",
            PlayerRole.COVER: "defense",
            PlayerRole.WING_BACK: "defense",
            PlayerRole.INVERTED_WING_BACK: "defense",
            PlayerRole.NO_NONSENSE_FULL_BACK: "defense",
            PlayerRole.LIBERO: "defense",
            # 门将
            PlayerRole.SWEEPER_KEEPER: "goalkeeper",
            PlayerRole.GOALKEEPER: "goalkeeper",
        }
        return category_map.get(self, "unknown")
    
    @property
    def display_name(self) -> str:
        """获取角色的显示名称 (中文)."""
        name_map = {
            # 进攻
            PlayerRole.PLAYMAKER: "组织核心",
            PlayerRole.FALSE_NINE: "伪九号",
            PlayerRole.ADVANCED_PLAYMAKER: "进攻组织核心",
            PlayerRole.TREQUARTISTA: "影子前锋",
            PlayerRole.COMPLETE_FORWARD: "全能前锋",
            PlayerRole.POACHER: "抢点型前锋",
            PlayerRole.TARGET_MAN: "站桩中锋",
            PlayerRole.PRESSING_FORWARD: "逼抢型前锋",
            # 中场
            PlayerRole.BOX_TO_BOX: "全能中场",
            PlayerRole.DEEP_LYING_PLAYMAKER: "拖后组织核心",
            PlayerRole.BALL_WINNING_MIDFIELDER: "抢球机器",
            PlayerRole.MEZZALA: "伪边锋",
            PlayerRole.SEGUNDO_VOLANTE: "自由人中场",
            PlayerRole.ANCHOR_MAN: "锚人",
            PlayerRole.REGISTA: "古典后腰",
            # 边路
            PlayerRole.WINGER: "传统边锋",
            PlayerRole.INSIDE_FORWARD: "内切型边锋",
            PlayerRole.WIDE_PLAYMAKER: "边路组织核心",
            PlayerRole.DEFENSIVE_WINGER: "防守型边锋",
            # 防守
            PlayerRole.BALL_PLAYING_DEFENDER: "出球型中卫",
            PlayerRole.STOPPER: "上抢型中卫",
            PlayerRole.COVER: "拖后型中卫",
            PlayerRole.WING_BACK: "进攻型边后卫",
            PlayerRole.INVERTED_WING_BACK: "内切型边后卫",
            PlayerRole.NO_NONSENSE_FULL_BACK: "务实型边后卫",
            PlayerRole.LIBERO: "清道夫",
            # 门将
            PlayerRole.SWEEPER_KEEPER: "清道夫门将",
            PlayerRole.GOALKEEPER: "传统门将",
        }
        return name_map.get(self, self.value)


# ============================================================================
# 球员角色档案数据类
# ============================================================================

@dataclass(frozen=True)
class PlayerRoleProfile:
    """球员角色档案 - 定义角色的详细属性.
    
    Attributes:
        role: 球员角色枚举
        suitable_positions: 适合的位置列表 (如 ["ST", "CF"])
        key_attributes: 关键属性及其权重 {属性名: 权重}
        behavior_modifiers: 行为修正器，影响AI决策
        description: 角色描述
    """
    
    role: PlayerRole
    suitable_positions: Tuple[str, ...]
    key_attributes: Dict[str, float]
    behavior_modifiers: Dict[str, float]
    description: str
    
    def __post_init__(self):
        """验证属性权重总和."""
        total_weight = sum(self.key_attributes.values())
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            # 允许一定误差范围，但不强制归一化以保持灵活性
            pass
    
    @property
    def category(self) -> str:
        """获取角色类别."""
        return self.role.category
    
    @property
    def display_name(self) -> str:
        """获取角色显示名称."""
        return self.role.display_name
    
    def get_primary_attributes(self, top_n: int = 5) -> List[str]:
        """获取最重要的N个属性.
        
        Args:
            top_n: 返回的属性数量
            
        Returns:
            按权重排序的属性名列表
        """
        sorted_attrs = sorted(
            self.key_attributes.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [attr for attr, _ in sorted_attrs[:top_n]]


# ============================================================================
# 角色管理器
# ============================================================================

class RoleManager:
    """角色管理器 - 管理所有球员角色档案.
    
    提供角色查询、适配性评分等功能。
    """
    
    def __init__(self):
        """初始化角色管理器，加载所有角色档案."""
        self._profiles: Dict[PlayerRole, PlayerRoleProfile] = {}
        self._initialize_profiles()
    
    def _initialize_profiles(self):
        """初始化所有角色档案."""
        profiles_data = {
            # ==================== 进攻型角色 ====================
            PlayerRole.PLAYMAKER: {
                "positions": ("CAM", "CF"),
                "attributes": {
                    "passing": 0.25, "vision": 0.20, "technique": 0.15,
                    "decisions": 0.15, "creativity": 0.15, "off_the_ball": 0.10
                },
                "modifiers": {
                    "passing_risk": 0.3, "creative_freedom": 0.4,
                    "pressing": -0.2, "dribbling": 0.2
                },
                "description": "组织核心 - 回撤接球，通过精准传球创造机会，球队的进攻大脑"
            },
            PlayerRole.FALSE_NINE: {
                "positions": ("ST", "CF"),
                "attributes": {
                    "passing": 0.20, "vision": 0.18, "technique": 0.15,
                    "off_the_ball": 0.15, "decisions": 0.15, "finishing": 0.12,
                    "anticipation": 0.05
                },
                "modifiers": {
                    "drop_deep": 0.5, "link_play": 0.4, "hold_up": 0.2,
                    "get_in_behind": -0.3
                },
                "description": "伪九号 - 从前锋位置回撤到中场，打乱对方防线，连接中场与锋线"
            },
            PlayerRole.ADVANCED_PLAYMAKER: {
                "positions": ("CAM", "CF", "ST"),
                "attributes": {
                    "passing": 0.22, "vision": 0.20, "technique": 0.18,
                    "off_the_ball": 0.15, "creativity": 0.15, "finishing": 0.10
                },
                "modifiers": {
                    "passing_risk": 0.35, "creative_freedom": 0.45,
                    "dribbling": 0.25, "shooting": 0.1
                },
                "description": "进攻组织核心 - 在前场危险区域组织进攻，兼具创造力和得分能力"
            },
            PlayerRole.TREQUARTISTA: {
                "positions": ("CAM", "CF"),
                "attributes": {
                    "creativity": 0.22, "technique": 0.20, "dribbling": 0.18,
                    "vision": 0.15, "flair": 0.15, "off_the_ball": 0.10
                },
                "modifiers": {
                    "creative_freedom": 0.6, "dribbling": 0.4,
                    "defensive_duty": -0.5, "roaming": 0.5
                },
                "description": "影子前锋 - 拥有极高自由度，在前场自由游走，依靠个人能力创造机会"
            },
            PlayerRole.COMPLETE_FORWARD: {
                "positions": ("ST", "CF"),
                "attributes": {
                    "finishing": 0.18, "heading": 0.12, "pace": 0.12,
                    "strength": 0.12, "technique": 0.12, "off_the_ball": 0.12,
                    "passing": 0.12, "composure": 0.10
                },
                "modifiers": {
                    "versatility": 0.4, "all_around": 0.4, "adaptability": 0.3
                },
                "description": "全能前锋 - 没有明显短板，能完成各种类型前锋的任务"
            },
            PlayerRole.POACHER: {
                "positions": ("ST", "CF"),
                "attributes": {
                    "finishing": 0.30, "anticipation": 0.20, "off_the_ball": 0.18,
                    "composure": 0.15, "heading": 0.12, "acceleration": 0.05
                },
                "modifiers": {
                    "stay_in_box": 0.6, "shoot_first": 0.4,
                    "link_play": -0.4, "drop_deep": -0.5
                },
                "description": "抢点型前锋 - 禁区内嗅觉灵敏，专注于把握机会破门"
            },
            PlayerRole.TARGET_MAN: {
                "positions": ("ST", "CF"),
                "attributes": {
                    "heading": 0.22, "strength": 0.20, "jumping": 0.15,
                    "passing": 0.12, "first_touch": 0.12, "off_the_ball": 0.12,
                    "work_rate": 0.07
                },
                "modifiers": {
                    "hold_up": 0.5, "aerial_threat": 0.5,
                    "lay_off": 0.4, "get_in_behind": -0.4
                },
                "description": "站桩中锋 - 作为进攻支点，争顶长传并为队友做球"
            },
            PlayerRole.PRESSING_FORWARD: {
                "positions": ("ST", "CF"),
                "attributes": {
                    "work_rate": 0.20, "stamina": 0.18, "teamwork": 0.15,
                    "off_the_ball": 0.15, "acceleration": 0.12, "aggression": 0.12,
                    "finishing": 0.08
                },
                "modifiers": {
                    "pressing": 0.5, "defensive_contribution": 0.4,
                    "harass_defenders": 0.4, "stay_in_box": -0.3
                },
                "description": "逼抢型前锋 - 从前场开始高强度压迫对方后卫，延缓对方出球"
            },
            
            # ==================== 中场角色 ====================
            PlayerRole.BOX_TO_BOX: {
                "positions": ("CM", "LCM", "RCM"),
                "attributes": {
                    "stamina": 0.18, "work_rate": 0.15, "passing": 0.12,
                    "tackling": 0.12, "off_the_ball": 0.12, "finishing": 0.10,
                    "positioning": 0.10, "pace": 0.08, "strength": 0.03
                },
                "modifiers": {
                    "box_to_box": 0.5, "get_forward": 0.3, "track_back": 0.3,
                    "all_around": 0.3
                },
                "description": "全能中场 - 攻防俱佳，覆盖两个禁区之间的所有区域"
            },
            PlayerRole.DEEP_LYING_PLAYMAKER: {
                "positions": ("CDM", "CM", "LCM", "RCM"),
                "attributes": {
                    "passing": 0.25, "vision": 0.20, "technique": 0.15,
                    "decisions": 0.15, "composure": 0.12, "positioning": 0.08,
                    "tackling": 0.05
                },
                "modifiers": {
                    "passing_risk": 0.3, "stay_back": 0.3, "dictate_tempo": 0.4,
                    "get_forward": -0.3
                },
                "description": "拖后组织核心 - 从后场发起进攻，用传球掌控比赛节奏"
            },
            PlayerRole.BALL_WINNING_MIDFIELDER: {
                "positions": ("CDM", "CM", "LCM", "RCM"),
                "attributes": {
                    "tackling": 0.22, "aggression": 0.18, "work_rate": 0.15,
                    "stamina": 0.15, "positioning": 0.12, "strength": 0.10,
                    "marking": 0.08
                },
                "modifiers": {
                    "closing_down": 0.5, "tight_marking": 0.4,
                    "risky_passing": -0.3, "creative_freedom": -0.4
                },
                "description": "抢球机器 - 专注于破坏对方进攻，积极拼抢夺回球权"
            },
            PlayerRole.MEZZALA: {
                "positions": ("LCM", "RCM", "CM"),
                "attributes": {
                    "dribbling": 0.18, "passing": 0.15, "off_the_ball": 0.15,
                    "finishing": 0.12, "vision": 0.12, "technique": 0.12,
                    "acceleration": 0.10, "stamina": 0.06
                },
                "modifiers": {
                    "drift_wide": 0.3, "get_in_box": 0.4, "dribble_inside": 0.4,
                    "combine_with_winger": 0.3
                },
                "description": "伪边锋 - 从中央向边路移动，内切制造威胁"
            },
            PlayerRole.SEGUNDO_VOLANTE: {
                "positions": ("CDM", "CM"),
                "attributes": {
                    "stamina": 0.18, "off_the_ball": 0.15, "finishing": 0.15,
                    "passing": 0.12, "tackling": 0.12, "positioning": 0.12,
                    "acceleration": 0.10, "work_rate": 0.06
                },
                "modifiers": {
                    "late_runs": 0.5, "surge_forward": 0.4, "arrive_in_box": 0.4,
                    "defensive_discipline": -0.2
                },
                "description": "自由人中场 - 防守型位置但积极插上参与进攻"
            },
            PlayerRole.ANCHOR_MAN: {
                "positions": ("CDM",),
                "attributes": {
                    "positioning": 0.22, "tackling": 0.18, "marking": 0.15,
                    "strength": 0.12, "concentration": 0.12, "decisions": 0.12,
                    "passing": 0.09
                },
                "modifiers": {
                    "hold_position": 0.5, "screen_defense": 0.5,
                    "get_forward": -0.5, "risky_passing": -0.3
                },
                "description": "锚人 - 固定在后防线前，保护后防，极少前插"
            },
            PlayerRole.REGISTA: {
                "positions": ("CDM",),
                "attributes": {
                    "passing": 0.28, "vision": 0.22, "technique": 0.18,
                    "creativity": 0.15, "decisions": 0.10, "composure": 0.07
                },
                "modifiers": {
                    "dictate_tempo": 0.6, "roaming": 0.3, "deep_distribution": 0.5,
                    "creative_freedom": 0.4, "defensive_duty": -0.3
                },
                "description": "古典后腰 - 自由 roam，从后场掌控全局，皮尔洛式球员"
            },
            
            # ==================== 边路角色 ====================
            PlayerRole.WINGER: {
                "positions": ("LW", "RW", "LM", "RM"),
                "attributes": {
                    "pace": 0.20, "dribbling": 0.18, "crossing": 0.18,
                    "acceleration": 0.15, "technique": 0.12, "off_the_ball": 0.12,
                    "work_rate": 0.05
                },
                "modifiers": {
                    "stay_wide": 0.5, "run_to_byline": 0.4, "cross": 0.4,
                    "cut_inside": -0.3
                },
                "description": "传统边锋 - 利用速度下底传中，拉开宽度"
            },
            PlayerRole.INSIDE_FORWARD: {
                "positions": ("LW", "RW", "LM", "RM"),
                "attributes": {
                    "dribbling": 0.20, "finishing": 0.18, "pace": 0.15,
                    "technique": 0.15, "acceleration": 0.15, "off_the_ball": 0.12,
                    "flair": 0.05
                },
                "modifiers": {
                    "cut_inside": 0.5, "shoot": 0.4, "dribble_inside": 0.4,
                    "cross": -0.4, "stay_wide": -0.3
                },
                "description": "内切型边锋 - 从边路内切射门，罗本式打法"
            },
            PlayerRole.WIDE_PLAYMAKER: {
                "positions": ("LW", "RW", "LM", "RM", "LWB", "RWB"),
                "attributes": {
                    "passing": 0.22, "vision": 0.20, "crossing": 0.15,
                    "technique": 0.15, "decisions": 0.15, "off_the_ball": 0.10,
                    "creativity": 0.03
                },
                "modifiers": {
                    "create_from_wide": 0.5, "cross": 0.3, "dictate_tempo": 0.3,
                    "roaming": 0.2
                },
                "description": "边路组织核心 - 从边路发起进攻，创造机会"
            },
            PlayerRole.DEFENSIVE_WINGER: {
                "positions": ("LW", "RW", "LM", "RM", "LWB", "RWB"),
                "attributes": {
                    "work_rate": 0.20, "tackling": 0.18, "stamina": 0.15,
                    "positioning": 0.15, "marking": 0.12, "teamwork": 0.12,
                    "crossing": 0.08
                },
                "modifiers": {
                    "track_back": 0.5, "support_defense": 0.4,
                    "get_forward": -0.3, "cross": -0.2
                },
                "description": "防守型边锋 - 优先考虑防守任务，协助边后卫"
            },
            
            # ==================== 防守型角色 ====================
            PlayerRole.BALL_PLAYING_DEFENDER: {
                "positions": ("CB", "LCB", "RCB"),
                "attributes": {
                    "passing": 0.22, "vision": 0.18, "technique": 0.15,
                    "decisions": 0.15, "positioning": 0.12, "tackling": 0.10,
                    "composure": 0.08
                },
                "modifiers": {
                    "bring_ball_out": 0.4, "start_attacks": 0.4,
                    "passing_risk": 0.2, "dribble_out": 0.3
                },
                "description": "出球型中卫 - 从后场组织进攻，长传发起攻势"
            },
            PlayerRole.STOPPER: {
                "positions": ("CB", "LCB", "RCB"),
                "attributes": {
                    "tackling": 0.22, "aggression": 0.18, "strength": 0.15,
                    "heading": 0.12, "bravery": 0.12, "marking": 0.12,
                    "positioning": 0.09
                },
                "modifiers": {
                    "step_up": 0.5, "tight_marking": 0.4, "closing_down": 0.4,
                    "hold_position": -0.3
                },
                "description": "上抢型中卫 - 主动前压逼抢，压迫对方前锋"
            },
            PlayerRole.COVER: {
                "positions": ("CB", "LCB", "RCB"),
                "attributes": {
                    "positioning": 0.22, "concentration": 0.18, "pace": 0.15,
                    "tackling": 0.15, "decisions": 0.15, "anticipation": 0.12,
                    "marking": 0.03
                },
                "modifiers": {
                    "hold_position": 0.5, "sweep_up": 0.5, "drop_deep": 0.3,
                    "closing_down": -0.3
                },
                "description": "拖后型中卫 - 保持防线最后，补位保护队友"
            },
            PlayerRole.WING_BACK: {
                "positions": ("LWB", "RWB", "LB", "RB"),
                "attributes": {
                    "stamina": 0.18, "work_rate": 0.15, "pace": 0.15,
                    "crossing": 0.15, "off_the_ball": 0.12, "dribbling": 0.12,
                    "tackling": 0.08, "acceleration": 0.05
                },
                "modifiers": {
                    "get_forward": 0.5, "overlap": 0.4, "cross": 0.3,
                    "stay_back": -0.4
                },
                "description": "进攻型边后卫 - 积极助攻，上下往返"
            },
            PlayerRole.INVERTED_WING_BACK: {
                "positions": ("LWB", "RWB", "LB", "RB"),
                "attributes": {
                    "passing": 0.20, "vision": 0.15, "technique": 0.15,
                    "decisions": 0.15, "stamina": 0.12, "positioning": 0.12,
                    "tackling": 0.08, "off_the_ball": 0.03
                },
                "modifiers": {
                    "cut_inside": 0.5, "sit_in_midfield": 0.5,
                    "create_overloads": 0.4, "stay_wide": -0.5
                },
                "description": "内切型边后卫 - 内收到中场参与组织"
            },
            PlayerRole.NO_NONSENSE_FULL_BACK: {
                "positions": ("LB", "RB", "LWB", "RWB"),
                "attributes": {
                    "tackling": 0.20, "marking": 0.18, "positioning": 0.18,
                    "concentration": 0.15, "strength": 0.12, "heading": 0.10,
                    "passing": 0.07
                },
                "modifiers": {
                    "safety_first": 0.5, "clear_danger": 0.4, "hold_position": 0.4,
                    "get_forward": -0.5, "cross": -0.3
                },
                "description": "务实型边后卫 - 安全第一，专注防守，少参与进攻"
            },
            PlayerRole.LIBERO: {
                "positions": ("CB", "LCB", "RCB"),
                "attributes": {
                    "positioning": 0.18, "passing": 0.15, "vision": 0.15,
                    "technique": 0.12, "pace": 0.12, "tackling": 0.12,
                    "decisions": 0.10, "concentration": 0.06
                },
                "modifiers": {
                    "roaming": 0.5, "bring_ball_out": 0.4, "sweep_up": 0.4,
                    "start_attacks": 0.3, "creative_freedom": 0.3
                },
                "description": "清道夫 - 防线后自由人，负责补位并带球推进"
            },
            
            # ==================== 门将角色 ====================
            PlayerRole.SWEEPER_KEEPER: {
                "positions": ("GK",),
                "attributes": {
                    "command_of_area": 0.20, "passing": 0.18, "vision": 0.15,
                    "anticipation": 0.15, "rushing_out": 0.15, "reflexes": 0.12,
                    "handling": 0.05
                },
                "modifiers": {
                    "sweep_up": 0.5, "start_attacks": 0.4, "high_line": 0.4,
                    "play_as_libero": 0.3
                },
                "description": "清道夫门将 - 大范围出击，参与后场组织，需要防线支持"
            },
            PlayerRole.GOALKEEPER: {
                "positions": ("GK",),
                "attributes": {
                    "handling": 0.20, "reflexes": 0.20, "positioning": 0.15,
                    "one_on_one": 0.15, "command_of_area": 0.15,
                    "concentration": 0.10, "communication": 0.05
                },
                "modifiers": {
                    "hold_position": 0.4, "safety_first": 0.4,
                    "sweep_up": -0.3, "short_passing": -0.2
                },
                "description": "传统门将 - 专注于门线技术，较少参与后场组织"
            },
        }
        
        for role, data in profiles_data.items():
            self._profiles[role] = PlayerRoleProfile(
                role=role,
                suitable_positions=data["positions"],
                key_attributes=data["attributes"],
                behavior_modifiers=data["modifiers"],
                description=data["description"]
            )
    
    def get_role_profile(self, role: PlayerRole) -> Optional[PlayerRoleProfile]:
        """获取指定角色的档案.
        
        Args:
            role: 球员角色枚举
            
        Returns:
            角色档案，如果不存在则返回None
        """
        return self._profiles.get(role)
    
    def get_all_roles(self) -> List[PlayerRole]:
        """获取所有角色枚举."""
        return list(PlayerRole)
    
    def get_roles_by_category(self, category: str) -> List[PlayerRole]:
        """按类别获取角色.
        
        Args:
            category: 类别名称 (attack, midfield, wide, defense, goalkeeper)
            
        Returns:
            该类别下的所有角色
        """
        return [role for role in PlayerRole if role.category == category]
    
    def get_suitable_roles(self, position: str) -> List[PlayerRole]:
        """获取适合指定位置的所有角色.
        
        Args:
            position: 位置代码 (如 "ST", "CM", "GK")
            
        Returns:
            适合该位置的角色列表
        """
        suitable = []
        for profile in self._profiles.values():
            if position.upper() in profile.suitable_positions:
                suitable.append(profile.role)
        return suitable
    
    def calculate_role_score(
        self,
        role: PlayerRole,
        player_attributes: Dict[str, float],
        position: Optional[str] = None
    ) -> Tuple[float, Dict[str, float]]:
        """计算球员对某个角色的适合度评分.
        
        Args:
            role: 要评估的角色
            player_attributes: 球员属性值 {属性名: 数值(0-100)}
            position: 球员当前位置 (可选，用于位置适配性加成)
            
        Returns:
            (总评分 0-100, 各维度评分详情)
        """
        profile = self._profiles.get(role)
        if not profile:
            return 0.0, {}
        
        details = {}
        total_score = 0.0
        
        # 计算属性匹配度
        for attr, weight in profile.key_attributes.items():
            player_value = player_attributes.get(attr, 0)
            # 标准化到 0-1 范围
            normalized = min(100, max(0, player_value)) / 100.0
            attr_score = normalized * weight * 100
            details[attr] = round(attr_score, 2)
            total_score += attr_score
        
        # 位置适配性加成/减益
        if position:
            pos_upper = position.upper()
            if pos_upper in profile.suitable_positions:
                # 主位置 +5%
                details["position_bonus"] = 5.0
                total_score = min(100, total_score + 5)
            elif self._is_related_position(pos_upper, profile.suitable_positions):
                # 相关位置 +2%
                details["position_bonus"] = 2.0
                total_score = min(100, total_score + 2)
            else:
                # 不相关位置 -10%
                details["position_penalty"] = -10.0
                total_score = max(0, total_score - 10)
        
        details["total"] = round(total_score, 2)
        return round(total_score, 2), details
    
    def _is_related_position(self, position: str, suitable_positions: Tuple[str, ...]) -> bool:
        """检查位置是否相关 (简化版).
        
        Args:
            position: 当前位置
            suitable_positions: 适合的位置列表
            
        Returns:
            是否相关
        """
        # 位置组映射
        position_groups = {
            "ST": ["CF", "ST_L", "ST_R", "LF", "RF"],
            "CF": ["ST", "LF", "RF", "CAM", "CAM_L", "CAM_R"],
            "CAM": ["CF", "CM", "ST", "CAM_L", "CAM_R"],
            "CM": ["LCM", "RCM", "CAM", "CDM", "CDM_L", "CDM_R"],
            "LCM": ["CM", "RCM", "LM", "CAM"],
            "RCM": ["CM", "LCM", "RM", "CAM"],
            "CDM": ["CM", "CB", "CDM_L", "CDM_R", "LCB", "RCB"],
            "LM": ["LW", "LCM", "LWB", "LB"],
            "RM": ["RW", "RCM", "RWB", "RB"],
            "LW": ["LM", "LF", "CAM"],
            "RW": ["RM", "RF", "CAM"],
            "LB": ["LWB", "LCB", "LM"],
            "RB": ["RWB", "RCB", "RM"],
            "LWB": ["LB", "LM", "LW"],
            "RWB": ["RB", "RM", "RW"],
            "CB": ["LCB", "RCB", "CDM"],
            "LCB": ["CB", "LB", "CDM"],
            "RCB": ["CB", "RB", "CDM"],
        }
        
        related = position_groups.get(position, [])
        return any(pos in related for pos in suitable_positions)
    
    def get_best_roles(
        self,
        player_attributes: Dict[str, float],
        position: str,
        top_n: int = 5
    ) -> List[Tuple[PlayerRole, float]]:
        """获取球员最适合的角色列表.
        
        Args:
            player_attributes: 球员属性
            position: 球员位置
            top_n: 返回前N个角色
            
        Returns:
            [(角色, 评分), ...] 按评分排序
        """
        scores = []
        for role in PlayerRole:
            score, _ = self.calculate_role_score(role, player_attributes, position)
            scores.append((role, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
    
    def compare_roles(
        self,
        role1: PlayerRole,
        role2: PlayerRole
    ) -> Dict[str, Any]:
        """比较两个角色的差异.
        
        Args:
            role1: 第一个角色
            role2: 第二个角色
            
        Returns:
            比较结果字典
        """
        p1 = self._profiles.get(role1)
        p2 = self._profiles.get(role2)
        
        if not p1 or not p2:
            return {"error": "Role not found"}
        
        # 共同位置
        common_positions = set(p1.suitable_positions) & set(p2.suitable_positions)
        # 共同关键属性
        common_attrs = set(p1.key_attributes.keys()) & set(p2.key_attributes.keys())
        
        return {
            "role1": role1.display_name,
            "role2": role2.display_name,
            "same_category": p1.category == p2.category,
            "common_positions": list(common_positions),
            "common_key_attributes": list(common_attrs),
            "role1_unique_attrs": list(set(p1.key_attributes.keys()) - set(p2.key_attributes.keys())),
            "role2_unique_attrs": list(set(p2.key_attributes.keys()) - set(p1.key_attributes.keys())),
        }


# ============================================================================
# 战术维度枚举 (Tactical Dimension Enums)
# ============================================================================

class DefensiveLine(Enum):
    """防线高度设置 (防线高度).
    
    决定球队防线在球场上的位置高度。
    """
    VERY_HIGH = 5   # 极高防线 - 在对方半场压迫
    HIGH = 4        # 高位防线 - 在中线附近
    MEDIUM = 3      # 中等防线 - 标准位置
    LOW = 2         # 低位防线 - 收缩防守
    VERY_LOW = 1    # 深度防线 - 禁区内密集防守


class PressingIntensity(Enum):
    """逼抢强度设置 (逼抢强度).
    
    决定球队失去球权后反抢的积极性。
    """
    EXTREME = 5     # 极限逼抢 - 全员疯狂逼抢
    HIGH = 4        # 高位逼抢 - 积极压迫
    MEDIUM = 3      # 标准逼抢 - 适度压迫
    LOW = 2         # 轻度逼抢 - 选择性压迫
    MINIMAL = 1     # 几乎不逼抢 - 退守阵型


class TeamWidth(Enum):
    """球队宽度设置 (球队宽度).
    
    决定球队在横向空间的利用程度。
    """
    EXTREMELY_WIDE = 5   # 极宽 - 充分利用边路
    WIDE = 4             # 宽 - 拉开宽度
    NORMAL = 3           # 标准 - 平衡宽度
    NARROW = 2           # 窄 - 中路密集
    EXTREMELY_NARROW = 1 # 极窄 - 完全收缩中路


class Tempo(Enum):
    """比赛节奏设置 (比赛节奏).
    
    决定球队攻防转换和传球的速度。
    """
    VERY_HIGH = 5   # 极快 - 快速传递
    HIGH = 4        # 快 - 积极进攻
    NORMAL = 3      # 标准 - 平衡节奏
    LOW = 2         # 慢 - 控制节奏
    VERY_LOW = 1    # 极慢 - 耐心组织


class PassingStyle(Enum):
    """传球风格设置 (传球风格).
    
    决定球队传球的距离和风格偏好。
    """
    VERY_SHORT = 5  # 极短传 - Tiki-taka风格
    SHORT = 4       # 短传 - 地面配合
    MIXED = 3       # 混合 - 长短结合
    LONG = 2        # 长传 - 直接打法
    VERY_LONG = 1   # 极长传 - 大脚长传


class TimeWasting(Enum):
    """拖延时间倾向 (拖延时间).
    
    决定球队在领先时拖延时间的倾向。
    """
    ALWAYS = 5      # 总是 - 任何情况都拖时间
    OFTEN = 4       # 经常 - 频繁拖延
    SOMETIMES = 3   # 有时 - 适度拖延
    RARELY = 2      # 很少 - 很少拖时间
    NEVER = 1       # 从不 - 始终保持快节奏


class Formation(Enum):
    """常用足球阵型枚举.
    
    标准的足球战术阵型配置。
    """
    F_4_4_2 = "4-4-2"           # 经典平行中场
    F_4_4_2_DIAMOND = "4-4-2d"  # 菱形中场
    F_4_3_3 = "4-3-3"           # 标准进攻阵型
    F_4_3_3_FALSE_9 = "4-3-3f9" # 伪九号阵型
    F_4_2_3_1 = "4-2-3-1"       # 现代流行阵型
    F_4_2_2_2 = "4-2-2-2"       # 双前锋双前腰
    F_4_1_4_1 = "4-1-4-1"       # 单后腰
    F_4_5_1 = "4-5-1"           # 防守型中场
    F_5_3_2 = "5-3-2"           # 三中卫
    F_5_4_1 = "5-4-1"           # 极致防守
    F_3_4_3 = "3-4-3"           # 进攻三中卫
    F_3_5_2 = "3-5-2"           # 三中卫双前锋
    F_3_4_2_1 = "3-4-2-1"       # 圣诞树变体


# ============================================================================
# 战术指令数据类
# ============================================================================

@dataclass
class TacticalInstructions:
    """战术指令集合 - 细粒度的战术参数系统.
    
    定义球队在比赛中的整体战术风格和行为模式。
    
    Attributes:
        defensive_line: 防线高度
        pressing: 逼抢强度
        width: 球队宽度
        tempo: 比赛节奏
        passing_style: 传球风格
        time_wasting: 拖延时间倾向
        counter_attack: 是否启用反击战术
        hold_shape: 是否保持阵型
        play_out_of_defence: 是否从后场组织进攻
        distribute_to_full_backs: 是否分边给边后卫
    """
    
    # 核心战术维度
    defensive_line: DefensiveLine = DefensiveLine.MEDIUM
    pressing: PressingIntensity = PressingIntensity.MEDIUM
    width: TeamWidth = TeamWidth.NORMAL
    tempo: Tempo = Tempo.NORMAL
    passing_style: PassingStyle = PassingStyle.MIXED
    time_wasting: TimeWasting = TimeWasting.NEVER
    
    # 转换阶段设置
    counter_attack: bool = False        # 反击 - 快速利用对方身后空当
    hold_shape: bool = False            # 保持阵型 - 不冒险前插
    
    # 定位球/门将设置
    play_out_of_defence: bool = True    # 从后场开始组织 - 短传出球
    distribute_to_full_backs: bool = False  # 分边给边后卫
    
    # 球员角色覆盖 (可选，用于覆盖默认角色)
    player_roles: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化.
        
        Returns:
            包含所有战术参数的字典
        """
        return {
            # 核心维度 - 存储枚举值
            "defensive_line": self.defensive_line.value,
            "pressing": self.pressing.value,
            "width": self.width.value,
            "tempo": self.tempo.value,
            "passing_style": self.passing_style.value,
            "time_wasting": self.time_wasting.value,
            # 布尔设置
            "counter_attack": self.counter_attack,
            "hold_shape": self.hold_shape,
            "play_out_of_defence": self.play_out_of_defence,
            "distribute_to_full_backs": self.distribute_to_full_backs,
            # 球员角色
            "player_roles": self.player_roles.copy(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TacticalInstructions":
        """从字典恢复战术指令对象.
        
        Args:
            data: 包含战术参数的字典
            
        Returns:
            恢复的TacticalInstructions实例
            
        Raises:
            ValueError: 当字典包含无效的枚举值时
        """
        # 处理枚举字段映射
        enum_fields = {
            "defensive_line": (DefensiveLine, DefensiveLine.MEDIUM),
            "pressing": (PressingIntensity, PressingIntensity.MEDIUM),
            "width": (TeamWidth, TeamWidth.NORMAL),
            "tempo": (Tempo, Tempo.NORMAL),
            "passing_style": (PassingStyle, PassingStyle.MIXED),
            "time_wasting": (TimeWasting, TimeWasting.NEVER),
        }
        
        kwargs = {}
        
        # 解析枚举字段
        for field_name, (enum_class, default_value) in enum_fields.items():
            value = data.get(field_name)
            if value is not None:
                # 尝试通过值查找枚举成员
                try:
                    kwargs[field_name] = enum_class(value)
                except ValueError:
                    # 尝试通过名称查找（兼容性）
                    try:
                        kwargs[field_name] = enum_class[value.upper()]
                    except (KeyError, AttributeError):
                        kwargs[field_name] = default_value
            else:
                kwargs[field_name] = default_value
        
        # 解析布尔字段
        bool_fields = [
            "counter_attack", "hold_shape",
            "play_out_of_defence", "distribute_to_full_backs"
        ]
        for field_name in bool_fields:
            kwargs[field_name] = data.get(field_name, getattr(cls(), field_name))
        
        # 解析球员角色
        kwargs["player_roles"] = data.get("player_roles", {})
        
        return cls(**kwargs)
    
    def copy(self) -> "TacticalInstructions":
        """创建战术指令的深拷贝.
        
        Returns:
            新的TacticalInstructions实例
        """
        return deepcopy(self)
    
    def get_compact_summary(self) -> str:
        """获取战术摘要，用于显示.
        
        Returns:
            格式化的战术摘要字符串
        """
        return (
            f"防线:{self.defensive_line.name[:3]} | "
            f"逼抢:{self.pressing.name[:3]} | "
            f"宽度:{self.width.name[:3]} | "
            f"节奏:{self.tempo.name[:3]} | "
            f"传球:{self.passing_style.name[:3]}"
        )
    
    def calculate_risk_level(self) -> float:
        """计算战术风险等级 (0.0-1.0).
        
        基于防线高度和逼抢强度计算整体风险。
        高风险战术在被打穿时更容易丢球。
        
        Returns:
            风险等级 0.0-1.0
        """
        # 防线高度风险 (0.0-0.5)
        line_risk = (self.defensive_line.value - 1) / 8.0
        
        # 逼抢强度风险 (0.0-0.5)
        press_risk = (self.pressing.value - 1) / 8.0
        
        return min(1.0, line_risk + press_risk)
    
    def get_possession_tendency(self) -> float:
        """计算控球倾向 (0.0-1.0).
        
        基于传球风格和比赛节奏评估控球可能性。
        高值表示更倾向于控球。
        
        Returns:
            控球倾向 0.0-1.0
        """
        # 传球风格影响 (极短传=1.0, 极长传=0.0)
        passing_score = (self.passing_style.value - 1) / 4.0
        
        # 节奏影响 (慢节奏=高控球, 快节奏=低控球)
        tempo_score = (6 - self.tempo.value) / 5.0
        
        return (passing_score * 0.6) + (tempo_score * 0.4)


# ============================================================================
# 战术阵型
# ============================================================================

@dataclass
class TacticalFormation:
    """战术阵型配置.
    
    将球员位置映射到场上具体位置，包含默认战术指令。
    """
    
    formation_code: str
    name: str
    positions: List[str]  # 11个位置代码的列表
    default_instructions: Optional[TacticalInstructions] = None
    
    # 位置映射表
    POSITION_MAP: Dict[str, tuple] = field(default_factory=lambda: {
        # 守门员
        "GK": (0, 50),
        # 后卫线
        "LWB": (15, 10), "LB": (15, 20), "LCB": (15, 35),
        "CB": (15, 50), "RCB": (15, 65), "RB": (15, 80), "RWB": (15, 90),
        # 后腰
        "CDM_L": (30, 35), "CDM": (30, 50), "CDM_R": (30, 65),
        # 中场
        "LM": (50, 15), "LCM": (50, 35), "CM": (50, 50), "RCM": (50, 65), "RM": (50, 85),
        # 前腰
        "CAM_L": (65, 35), "CAM": (65, 50), "CAM_R": (65, 65),
        # 边锋/前锋
        "LW": (80, 20), "LF": (80, 35), "CF": (80, 50), "RF": (80, 65), "RW": (80, 80),
        # 前锋
        "ST_L": (90, 35), "ST": (90, 50), "ST_R": (90, 65),
    })
    
    def __post_init__(self):
        """初始化后验证阵型配置."""
        if len(self.positions) != 11:
            raise ValueError(f"Formation must have exactly 11 positions, got {len(self.positions)}")
        
        if self.default_instructions is None:
            self.default_instructions = TacticalInstructions()
    
    def get_coordinates(self, position: str) -> Optional[tuple]:
        """获取位置的场上坐标.
        
        Args:
            position: 位置代码
            
        Returns:
            (x, y) 坐标元组，x为纵向(0-100, 0=本方球门)，y为横向(0-100)
        """
        return self.POSITION_MAP.get(position)
    
    def get_defensive_coordinates(self, position: str) -> Optional[tuple]:
        """获取防守时的场上坐标.
        
        Args:
            position: 位置代码
            
        Returns:
            防守时的 (x, y) 坐标元组
        """
        coords = self.get_coordinates(position)
        if coords is None:
            return None
        
        x, y = coords
        # 防守时整体后撤
        if "GK" in position:
            return (0, y)
        elif "B" in position or "WB" in position:
            return (max(5, x - 5), y)
        else:
            return (max(20, x - 15), y)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式."""
        return {
            "formation_code": self.formation_code,
            "name": self.name,
            "positions": self.positions.copy(),
            "instructions": self.default_instructions.to_dict() if self.default_instructions else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TacticalFormation":
        """从字典恢复阵型配置."""
        instructions = None
        if data.get("instructions"):
            instructions = TacticalInstructions.from_dict(data["instructions"])
        
        return cls(
            formation_code=data["formation_code"],
            name=data["name"],
            positions=data["positions"],
            default_instructions=instructions,
        )


# ============================================================================
# 战术指令验证器
# ============================================================================

class TacticalInstructionsValidator:
    """战术指令验证器.
    
    验证战术指令的合理性，并根据球员阵容提供建议。
    """
    
    def __init__(self):
        """初始化验证器."""
        self.warnings: List[str] = []
        self.suggestions: List[str] = []
    
    def validate(self, instructions: TacticalInstructions) -> bool:
        """验证战术指令是否合理.
        
        检查战术指令中是否存在明显矛盾或不合理的配置。
        
        Args:
            instructions: 要验证的战术指令
            
        Returns:
            True 如果战术合理，False 如果有严重问题
        """
        self.warnings = []
        self.suggestions = []
        
        is_valid = True
        
        # 检查 1: 防线高度 vs 逼抢强度的合理性
        if (instructions.defensive_line == DefensiveLine.VERY_LOW and 
            instructions.pressing == PressingIntensity.EXTREME):
            self.warnings.append(
                "深度防线配合极限逼抢不合理: 防线过低时无法有效逼抢"
            )
            is_valid = False
        
        if (instructions.defensive_line == DefensiveLine.VERY_HIGH and 
            instructions.pressing == PressingIntensity.MINIMAL):
            self.warnings.append(
                "极高防线但不逼抢: 高位防线需要逼抢来保护身后空当"
            )
            is_valid = False
        
        # 检查 2: 反击 vs 保持阵型
        if instructions.counter_attack and instructions.hold_shape:
            self.warnings.append(
                "同时启用反击和保持阵型: 这两个指令相互矛盾"
            )
            is_valid = False
        
        # 检查 3: 节奏 vs 传球风格的协调性
        if (instructions.tempo in [Tempo.VERY_HIGH, Tempo.HIGH] and 
            instructions.passing_style in [PassingStyle.LONG, PassingStyle.VERY_LONG]):
            self.suggestions.append(
                "快节奏+长传: 适合快速反击，但控球率可能较低"
            )
        
        if (instructions.tempo in [Tempo.VERY_LOW, Tempo.LOW] and 
            instructions.passing_style in [PassingStyle.VERY_SHORT, PassingStyle.SHORT]):
            self.suggestions.append(
                "慢节奏+短传: 适合控球战术，但要注意对方逼抢"
            )
        
        # 检查 4: 宽度设置与传球风格
        if (instructions.width == TeamWidth.EXTREMELY_NARROW and 
            instructions.passing_style in [PassingStyle.LONG, PassingStyle.VERY_LONG]):
            self.warnings.append(
                "极窄阵型配合长传: 缺乏边路接应点，长传效果会受限"
            )
        
        # 检查 5: 拖延时间的合理性
        if instructions.time_wasting == TimeWasting.ALWAYS and instructions.tempo == Tempo.VERY_HIGH:
            self.warnings.append(
                "总是拖延时间但节奏极快: 这两个设置相互矛盾"
            )
        
        return is_valid
    
    def get_recommendations(self, squad: List[Player]) -> List[str]:
        """根据球员阵容生成战术建议.
        
        分析球员能力，推荐适合的战术配置。
        
        Args:
            squad: 球员阵容列表
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if not squad:
            return ["阵容为空，无法生成建议"]
        
        # 分析球员属性 (简化版)
        avg_pace = self._calculate_avg_attribute(squad, "pace")
        avg_passing = self._calculate_avg_attribute(squad, "passing")
        avg_stamina = self._calculate_avg_attribute(squad, "stamina")
        
        # 基于速度的建议
        if avg_pace and avg_pace >= 75:
            recommendations.append(
                f"球队速度较快(avg={avg_pace:.1f}): 适合高位逼抢和反击战术"
            )
        elif avg_pace and avg_pace <= 60:
            recommendations.append(
                f"球队速度偏慢(avg={avg_pace:.1f}): 建议降低防线，采用控制型打法"
            )
        
        # 基于传球能力的建议
        if avg_passing and avg_passing >= 75:
            recommendations.append(
                f"传球能力出色(avg={avg_passing:.1f}): 适合短传控制和高位防线"
            )
        elif avg_passing and avg_passing <= 60:
            recommendations.append(
                f"传球能力一般(avg={avg_passing:.1f}): 建议采用直接打法，减少后场组织"
            )
        
        # 基于体能的建议
        if avg_stamina and avg_stamina >= 75:
            recommendations.append(
                f"体能充沛(avg={avg_stamina:.1f}): 可以支撑高强度逼抢90分钟"
            )
        elif avg_stamina and avg_stamina <= 60:
            recommendations.append(
                f"体能偏弱(avg={avg_stamina:.1f}): 建议降低逼抢强度，保留体力"
            )
        
        # 守门员出球能力
        gks = [p for p in squad if hasattr(p, 'position') and str(p.position) == "GK"]
        if gks:
            gk_passing = getattr(gks[0], 'passing', 0)
            if gk_passing < 50:
                recommendations.append(
                    f"门将出球能力较弱({gk_passing}): 建议关闭'从后场组织'，选择大脚解围"
                )
        
        return recommendations if recommendations else ["阵容分析: 未发现明显的战术偏好"]
    
    def _calculate_avg_attribute(self, squad: List[Player], attr: str) -> Optional[float]:
        """计算阵容的平均属性值.
        
        Args:
            squad: 球员列表
            attr: 属性名称
            
        Returns:
            平均值或None
        """
        values = []
        for player in squad:
            val = getattr(player, attr, None)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    continue
        
        return sum(values) / len(values) if values else None
    
    def suggest_tactical_adjustment(
        self, 
        instructions: TacticalInstructions,
        game_state: Dict[str, Any]
    ) -> List[str]:
        """根据比赛状态建议战术调整.
        
        Args:
            instructions: 当前战术指令
            game_state: 比赛状态 (比分、时间、体能等)
            
        Returns:
            调整建议列表
        """
        suggestions = []
        
        score_diff = game_state.get("score_diff", 0)  # 我方 - 对方
        minute = game_state.get("minute", 0)
        is_second_half = minute > 45
        
        # 落后的情况
        if score_diff < 0:
            if not is_second_half:
                suggestions.append("落后且上半场: 可以耐心等待机会，暂不需要激进调整")
            else:
                suggestions.append(f"落后且第{minute}分钟: 建议提高防线，增加逼抢强度")
                if instructions.passing_style in [PassingStyle.VERY_SHORT, PassingStyle.SHORT]:
                    suggestions.append("考虑增加传球距离，直接威胁对方球门")
                if instructions.tempo in [Tempo.LOW, Tempo.VERY_LOW]:
                    suggestions.append("考虑提高比赛节奏，加快进攻速度")
        
        # 领先的情况
        elif score_diff > 0:
            if is_second_half and minute > 75:
                suggestions.append(f"领先且第{minute}分钟: 可以考虑收缩防线，启用拖延时间")
                if instructions.time_wasting == TimeWasting.NEVER:
                    suggestions.append("适当拖延时间可以帮助保持领先优势")
            elif score_diff >= 2:
                suggestions.append("两球领先: 可以考虑回收阵型，保存体能")
        
        # 平局的情况
        else:
            if is_second_half and minute > 80:
                suggestions.append("平局且比赛尾声: 需要做出抉择 - 全力争胜还是保平")
        
        return suggestions


# ============================================================================
# 预定义阵型工厂
# ============================================================================

class FormationFactory:
    """预定义阵型工厂.
    
    提供常用阵型的快速创建方法。
    """
    
    @staticmethod
    def create_4_4_2() -> TacticalFormation:
        """创建经典4-4-2阵型."""
        return TacticalFormation(
            formation_code="4-4-2",
            name="4-4-2 平行中场",
            positions=["GK", "LB", "LCB", "RCB", "RB", "LM", "LCM", "RCM", "RM", "ST_L", "ST_R"],
            default_instructions=TacticalInstructions(
                defensive_line=DefensiveLine.MEDIUM,
                pressing=PressingIntensity.MEDIUM,
                width=TeamWidth.NORMAL,
                tempo=Tempo.NORMAL,
                passing_style=PassingStyle.MIXED,
            ),
        )
    
    @staticmethod
    def create_4_3_3() -> TacticalFormation:
        """创建4-3-3进攻阵型."""
        return TacticalFormation(
            formation_code="4-3-3",
            name="4-3-3 进攻阵型",
            positions=["GK", "LB", "LCB", "RCB", "RB", "CDM", "LCM", "RCM", "LW", "ST", "RW"],
            default_instructions=TacticalInstructions(
                defensive_line=DefensiveLine.HIGH,
                pressing=PressingIntensity.HIGH,
                width=TeamWidth.WIDE,
                tempo=Tempo.HIGH,
                passing_style=PassingStyle.SHORT,
            ),
        )
    
    @staticmethod
    def create_4_2_3_1() -> TacticalFormation:
        """创建4-2-3-1现代阵型."""
        return TacticalFormation(
            formation_code="4-2-3-1",
            name="4-2-3-1 现代阵型",
            positions=["GK", "LB", "LCB", "RCB", "RB", "CDM_L", "CDM_R", "LW", "CAM", "RW", "ST"],
            default_instructions=TacticalInstructions(
                defensive_line=DefensiveLine.HIGH,
                pressing=PressingIntensity.HIGH,
                width=TeamWidth.NORMAL,
                tempo=Tempo.NORMAL,
                passing_style=PassingStyle.MIXED,
            ),
        )
    
    @staticmethod
    def create_5_3_2() -> TacticalFormation:
        """创建5-3-2防守阵型."""
        return TacticalFormation(
            formation_code="5-3-2",
            name="5-3-2 三中卫",
            positions=["GK", "LWB", "LCB", "CB", "RCB", "RWB", "LCM", "CM", "RCM", "ST_L", "ST_R"],
            default_instructions=TacticalInstructions(
                defensive_line=DefensiveLine.LOW,
                pressing=PressingIntensity.LOW,
                width=TeamWidth.NARROW,
                tempo=Tempo.LOW,
                passing_style=PassingStyle.LONG,
                counter_attack=True,
            ),
        )
    
    @classmethod
    def from_enum(cls, formation: Formation) -> TacticalFormation:
        """从枚举创建阵型."""
        formation_map = {
            Formation.F_4_4_2: cls.create_4_4_2,
            Formation.F_4_3_3: cls.create_4_3_3,
            Formation.F_4_2_3_1: cls.create_4_2_3_1,
            Formation.F_5_3_2: cls.create_5_3_2,
        }
        
        creator = formation_map.get(formation, cls.create_4_4_2)
        return creator()


# ============================================================================
# 便捷函数
# ============================================================================

def get_default_instructions() -> TacticalInstructions:
    """获取默认战术指令."""
    return TacticalInstructions()


def create_balanced_tactics() -> TacticalInstructions:
    """创建平衡型战术指令."""
    return TacticalInstructions(
        defensive_line=DefensiveLine.MEDIUM,
        pressing=PressingIntensity.MEDIUM,
        width=TeamWidth.NORMAL,
        tempo=Tempo.NORMAL,
        passing_style=PassingStyle.MIXED,
        time_wasting=TimeWasting.NEVER,
    )


def create_possession_tactics() -> TacticalInstructions:
    """创建控球型战术指令."""
    return TacticalInstructions(
        defensive_line=DefensiveLine.HIGH,
        pressing=PressingIntensity.HIGH,
        width=TeamWidth.WIDE,
        tempo=Tempo.LOW,
        passing_style=PassingStyle.VERY_SHORT,
        play_out_of_defence=True,
    )


def create_counter_attack_tactics() -> TacticalInstructions:
    """创建反击型战术指令."""
    return TacticalInstructions(
        defensive_line=DefensiveLine.LOW,
        pressing=PressingIntensity.LOW,
        width=TeamWidth.NARROW,
        tempo=Tempo.HIGH,
        passing_style=PassingStyle.LONG,
        counter_attack=True,
        hold_shape=True,
    )


def create_park_the_bus_tactics() -> TacticalInstructions:
    """创建大巴战术指令."""
    return TacticalInstructions(
        defensive_line=DefensiveLine.VERY_LOW,
        pressing=PressingIntensity.MINIMAL,
        width=TeamWidth.EXTREMELY_NARROW,
        tempo=Tempo.VERY_LOW,
        passing_style=PassingStyle.VERY_LONG,
        hold_shape=True,
        time_wasting=TimeWasting.ALWAYS,
    )


# ============================================================================
# 比赛风格系统 (PlayStyle System)
# ============================================================================

class PlayStyle(Enum):
    """比赛风格枚举 - 基于现实足球战术和FM游戏风格系统.
    
    定义球队的整体战术哲学和比赛方式。
    """
    # 控球型风格
    POSSESSION = "possession"           # 控球 - 耐心组织，控制比赛
    TIKI_TAKA = "tiki_taka"             # Tiki-Taka - 极致短传，高位压迫
    
    # 压迫型风格
    HIGH_PRESS = "high_press"           # 高位逼抢 - 积极压迫，快速转换
    GEGENPRESSING = "gegenpressing"     # 高位逼抢+ - 极限逼抢，疯狂跑动
    
    # 反击型风格
    COUNTER_ATTACK = "counter_attack"   # 快速反击 - 低位防守，速度致胜
    DIRECT = "direct"                   # 直接打法 - 快速推进，简洁高效
    ROUTE_ONE = "route_one"             # 长传冲吊 - 大脚长传，身体对抗
    
    # 防守型风格
    LOW_BLOCK = "low_block"             # 低位防守 - 收缩防线，稳固防守
    PARK_BUS = "park_bus"               # 摆大巴 - 全员退守，门前密集
    
    # 灵活型风格
    FLUID = "fluid"                     # 流动打法 - 位置轮换，自由发挥


@dataclass
class PlayStyleProfile:
    """比赛风格配置档案.
    
    详细定义每种比赛风格的战术参数、推荐角色和适用条件。
    
    Attributes:
        style: 比赛风格枚举值
        name: 风格显示名称
        description: 风格描述
        instructions: 核心战术指令配置
        recommended_roles: 推荐的球员角色字典 {位置: 角色}
        suitable_formations: 适用的阵型列表
        required_attributes: 要求的球员属性权重
        tags: 风格标签列表
    """
    style: PlayStyle
    name: str
    description: str
    instructions: TacticalInstructions
    recommended_roles: Dict[str, List[str]] = field(default_factory=dict)
    suitable_formations: List[Formation] = field(default_factory=list)
    required_attributes: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式."""
        return {
            "style": self.style.value,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions.to_dict(),
            "recommended_roles": self.recommended_roles.copy(),
            "suitable_formations": [f.value for f in self.suitable_formations],
            "required_attributes": self.required_attributes.copy(),
            "tags": self.tags.copy(),
        }


# ============================================================================
# 比赛风格详细配置 (参考FM游戏风格系统)
# ============================================================================

PLAYSTYLE_PROFILES: Dict[PlayStyle, PlayStyleProfile] = {
    # 1. 控球风格 - 控制比赛节奏
    PlayStyle.POSSESSION: PlayStyleProfile(
        style=PlayStyle.POSSESSION,
        name="控球打法",
        description="通过耐心传球控制比赛，等待最佳进攻时机。强调技术、视野和决策能力。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.HIGH,
            pressing=PressingIntensity.HIGH,
            width=TeamWidth.WIDE,
            tempo=Tempo.LOW,
            passing_style=PassingStyle.SHORT,
            play_out_of_defence=True,
            distribute_to_full_backs=True,
            counter_attack=False,
            hold_shape=True,
        ),
        recommended_roles={
            "GK": ["清道夫门将(策应)", "门将(策应)"],
            "CB": ["出球后卫(策应)", "中后卫(防守)"],
            "FB": ["进攻型边翼卫(策应)", "边后卫(策应)"],
            "DM": ["拖后组织核心(策应)", "后腰(策应)"],
            "CM": ["全能中场(策应)", "前场组织核心(策应)"],
            "AM": ["攻击型中场(策应)", "影子前锋(策应)"],
            "W": ["内切型边锋(策应)", "边锋(策应)"],
            "ST": ["拖后前锋(策应)", "伪九号(策应)"],
        },
        suitable_formations=[
            Formation.F_4_3_3,
            Formation.F_4_2_3_1,
            Formation.F_4_3_3_FALSE_9,
            Formation.F_4_1_4_1,
        ],
        required_attributes={
            "传球": 0.25,
            "技术": 0.20,
            "视野": 0.15,
            "决断": 0.15,
            "集中": 0.10,
            " teamwork": 0.15,
        },
        tags=["控球", "技术流", "耐心", "高位防线", "短传"],
    ),
    
    # 2. Tiki-Taka - 极致控球
    PlayStyle.TIKI_TAKA: PlayStyleProfile(
        style=PlayStyle.TIKI_TAKA,
        name="Tiki-Taka",
        description="极致的短传配合，全员参与进攻组织。需要极高的技术能力和战术理解力。源自西班牙足球哲学。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.VERY_HIGH,
            pressing=PressingIntensity.EXTREME,
            width=TeamWidth.EXTREMELY_NARROW,
            tempo=Tempo.VERY_LOW,
            passing_style=PassingStyle.VERY_SHORT,
            play_out_of_defence=True,
            distribute_to_full_backs=False,
            counter_attack=False,
            hold_shape=True,
        ),
        recommended_roles={
            "GK": ["清道夫门将(策应)", "清道夫门将(进攻)"],
            "CB": ["出球后卫(策应)", "自由人(策应)"],
            "FB": ["边后卫(策应)", "内切型边后卫(策应)"],
            "DM": ["拖后组织核心(策应)", "节拍器(策应)"],
            "CM": ["全能中场(策应)", "前场组织核心(进攻)"],
            "AM": ["攻击型中场(策应)", "伪九号(策应)"],
            "W": ["内切型边锋(策应)", "边锋(策应)"],
            "ST": ["伪九号(策应)", "拖后前锋(策应)"],
        },
        suitable_formations=[
            Formation.F_4_3_3_FALSE_9,
            Formation.F_4_1_4_1,
            Formation.F_4_3_3,
            Formation.F_3_4_3,
        ],
        required_attributes={
            "传球": 0.30,
            "技术": 0.25,
            "视野": 0.20,
            "决断": 0.15,
            "团队合作": 0.10,
        },
        tags=["极致控球", "极致短传", "极高防线", "极限逼抢", "西班牙风格"],
    ),
    
    # 3. 高位逼抢
    PlayStyle.HIGH_PRESS: PlayStyleProfile(
        style=PlayStyle.HIGH_PRESS,
        name="高位逼抢",
        description="在对方半场积极压迫，试图在高位夺回球权。强调体能、侵略性和快速转换。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.VERY_HIGH,
            pressing=PressingIntensity.HIGH,
            width=TeamWidth.WIDE,
            tempo=Tempo.HIGH,
            passing_style=PassingStyle.SHORT,
            play_out_of_defence=True,
            distribute_to_full_backs=True,
            counter_attack=False,
            hold_shape=False,
        ),
        recommended_roles={
            "GK": ["清道夫门将(策应)", "门将(策应)"],
            "CB": ["出球后卫(策应)", "中后卫(防守)"],
            "FB": ["进攻型边翼卫(策应)", "边后卫(策应)"],
            "DM": ["抢球机器(策应)", "后腰(策应)"],
            "CM": ["全能中场(策应)", "盒到盒中场(策应)"],
            "AM": ["攻击型中场(进攻)", "影子前锋(策应)"],
            "W": ["边锋(进攻)", "内切型边锋(进攻)"],
            "ST": ["紧逼型前锋(策应)", "抢点型前锋(进攻)"],
        },
        suitable_formations=[
            Formation.F_4_3_3,
            Formation.F_4_2_3_1,
            Formation.F_4_4_2,
            Formation.F_4_2_2_2,
        ],
        required_attributes={
            "工作投入": 0.20,
            "耐力": 0.20,
            "速度": 0.15,
            "抢断": 0.15,
            "传球": 0.15,
            "决断": 0.15,
        },
        tags=["高位压迫", "积极逼抢", "快速转换", "高体能要求"],
    ),
    
    # 4. 高位逼抢+(Gegenpressing)
    PlayStyle.GEGENPRESSING: PlayStyleProfile(
        style=PlayStyle.GEGENPRESSING,
        name="高位逼抢+",
        description="失去球权后立即疯狂反抢，通过极限逼抢压制对手。克洛普式足球哲学的极致体现。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.VERY_HIGH,
            pressing=PressingIntensity.EXTREME,
            width=TeamWidth.EXTREMELY_WIDE,
            tempo=Tempo.VERY_HIGH,
            passing_style=PassingStyle.SHORT,
            play_out_of_defence=False,
            distribute_to_full_backs=False,
            counter_attack=False,
            hold_shape=False,
        ),
        recommended_roles={
            "GK": ["清道夫门将(策应)", "清道夫门将(进攻)"],
            "CB": ["出球后卫(策应)", "中后卫(防守)"],
            "FB": ["进攻型边翼卫(策应)", "翼卫(策应)"],
            "DM": ["抢球机器(策应)", "全能中场(策应)"],
            "CM": ["盒到盒中场(策应)", "全能中场(策应)"],
            "AM": ["攻击型中场(进攻)", "影子前锋(策应)"],
            "W": ["边锋(进攻)", "内切型边锋(进攻)"],
            "ST": ["紧逼型前锋(策应)", "抢点型前锋(进攻)"],
        },
        suitable_formations=[
            Formation.F_4_3_3,
            Formation.F_4_2_3_1,
            Formation.F_4_2_2_2,
            Formation.F_3_4_3,
        ],
        required_attributes={
            "工作投入": 0.25,
            "耐力": 0.25,
            "速度": 0.20,
            "抢断": 0.15,
            "团队合作": 0.15,
        },
        tags=["极限逼抢", "极高防线", "疯狂跑动", "克洛普", "利物浦风格"],
    ),
    
    # 5. 快速反击
    PlayStyle.COUNTER_ATTACK: PlayStyleProfile(
        style=PlayStyle.COUNTER_ATTACK,
        name="快速反击",
        description="低位防守，利用对方身后的空当快速反击。需要速度型前锋和精准的长传能力。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.LOW,
            pressing=PressingIntensity.LOW,
            width=TeamWidth.NORMAL,
            tempo=Tempo.HIGH,
            passing_style=PassingStyle.MIXED,
            play_out_of_defence=False,
            distribute_to_full_backs=False,
            counter_attack=True,
            hold_shape=False,
        ),
        recommended_roles={
            "GK": ["门将(策应)", "清道夫门将(策应)"],
            "CB": ["中后卫(防守)", "出球后卫(防守)"],
            "FB": ["边后卫(策应)", "边翼卫(策应)"],
            "DM": ["后腰(策应)", "抢球机器(策应)"],
            "CM": ["全能中场(策应)", "拖后组织核心(策应)"],
            "AM": ["攻击型中场(策应)", "影子前锋(策应)"],
            "W": ["边锋(进攻)", "内切型边锋(进攻)"],
            "ST": ["突前前锋(进攻)", "抢点型前锋(进攻)"],
        },
        suitable_formations=[
            Formation.F_4_3_3,
            Formation.F_4_2_3_1,
            Formation.F_5_3_2,
            Formation.F_5_4_1,
        ],
        required_attributes={
            "速度": 0.25,
            "加速": 0.20,
            "传球": 0.15,
            "决断": 0.15,
            "无球跑": 0.15,
            "防守": 0.10,
        },
        tags=["反击", "速度", "低位防守", "直接", "转换快"],
    ),
    
    # 6. 直接打法
    PlayStyle.DIRECT: PlayStyleProfile(
        style=PlayStyle.DIRECT,
        name="直接打法",
        description="简洁快速的进攻方式，减少无谓的传球，尽快将球送入危险区域。英式传统风格。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.MEDIUM,
            pressing=PressingIntensity.MEDIUM,
            width=TeamWidth.WIDE,
            tempo=Tempo.HIGH,
            passing_style=PassingStyle.LONG,
            play_out_of_defence=False,
            distribute_to_full_backs=True,
            counter_attack=True,
            hold_shape=False,
        ),
        recommended_roles={
            "GK": ["门将(策应)", "清道夫门将(策应)"],
            "CB": ["中后卫(防守)", "出球后卫(防守)"],
            "FB": ["边后卫(策应)", "进攻型边翼卫(策应)"],
            "DM": ["后腰(策应)", "抢球机器(策应)"],
            "CM": ["全能中场(策应)", "拖后组织核心(策应)"],
            "AM": ["攻击型中场(进攻)", "影子前锋(策应)"],
            "W": ["边锋(进攻)", "内切型边锋(进攻)"],
            "ST": ["突前前锋(进攻)", "站桩中锋(策应)"],
        },
        suitable_formations=[
            Formation.F_4_4_2,
            Formation.F_4_3_3,
            Formation.F_4_2_3_1,
            Formation.F_4_2_2_2,
        ],
        required_attributes={
            "传球": 0.20,
            "头球": 0.15,
            "速度": 0.15,
            "强壮": 0.15,
            "无球跑": 0.15,
            "决断": 0.20,
        },
        tags=["直接", "英式", "简洁", "快速推进"],
    ),
    
    # 7. 长传冲吊 (Route One)
    PlayStyle.ROUTE_ONE: PlayStyleProfile(
        style=PlayStyle.ROUTE_ONE,
        name="长传冲吊",
        description="大脚长传寻找前锋，依靠身体对抗和第二落点创造机会。传统英式长传打法。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.LOW,
            pressing=PressingIntensity.LOW,
            width=TeamWidth.NARROW,
            tempo=Tempo.HIGH,
            passing_style=PassingStyle.VERY_LONG,
            play_out_of_defence=False,
            distribute_to_full_backs=False,
            counter_attack=True,
            hold_shape=True,
        ),
        recommended_roles={
            "GK": ["门将(策应)", "清道夫门将(策应)"],
            "CB": ["中后卫(防守)", "出球后卫(防守)"],
            "FB": ["边后卫(策应)", "防守型边后卫(策应)"],
            "DM": ["后腰(策应)", "抢球机器(策应)"],
            "CM": ["全能中场(策应)", "拖后组织核心(策应)"],
            "AM": ["攻击型中场(进攻)", "影子前锋(策应)"],
            "W": ["边锋(策应)", "传统边锋(策应)"],
            "ST": ["站桩中锋(策应)", "抢点型前锋(进攻)"],
        },
        suitable_formations=[
            Formation.F_4_4_2,
            Formation.F_4_4_2_DIAMOND,
            Formation.F_4_3_3,
            Formation.F_4_2_2_2,
        ],
        required_attributes={
            "头球": 0.30,
            "强壮": 0.20,
            "传球": 0.15,
            "速度": 0.15,
            "预判": 0.20,
        },
        tags=["长传", "英式传统", "身体对抗", "第二落点"],
    ),
    
    # 8. 低位防守
    PlayStyle.LOW_BLOCK: PlayStyleProfile(
        style=PlayStyle.LOW_BLOCK,
        name="低位防守",
        description="收缩防线深度防守，压缩对手进攻空间。适合对阵强队时的稳守策略。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.LOW,
            pressing=PressingIntensity.LOW,
            width=TeamWidth.NARROW,
            tempo=Tempo.LOW,
            passing_style=PassingStyle.SHORT,
            play_out_of_defence=True,
            distribute_to_full_backs=False,
            counter_attack=False,
            hold_shape=True,
        ),
        recommended_roles={
            "GK": ["门将(策应)", "清道夫门将(策应)"],
            "CB": ["中后卫(防守)", "出球后卫(防守)"],
            "FB": ["防守型边后卫(策应)", "边后卫(策应)"],
            "DM": ["后腰(策应)", "抢球机器(策应)"],
            "CM": ["全能中场(策应)", "拖后组织核心(策应)"],
            "AM": ["攻击型中场(策应)", "影子前锋(策应)"],
            "W": ["边锋(策应)", "传统边锋(策应)"],
            "ST": ["拖后前锋(策应)", "站桩中锋(策应)"],
        },
        suitable_formations=[
            Formation.F_5_4_1,
            Formation.F_5_3_2,
            Formation.F_4_5_1,
            Formation.F_4_1_4_1,
        ],
        required_attributes={
            "防守": 0.25,
            "位置感": 0.20,
            "集中": 0.15,
            "传球": 0.15,
            "决断": 0.15,
            "纪律": 0.10,
        },
        tags=["防守", "低位", "稳固", "保守", "稳守反击"],
    ),
    
    # 9. 摆大巴 (Park the Bus)
    PlayStyle.PARK_BUS: PlayStyleProfile(
        style=PlayStyle.PARK_BUS,
        name="摆大巴",
        description="全员退守，门前密集防守，牺牲进攻换取不失球。穆里尼奥式的极致防守战术。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.VERY_LOW,
            pressing=PressingIntensity.MINIMAL,
            width=TeamWidth.EXTREMELY_NARROW,
            tempo=Tempo.VERY_LOW,
            passing_style=PassingStyle.VERY_LONG,
            play_out_of_defence=False,
            distribute_to_full_backs=False,
            counter_attack=False,
            hold_shape=True,
            time_wasting=TimeWasting.OFTEN,
        ),
        recommended_roles={
            "GK": ["门将(策应)", "清道夫门将(策应)"],
            "CB": ["中后卫(防守)", "出球后卫(防守)"],
            "FB": ["防守型边后卫(策应)", "防守型边后卫(防守)"],
            "DM": ["后腰(策应)", "抢球机器(策应)"],
            "CM": ["全能中场(策应)", "拖后组织核心(策应)"],
            "AM": ["攻击型中场(策应)", "影子前锋(策应)"],
            "W": ["边锋(策应)", "防守型边锋(策应)"],
            "ST": ["站桩中锋(策应)", "紧逼型前锋(策应)"],
        },
        suitable_formations=[
            Formation.F_5_4_1,
            Formation.F_5_3_2,
            Formation.F_4_5_1,
        ],
        required_attributes={
            "防守": 0.30,
            "位置感": 0.20,
            "集中": 0.15,
            "强壮": 0.15,
            "头球": 0.10,
            "纪律": 0.10,
        },
        tags=["极致防守", "门前密集", "穆帅风格", "铁桶阵", "拖延时间"],
    ),
    
    # 10. 流动打法
    PlayStyle.FLUID: PlayStyleProfile(
        style=PlayStyle.FLUID,
        name="流动打法",
        description="球员位置灵活轮换，创造人数优势和空间。需要高智商球员和默契配合。",
        instructions=TacticalInstructions(
            defensive_line=DefensiveLine.HIGH,
            pressing=PressingIntensity.MEDIUM,
            width=TeamWidth.WIDE,
            tempo=Tempo.NORMAL,
            passing_style=PassingStyle.SHORT,
            play_out_of_defence=True,
            distribute_to_full_backs=True,
            counter_attack=False,
            hold_shape=False,
        ),
        recommended_roles={
            "GK": ["清道夫门将(策应)", "清道夫门将(进攻)"],
            "CB": ["出球后卫(策应)", "自由人(策应)"],
            "FB": ["进攻型边翼卫(策应)", "翼卫(策应)"],
            "DM": ["拖后组织核心(策应)", "节拍器(策应)"],
            "CM": ["全能中场(策应)", "前场组织核心(策应)"],
            "AM": ["攻击型中场(自由)", "影子前锋(策应)"],
            "W": ["内切型边锋(策应)", "边锋(策应)"],
            "ST": ["伪九号(策应)", "全能前锋(策应)"],
        },
        suitable_formations=[
            Formation.F_4_3_3,
            Formation.F_4_3_3_FALSE_9,
            Formation.F_3_4_3,
            Formation.F_3_4_2_1,
            Formation.F_3_5_2,
        ],
        required_attributes={
            "传球": 0.20,
            "视野": 0.20,
            "决断": 0.20,
            "技术": 0.20,
            "团队合作": 0.10,
            "想象力": 0.10,
        },
        tags=["位置轮换", "流动性", "创造力", "荷兰风格", "克鲁伊夫"],
    ),
}


# ============================================================================
# 比赛风格管理器
# ============================================================================

class PlayStyleManager:
    """比赛风格管理器.
    
    管理所有比赛风格配置，提供风格查询、推荐和应用功能。
    """
    
    def __init__(self):
        """初始化管理器."""
        self._profiles = PLAYSTYLE_PROFILES
    
    def get_style_profile(self, style: PlayStyle) -> Optional[PlayStyleProfile]:
        """获取指定风格档案.
        
        Args:
            style: 比赛风格枚举值
            
        Returns:
            PlayStyleProfile 实例或 None
        """
        return self._profiles.get(style)
    
    def get_all_styles(self) -> List[PlayStyleProfile]:
        """获取所有风格档案.
        
        Returns:
            PlayStyleProfile 列表
        """
        return list(self._profiles.values())
    
    def get_styles_by_tag(self, tag: str) -> List[PlayStyleProfile]:
        """按标签获取风格.
        
        Args:
            tag: 风格标签
            
        Returns:
            包含该标签的风格列表
        """
        return [p for p in self._profiles.values() if tag in p.tags]
    
    def recommend_style(
        self,
        squad_attributes: Dict[str, float],
        opponent_strength: float = 0.5,
        game_importance: float = 0.5,
    ) -> List[Tuple[PlayStyle, float]]:
        """根据阵容属性推荐比赛风格.
        
        计算每种风格与球队属性的匹配度，返回排序后的推荐列表。
        
        Args:
            squad_attributes: 球队平均属性字典
            opponent_strength: 对手实力 (0.0-1.0)
            game_importance: 比赛重要程度 (0.0-1.0)
            
        Returns:
            [(PlayStyle, 匹配度分数), ...] 按匹配度降序排列
        """
        scores = []
        
        for style, profile in self._profiles.items():
            score = self._calculate_style_match(profile, squad_attributes)
            
            # 根据对手实力调整
            if opponent_strength > 0.7:  # 对阵强队
                if style in [PlayStyle.LOW_BLOCK, PlayStyle.PARK_BUS, PlayStyle.COUNTER_ATTACK]:
                    score *= 1.2
                elif style in [PlayStyle.TIKI_TAKA, PlayStyle.GEGENPRESSING]:
                    score *= 0.9
            elif opponent_strength < 0.3:  # 对阵弱队
                if style in [PlayStyle.POSSESSION, PlayStyle.TIKI_TAKA, PlayStyle.HIGH_PRESS]:
                    score *= 1.2
                elif style in [PlayStyle.PARK_BUS, PlayStyle.LOW_BLOCK]:
                    score *= 0.8
            
            # 根据比赛重要性调整
            if game_importance > 0.8:  # 重要比赛
                if style in [PlayStyle.LOW_BLOCK, PlayStyle.DIRECT]:
                    score *= 1.1
            
            scores.append((style, score))
        
        # 按匹配度降序排列
        return sorted(scores, key=lambda x: x[1], reverse=True)
    
    def _calculate_style_match(
        self,
        profile: PlayStyleProfile,
        squad_attributes: Dict[str, float],
    ) -> float:
        """计算风格与阵容的匹配度.
        
        Args:
            profile: 风格档案
            squad_attributes: 球队属性
            
        Returns:
            匹配度分数 (0.0-1.0)
        """
        if not profile.required_attributes or not squad_attributes:
            return 0.5
        
        total_weight = sum(profile.required_attributes.values())
        if total_weight == 0:
            return 0.5
        
        weighted_score = 0.0
        for attr, weight in profile.required_attributes.items():
            squad_value = squad_attributes.get(attr, 50)
            # 将属性值归一化到 0-1
            normalized = min(1.0, max(0.0, squad_value / 100.0))
            weighted_score += normalized * (weight / total_weight)
        
        return weighted_score
    
    def apply_style(
        self,
        style: PlayStyle,
        base_formation: Optional[TacticalFormation] = None,
        custom_adjustments: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TacticalInstructions, Optional[TacticalFormation], Dict[str, List[str]]]:
        """应用比赛风格到战术配置.
        
        根据风格生成完整的战术配置，包括指令、阵型和角色建议。
        
        Args:
            style: 要应用的风格
            base_formation: 基础阵型（可选）
            custom_adjustments: 自定义调整（可选）
            
        Returns:
            (战术指令, 建议阵型, 推荐角色字典)
        """
        profile = self._profiles.get(style)
        if not profile:
            raise ValueError(f"未知的比赛风格: {style}")
        
        # 复制风格的基础指令
        instructions = profile.instructions.copy()
        
        # 应用自定义调整
        if custom_adjustments:
            for key, value in custom_adjustments.items():
                if hasattr(instructions, key):
                    setattr(instructions, key, value)
        
        # 确定阵型
        formation = base_formation
        if formation is None and profile.suitable_formations:
            # 使用推荐的第一个阵型
            from_factory = FormationFactory.from_enum(profile.suitable_formations[0])
            formation = from_factory
        
        return instructions, formation, profile.recommended_roles
    
    def compare_styles(self, style1: PlayStyle, style2: PlayStyle) -> Dict[str, Any]:
        """比较两种比赛风格.
        
        Args:
            style1: 第一种风格
            style2: 第二种风格
            
        Returns:
            比较结果字典
        """
        p1 = self._profiles.get(style1)
        p2 = self._profiles.get(style2)
        
        if not p1 or not p2:
            return {"error": "风格不存在"}
        
        return {
            "style1": {"name": p1.name, "style": p1.style.value},
            "style2": {"name": p2.name, "style": p2.style.value},
            "defensive_line_diff": p1.instructions.defensive_line.value - p2.instructions.defensive_line.value,
            "pressing_diff": p1.instructions.pressing.value - p2.instructions.pressing.value,
            "tempo_diff": p1.instructions.tempo.value - p2.instructions.tempo.value,
            "passing_diff": p1.instructions.passing_style.value - p2.instructions.passing_style.value,
            "common_tags": list(set(p1.tags) & set(p2.tags)),
            "unique_to_1": list(set(p1.tags) - set(p2.tags)),
            "unique_to_2": list(set(p2.tags) - set(p1.tags)),
        }
    
    def get_styles_by_category(self, category: str) -> List[PlayStyleProfile]:
        """按类别获取风格.
        
        Args:
            category: 类别名称 ("possession", "pressing", "counter", "defensive", "flexible")
            
        Returns:
            该类别下的风格列表
        """
        category_map = {
            "possession": [PlayStyle.POSSESSION, PlayStyle.TIKI_TAKA],
            "pressing": [PlayStyle.HIGH_PRESS, PlayStyle.GEGENPRESSING],
            "counter": [PlayStyle.COUNTER_ATTACK, PlayStyle.DIRECT, PlayStyle.ROUTE_ONE],
            "defensive": [PlayStyle.LOW_BLOCK, PlayStyle.PARK_BUS],
            "flexible": [PlayStyle.FLUID],
        }
        
        styles = category_map.get(category.lower(), [])
        return [self._profiles[s] for s in styles if s in self._profiles]


# ============================================================================
# 便捷函数
# ============================================================================

def get_playstyle_manager() -> PlayStyleManager:
    """获取比赛风格管理器实例."""
    return PlayStyleManager()


def quick_apply_style(
    style: PlayStyle,
    formation: Optional[Formation] = None,
) -> Tuple[TacticalInstructions, Optional[TacticalFormation]]:
    """快速应用比赛风格.
    
    Args:
        style: 比赛风格
        formation: 阵型枚举（可选）
        
    Returns:
        (战术指令, 阵型配置)
    """
    manager = PlayStyleManager()
    base_formation = None
    if formation:
        base_formation = FormationFactory.from_enum(formation)
    
    instructions, form, _ = manager.apply_style(style, base_formation)
    return instructions, form


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 球员角色系统
    "PlayerRole",
    "PlayerRoleProfile",
    "RoleManager",
    # 枚举
    "DefensiveLine",
    "PressingIntensity",
    "TeamWidth",
    "Tempo",
    "PassingStyle",
    "TimeWasting",
    "Formation",
    "PlayStyle",
    # 数据类
    "TacticalInstructions",
    "TacticalFormation",
    "PlayStyleProfile",
    # 验证器和工厂
    "TacticalInstructionsValidator",
    "FormationFactory",
    "PlayStyleManager",
    # 风格配置
    "PLAYSTYLE_PROFILES",
    # 便捷函数
    "get_default_instructions",
    "create_balanced_tactics",
    "create_possession_tactics",
    "create_counter_attack_tactics",
    "create_park_the_bus_tactics",
    "get_playstyle_manager",
    "quick_apply_style",
]
