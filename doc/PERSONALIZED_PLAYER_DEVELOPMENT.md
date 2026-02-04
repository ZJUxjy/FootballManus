# 个性化球员成长系统设计文档

## 1. 系统概述

### 1.1 设计目标
创建一个高度个性化的球员成长系统，让每个球员都有独特的发展轨迹，基于：
- 球员发展类型（早熟型/标准型/晚熟型/持续型）
- 位置类型特点（速度型/技术型/稳定型等）
- 性格特征（职业素养/野心/抗压能力）
- 动态成长曲线（基于潜力的随机波动）

### 1.2 核心特性
- ✅ 四种发展类型：早熟型、标准型、晚熟型、持续型
- ✅ 六种位置类型：速度型边锋、技术型中场、全能型后卫、守门员等
- ✅ 三种性格维度：职业素养、野心、抗压能力
- ✅ 个性化成长曲线：每个球员独特，非固定值
- ✅ 环境因素影响：联赛水平、教练质量、出场时间
- ✅ 兼容现有系统：平滑迁移，不影响现有数据

---

## 2. 数据模型设计

### 2.1 新增枚举类型

```python
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
```

### 2.2 新增 Player 模型字段

```python
class Player(Base):
    """Player entity with personalized development."""
    
    # ... 现有字段 ...
    
    # --- 新增：发展系统字段 ---
    
    # 发展类型
    development_type: Mapped[PlayerDevelopmentType] = mapped_column(
        Enum(PlayerDevelopmentType), 
        default=PlayerDevelopmentType.STANDARD
    )
    
    # 球员子类型
    player_sub_type: Mapped[PlayerSubType] = mapped_column(
        Enum(PlayerSubType),
        nullable=True  # 可为空，保持向后兼容
    )
    
    # 性格特征 (1-20 scale)
    professionalism: Mapped[int] = mapped_column(Integer, default=10)    # 职业素养
    ambition: Mapped[int] = mapped_column(Integer, default=10)         # 野心
    pressure_resistance: Mapped[int] = mapped_column(Integer, default=10)  # 抗压能力
    
    # 个性化成长参数
    peak_age_start: Mapped[int] = mapped_column(Integer, default=24)     # 巅峰开始年龄
    peak_age_end: Mapped[int] = mapped_column(Integer, default=28)       # 巅峰结束年龄
    growth_rate: Mapped[float] = mapped_column(Float, default=1.0)       # 成长速率
    decline_rate: Mapped[float] = mapped_column(Float, default=1.0)      # 衰退速率
    
    # 环境适应度 (0-100)
    league_fit: Mapped[int] = mapped_column(Integer, default=70)        # 对当前联赛的适应度
    
    # 历史记录
    total_hours_trained: Mapped[int] = mapped_column(Integer, default=0)
    coaches_mentored: Mapped[int] = mapped_column(Integer, default=0)
```

---

## 3. 成长曲线系统

### 3.1 个性化成长曲线生成

