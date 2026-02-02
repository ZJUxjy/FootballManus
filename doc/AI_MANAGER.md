# AI 经理系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/ai_manager.py`

---

## 核心功能

### 1. AI 个性类型

```python
class AIPersonality(Enum):
    AGGRESSIVE      # 高风险，高压逼抢
    DEFENSIVE       # 保守，反击
    TIKI_TAKA       # 控球
    LONG_BALL       # 长传冲吊
    YOUTH_FOCUS     # 重视青训
    MONEYBALL       # 数据驱动
    SUPERSTAR       # 追求明星球员
    BALANCED        # 平衡
```

#### 个性影响

| 个性 | 风格 | 风险承受 | 青训偏好 |
|-----|------|---------|---------|
| Aggressive | High Press | 0.8 | 0.3 |
| Defensive | Low Block | 0.2 | 0.4 |
| Youth Focus | Balanced | 0.5 | 0.9 |
| Moneyball | Balanced | 0.4 | 0.7 |
| Superstar | Possession | 0.6 | 0.2 |

### 2. 阵容评估

```python
class AISquadAssessment:
    goalkeeper_strength: int
    defense_strength: int
    midfield_strength: int
    attack_strength: int
    squad_depth: int
    needs: list[Position]
    star_players: list[int]
    deadwood: list[int]
```

### 3. 转会策略

```python
class AITransferStrategy:
    priority_positions: list[Position]
    max_budget: int
    max_wage: int
    age_preference: tuple[int, int]
    min_potential: int
    sell_threshold: int  # % of value to accept
```

#### 报价决策逻辑

```
score = base_score + personality_modifiers

modifiers:
  - Star player: -20
  - Youth (U21) with Youth Focus: -15
  - Moneyball + high profit margin: accept
  - Superstar + star player: -25

decision:
  score >= 90 → ACCEPT
  75 <= score < 90 → COUNTER
  score < 75 → REJECT
```

### 4. 比赛决策

```python
class AIMatchDecision:
    minute: int
    decision_type: str  # substitution/tactic_change/instruction
    player_out: int
    player_in: int
    new_mentality: str
```

#### 决策规则

| 情况 | 决策 |
|-----|------|
| < 60分钟, 落后 | 战术调整为进攻 |
| < 60分钟, 疲劳 | 换人 |
| 60-75分钟, 落后 | 增加进攻性 |
| > 75分钟, 领先 | 转为防守 |
| > 75分钟, 落后 | 全力进攻 |

---

## 使用示例

### 创建 AI 经理

```python
from fm_manager.engine.ai_manager import AIManager, AIPersonality

manager = AIManager(
    club=club,
    personality=AIPersonality.YOUTH_FOCUS,
)

print(f"Style: {manager.tactics.style.value}")
print(f"Risk tolerance: {manager.risk_tolerance}")
```

### 阵容评估

```python
assessment = manager.assess_squad(players)

print(f"Defense: {assessment.defense_strength}")
print(f"Attack: {assessment.attack_strength}")
print(f"Needs: {assessment.needs}")
```

### 转会决策

```python
strategy = manager.create_transfer_strategy(finances, players)

print(f"Max budget: €{strategy.max_budget/1e6:.1f}M")
print(f"Priority positions: {strategy.priority_positions}")

# 评估报价
decision = manager.decide_on_transfer_offer(offer, player, transfer_engine)
print(f"Decision: {decision['decision']}")
```

### 比赛内决策

```python
decision = manager.make_match_decision(
    minute=75,
    score_for=1,
    score_against=0,
    available_subs=subs,
    tired_players=tired,
)

if decision:
    print(f"{decision.decision_type}: {decision.reason}")
```

---

## AI 经理控制器

```python
controller = AIManagerController()

# 为所有俱乐部创建AI经理
for club in clubs:
    controller.create_manager(club)

# 处理转会窗口
transfers = controller.process_transfer_window(
    clubs, players, current_date
)
```

---

## 测试验证

```
AI Personalities:
  Superstar (Manchester United):
    Style: possession
    Mentality: attacking
    Risk tolerance: 0.6
    Youth preference: 0.2

  Youth Focus (Manchester United):
    Style: balanced
    Youth preference: 0.9

Squad Assessment:
  Defense strength: 75
  Attack strength: 85
  Star players: 3

Transfer Strategy:
  Max budget: €100.0M
  Sell threshold: 90%
```
