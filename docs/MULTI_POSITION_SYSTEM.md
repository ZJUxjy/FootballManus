# 多位置熟练度系统

## 🎯 问题分析

### 当前问题

1. **Bellingham 位置错误**：
   - 数据源位置：**RW** ❌
   - 真实位置：**CM/CAM** ✅
   - 系统识别为：**RW** ❌

2. **Vinícius Jr 位置问题**：
   - 数据源位置：**CAM** ❌
   - 真实位置：**LW** ✅
   - 系统识别为：**CF** ❌

3. **属性发挥问题**：
   - 当前系统假设球员在所有位置都发挥100%属性
   - 但现实中，球员在不熟悉的位置发挥会下降

### 根本原因

`get_best_position()` 返回的是**评分最高的位置**，但没有考虑：
1. 真实足球位置合理性
2. 球员的多位置能力
3. 位置熟练度对属性发挥的影响

---

## ✨ 解决方案：多位置熟练度系统

### 核心概念

```python
# 位置熟练度 = Base Proficiency (0-100)
Position Proficiency:
  - 90+: Master (1.05x 属性加成)
  - 80-90: Comfortable (1.00x 属性正常发挥)
  - 70-80: Learning (0.90x 属性略降)
  - 60-70: Struggling (0.80x 属性显著下降)
  - <60: Out of position (0.70x 属性大幅下降)

# 有效属性 = Base Attribute × Proficiency Modifier
Effective Shooting = Base Shooting × sqrt(proficiency/100)
```

### 实现文件

**`/fm_manager/engine/multi_position_player.py`**

包含：
- `Position` 枚举：所有标准位置
- `PositionProficiency`：位置熟练度
- `MultiPositionPlayer`：多位置球员类

---

### 📊 示例：Bellingham

```
Player: Bellingham, Jude
Primary Position: CM (更符合现实)

Position Proficiencies:
  CM:  90.0 → modifier: 1.05  (主位置，5%加成)
  CAM: 80.0 → modifier: 1.00  (舒适位置)
  CDM: 75.0 → modifier: 0.90  (可以踢但略生疏)
  LM:  65.0 → modifier: 0.80  (不熟悉)
  RM:  65.0 → modifier: 0.80  (不熟悉)

Effective Shooting at different positions:
  CM:  Shooting=73  (modifier: 1.05) ← 熟悉位置，发挥最佳
  CAM: Shooting=70  (modifier: 1.00) ← 可以胜任
  CF:  Shooting=49  (modifier: 0.70) ← 不熟悉，大幅下降
```

---

### 🔧 位置兼容性矩阵

| 主位置 | 可踢次级位置 | 熟练度 |
|--------|------------|--------|
| **ST** | CF(85), LW(70), RW(70) | 天生前锋踢边锋会下降 |
| **CM** | CAM(80), CDM(75), LM(65), RM(65) | 中场多面手 |
| **CAM** | CM(85), LW(75), RW(75), ST(70) | 进攻中场可踢边锋/前锋 |
| **LW** | RW(80), LM(75), CAM(75) | 边锋可换边 |
| **CB** | LB(60), RB(60) | 后卫踢边路会下降 |

---

## 📈 与现有系统整合方案

### 方案A：替换 AdaptedPlayer（推荐）

```python
# 在 ClubSquadBuilder 中
from fm_manager.engine.multi_position_player import MultiPositionPlayer, create_multi_position_player

def build_lineup(self, ...):
    if self.enable_rotation and self.rotation_system:
        # 转换为 MultiPositionPlayer
        adapted_lineup = [
            create_multi_position_player(p.player)
            for p in self.rotation_system.select_lineup(...)
        ]
        return adapted_lineup
    else:
        # 原逻辑
        return [AdaptedPlayer(p) for p in ...]
```

### 方案B：在 xG 计算时动态调整

```python
def compute_shot_xg_with_proficiency(
    shooter,           # MultiPositionPlayer
    actual_position,   # 当前踢的位置
    ...
):
    # 获取当前实际位置的属性
    attrs = shooter.get_attributes_for_position(actual_position)

    # 使用这些属性计算xG
    compute_shot_xg(
        shooter_shooting=attrs['shooting'],
        shooter_positioning=attrs['positioning'],
        ...
    )
```

---

## 🎯 实施步骤

### Phase 1：位置识别改进

**目标**：修复顶级球员位置错误

修改 `_detect_primary_position()` 函数，增加智能映射：

```python
smart_mappings = {
    # Position Ratings → Real Position
    ('RW', 'CAM'): Position.CM,    # 高RW评分但实际是CAM
    ('LW', 'CAM'): Position.CAM,    # 高LW评分但实际是CAM
    ('FS', 'ST'): Position.ST,       # Forward Striker → ST
    ('TS', 'CF'): Position.CF,       # Target Shadow → CF
}
```

### Phase 2：属性动态发挥

**目标**：根据熟练度调整属性

```python
def get_attribute_with_proficiency(player, attribute, position):
    proficiency = player.get_proficiency(position)
    base_value = getattr(player, attribute, 70)

    # 熟练度修正
    modifier = proficiency.get_proficiency_modifier()

    return int(base_value * modifier)
```

### Phase 3：轮换系统整合

**目标**：轮换时考虑多位置能力

```python
# LineupSelector 选择时考虑多位置
for position in ["CM", "CAM", "ST"]:
    # 检查每个球员在这个位置的熟练度
    for player in squad:
        if player.can_play_position(Position.CM):
            score = player.get_score_for_position(Position.CM)
```

---

## 📊 预期效果

### 改进前 vs 改进后

| 球员 | 改进前位置 | 改进后位置 | 射门属性发挥 |
|------|-----------|-----------|------------|
| Bellingham | RW (错误) | **CM/CAM** | 73 (vs 之前70) |
| Vinícius | CF (错误) | **LW** | 保持高水平 |
| Mbappé | CF (正确) | **CF/LW** | 多位置可用 |

### 对进球率的影响

- **更准确的属性发挥**：顶级球员在正确位置发挥100%+能力
- **合理的轮换**：球员可以在熟悉的位置轮换
- **战术多样性**：可以根据对手选择最优位置

---

## 🚀 优先级建议

1. **高优先级**：修复位置识别（Phase 1）
   - 立即解决 Bellingham、Vinícius 等顶级球员位置错误

2. **中优先级**：属性动态发挥（Phase 2）
   - 让熟练度系统实际影响比赛计算

3. **低优先级**：轮换系统整合（Phase 3）
   - 在轮换启用时考虑多位置能力

---

## 📝 后续扩展

1. **熟练度增长**：球员在某位置踢得越多，熟练度会提升
2. **位置训练**：训练系统可以提升特定位置熟练度
3. **伤病风险**：在不熟悉位置踢球增加伤病风险
4. **战术灵活性**：根据对手调整阵型更灵活

---

**当前状态**：✅ 框架已实现，待整合到比赛引擎