```python
class PersonalizedGrowthCurve:
    """生成每个球员独特的成长曲线"""
    
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
        PlayerSubType.CREATIVE_PLAYMAKER: {
            "peak_start": +2, "peak_end": +3,  # 巅峰期延后
            "decline_mult": 0.7                # 技术型晚衰
        },
        PlayerSubType.SWEEP_KEEPER: {
            "peak_start": +3, "peak_end": +4,  # 门将最晚熟
            "decline_mult": 0.5
        },
        PlayerSubType.TARGET_MAN: {
            "peak_start": -1, "peak_end": +1,  # 相对标准
            "decline_mult": 0.8
        },
    }
    
    # 性格影响系数
    PERSONALITY_MODIFIERS = {
        "professionalism": {"growth": 0.05, "decline": -0.03},  # 职业素养越高，成长越快，衰退越慢
        "ambition": {"growth": 0.03, "decline": -0.01},       # 野心强，成长快
        "pressure_resistance": {"form": 0.1},                   # 抗压能力影响比赛表现
    }
    
    @classmethod
    def generate_player_curve(cls, player: Player) -> Dict:
        """为单个球员生成个性化成长曲线"""
        
        # 1. 获取基础模板
        dev_type = player.development_type
        base = cls.CURVE_TEMPLATES[dev_type].copy()
        
        # 2. 应用位置类型修正
        if player.player_sub_type:
            pos_mod = cls.POSITION_MODIFIERS.get(player.player_sub_type, {})
            base["peak_start"] += pos_mod.get("peak_start", 0)
            base["peak_end"] += pos_mod.get("peak_end", 0)
            base["decline_mult"] *= pos_mod.get("decline_mult", 1.0)
        
        # 3. 应用性格修正
        prof_mod = (player.professionalism - 10) * 0.02  # 归一化到 -0.2 到 +0.2
        base["growth_mult"] *= (1.0 + prof_mod)
        base["decline_mult"] *= (1.0 - prof_mod * 0.5)
        
        # 4. 基于潜力的随机波动
        potential_factor = (player.potential_ability - 50) / 50  # 0-1
        variance = random.gauss(0, 0.1 * potential_factor)  # 潜力越高，波动越小
        base["growth_mult"] *= (1.0 + variance)
        
        # 5. 确保合理范围
        base["growth_mult"] = max(0.5, min(1.5, base["growth_mult"]))
        base["decline_mult"] = max(0.3, min(1.5, base["decline_mult"]))
        base["peak_start"] = max(17, min(28, base["peak_start"]))
        base["peak_end"] = max(base["peak_start"] + 2, min(33, base["peak_end"]))
        
        return base
    
    @classmethod
    def get_age_multiplier(cls, player: Player, age: int) -> float:
        """获取指定年龄的成长倍率"""
        
        curve = cls.generate_player_curve(player)
        peak_start = curve["peak_start"]
        peak_end = curve["peak_end"]
        growth_phase = curve["growth_phase"]
        decline_start = curve["decline_start"]
        growth_mult = curve["growth_mult"]
        decline_mult = curve["decline_mult"]
        
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
            years_since_decline = age - decline_start
            decline = years_since_decline * 0.2 * decline_mult
            return max(-2.0, -decline)
```

---

## 4. 重构 PlayerDevelopmentEngine

### 4.1 新的引擎架构

