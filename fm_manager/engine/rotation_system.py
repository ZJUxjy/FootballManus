"""阵容轮换系统

根据比赛重要性、球员疲劳、战术需求等因素智能选择首发阵容。
"""

import random
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum

from fm_manager.core.models import Player, Position


class MatchImportance(Enum):
    """比赛重要性分级"""
    CRITICAL = 1      # 德比、争冠战、保级战
    HIGH = 2          # 欧战资格战
    MEDIUM = 3        # 普通联赛
    LOW = 4           # 杯赛/弱队


@dataclass
class PlayerFitness:
    """球员状态追踪"""
    player: Player
    fatigue: float = 0.0        # 0-100, 累积疲劳
    matches_played: int = 0     # 已出场次数
    minutes_accumulated: int = 0 # 累计出场分钟
    last_match_minutes: int = 0 # 上一场出场分钟
    is_injured: bool = False
    injury_recovery_matches: int = 0

    def get_fitness_score(self) -> float:
        """获取体能评分 (0-100)，考虑疲劳和恢复"""
        base_fitness = 100.0 - self.fatigue

        # 每场比赛后恢复一些疲劳（假设有休息时间）
        recovery_rate = 15.0  # 每场比赛间隔恢复15点疲劳
        recovery = self.matches_played * recovery_rate
        actual_fitness = min(100.0, base_fitness + recovery)

        return max(30.0, actual_fitness)  # 最低30

    def update_after_match(self, minutes: int):
        """比赛后更新状态"""
        self.matches_played += 1
        self.minutes_accumulated += minutes
        self.last_match_minutes = minutes

        # 疲劳累积（出场时间越长，疲劳越多）
        fatigue_gain = minutes * 0.8  # 出场90分钟 ≈ +72疲劳
        self.fatigue = min(100.0, self.fatigue + fatigue_gain)


