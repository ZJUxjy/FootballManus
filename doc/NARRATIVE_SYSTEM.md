# 叙事系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/narrative_engine.py`

---

## 核心功能

### 1. 比赛叙事生成

```python
class MatchNarrativeGenerator:
    - 生成比赛标题
    - 提取关键时刻
    - 生成开场/结尾段落
    - 完整比赛报道
```

#### 标题模板

| 结果 | 模板示例 |
|-----|---------|
| 险胜 | "{team} Edge Past {opponent} in Tight Contest" |
| 大胜 | "{team} Dominate {opponent} in Emphatic Victory" |
| 平局 | "{team} and {opponent} Share the Spoils" |
| 冷门 | "Shock Result as {opponent} Stun {team}" |

### 2. 球员故事生成

```python
class PlayerNarrativeGenerator:
    - 个性特质分析
    - 职业生涯亮点
    - 媒体形象描述
    - 球迷观感评估
```

#### 个性特质

基于球员属性自动推断:
- `determination > 70` → "highly determined"
- `leadership > 70` → "natural leader"
- `work_rate > 70` → "hard worker"
- `flair > 70` → "flamboyant"

### 3. 赛季故事生成

```python
class SeasonNarrativeGenerator:
    - 赛季标题
    - 总结段落
    - 关键比赛
    - 转折点
    - 最终评估
```

---

## 数据结构

### MatchNarrative

```python
@dataclass
class MatchNarrative:
    match_id: int
    headline: str
    opening_paragraph: str
    key_moments: list[dict]
    closing_paragraph: str
    tone: str  # dramatic/neutral/analytical
```

### PlayerStory

```python
@dataclass
class PlayerStory:
    player_id: int
    personality_traits: list[str]
    career_highlights: list[str]
    media_narrative: str
    fan_perception: str
```

---

## 使用示例

### 比赛报道

```python
engine = NarrativeEngine()

narrative = engine.generate_match_report(
    match=match,
    events=events,
    home_club=home,
    away_club=away,
    use_llm=False,  # 使用模板生成
)

print(narrative.headline)
print(narrative.to_full_report())
```

### 球员档案

```python
story = engine.generate_player_profile(player, use_llm=False)

print(story.personality_traits)
print(story.fan_perception)
```

### 赛季回顾

```python
season_story = engine.generate_season_review(
    club=club,
    season_year=2024,
    final_position=1,
    key_matches=matches,
    top_scorer=player,
)

print(season_story.title)
print(season_story.summary)
```

---

## 测试验证

```
Match Narrative:
  Headline: Manchester City Snatch Late Win Over Liverpool
  Tone: neutral
  Key moments: 4

Player Profile:
  Traits: reliable, ambitious, professional
  Fan perception: loved

Season Story:
  Title: Manchester City: Champions!
  Turning points: 3
```