```python
class EnhancedPlayerDevelopmentEngine:
    """增强的球员发展引擎 - 支持个性化成长"""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.curve_generator = PersonalizedGrowthCurve()
        
    def calculate_season_development(
        self,
        player: Player,
        minutes_played: int,
        training_quality: int = 50,
        coach_ability: int = 50,
        league_level: int = 3,  # 1-5, 1为最高
        match_ratings: Optional[List[float]] = None,
    ) -> Dict:
        """计算赛季发展（增强版）"""
        
        age = player.age or 25
        old_ability = player.current_ability
        old_potential = player.potential_ability
        
        # 1. 获取个性化年龄倍率
        age_multiplier = self.curve_generator.get_age_multiplier(player, age)
        
        # 2. 出场时间奖励（保持原有逻辑）
        playing_bonus = self._get_playing_time_bonus(minutes_played)
        
        # 3. 训练质量因子
        training_factor = 0.5 + (training_quality / 100)
        
        # 4. 教练影响
        coach_factor = 0.8 + (coach_ability / 250)
        
        # 5. 联赛水平影响
        # 高水平联赛竞争激烈，成长快但也压力大
        league_multiplier = {
            1: 1.2,  # 五大联赛
            2: 1.1,  # 次级顶级联赛
            3: 1.0,  # 中等联赛
            4: 0.9,  # 低级联赛
            5: 0.8,  # 低级别联赛
        }.get(league_level, 1.0)
        
        # 6. 联赛适应度影响
        fit_factor = player.league_fit / 100
        
        # 7. 比赛表现奖励
        form_bonus = 0.0
        if match_ratings:
            avg_rating = sum(match_ratings) / len(match_ratings)
            # 抗压能力影响大赛表现
            pressure_boost = (player.pressure_resistance - 10) * 0.005
            effective_rating = avg_rating + pressure_boost
            
            if effective_rating > 7.5:
                form_bonus = 0.2
            elif effective_rating > 7.0:
                form_bonus = 0.1
            elif effective_rating < 6.0:
                form_bonus = -0.1
        
        # 8. 野心影响转会意愿（不直接影响成长，但影响数据）
        # 野心高的球员在低水平联赛会不满，影响状态
        
        # 9. 计算总成长
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
            personality_stability = player.professionalism / 10  # 1-2
            growth = max(0, int(self.rng.gauss(growth, growth * 0.2 / personality_stability)))
            
        else:  # 衰退期
            decline = abs(age_multiplier) * 5 * total_factors
            
            # 训练和出场可减缓衰退
            if minutes_played > 2000:
                decline *= 0.8
            elif minutes_played > 1000:
                decline *= 0.9
            
            # 职业素养高衰退慢
            decline *= (1.0 - (player.professionalism - 10) * 0.01)
            
            growth = -max(1, int(decline))
        
        # 10. 应用成长
        new_ability = max(1, min(99, old_ability + growth))
        actual_growth = new_ability - old_ability
        
        # 11. 更新球员
        player.current_ability = new_ability
        player.total_hours_trained += int(500 * training_factor)  # 估算训练小时数
        
        # 12. 更新联赛适应度
        self._update_league_fit(player, league_level)
        
        # 13. 更新物理属性（年龄衰退）
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
            "development_type": player.development_type.value,
            "player_sub_type": player.player_sub_type.value if player.player_sub_type else None,
        }
    
    def _update_league_fit(self, player: Player, league_level: int):
        """更新联赛适应度"""
        # 每赛季逐渐适应
        target_fit = 70 + (5 - league_level) * 10  # 高水平联赛初期适应度低
        player.league_fit += (target_fit - player.league_fit) * 0.1
    
    def _apply_age_decline(self, player: Player, age: int) -> Dict[str, int]:
        """应用年龄衰退（基于位置类型）"""
        changes = {}
        decline_rate = max(1, (age - 29) // 2)
        
        # 速度型边锋的pace衰退更快
        if player.player_sub_type == PlayerSubType.PACING_WINGER:
            pace_decline = decline_rate + 1
        else:
            pace_decline = decline_rate
        
        # 技术型中场技术属性衰退慢
        if player.player_sub_type == PlayerSubType.CREATIVE_PLAYMAKER:
            tech_decline = max(0, decline_rate - 1)
        else:
            tech_decline = decline_rate
        
        # 物理属性
        physical_attrs = ["pace", "acceleration", "stamina", "strength"]
        for attr in physical_attrs:
            old_val = getattr(player, attr, 50)
            current_decline = pace_decline if attr in ["pace", "acceleration"] else decline_rate
            current_decline = tech_decline if attr in ["dribbling", "passing"] else current_decline
            
            if old_val > 1:
                decline = self.rng.randint(0, current_decline)
                new_val = max(1, old_val - decline)
                setattr(player, attr, new_val)
                if decline > 0:
                    changes[attr] = -decline
        
        return changes
```

---

## 5. 数据初始化系统

### 5.1 为现有球员生成个性化参数

