# 青训系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/youth_engine.py`

---

## 核心功能

### 1. 青训学院系统

#### 学院等级配置
```python
@dataclass
class YouthAcademy:
    club_id: int
    level: int = 50              # 0-100 整体水平
    coaching_quality: int = 50   # 教练质量
    facilities_quality: int = 50 # 设施质量
    players_per_intake: int = 3  # 每年产出人数
```

#### 质量计算
```python
intake_quality = level×0.5 + coaching×0.3 + facilities×0.2

产出球员潜力 = 50 + intake_quality×0.5 + random(-15, +15)
```

### 2. 青训球员生成

#### 年龄分布
| 年龄 | 概率 | 说明 |
|-----|------|------|
| 14 | 20% | 天赋异禀少年 |
| 15 | 35% | 常规招生 |
| 16 | 30% | 成熟新星 |
| 17 | 15% | 即战力型 |

#### 潜力分布
```
潜力范围: 40-100

顶级学院 (85+):
  - PA 80+: 30%
  - PA 70-79: 40%
  - PA 60-69: 25%
  - PA <60: 5%

普通学院 (50):
  - PA 70+: 10%
  - PA 60-69: 30%
  - PA 50-59: 45%
  - PA <50: 15%
```

#### 当前能力
```python
current_ability = potential_ability - random(10, 40)
# 年轻球员CA比PA低10-40点
```

### 3. 球员成长系统

#### 年龄成长曲线
| 年龄段 | 成长系数 | 说明 |
|-------|---------|------|
| <18 | 1.2 | 快速成长 |
| 18-22 | 1.0 | 巅峰成长 |
| 23-26 | 0.6 | 成长放缓 |
| 27-30 | 0.3 | 微小进步 |
| >30 | -0.2 | 能力衰退 |

#### 成长计算公式
```python
growth = base_growth × age_factor × playing_factor × training_factor

base_growth = 5  # 基础每年成长
playing_factor:
  >2000分钟/赛季: 1.3
  >1000分钟: 1.0
  >500分钟: 0.7
  <500分钟: 0.4

training_factor = 0.5 + training_quality/100  # 0.5-1.5
```

#### 物理属性衰退 (30+)
```python
decline = (age - 30) × random(0, 2)

pace -= decline
acceleration -= decline
stamina -= decline
```

### 4. 球探网络

#### 球探任务
```python
@dataclass
class ScoutingAssignment:
    region: str              # 国家/地区
    focus_position: Position # 专注位置
    min_potential: int       # 最低潜力要求
    max_age: int             # 最大年龄
    duration_days: int       # 任务时长
```

#### 球探报告
```python
@dataclass
class ScoutingReport:
    # 能力评估 (带误差)
    current_ability_estimate: int
    potential_ability_estimate: int
    confidence: int          # 0-100 置信度
    
    # 详细分析
    strengths: list[str]     # 优点
    weaknesses: list[str]    # 缺点
    
    # 建议
    recommendation: str      # sign/monitor/avoid
    estimated_cost: int
```

#### 评估误差
```python
error_margin = (100 - scout_quality) / 2

# 能力估算
estimate = true_value + gauss(0, error_margin)

# 低质量球探 (<40): ±30点误差
# 高质量球探 (>80): ±10点误差
```

---

## 数据结构

### PlayerDevelopment
```python
@dataclass
class PlayerDevelopment:
    player_id: int
    potential_ability: int
    training_focus: str      # balanced/physical/technical/mental
    
    # 赛季统计
    minutes_played_season: int
    matches_played_season: int
    recent_ratings: list[float]
    
    def calculate_growth_rate(self) -> float:
        # 基于出场时间和表现计算成长速度
```

### YouthIntake
```python
class YouthPlayerGenerator:
    def generate_youth_player(
        self,
        club_id: int,
        academy_level: int,
        nationality: str,
        position: Position | None,
        min_age: int = 15,
        max_age: int = 17,
    ) -> Player:
        # 生成符合俱乐部青训标准的球员
```

---

## 使用示例

### 青训球员生成
```python
engine = YouthEngine()

academy = YouthAcademy(
    club_id=club.id,
    level=85,              # 顶级学院
    coaching_quality=80,
    facilities_quality=90,
    players_per_intake=4,
)

# 年度青训招生
new_players = engine.generate_youth_intake(
    club, academy, date(2024, 3, 1)
)

for player in new_players:
    print(f"{player.full_name}: CA{player.current_ability}/PA{player.potential_ability}")
```

### 球员发展
```python
# 计算成长潜力
growth_info = engine.development_calculator.calculate_growth_potential(
    player, age=19, training_quality=80, playing_time=2500
)

print(f"预计成长: +{growth_info['likely_growth']} 能力点")

# 应用赛季发展
result = engine.process_yearly_development(
    player,
    playing_time=2500,
    training_quality=80,
    match_ratings=[7.0, 7.5, 6.5, 8.0, 7.0],
)

print(f"{result['old_ability']} → {result['new_ability']} (+{result['growth']})")
```

### 球探任务
```python
# 派遣球探
assignment = engine.scout_region(
    region="Brazil",
    duration_days=30,
    focus_position=Position.ST,
)

# 生成球探报告
report = engine.scouting_network.generate_scouting_report(
    player, scout_quality=75
)

print(f"CA评估: {report.current_ability_estimate} (置信度{report.confidence}%)")
print(f"PA评估: {report.potential_ability_estimate}")
print(f"建议: {report.recommendation}")
```

---

## 测试验证

### 青训产出测试
```
俱乐部: Manchester United
学院等级: 85/100

年度青训招生 (4人):
┌─────────────────┬──────────┬─────┬────┳━━━━━┬───────┐
│ Name            │ Position │ Age │ CA ┃ PA  │ Value │
├─────────────────┼──────────┼─────┼────╋━━━━━┼───────┤
│ Thomas Smith    │ ST       │  15 │ 66 │  83 │ €107K │
│ James Brown     │ RW       │  14 │ 41 │  60 │ €212K │
│ George Williams │ CDM      │  16 │ 75 │  97 │ €167K │
│ Charlie Davis   │ CAM      │  17 │ 77 │ 100 │ €344K │
└─────────────────┴──────────┴─────┴────┻━━━━━┴───────┘

球员: Thomas Smith (15岁, CA66/PA83)
  成长曲线:
    年龄 15: CA 66 → 预计 +10/年
    年龄 18: CA ~85 (接近PA)
    年龄 22: CA ~90 (达到PA)
```

### 成长模拟
```
Harry Brown (15岁, CA66/PA83)
  第1季: 66 → 73 (+7)  出场2500分钟
  第2季: 73 → 79 (+6)  出场2400分钟
  第3季: 79 → 83 (+4)  出场2200分钟
  第4季: 83 → 85 (+2)  接近PA上限
```

---

## 未来扩展

- [ ] 青训营升级系统
- [ ] 多级别青训梯队(U18/U21)
- [ ] 青训球员外租系统
- [ ] 青训球员心理属性
- [ ] 青训营评级系统
- [ ] 球探网络升级
- [ ] 青训教练系统
- [ ] 青训球员忠诚度
