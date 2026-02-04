# 个性化球员成长系统 - 快速入门

## 概述

这个系统为每个球员创建了独特的成长轨迹，基于他们的发展类型、位置风格和性格特征。

## 快速开始

### 1. 运行测试（无需数据库）

```bash
python scripts/test_personalized_development.py
```

这将运行测试套件，展示：
- 不同发展类型的球员对比
- 性格对成长的影响
- 位置子类型对衰退的影响

### 2. 数据库迁移

如果你有现有数据库需要升级：

```bash
# 1. 备份数据库
cp data/fm_manager.db data/fm_manager.db.backup

# 2. 运行数据库迁移
alembic upgrade head

# 3. 初始化现有球员的个性化参数
python scripts/initialize_player_personalities.py
```

### 3. 在代码中使用

#### 基本使用

```python
from fm_manager.engine.player_development_enhanced import (
    EnhancedPlayerDevelopmentEngine,
    PlayerPersonalityInitializer,
)
from fm_manager.core.database import SessionLocal
from fm_manager.core.models import Player

# 初始化引擎
engine = EnhancedPlayerDevelopmentEngine(seed=42)
db = SessionLocal()

# 获取球员
player = db.query(Player).filter(Player.id == 1).first()

# 计算赛季发展
result = engine.calculate_season_development(
    player=player,
    minutes_played=2500,      # 出场时间
    training_quality=70,       # 训练质量 (0-100)
    coach_ability=70,          # 教练能力 (0-100)
    league_level=2,            # 联赛水平 (1-5)
    match_ratings=[7.2] * 38,   # 比赛评分
)

print(f"Growth: {result['growth']}")
print(f"New CA: {result['new_ability']}")
print(f"Age Multiplier: {result['age_multiplier']}")

db.commit()
db.close()
```

#### 初始化新球员

```python
from fm_manager.core.models.player_enums import (
    PlayerDevelopmentType,
    PlayerSubType,
)

# 创建球员
player = Player(
    first_name="Kylian",
    last_name="Mbappe",
    position=Position.LW,
    current_ability=75,
    potential_ability=92,
    development_type=PlayerDevelopmentType.EARLY_BLOOMER,
    player_sub_type=PlayerSubType.PACING_WINGER,
)

# 初始化个性化参数
initializer = PlayerPersonalityInitializer(seed=42)
initializer.initialize_player(player)

print(f"Professionalism: {player.professionalism}")
print(f"Ambition: {player.ambition}")
print(f"Peak Age: {player.peak_age_start}-{player.peak_age_end}")
```

#### 查看球员的成长曲线

```python
from fm_manager.engine.player_development_enhanced import PersonalizedGrowthCurve

# 生成成长曲线
curve = PersonalizedGrowthCurve.generate_player_curve(player)

print(f"Peak Age: {curve['peak_start']}-{curve['peak_end']}")
print(f"Growth Rate: {curve['growth_mult']:.2f}")
print(f"Decline Rate: {curve['decline_mult']:.2f}")

# 查看特定年龄的倍率
for age in range(15, 40):
    multiplier = PersonalizedGrowthCurve.get_age_multiplier(player, age)
    print(f"Age {age}: {multiplier:.2f}")
```

## 球员类型说明

### 发展类型

| 类型 | 巅峰年龄 | 特点 | 适合位置 |
|------|----------|------|----------|
| **早熟型** | 18-22 | 早期快速成长，23岁开始衰退 | 速度型边锋 |
| **标准型** | 24-28 | 平衡发展，最常见 | 大多数位置 |
| **晚熟型** | 27-31 | 慢热但巅峰期长 | 组织型中场、门将 |
| **持续型** | 24-30 | 巅峰期长，衰退缓慢 | 防守型后卫 |

### 位置子类型

#### 边锋
- **速度型边锋** (PACING_WINGER): 依赖速度，早期巅峰，早衰
- **技术型边锋** (TECHNICAL_WINGER): 依赖技术，巅峰期稍长

#### 中场
- **组织型中场** (CREATIVE_PLAYMAKER): 晚熟，技术衰退慢
- **全能型中场** (BOX_TO_BOX): 平衡型
- **防守型中场** (DEFENSIVE_MIDFIELDER): 稳定型