```python
class PlayerPersonalityInitializer:
    """为球员初始化个性化参数"""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def assign_development_type(self, player: Player) -> PlayerDevelopmentType:
        """根据位置和年龄分配发展类型"""
        position = player.position
        age = player.age or 25
        
        # 速度型边锋更容易早熟
        if position in [Position.LW, Position.RW] and player.pace > 75:
            weights = {
                PlayerDevelopmentType.EARLY_BLOOMER: 40,
                PlayerDevelopmentType.STANDARD: 40,
                PlayerDevelopmentType.LATE_BLOOMER: 10,
                PlayerDevelopmentType.CONSISTENT: 10,
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
        elif position in [Position.CAM, Position.CM] and player.vision > 70:
            weights = {
                PlayerDevelopmentType.EARLY_BLOOMER: 10,
                PlayerDevelopmentType.STANDARD: 50,
                PlayerDevelopmentType.LATE_BLOOMER: 30,
                PlayerDevelopmentType.CONSISTENT: 10,
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
        """根据属性分配子类型"""
        position = player.position
        
        if position == Position.GK:
            # 根据passing和vision区分出球型
            if player.passing > 65 and player.vision > 65:
                return PlayerSubType.SWEEP_KEEPER
            return PlayerSubType.TRADITIONAL_KEEPER
        
        elif position in [Position.LW, Position.RW]:
            # 根据pace和dribbling区分
            if player.pace > player.dribbling + 10:
                return PlayerSubType.PACING_WINGER
            return PlayerSubType.TECHNICAL_WINGER
        
        elif position in [Position.CM, Position.CDM, Position.CAM]:
            # 根据vision和passing区分
            if player.vision > 75 and player.passing > 70:
                return PlayerSubType.CREATIVE_PLAYMAKER
            elif player.tackling > 70 and player.stamina > 70:
                return PlayerSubType.BOX_TO_BOX
            return PlayerSubType.DEFENSIVE_MIDFIELDER
        
        elif position in [Position.CB, Position.LB, Position.RB]:
            # 根据passing区分
            if player.passing > 60:
                return PlayerSubType.BALL_PLAYING_DEFENDER
            return PlayerSubType.PURE_DEFENDER
        
        elif position in [Position.ST, Position.CF]:
            # 根据strength和positioning区分
            if player.strength > 70 and player.heading > 65:  # heading属性如果有的话
                return PlayerSubType.TARGET_MAN
            return PlayerSubType.POACHER
        
        return None
    
    def generate_personality(self, player: Player) -> Tuple[int, int, int]:
        """生成性格特征（1-20）"""
        # 潜力高通常职业素养和野心高
        potential_factor = (player.potential_ability - 50) / 50
        
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
        """初始化球员的所有个性化参数"""
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
        curve = PersonalizedGrowthCurve.generate_player_curve(player)
        player.peak_age_start = curve["peak_start"]
        player.peak_age_end = curve["peak_end"]
        player.growth_rate = curve["growth_mult"]
        player.decline_rate = curve["decline_mult"]
        
        # 5. 设置联赛适应度（初始70）
        player.league_fit = 70
    
    def _weighted_random_choice(self, weights: Dict) -> Any:
        """加权随机选择"""
        total = sum(weights.values())
        r = self.rng.random() * total
        cumulative = 0
        for key, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return key
        return list(weights.keys())[0]
```

---

## 6. 数据库迁移方案

### 6.1 Alembic迁移脚本

```python
"""revision: add personalized development fields

Revision ID: add_personalized_development
Revises: initial
Create Date: 2024-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers
revision = 'add_personalized_development'
down_revision = 'initial'
branch_labels = None
depends_on = None

def upgrade():
    # 添加新枚举类型（PostgreSQL需要）
    # 注意：SQLite不支持真正的enum，使用字符串代替
    
    op.add_column('players', sa.Column(
        'development_type', 
        sa.String(50), 
        server_default='standard',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'player_sub_type', 
        sa.String(50), 
        nullable=True
    ))
    
    op.add_column('players', sa.Column(
        'professionalism', 
        sa.Integer, 
        server_default='10',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'ambition', 
        sa.Integer, 
        server_default='10',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'pressure_resistance', 
        sa.Integer, 
        server_default='10',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'peak_age_start', 
        sa.Integer, 
        server_default='24',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'peak_age_end', 
        sa.Integer, 
        server_default='28',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'growth_rate', 
        sa.Float, 
        server_default='1.0',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'decline_rate', 
        sa.Float, 
        server_default='1.0',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'league_fit', 
        sa.Integer, 
        server_default='70',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'total_hours_trained', 
        sa.Integer, 
        server_default='0',
        nullable=False
    ))
    
    op.add_column('players', sa.Column(
        'coaches_mentored', 
        sa.Integer, 
        server_default='0',
        nullable=False
    ))

def downgrade():
    op.drop_column('players', 'coaches_mentored')
    op.drop_column('players', 'total_hours_trained')
    op.drop_column('players', 'league_fit')
    op.drop_column('players', 'decline_rate')
    op.drop_column('players', 'growth_rate')
    op.drop_column('players', 'peak_age_end')
    op.drop_column('players', 'peak_age_start')
    op.drop_column('players', 'pressure_resistance')
    op.drop_column('players', 'ambition')
    op.drop_column('players', 'professionalism')
    op.drop_column('players', 'player_sub_type')
    op.drop_column('players', 'development_type')
```

### 6.2 数据初始化脚本

