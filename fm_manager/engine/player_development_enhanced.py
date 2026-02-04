"""Enhanced Player Development System with Personalized Growth Curves.

This module implements a personalized player development system where each player
has unique growth trajectories based on:
- Development type (early bloomer, standard, late bloomer, consistent)
- Position sub-type (speed winger, technical midfielder, etc.)
- Personality traits (professionalism, ambition, pressure resistance)
- Environmental factors (league level, coach quality, playing time)
"""

import math
import random
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from fm_manager.core.models import Player, Position
from fm_manager.core.models.player_enums import (
    PlayerDevelopmentType,
    PlayerSubType,
)


class PersonalizedGrowthCurve:
    """Generate personalized growth curves for each player."""
    
    # 基础曲线模板（按发展类型）
    CURVE_TEMPLATES = {
        PlayerDevelopmentType.EARLY_BLOOMER: {
            "peak_start": 18, "peak_end": 22,
            "growth_phase": (15, 21), "decline_start": 23,
            "growth_mult": 1.3, "decline_mult": 1.2
        },
        PlayerDevelopmentType.STANDARD: {
            "peak_start": 24, "peak_end": 28,
            "growth_phase": (16, 25), "decline_start": 29,
            "growth_mult": 1.0, "decline_mult": 1.0
        },
        PlayerDevelopmentType.LATE_BLOOMER: {
            "peak_start": 27, "peak_end": 31,
            "growth_phase": (18, 28), "decline_start": 32,
            "growth_mult": 0.8, "decline_mult": 0.8
        },
        PlayerDevelopmentType.CONSISTENT: {
            "peak_start": 24, "peak_end": 30,
            "growth_phase": (16, 26), "decline_start": 31,
            "growth_mult": 0.9, "decline_mult": 0.6
        },
    }
    
    # 位置类型修正系数
    POSITION_MODIFIERS = {
        PlayerSubType.PACING_WINGER: {
            "peak_start": -2, "peak_end": -1,  # 巅峰期提前
            "decline_mult": 1.3                # 速度型早衰
        },
        PlayerSubType.TECHNICAL_WINGER: {
            "peak_start": -1, "peak_end": 0,   # 略微提前
            "decline_mult": 0.9
        },
        PlayerSubType.CREATIVE_PLAYMAKER: {
            "peak_start": +2, "peak_end": +3,  # 巅峰期延后
            "decline_mult": 0.7                # 技术型晚衰
        },
        PlayerSubType.BOX_TO_BOX: {
            "peak_start": +1, "peak_end": +2,
            "decline_mult": 0.9
        },
        PlayerSubType.DEFENSIVE_MIDFIELDER: {
            "peak_start": +1, "peak_end": +2,
            "decline_mult": 0.9
        },
        PlayerSubType.SWEEP_KEEPER: {
            "peak_start": +3, "peak_end": +4,  # 门将最晚熟
            "decline_mult": 0.5
        },
        PlayerSubType.TRADITIONAL_KEEPER: {
            "peak_start": +2, "peak_end": +3,
            "decline_mult": 0.6
        },
        PlayerSubType.BALL_PLAYING_DEFENDER: {
            "peak_start": 0, "peak_end": +1,
            "decline_mult": 0.9
        },
        PlayerSubType.PURE_DEFENDER: {
            "peak_start": 0, "peak_end": +1,
            "decline_mult": 0.95
        },
        PlayerSubType.TARGET_MAN: {
            "peak_start": -1, "peak_end": +1,  # 相对标准
            "decline_mult": 0.8
        },
        PlayerSubType.POACHER: {
            "peak_start": 0, "peak_end": 0,
            "decline_mult": 1.0
        },
    }
    
    @classmethod
    def generate_player_curve(cls, player: Player, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """Generate personalized growth curve parameters for a player.
        
        Args:
            player: The player to generate curve for
            rng: Optional random generator for reproducibility
            
        Returns:
            Dict with curve parameters
        """
        if rng is None:
            rng = random
        
        # 1. 获取基础模板
        dev_type = getattr(player, 'development_type', PlayerDevelopmentType.STANDARD)
        base = cls.CURVE_TEMPLATES[dev_type].copy()
        
        # 2. 应用位置类型修正
        sub_type = getattr(player, 'player_sub_type', None)
        if sub_type and sub_type in cls.POSITION_MODIFIERS:
            pos_mod = cls.POSITION_MODIFIERS[sub_type]
            base["peak_start"] += pos_mod.get("peak_start", 0)
            base["peak_end"] += pos_mod.get("peak_end", 0)
            base["decline_mult"] *= pos_mod.get("decline_mult", 1.0)
        
        # 3. 应用性格修正
        professionalism = getattr(player, 'professionalism', 10)
        prof_mod = (professionalism - 10) * 0.02  # 归一化到 -0.2 到 +0.2
        base["growth_mult"] *= (1.0 + prof_mod)
        base["decline_mult"] *= (1.0 - prof_mod * 0.5)
        
        # 4. 基于潜力的随机波动
        potential = getattr(player, 'potential_ability', 70)
        potential_factor = (potential - 50) / 50  # 0-1
        variance = rng.gauss(0, 0.1 * max(0.2, potential_factor))
        base["growth_mult"] *= (1.0 + variance)
        
        # 5. 确保合理范围
        base["growth_mult"] = max(0.5, min(1.5, base["growth_mult"]))
        base["decline_mult"] = max(0.3, min(1.5, base["decline_mult"]))
        base["peak_start"] = max(17, min(28, base["peak_start"]))
        base["peak_end"] = max(base["peak_start"] + 2, min(33, base["peak_end"]))
        
        return base
    
    @classmethod
    def get_age_multiplier(cls, player: Player, age: int, curve: Optional[Dict] = None) -> float:
        """Get growth multiplier for a specific age.
        
        Args:
            player: The player
            age: The age to calculate for
            curve: Optional pre-calculated curve parameters
            
        Returns:
            Growth multiplier (positive = growth, negative = decline)
        """
        if curve is None:
            curve = cls.generate_player_curve(player)
        
        peak_start = curve["peak_start"]
        peak_end = curve["peak_end"]
        growth_phase = curve["growth_phase"]
        decline_start = curve["decline_start"]
        growth_mult = curve["growth_mult"]
        
        # 成长期
        if age < peak_start:
            progress = (age - growth_phase[0]) / (growth_phase[1] - growth_phase[0])
            progress = max(0, min(1, progress))
            # 使用钟形曲线，成长期中期最快
            return 1.5 * math.sin(progress * math.pi / 2) * growth_mult
        
        # 巅峰期（缓慢增长）
        elif peak_start <= age <= peak_end:
            return 0.2 * growth_mult  # 巅峰期仍有小幅增长
        
        # 衰退期
        else:
            decline_rate = curve["decline_mult"]
            years_since_decline = age - decline_start
            decline = years_since_decline * 0.2 * decline_rate
            return max(-2.0, -decline)


class PlayerPersonalityInitializer:
    """Initialize player personality and development parameters."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def assign_development_type(self, player: Player) -> PlayerDevelopmentType:
        """Assign development type based on position and attributes."""
        position = player.position
        age = player.age or 25
        
        # 速度型边锋更容易早熟
        if position in [Position.LW, Position.RW]:
            pace = getattr(player, 'pace', 50)
            if pace > 75:
                weights = {
                    PlayerDevelopmentType.EARLY_BLOOMER: 40,
                    PlayerDevelopmentType.STANDARD: 40,
                    PlayerDevelopmentType.LATE_BLOOMER: 10,
                    PlayerDevelopmentType.CONSISTENT: 10,
                }
            else:
                weights = {
                    PlayerDevelopmentType.EARLY_BLOOMER: 20,
                    PlayerDevelopmentType.STANDARD: 50,
                    PlayerDevelopmentType.LATE_BLOOMER: 15,
                    PlayerDevelopmentType.CONSISTENT: 15,
                }
        # 门将更容易晚熟
        elif position == Position.GK:
            weights = {
                PlayerDevelopmentType.EARLY_BLOOMER: 5,
                PlayerDevelopmentType.STANDARD: 35,
                PlayerDevelopmentType.LATE_BLOOMER: 40,
                PlayerDevelopmentType.CONSISTENT: 20,
            }
        # 组织型中场晚熟
        elif position in [Position.CAM, Position.CM]:
            vision = getattr(player, 'vision', 50)
            if vision > 70:
                weights = {
                    PlayerDevelopmentType.EARLY_BLOOMER: 10,
                    PlayerDevelopmentType.STANDARD: 50,
                    PlayerDevelopmentType.LATE_BLOOMER: 30,
                    PlayerDevelopmentType.CONSISTENT: 10,
                }
            else:
                weights = {
                    PlayerDevelopmentType.EARLY_BLOOMER: 15,
                    PlayerDevelopmentType.STANDARD: 50,
                    PlayerDevelopmentType.LATE_BLOOMER: 20,
                    PlayerDevelopmentType.CONSISTENT: 15,
                }
        # 其他位置默认分布
        else:
            weights = {
                PlayerDevelopmentType.EARLY_BLOOMER: 15,
                PlayerDevelopmentType.STANDARD: 50,
                PlayerDevelopmentType.LATE_BLOOMER: 20,
                PlayerDevelopmentType.CONSISTENT: 15,
            }
        
        return self._weighted_random_choice(weights)
    
    def assign_sub_type(self, player: Player) -> Optional[PlayerSubType]:
        """Assign sub-type based on position and attributes."""
        position = player.position
        
        if position == Position.GK:
            # 根据passing和vision区分出球型
            if getattr(player, 'passing', 50) > 65 and getattr(player, 'vision', 50) > 65:
                return PlayerSubType.SWEEP_KEEPER
            return PlayerSubType.TRADITIONAL_KEEPER
        
        elif position in [Position.LW, Position.RW]:
            # 根据pace和dribbling区分
            pace = getattr(player, 'pace', 50)
            dribbling = getattr(player, 'dribbling', 50)
            if pace > dribbling + 10:
                return PlayerSubType.PACING_WINGER
            return PlayerSubType.TECHNICAL_WINGER
        
        elif position in [Position.CM, Position.CDM, Position.CAM]:
            # 根据vision和passing区分
            vision = getattr(player, 'vision', 50)
            passing = getattr(player, 'passing', 50)
            tackling = getattr(player, 'tackling', 50)
            stamina = getattr(player, 'stamina', 50)
            
            if vision > 75 and passing > 70:
                return PlayerSubType.CREATIVE_PLAYMAKER
            elif tackling > 70 and stamina > 70:
                return PlayerSubType.BOX_TO_BOX
            return PlayerSubType.DEFENSIVE_MIDFIELDER
        
        elif position in [Position.CB, Position.LB, Position.RB, Position.LWB, Position.RWB]:
            # 根据passing区分
            if getattr(player, 'passing', 50) > 60:
                return PlayerSubType.BALL_PLAYING_DEFENDER
            return PlayerSubType.PURE_DEFENDER
        
        elif position in [Position.ST, Position.CF]:
            # 根据strength和positioning区分
            strength = getattr(player, 'strength', 50)
            positioning = getattr(player, 'positioning', 50)
            
            if strength > 70 and positioning > 65:
                return PlayerSubType.TARGET_MAN
            return PlayerSubType.POACHER
        
        return None
    
    def generate_personality(self, player: Player) -> Tuple[int, int, int]:
        """Generate personality traits (1-20 scale).
        
        Returns:
            Tuple of (professionalism, ambition, pressure_resistance)
        """
        # 潜力高通常职业素养和野心高
        potential = getattr(player, 'potential_ability', 70)
        potential_factor = (potential - 50) / 50
        
        # 职业素养：基准10 + 潜力影响 + 随机
        prof = int(10 + potential_factor * 4 + self.rng.gauss(0, 2))
        prof = max(1, min(20, prof))
        
        # 野心：基准10 + 潜力影响 + 随机
        amb = int(10 + potential_factor * 3 + self.rng.gauss(0, 2))
        amb = max(1, min(20, amb))
        
        # 抗压能力：基准10 + 个性随机
        press = int(10 + self.rng.gauss(0, 3))
        press = max(1, min(20, press))
        
        return prof, amb, press
    
    def initialize_player(self, player: Player):
        """Initialize all personalized parameters for a player."""
        # 1. 分配发展类型
        player.development_type = self.assign_development_type(player)
        
        # 2. 分配子类型
        player.player_sub_type = self.assign_sub_type(player)
        
        # 3. 生成性格
        prof, amb, press = self.generate_personality(player)
        player.professionalism = prof
        player.ambition = amb
        player.pressure_resistance = press
        
        # 4. 生成成长曲线参数
        curve = PersonalizedGrowthCurve.generate_player_curve(player, self.rng)
        player.peak_age_start = curve["peak_start"]
        player.peak_age_end = curve["peak_end"]
        player.growth_rate = curve["growth_mult"]
        player.decline_rate = curve["decline_mult"]
        
        # 5. 设置联赛适应度（初始70）
        player.league_fit = 70
        
        # 6. 初始化其他字段
        if not hasattr(player, 'total_hours_trained') or player.total_hours_trained is None:
            player.total_hours_trained = 0
        if not hasattr(player, 'coaches_mentored') or player.coaches_mentored is None:
            player.coaches_mentored = 0
    
    def _weighted_random_choice(self, weights: Dict[Any, float]) -> Any:
        """Weighted random choice from dictionary."""
        total = sum(weights.values())
        r = self.rng.random() * total
        cumulative = 0
        for key, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return key
        return list(weights.keys())[0]


class EnhancedPlayerDevelopmentEngine:
    """Enhanced player development engine with personalized growth curves."""
    
    # Playing time thresholds (minutes per season)
    PLAYING_TIME_BONUS = {
        0: 0.0,
        500: 0.3,
        1000: 0.6,
        1500: 0.8,
        2000: 1.0,
        2500: 1.1,
        3000: 1.2,
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.curve_generator = PersonalizedGrowthCurve()
    
    def calculate_season_development(
        self,
        player: Player,
        minutes_played: int,
        training_quality: int = 50,
        coach_ability: int = 50,
        league_level: int = 3,
        match_ratings: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Calculate development for a full season with personalized factors.
        
        Args:
            player: The player
            minutes_played: Minutes played in the season
            training_quality: Training facility quality (0-100)
            coach_ability: Coach ability (0-100)
            league_level: League level (1-5, 1 is highest)
            match_ratings: List of match ratings for form bonus
            
        Returns:
            Dict with development details
        """
        age = player.age or 25
        old_ability = player.current_ability
        old_potential = player.potential_ability
        
        # 1. 获取个性化年龄倍率
        age_multiplier = self.curve_generator.get_age_multiplier(player, age)
        
        # 2. 出场时间奖励
        playing_bonus = self._get_playing_time_bonus(minutes_played)
        
        # 3. 训练质量因子
        training_factor = 0.5 + (training_quality / 100)
        
        # 4. 教练影响
        coach_factor = 0.8 + (coach_ability / 250)
        
        # 5. 联赛水平影响
        league_multiplier = {
            1: 1.2,  # 五大联赛
            2: 1.1,  # 次级顶级联赛
            3: 1.0,  # 中等联赛
            4: 0.9,  # 低级联赛
            5: 0.8,  # 低级别联赛
        }.get(league_level, 1.0)
        
        # 6. 联赛适应度影响
        league_fit = getattr(player, 'league_fit', 70)
        fit_factor = league_fit / 100
        
        # 7. 比赛表现奖励
        form_bonus = 0.0
        if match_ratings:
            avg_rating = sum(match_ratings) / len(match_ratings)
            # 抗压能力影响大赛表现
            pressure_resistance = getattr(player, 'pressure_resistance', 10)
            pressure_boost = (pressure_resistance - 10) * 0.005
            effective_rating = avg_rating + pressure_boost
            
            if effective_rating > 7.5:
                form_bonus = 0.2
            elif effective_rating > 7.0:
                form_bonus = 0.1
            elif effective_rating < 6.0:
                form_bonus = -0.1
        
        # 8. 计算总成长
        total_factors = (
            age_multiplier * playing_bonus * 
            training_factor * coach_factor * 
            league_multiplier * fit_factor
        )
        
        if age_multiplier > 0:  # 成长期
            base_growth = 5 * total_factors
            base_growth += form_bonus * 2
            
            # 潜力上限
            potential_gap = old_potential - old_ability
            growth = min(base_growth, potential_gap)
            
            # 随机波动（性格影响波动幅度）
            professionalism = getattr(player, 'professionalism', 10)
            personality_stability = professionalism / 10  # 1-2
            growth = max(0, int(self.rng.gauss(growth, growth * 0.2 / personality_stability)))
            
        else:  # 衰退期
            decline = abs(age_multiplier) * 5 * total_factors
            
            # 训练和出场可减缓衰退
            if minutes_played > 2000:
                decline *= 0.8
            elif minutes_played > 1000:
                decline *= 0.9
            
            # 职业素养高衰退慢
            prof = getattr(player, 'professionalism', 10)
            decline *= (1.0 - (prof - 10) * 0.01)
            
            growth = -max(1, int(decline))
        
        # 9. 应用成长
        new_ability = max(1, min(99, old_ability + growth))
        actual_growth = new_ability - old_ability
        
        # 10. 更新球员
        player.current_ability = new_ability
        player.total_hours_trained = getattr(player, 'total_hours_trained', 0) + int(500 * training_factor)
        
        # 11. 更新联赛适应度
        self._update_league_fit(player, league_level)
        
        # 12. 更新物理属性（年龄衰退）
        attribute_changes = {}
        if age > 30:
            attribute_changes = self._apply_age_decline(player, age)
        
        return {
            "old_ability": old_ability,
            "new_ability": new_ability,
            "growth": actual_growth,
            "age": age,
            "age_multiplier": age_multiplier,
            "playing_bonus": playing_bonus,
            "training_factor": training_factor,
            "coach_factor": coach_factor,
            "league_multiplier": league_multiplier,
            "fit_factor": fit_factor,
            "form_bonus": form_bonus,
            "attribute_changes": attribute_changes,
            "development_type": getattr(player, 'development_type', PlayerDevelopmentType.STANDARD).value,
            "player_sub_type": getattr(player, 'player_sub_type', None),
        }
    
    def _get_playing_time_bonus(self, minutes: int) -> float:
        """Get development bonus based on playing time."""
        thresholds = sorted(self.PLAYING_TIME_BONUS.keys())
        for threshold in reversed(thresholds):
            if minutes >= threshold:
                return self.PLAYING_TIME_BONUS[threshold]
        return 0.0
    
    def _update_league_fit(self, player: Player, league_level: int):
        """Update league fit based on time spent in league."""
        current_fit = getattr(player, 'league_fit', 70)
        target_fit = 70 + (5 - league_level) * 10  # 高水平联赛初期适应度低
        player.league_fit = int(current_fit + (target_fit - current_fit) * 0.1)
    
    def _apply_age_decline(self, player: Player, age: int) -> Dict[str, int]:
        """Apply age-related decline based on position sub-type."""
        changes = {}
        decline_rate = max(1, (age - 29) // 2)
        
        # 速度型边锋的pace衰退更快
        sub_type = getattr(player, 'player_sub_type', None)
        if sub_type == PlayerSubType.PACING_WINGER:
            pace_decline = decline_rate + 1
        else:
            pace_decline = decline_rate
        
        # 技术型中场技术属性衰退慢
        if sub_type == PlayerSubType.CREATIVE_PLAYMAKER:
            tech_decline = max(0, decline_rate - 1)
        else:
            tech_decline = decline_rate
        
        # 物理属性
        physical_attrs = ["pace", "acceleration", "stamina", "strength"]
        for attr in physical_attrs:
            old_val = getattr(player, attr, 50)
            if old_val is None:
                old_val = 50
            
            current_decline = pace_decline if attr in ["pace", "acceleration"] else decline_rate
            
            if old_val > 1:
                decline = self.rng.randint(0, current_decline)
                new_val = max(1, old_val - decline)
                setattr(player, attr, new_val)
                if decline > 0:
                    changes[attr] = -decline
        
        return changes


# Compatibility layer - can be used with existing development system
def enhance_existing_development(
    player: Player,
    minutes_played: int,
    training_quality: int = 50,
    league_level: int = 3,
) -> Dict[str, Any]:
    """Convenience function to use enhanced development with minimal changes.
    
    This function provides backward compatibility with the existing
    player_development system.
    """
    engine = EnhancedPlayerDevelopmentEngine()
    return engine.calculate_season_development(
        player=player,
        minutes_played=minutes_played,
        training_quality=training_quality,
        league_level=league_level,
    )
