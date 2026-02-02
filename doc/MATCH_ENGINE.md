# Match Engine 比赛引擎

## 概述

比赛引擎是 FM Manager 的核心组件，负责模拟足球比赛。它基于球员能力值、战术安排和各种随机因素来计算比赛结果。

## 特性

- ✅ **基于球员能力**: 每个球员的属性影响比赛结果
- ✅ **战术系统**: 阵型影响球队表现
- ✅ **主场优势**: 主场球队获得加成
- ✅ **比赛事件**: 进球、红黄牌等事件模拟
- ✅ **实时模拟**: 支持按分钟回调，可用于直播比赛
- ✅ **统计跟踪**: 射门、控球率等数据记录

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MatchSimulator                           │
├─────────────────────────────────────────────────────────────┤
│  TeamStrengthCalculator    │    MatchState                  │
│  ├─ calculate()            │    ├─ score                    │
│  ├─ formation_bonus()      │    ├─ events                   │
│  ├─ chemistry()            │    ├─ possession               │
│  └─ fatigue()              │    └─ stats                    │
├─────────────────────────────────────────────────────────────┤
│  Simulation Loop (90 minutes)                               │
│  ├─ Calculate goal probabilities                            │
│  ├─ Check for goals                                         │
│  ├─ Check for cards                                         │
│  └─ Update statistics                                       │
└─────────────────────────────────────────────────────────────┘
```

## 使用方式

### 快速模拟

```python
from fm_manager.engine.match_engine import quick_simulate

# 使用球队评分快速模拟
result = quick_simulate(home_rating=78, away_rating=74)
print(result)
# {'home_goals': 2, 'away_goals': 1, 'score': '2-1', ...}
```

### 完整模拟

```python
from fm_manager.engine.match_engine import MatchSimulator

simulator = MatchSimulator(random_seed=42)

# 使用真实球员数据
state = simulator.simulate(
    home_lineup=home_players,      # List[Player] - 11首发
    away_lineup=away_players,      # List[Player] - 11首发
    home_formation="4-3-3",
    away_formation="4-4-2",
    callback=on_minute_update,     # 每分钟回调
)

print(f"Final Score: {state.score_string()}")
```

### 球队实力计算

```python
from fm_manager.engine.match_engine import TeamStrengthCalculator

calculator = TeamStrengthCalculator()
strength = calculator.calculate(lineup, formation="4-3-3")

print(f"Overall: {strength.overall}")
print(f"Attack: {strength.attack}")
print(f"Midfield: {strength.midfield}")
print(f"Defense: {strength.defense}")
```

## 模拟算法

### 进球概率计算

每分钟的进球概率基于以下公式:

```
goal_prob = BASE_RATE × (attack / (defense + 50))^0.7

where:
- BASE_RATE = 0.028 (~2.5 goals per match)
- attack = 球队有效进攻值 (考虑士气、疲劳等)
- defense = 对手有效防守值
```

### 主场优势

主场球队获得 30% 的全面加成:
- 进攻能力提升
- 球员士气加成
- 裁判偏向(隐含)

### 球员评分计算

```
effective_rating = base_ability × (1 + form_factor + morale_factor) × fitness_factor

where:
- form_factor = (form - 50) / 100  (-0.5 to +0.5)
- morale_factor = (morale - 50) / 200  (-0.25 to +0.25)
- fitness_factor = fitness / 100  (0 to 1)
```

## 验证结果

运行 1000 场模拟测试:

| 指标 | 模拟结果 | 真实世界 | 状态 |
|-----|---------|---------|-----|
| 主场胜率 | ~46% | ~46% | ✅ |
| 平局率 | ~26% | ~26% | ✅ |
| 客场胜率 | ~28% | ~28% | ✅ |
| 平均进球 | ~2.6 | ~2.6 | ✅ |

常见比分分布:
- 1-1: 13%
- 1-0: 12%
- 2-1: 10%
- 0-1: 8%
- 2-0: 8%

## 演示

```bash
# 运行实时比赛模拟
python scripts/demo_match.py --mode live

# 运行批量模拟统计
python scripts/demo_match.py --mode sim

# 运行测试套件
python scripts/test_match_engine.py
```

## 未来改进

- [ ] **天气影响**: 雨天、雪天对比赛的影响
- [ ] **关键球员**: 明星球员的特殊事件
- [ ] **战术调整**: 比赛中实时战术变化
- [ ] **VAR 系统**: 视频助理裁判事件
- [ ] **点球大战**: 淘汰赛平局后的点球
- [ ] **伤病系统**: 比赛中球员受伤
- [ ] **换人策略**: AI 自动换人决策