```python
#!/usr/bin/env python
"""初始化现有球员的个性化参数"""

import sys
import random
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_manager.core.database import SessionLocal
from fm_manager.core.models import Player
from fm_manager.engine.player_development_enhanced import (
    PlayerPersonalityInitializer,
    PersonalizedGrowthCurve,
)
from fm_manager.core.models.player import (
    PlayerDevelopmentType,
    PlayerSubType,
)

def main():
    """初始化所有现有球员"""
    db = SessionLocal()
    
    try:
        players = db.query(Player).all()
        print(f"找到 {len(players)} 名球员")
        
        initializer = PlayerPersonalityInitializer(seed=42)
        
        for i, player in enumerate(players):
            # 只初始化尚未设置个性化参数的球员
            if player.professionalism == 10 and player.ambition == 10:
                initializer.initialize_player(player)
                db.commit()
                
                if (i + 1) % 100 == 0:
                    print(f"已初始化 {i + 1} 名球员...")
        
        print(f"✓ 成功初始化 {len(players)} 名球员的个性化参数")
        
        # 统计
        dev_types = db.query(Player.development_type).all()
        print("\n发展类型分布:")
        from collections import Counter
        for dev_type, count in Counter([t[0] for t in dev_types]).items():
            print(f"  {dev_type}: {count}")
        
    except Exception as e:
        db.rollback()
        print(f"错误: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

---

## 7. API接口设计

### 7.1 球员发展信息查询

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fm_manager.core.database import get_db
from fm_manager.core.models import Player
from fm_manager.engine.player_development_enhanced import (
    PersonalizedGrowthCurve,
    EnhancedPlayerDevelopmentEngine,
)

router = APIRouter(prefix="/api/player-development", tags=["player-development"])

@router.get("/{player_id}/curve")
def get_player_development_curve(
    player_id: int,
    db: Session = Depends(get_db)
):
    """获取球员的成长曲线数据"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    curve_generator = PersonalizedGrowthCurve()
    
    # 生成15-40岁的成长曲线
    curve_data = []
    for age in range(15, 41):
        multiplier = curve_generator.get_age_multiplier(player, age)
        curve_data.append({
            "age": age,
            "growth_multiplier": multiplier,
            "phase": _get_phase_from_multiplier(multiplier)
        })
    
    return {
        "player_id": player_id,
        "player_name": player.full_name,
        "development_type": player.development_type.value,
        "player_sub_type": player.player_sub_type.value if player.player_sub_type else None,
        "peak_ages": {
            "start": player.peak_age_start,
            "end": player.peak_age_end
        },
        "curve_data": curve_data,
        "personality": {
            "professionalism": player.professionalism,
            "ambition": player.ambition,
            "pressure_resistance": player.pressure_resistance,
        }
    }

def _get_phase_from_multiplier(multiplier: float) -> str:
    if multiplier > 1.0:
        return "rapid_growth"
    elif multiplier > 0:
        return "growth"
    else:
        return "decline"

@router.post("/{player_id}/simulate")
def simulate_season_development(
    player_id: int,
    minutes_played: int = 2000,
    training_quality: int = 50,
    coach_ability: int = 50,
    league_level: int = 3,
    db: Session = Depends(get_db)
):
    """模拟球员一个赛季的发展"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    engine = EnhancedPlayerDevelopmentEngine(seed=42)
    result = engine.calculate_season_development(
        player=player,
        minutes_played=minutes_played,
        training_quality=training_quality,
        coach_ability=coach_ability,
        league_level=league_level,
    )
    
    # 注意：这里不应该commit到数据库，因为这是模拟
    # 实际游戏中的赛季推进会调用这个方法并提交
    
    return result
```

---

## 8. 测试策略

### 8.1 单元测试