class LineupSelector:
    """智能阵容选择器"""

    def __init__(self, squad: List, formation: str = "4-3-3"):
        self.squad = squad
        self.formation = formation
        self.player_fitness: Dict[int, PlayerFitness] = {}
        self.last_gk_player_id = None  # 追踪上次使用的门将

        # 初始化所有球员状态
        for player in squad:
            # 处理不同类型的球员对象
            player_id = getattr(player, 'id', None)
            if player_id is None and hasattr(player, 'player'):
                player_id = player.player.id

            if player_id:
                self.player_fitness[player_id] = PlayerFitness(player=player)

    def select_lineup(
        self,
        importance: MatchImportance,
        opponent_strength: float = 70.0,
        is_home: bool = True,
        days_since_last_match: int = 7,
    ) -> List[Player]:
        """
        根据比赛重要性和球员状态选择首发

        Args:
            importance: 比赛重要性
            opponent_strength: 对手实力 (0-100)
            is_home: 是否主场
            days_since_last_match: 距离上场比赛天数

        Returns:
            11名首发球员列表
        """
        # 根据阵型确定位置需求
        position_needs = self._parse_formation(self.formation)

        lineup = []
        used_players = set()

        # 按优先级选择各个位置
        # 优先级：GK > CB > CDM/CM > CAM/ST > WB/Winger
        position_order = [
            "GK", "CB", "CB", "LB", "RB",  # 后防线
            "CDM", "CM", "CM",             # 中场
            "LW", "ST", "RW",              # 前场
        ]

        for position in position_order:
            if position in position_needs and position_needs[position] > 0:
                # 选择该位置的最佳球员
                player = self._select_best_for_position(
                    position,
                    lineup,
                    used_players,
                    importance,
                    opponent_strength,
                )

                if player:
                    lineup.append(player)
                    used_players.add(player.id)

                    # 记录门将选择
                    if position == "GK":
                        self.last_gk_player_id = player.id

        return lineup

    def _select_best_for_position(
        self,
        position: str,
        current_lineup: List,
        used_players: set,
        importance: MatchImportance,
        opponent_strength: float,
    ) -> Optional:
        """为指定位置选择最佳球员"""

        # 获取该位置的所有候选球员
        candidates = []
        for player in self.squad:
            # 获取球员ID
            player_id = getattr(player, 'id', None)
            if player_id is None and hasattr(player, 'player'):
                player_id = player.player.id

            if player_id in used_players:
                continue

            fitness = self.player_fitness.get(player_id)
            if not fitness or fitness.is_injured:
                continue

            # 检查位置匹配
            if self._can_play_position(player, position):
                score = self._calculate_player_score(
                    player, fitness, position, importance, opponent_strength
                )
                candidates.append((score, player))

        # 按评分排序，选择最佳
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1] if candidates else None

    def _calculate_player_score(
        self,
        player,  # 可以是Player或AdaptedPlayer
        fitness: PlayerFitness,
        position: str,
        importance: MatchImportance,
        opponent_strength: float,
    ) -> float:
        """
        计算球员评分，考虑多个因素

        评分因素：
        1. 基础能力 (50%)
        2. 位置匹配度 (20%)
        3. 体能状态 (15%)
        4. 比赛重要性权重 (10%)
        5. 连续出场惩罚 (5%)
        """
        # 1. 基础能力 - 兼容不同类型
        ability = getattr(player, 'current_ability', None)
        if ability is None and hasattr(player, 'player'):
            ability = player.player.current_ability
        ability = ability or 70.0

        # 2. 位置匹配度
        player_pos = getattr(player, 'position', None)
        if player_pos is None and hasattr(player, 'player'):
            player_pos = player.player.position
        position_value = player_pos.value if hasattr(player_pos, 'value') else str(player_pos)
        position_match = self._get_position_match_score(position_value, position)

        # 3. 体能状态
        fitness_score = fitness.get_fitness_score()

        # 4. 比赛重要性权重
        # 重要比赛更依赖主力（高能力），不重要的比赛可以轮换
        importance_weight = {
            MatchImportance.CRITICAL: 1.2,  # 德比/争冠战：主力优先
            MatchImportance.HIGH: 1.0,      # 欧战资格：正常轮换
            MatchImportance.MEDIUM: 0.85,   # 普通比赛：多轮换
            MatchImportance.LOW: 0.7,      # 杯赛：大幅轮换
        }
        importance_factor = importance_weight[importance]

        # 5. 连续出场惩罚（防止过度使用）
        fatigue_penalty = 0
        if fitness.matches_played >= 3:  # 连续3场+
            fatigue_penalty = (fitness.matches_played - 2) * 3  # 每多一场-3分

        # 综合评分
        score = (
            ability * 0.50 +
            position_match * 20 +
            fitness_score * 0.15 +
            fatigue_penalty
        ) * importance_factor

        # 获取球员ID（用于门将特殊处理）
        player_id = getattr(player, 'id', None)
        if player_id is None and hasattr(player, 'player'):
            player_id = player.player.id

        # 门将特殊处理：门将在现实中很少轮换
        # 如果是上次使用的门将且状态尚可（疲劳度 < 70），给予稳定性加分
        if position_value == "GK":
            if player_id == self.last_gk_player_id:
                # 主力门将的稳定性加成
                # 只有在疲劳度不是特别高时才给予加成
                if fitness.fatigue < 70:
                    score += 50  # 大幅加分，确保继续使用
                elif fitness.fatigue < 85:
                    score += 20  # 轻微加分
                # 疲劳度 >= 85 时不加分，允许轮换
            elif fitness.fatigue > 80:
                # 替补门将在主力门将疲劳时获得加分
                score += 30

        return score

    def _can_play_position(self, player, position: str) -> bool:
        """检查球员是否可以打这个位置"""
        from fm_manager.core.models.player import Position

        # 获取球员位置
        player_pos = getattr(player, 'position', None)
        if player_pos is None and hasattr(player, 'player'):
            player_pos = player.player.position

        # 获取位置值
        if hasattr(player_pos, 'value'):
            primary_pos = player_pos.value
        elif isinstance(player_pos, Position):
            primary_pos = player_pos.value  # Position枚举
        else:
            primary_pos = str(player_pos).upper()

        target_pos = position.upper()

        # 完全匹配
        if primary_pos == target_pos:
            return True

        # 兼容位置映射（扩展版）
        position_compat = {
            "GK": ["GK"],
            "CB": ["CB"],
            "LB": ["LB", "LWB", "CB"],
            "RB": ["RB", "RWB", "CB"],
            "LWB": ["LB", "LWB", "LM"],
            "RWB": ["RB", "RWB", "RM"],
            "CDM": ["CDM", "CM", "CB"],
            "CM": ["CM", "CDM", "CAM", "LM", "RM"],
            "CAM": ["CAM", "CM", "ST", "CF"],
            "LM": ["LM", "LW", "CM", "LB"],
            "RM": ["RM", "RW", "CM", "RB"],
            "LW": ["LW", "LM", "ST"],
            "RW": ["RW", "RM", "ST"],
            "ST": ["ST", "CF", "CAM"],
            "CF": ["CF", "ST"],
        }

        compatible = position_compat.get(target_pos, [])
        return primary_pos in compatible

    def _get_position_match_score(self, player_position: str, target_position: str) -> float:
        """获取位置匹配评分 (0-20)"""
        if player_position == target_position:
            return 20  # 完全匹配

        # 位置兼容性评分
        compat_scores = {
            ("CB", "LB"): 12, ("CB", "RB"): 12,
            ("CB", "LWB"): 10, ("CB", "RWB"): 10,
            ("CM", "CDM"): 18, ("CM", "CAM"): 16,
            ("CM", "LM"): 14, ("CM", "RM"): 14,
            ("CDM", "CB"): 15,
            ("CAM", "ST"): 14, ("CAM", "CF"): 16,
            ("LM", "LW"): 16, ("LM", "LB"): 12,
            ("RM", "RW"): 16, ("RM", "RB"): 12,
            ("LW", "ST"): 14, ("RW", "ST"): 14,
            ("ST", "CF"): 18,
        }

        return compat_scores.get((player_position, target_position), 8)

    def _parse_formation(self, formation: str) -> Dict[str, int]:
        """解析阵型，返回各位置需求数量"""
        formation_map = {
            "4-3-3": {"GK": 1, "CB": 2, "LB": 1, "RB": 1, "CM": 2, "CDM": 1, "LW": 1, "RW": 1, "ST": 1},
            "4-2-3-1": {"GK": 1, "CB": 2, "LB": 1, "RB": 1, "CDM": 2, "CAM": 1, "LW": 1, "RW": 1, "ST": 1},
            "4-4-2": {"GK": 1, "CB": 2, "LB": 1, "RB": 1, "CM": 2, "LM": 1, "RM": 1, "ST": 2},
            "3-5-2": {"GK": 1, "CB": 3, "CM": 2, "CDM": 1, "CAM": 1, "LM": 1, "RM": 1, "ST": 2},
            "5-3-2": {"GK": 1, "CB": 3, "LB": 1, "RB": 1, "CDM": 1, "CM": 2, "LW": 1, "RW": 1, "ST": 2},
            "5-4-1": {"GK": 1, "CB": 3, "LB": 1, "RB": 1, "CM": 3, "ST": 1},
        }

        return formation_map.get(formation, formation_map["4-3-3"])

    def update_after_match(self, lineup: List, minutes_played: Dict[int, int]):
        """比赛后更新球员状态

        Args:
            lineup: 首发阵容
            minutes_played: {player_id: 出场分钟数}
        """
        for player in lineup:
            # 获取球员ID
            player_id = getattr(player, 'id', None)
            if player_id is None and hasattr(player, 'player'):
                player_id = player.player.id

            if player_id in self.player_fitness:
                minutes = minutes_played.get(player_id, 90)
                self.player_fitness[player_id].update_after_match(minutes)

        # 所有未出场球员恢复一些疲劳
        lineup_ids = set()
        for player in lineup:
            pid = getattr(player, 'id', None)
            if pid is None and hasattr(player, 'player'):
                pid = player.player.id
            if pid:
                lineup_ids.add(pid)

        for player_id, fitness in self.player_fitness.items():
            if player_id not in lineup_ids:
                # 未出场球员恢复30%疲劳
                fitness.fatigue = max(0, fitness.fatigue * 0.7)

    def get_rotation_status(self) -> Dict[str, any]:
        """获取轮换状态统计"""
        status = {
            "total_players": len(self.squad),
            "players_high_fatigue": 0,
            "players_very_high_fatigue": 0,
            "avg_matches_played": 0,
        }

        total_matches = 0
        for fitness in self.player_fitness.values():
            if fitness.fatigue > 60:
                status["players_high_fatigue"] += 1
            if fitness.fatigue > 80:
                status["players_very_high_fatigue"] += 1
            total_matches += fitness.matches_played

        if len(self.player_fitness) > 0:
            status["avg_matches_played"] = total_matches / len(self.player_fitness)

        return status


