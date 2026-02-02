# 球迷与董事会系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/fan_board_system.py`

---

## 核心功能

### 1. 球迷情绪系统

```python
class FanSentiment(Enum):
    ECSTATIC = "ecstatic"      # 90-100
    HAPPY = "happy"            # 75-89
    CONTENT = "content"        # 60-74
    NEUTRAL = "neutral"        # 45-59
    CONCERNED = "concerned"    # 30-44
    UNHAPPY = "unhappy"        # 15-29
    ANGRY = "angry"            # 0-14
```

#### 比赛结果影响

```
胜利: +8 (×重要性倍数)
平局: +2
失败: -10 (×重要性倍数)

重要性倍数:
  德比: 1.5
  争冠: 1.3
  保级: 1.4
```

#### 上座率影响

| 情绪分数 | 上座率倍数 |
|---------|-----------|
| 80+ | 1.1 (爆满) |
| 60-79 | 1.0 (正常) |
| 40-59 | 0.9 (轻微下降) |
| 20-39 | 0.75 (明显下降) |
| <20 | 0.6 (可能罢看) |

### 2. 董事会系统

```python
class BoardConfidence(Enum):
    FULL = "full"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    CRITICAL = "critical"
```

#### 期望值设定

| 声望 | 联赛目标 | 杯赛目标 | 欧战目标 |
|-----|---------|---------|---------|
| 9000+ | 冠军 | 夺冠 | 欧冠夺冠 |
| 8000+ | 前四 | 决赛 | 欧冠八强 |
| 7000+ | 前六 | 八强 | 欧战资格 |
| 5000+ | 前十 | 八强 | - |
| 3000+ | 前十五 | 第三轮 | - |
| <3000 | 保级 | 第三轮 | - |

#### 经理评估算法

```python
def evaluate_manager():
    # 基础评分 (位置对比目标)
    position_diff = target - current_position
    
    if position_diff >= 5: base = 85
    elif position_diff >= 2: base = 75
    elif position_diff >= -2: base = 60
    elif position_diff >= -5: base = 45
    else: base = 30
    
    # 近期状态调整 (最近5场)
    recent_form = recent_points / max_points
    if recent_form >= 0.8: base += 10
    elif recent_form <= 0.2: base -= 15
    
    # FFP 违规惩罚
    if not ffp_compliant: base -= 10
    
    return base
```

#### 工作安全性

| 评级 | 信心度 | 状态 |
|-----|-------|------|
| >= 80 | FULL | 非常安全 |
| >= 65 | HIGH | 安全 |
| >= 45 | MODERATE | 相对稳定 |
| >= 30 | LOW | 有压力 |
| < 30 | CRITICAL | 濒临解雇 |

---

## 数据结构

### FanSentimentState

```python
@dataclass
class FanSentimentState:
    club_id: int
    overall_score: int  # 0-100
    trend: str          # rising/falling/stable
    attendance_modifier: float  # 0.5-1.5
    opinions: dict[str, FanOpinion]
```

### ManagerEvaluation

```python
@dataclass
class ManagerEvaluation:
    club_id: int
    overall_rating: int
    confidence: BoardConfidence
    weeks_under_pressure: int
    recent_feedback: list[str]
```

---

## 使用示例

### 球迷系统

```python
fan_system = FanSystem()

# 更新比赛后情绪
sentiment = fan_system.update_after_match(
    club_id=1,
    won=True,
    drawn=False,
    importance="derby",
)

print(sentiment.get_sentiment_level().value)
print(sentiment.get_description())

# 转会反应
reaction = fan_system.react_to_transfer(
    club_id=1,
    player_name="New Signing",
    is_arrival=True,
    fee=50_000_000,
    player_quality=80,
)
print(reaction)

# 获取球迷歌曲
chants = fan_system.get_fan_chants(club_id)

# 社交媒体反应
social = fan_system.get_social_media_reaction(club_id)
```

### 董事会系统

```python
board_system = BoardSystem()

# 设置期望
expectations = board_system.set_expectations(club)
print(f"Target position: {expectations.league_position_target}")

# 评估经理
evaluation = board_system.evaluate_manager(
    club_id=1,
    current_position=3,
    matches_played=20,
    wins=12,
    draws=4,
    losses=4,
)

print(f"Rating: {evaluation.overall_rating}")
print(f"Confidence: {evaluation.confidence.value}")
print(f"Feedback: {evaluation.recent_feedback}")

# 检查工作安全
security = board_system.check_job_security(club_id)
print(security['message'])
```

### 综合系统

```python
system = FanBoardSystem()

# 处理比赛结果
result = system.process_match_result(
    club_id=1,
    won=True,
    drawn=False,
    importance="normal",
)

# 获取俱乐部氛围
atmosphere = system.get_club_atmosphere(club_id)
print(atmosphere['description'])

# 赛季总结
review = system.generate_end_of_season_review(club_id)
```

---

## 测试验证

```
Board Expectations:
  Target position: 4
  Cup target: reach_final
  Youth minutes target: 5000

Fan Sentiment Progression:
  Initial: neutral (50)
  After Win: content (66)
  After Loss: neutral (46)
  After Win: neutral (54)

Manager Evaluation:
  Overall rating: 70/100
  Confidence: high
  Summary: Good progress

Job Security:
  Secure: True
  Message: The board has full confidence in your leadership.

Club Atmosphere:
  Overall score: 63
  Atmosphere: Stable
```