#### 后卫
- **出球型后卫** (BALL_PLAYING_DEFENDER): 技术好，巅峰期长
- **纯防守型后卫** (PURE_DEFENDER): 稳定型

#### 前锋
- **高点型前锋** (TARGET_MAN): 身体强壮，巅峰期中等
- **抢点型前锋** (POACHER): 标准发展

#### 门将
- **出球型门将** (SWEEP_KEEPER): 晚熟，最晚衰退
- **传统型门将** (TRADITIONAL_KEEPER): 标准门将发展

### 性格特征

| 特征 | 范围 | 影响 |
|------|------|------|
| **职业素养** | 1-20 | 高=成长快，衰退慢 |
| **野心** | 1-20 | 高=成长快，转会意愿强 |
| **抗压能力** | 1-20 | 高=大赛表现稳定 |

## 配置选项

在 `fm_manager/core/config.py` 中添加：

```python
PLAYER_DEVELOPMENT_CONFIG = {
    # 是否启用个性化成长
    "enabled": True,
    
    # 随机性控制（0-1）
    "randomness_factor": 0.3,
    
    # 基础倍率
    "base_growth_multiplier": 1.0,
    "base_decline_multiplier": 1.0,
}
```

## 与现有系统集成

### 选项1：完全替换

在 `season_simulator.py` 中：

```python
from fm_manager.engine.player_development_enhanced import EnhancedPlayerDevelopmentEngine

# 替换原来的 PlayerDevelopmentEngine
development_engine = EnhancedPlayerDevelopmentEngine(seed=42)

# 使用相同的接口
result = development_engine.calculate_season_development(
    player=player,
    minutes_played=minutes,
    training_quality=club.training_facility_level,
    # ... 其他参数
)
```

### 选项2：并存（推荐）

保持原有系统，逐步迁移：

```python
from fm_manager.engine.player_development import PlayerDevelopmentEngine
from fm_manager.engine.player_development_enhanced import EnhancedPlayerDevelopmentEngine

# 使用标志切换
USE_ENHANCED_DEVELOPMENT = True

if USE_ENHANCED_DEVELOPMENT:
    engine = EnhancedPlayerDevelopmentEngine()
else:
    engine = PlayerDevelopmentEngine()

# 统一接口调用
result = engine.calculate_season_development(player, minutes, ...)
```

## 常见问题

### Q: 现有球员的数据会丢失吗？
A: 不会。迁移脚本使用默认值初始化新字段，不会影响现有数据。

### Q: 如何调整系统的随机性？
A: 使用固定的 `seed` 参数：
```python
engine = EnhancedPlayerDevelopmentEngine(seed=42)  # 固定随机性
engine = EnhancedPlayerDevelopmentEngine(seed=None)  # 完全随机
```

### Q: 性格特征如何影响转会？
A: 当前系统只影响成长。转会系统可以通过读取 `ambition` 字段来实现：
```python
if player.ambition > 15 and club.league_level < 3:
    # 球员可能要求转会
    pass
```

### Q: 可以手动调整球员的发展类型吗？
A: 可以：
```python
player.development_type = PlayerDevelopmentType.LATE_BLOOMER
curve = PersonalizedGrowthCurve.generate_player_curve(player)
player.peak_age_start = curve["peak_start"]
player.peak_age_end = curve["peak_end"]
```

## 性能优化

如果发现性能问题：

1. **缓存曲线计算**：
```python
# 在 Player 模型中添加
_cached_curve: Optional[Dict] = None

# 使用时检查
if not hasattr(player, '_cached_curve'):
    player._cached_curve = PersonalizedGrowthCurve.generate_player_curve(player)
```

2. **批量处理**：
```python
# 避免循环中的单独查询
players = db.query(Player).filter(Player.age < 25).all()
for player in players:
    # 批量更新
    pass
```

## 下一步

1. 运行测试脚本了解系统行为
2. 在开发环境中测试迁移
3. 逐步集成到现有系统
4. 根据反馈调整参数

## 支持

如有问题，请查看：
- 完整设计文档：`doc/PERSONALIZED_PLAYER_DEVELOPMENT.md`
- 测试脚本：`scripts/test_personalized_development.py`
- 源代码：`fm_manager/engine/player_development_enhanced.py`