```python
"""测试个性化球员发展系统"""

import pytest
from datetime import date
from fm_manager.core.models import Player, Position
from fm_manager.engine.player_development_enhanced import (
    PersonalizedGrowthCurve,
    EnhancedPlayerDevelopmentEngine,
    PlayerPersonalityInitializer,
    PlayerDevelopmentType,
    PlayerSubType,
)

class TestPersonalizedGrowthCurve:
    """测试个性化成长曲线"""
    
    def test_early_bloomer_peak_age(self):
        """测试早熟型球员的巅峰期"""
        player = Player(
            first_name="Early",
            last_name="Bloomer",
            birth_date=date(2004, 1, 1),  # 20岁
            position=Position.LW,
            pace=85,
            potential_ability=85,
            development_type=PlayerDevelopmentType.EARLY_BLOOMER,
        )
        
        curve = PersonalizedGrowthCurve.generate_player_curve(player)
        
        assert curve["peak_start"] <= 22
        assert curve["peak_end"] <= 25
        assert curve["growth_mult"] > 1.0
    
    def test_late_bloomer_peak_age(self):
        """测试晚熟型球员的巅峰期"""
        player = Player(
            first_name="Late",
            last_name="Bloomer",
            birth_date=date(1997, 1, 1),  # 27岁
            position=Position.GK,
            vision=80,
            potential_ability=85,
            development_type=PlayerDevelopmentType.LATE_BLOOMER,
        )
        
        curve = PersonalizedGrowthCurve.generate_player_curve(player)
        
        assert curve["peak_start"] >= 26
        assert curve["peak_end"] >= 30
        assert curve["decline_mult"] < 1.0
    
    def test_pacing_winger_decline(self):
        """测试速度型边锋衰退更快"""
        player = Player(
            first_name="Pacing",
            last_name="Winger",
            birth_date=date(2000, 1, 1),
            position=Position.LW,
            pace=80,
            player_sub_type=PlayerSubType.PACING_WINGER,
            potential_ability=80,
            development_type=PlayerDevelopmentType.STANDARD,
        )
        
        curve = PersonalizedGrowthCurve.generate_player_curve(player)
        
        assert curve["decline_mult"] > 1.0  # 衰退加速
    
    def test_professionalism_impact(self):
        """测试职业素养对成长的影响"""
        player1 = Player(
            first_name="High",
            last_name="Pro",
            birth_date=date(2002, 1, 1),
            position=Position.CM,
            potential_ability=80,
            development_type=PlayerDevelopmentType.STANDARD,
            professionalism=18,  # 高职业素养
        )
        
        player2 = Player(
            first_name="Low",
            last_name="Pro",
            birth_date=date(2002, 1, 1),
            position=Position.CM,
            potential_ability=80,
            development_type=PlayerDevelopmentType.STANDARD,
            professionalism=5,  # 低职业素养
        )
        
        curve1 = PersonalizedGrowthCurve.generate_player_curve(player1)
        curve2 = PersonalizedGrowthCurve.generate_player_curve(player2)
        
        assert curve1["growth_mult"] > curve2["growth_mult"]
        assert curve1["decline_mult"] < curve2["decline_mult"]

class TestEnhancedDevelopmentEngine:
    """测试增强的发展引擎"""
    
    def test_early_bloomer_fast_growth(self):
        """测试早熟型球员前期成长快"""
        player = Player(
            first_name="Early",
            last_name="Bloomer",
            birth_date=date(2006, 1, 1),  # 18岁
            position=Position.LW,
            current_ability=60,
            potential_ability=85,
            development_type=PlayerDevelopmentType.EARLY_BLOOMER,
            player_sub_type=PlayerSubType.PACING_WINGER,
        )
        
        engine = EnhancedPlayerDevelopmentEngine(seed=42)
        result = engine.calculate_season_development(
            player=player,
            minutes_played=2500,
            training_quality=70,
            coach_ability=70,
            league_level=2,
        )
        
        assert result["growth"] > 5  # 早熟型前期成长快
    
    def test_pressure_resistance_impact(self):
        """测试抗压能力对表现的影响"""
        player1 = Player(
            first_name="High",
            last_name="Pressure",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
            current_ability=70,
            potential_ability=80,
            pressure_resistance=18,
        )
        
        player2 = Player(
            first_name="Low",
            last_name="Pressure",
            birth_date=date(2000, 1, 1),
            position=Position.ST,
            current_ability=70,
            potential_ability=80,
            pressure_resistance=5,
        )
        
        engine = EnhancedPlayerDevelopmentEngine(seed=42)
        
        # 模拟高压比赛（平均评分6.5，不算好）
        match_ratings = [6.5] * 10
        
        result1 = engine.calculate_season_development(
            player=player1,
            minutes_played=2000,
            match_ratings=match_ratings,
        )
        
        result2 = engine.calculate_season_development(
            player=player2,
            minutes_played=2000,
            match_ratings=match_ratings,
        )
        
        # 高抗压能力的球员受到的负面影响更小
        assert result1["form_bonus"] >= result2["form_bonus"]

class TestPersonalityInitializer:
    """测试性格初始化器"""
    
    def test_assign_development_type_based_on_position(self):
        """测试基于位置分配发展类型"""
        initializer = PlayerPersonalityInitializer(seed=42)
        
        # 速度型边锋倾向于早熟
        winger = Player(
            first_name="Pacing",
            last_name="Winger",
            position=Position.LW,
            pace=85,
            potential_ability=80,
        )
        
        dev_type = initializer.assign_development_type(winger)
        # 有较高概率是早熟型
        assert dev_type in [
            PlayerDevelopmentType.EARLY_BLOOMER,
            PlayerDevelopmentType.STANDARD,
        ]
        
        # 门将倾向于晚熟
        keeper = Player(
            first_name="Keeper",
            last_name="Player",
            position=Position.GK,
            potential_ability=80,
        )
        
        dev_type = initializer.assign_development_type(keeper)
        # 有较高概率是晚熟型或持续型
        assert dev_type in [
            PlayerDevelopmentType.LATE_BLOOMER,
            PlayerDevelopmentType.CONSISTENT,
            PlayerDevelopmentType.STANDARD,
        ]
    
    def test_assign_sub_type_based_on_attributes(self):
        """测试基于属性分配子类型"""
        initializer = PlayerPersonalityInitializer(seed=42)
        
        # 高pace且pace>dribbling的边锋是速度型
        pacing_winger = Player(
            position=Position.LW,
            pace=85,
            dribbling=70,
        )
        
        sub_type = initializer.assign_sub_type(pacing_winger)
        assert sub_type == PlayerSubType.PACING_WINGER
        
        # 高vision的边锋是技术型
        technical_winger = Player(
            position=Position.LW,
            pace=70,
            dribbling=85,
            passing=80,
            vision=75,
        )
        
        sub_type = initializer.assign_sub_type(technical_winger)
        assert sub_type == PlayerSubType.TECHNICAL_WINGER
```