class MatchScheduler:
    """比赛调度器 - 确定比赛重要性"""

    @staticmethod
    def determine_match_importance(
        home_team: str,
        away_team: str,
        home_league_position: int,
        away_league_position: int,
        is_cup_match: bool = False,
    ) -> MatchImportance:
        """
        确定比赛重要性

        Args:
            home_team: 主队名称
            away_team: 客队名称
            home_league_position: 主队联赛排名
            away_league_position: 客队联赛排名
            is_cup_match: 是否杯赛
        """
        # 德比战（同一城市）
        home_city = home_team.split()[0] if " " in home_team else home_team
        away_city = away_team.split()[0] if " " in away_team else away_team
        is_derby = home_city == away_city and home_city in [
            "Real", "FC", "Athletic", "Tottenham", "Man"
        ]

        if is_cup_match:
            # 杯赛后期更重要
            return MatchImportance.HIGH

        # 联赛排名前6名的对决
        top_6_clash = (home_league_position <= 6 and away_league_position <= 6)

        # 保级区对决（后6名）
        relegation_battle = (home_league_position >= 15 and away_league_position >= 15)

        if is_derby or top_6_clash:
            return MatchImportance.CRITICAL
        elif relegation_battle:
            return MatchImportance.HIGH
        elif home_league_position <= 10 or away_league_position <= 10:
            return MatchImportance.MEDIUM
        else:
            return MatchImportance.LOW