---

## 9. 实施计划

### 阶段1：核心数据模型（1-2天）
1. ✅ 在 `player.py` 中添加新枚举类型
2. ✅ 在 `Player` 模型中添加新字段
3. ✅ 创建数据库迁移脚本
4. ✅ 运行迁移并验证

### 阶段2：个性化成长曲线（2-3天）
1. ✅ 创建 `PersonalizedGrowthCurve` 类
2. ✅ 实现基于发展类型的曲线模板
3. ✅ 实现基于位置类型的修正系数
4. ✅ 实现基于性格的影响系数
5. ✅ 单元测试曲线生成逻辑

### 阶段3：增强发展引擎（2-3天）
1. ✅ 创建 `EnhancedPlayerDevelopmentEngine` 类
2. ✅ 集成个性化成长曲线
3. ✅ 实现联赛水平影响
4. ✅ 实现教练影响
5. ✅ 实现性格对发展的影响
6. ✅ 单元测试发展计算

### 阶段4：数据初始化（1天）
1. ✅ 创建 `PlayerPersonalityInitializer` 类
2. ✅ 实现有数据球员参数生成
3. ✅ 创建初始化脚本
4. ✅ 执行初始化并验证

### 阶段5：集成测试（1天）
1. ✅ 模拟多个赛季验证发展曲线
2. ✅ 对比不同类型球员的发展差异
3. ✅ 验证与现有系统的兼容性
4. ✅ 性能测试

### 阶段6：文档和API（1天）
1. ✅ 编写使用文档
2. ✅ 创建API接口
3. ✅ 编写示例代码

**总估计时间：8-11天**

---

## 10. 风险和注意事项

### 10.1 数据兼容性
- ⚠️ 现有球员需要初始化个性化参数
- ✅ 使用合理的默认值和初始化策略
- ✅ 提供回滚方案

### 10.2 性能考虑
- ⚠️ 每次计算都需要生成曲线，可能影响性能
- ✅ 缓存计算结果
- ✅ 批量计算时优化

### 10.3 平衡性
- ⚠️ 新系统可能打破游戏平衡
- ✅ 大量测试和调整参数
- ✅ 提供配置选项调整倍率

### 10.4 随机性控制
- ⚠️ 过度随机导致不可预测
- ✅ 使用固定种子进行测试
- ✅ 提供可配置的随机性控制

---

## 11. 配置选项

```python
# config.py 新增配置项

PLAYER_DEVELOPMENT_CONFIG = {
    # 是否启用个性化成长系统
    "enabled": True,
    
    # 随机性控制（0-1，越低越稳定）
    "randomness_factor": 0.3,
    
    # 基础成长倍率
    "base_growth_multiplier": 1.0,
    
    # 基础衰退倍率
    "base_decline_multiplier": 1.0,
    
    # 联赛水平影响权重
    "league_level_weight": 0.3,
    
    # 教练影响权重
    "coach_weight": 0.2,
    
    # 出场时间影响权重
    "playing_time_weight": 0.4,
    
    # 性格影响权重
    "personality_weight": 0.1,
}
```

---

## 12. 示例：模拟不同类型球员

### 12.1 早熟型速度边锋

```python
# Mbappe类型
early_bloomer = Player(
    first_name="Kylian",
    last_name="Mbappe",
    position=Position.LW,
    age=18,
    current_ability=75,
    potential_ability=92,
    pace=95,
    dribbling=88,
    development_type=PlayerDevelopmentType.EARLY_BLOOMER,
    player_sub_type=PlayerSubType.PACING_WINGER,
    professionalism=15,
    ambition=18,
    pressure_resistance=16,
)

# 预期：18-22岁快速成长，23岁开始衰退
```

### 12.2 晚熟型组织核心

```python
# Modric类型
late_bloomer = Player(
    first_name="Luka",
    last_name="Modric",
    position=Position.CM,
    age=27,
    current_ability=82,
    potential_ability=88,
    vision=90,
    passing=88,
    development_type=PlayerDevelopmentType.LATE_BLOOMER,
    player_sub_type=PlayerSubType.CREATIVE_PLAYMAKER,
    professionalism=19,
    ambition=12,
    pressure_resistance=18,
)

# 预期：27-31岁达到巅峰，35岁后才明显衰退
```

### 12.3 持续型传奇

```python
# Zanetti类型
consistent = Player(
    first_name="Javier",
    last_name="Zanetti",
    position=Position.RB,
    age=24,
    current_ability=78,
    potential_ability=85,
    tackling=85,
    stamina=90,
    development_type=PlayerDevelopmentType.CONSISTENT,
    player_sub_type=PlayerSubType.PURE_DEFENDER,
    professionalism=20,
    ambition=14,
    pressure_resistance=18,
)

# 预期：24-30岁巅峰期长，38岁后才退役
```

---

## 13. 未来扩展方向

1. **伤病对成长曲线的影响**：重大伤病可能改变发展类型
2. **教练风格影响**：不同教练类型（进攻型/防守型）对不同子类型的影响
3. **心理因素**：压力、信心、动力等因素的动态变化
4. **适应性系统**：球员学习新位置的能力
5. **传奇球员模式**：特别属性的职业末期发展

---

## 附录A：完整代码文件清单

### 需要创建的文件
1. `fm_manager/core/models/player.py` - 修改：添加枚举和字段
2. `fm_manager/engine/player_development_enhanced.py` - 新建：完整实现
3. `alembic/versions/xxx_add_personalized_development.py` - 新建：迁移脚本
4. `scripts/initialize_player_personalities.py` - 新建：初始化脚本

### 需要修改的文件
1. `fm_manager/engine/player_development.py` - 可能需要调整以兼容新系统

---

## 附录B：参考资料

- Football Manager系列游戏的球员发展机制
- FIFA系列游戏的球员成长系统
- 现实足球运动中的球员发展轨迹研究
- 运动科学关于运动员巅峰期的研究

---

**文档版本**: 1.0  
**创建日期**: 2024-02-04  
**作者**: AI Assistant  
**状态**: 待审核
