# 新闻系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/news_system.py`

---

## 核心功能

### 1. 新闻分类

```python
class NewsCategory(Enum):
    MATCH_RESULT = "match_result"
    TRANSFER_RUMOR = "transfer_rumor"
    TRANSFER_CONFIRMED = "transfer_confirmed"
    INJURY = "injury"
    MANAGER_STATEMENT = "manager_statement"
    TACTICAL_ANALYSIS = "tactical_analysis"
    AWARD = "award"
```

### 2. 新闻优先级

```python
class NewsPriority(Enum):
    BREAKING = "breaking"      # 红色横幅，即时通知
    HIGH = "high"              # 头条位置
    MEDIUM = "medium"          # 标准位置
    LOW = "low"                # 底部
```

#### 优先级自动判定

| 类型 | 金额/条件 | 优先级 |
|-----|----------|--------|
| 转会确认 | > €50M | BREAKING |
| 转会确认 | > €20M | HIGH |
| 球员受伤 | 核心球员 | HIGH |
| 比赛结果 | 豪门对决 | HIGH |
| 战术分析 | - | LOW |

### 3. 新闻来源

```python
SOURCES = [
    "BBC Sport",
    "Sky Sports",
    "ESPN FC",
    "Goal.com",
    "Transfermarkt",
    "Club Media",
    "The Guardian",
]
```

---

## 数据结构

### NewsItem

```python
@dataclass
class NewsItem:
    id: int
    headline: str
    content: str
    category: NewsCategory
    priority: NewsPriority
    club_id: int | None
    player_id: int | None
    date: date
    source: str
    is_read: bool
```

### NewsFeed

```python
@dataclass
class NewsFeed:
    items: list[NewsItem]
    
    def get_unread(self) -> list[NewsItem]
    def get_by_category(self, category) -> list[NewsItem]
    def get_recent(self, days: int) -> list[NewsItem]
```

---

## 使用示例

### 系统初始化

```python
from fm_manager.engine.news_system import NewsSystem

system = NewsSystem()
```

### 添加比赛新闻

```python
news = system.add_match_result(match, home_club, away_club, key_player)

print(news.headline)
print(news.category.value)
```

### 添加转会新闻

```python
# 转会传闻
rumor = system.add_transfer_rumor(
    player, from_club, to_club, strength="strong"
)

# 确认转会
confirmed = system.add_transfer_confirmed(
    player, from_club, to_club, fee=80_000_000
)
```

### 添加伤病新闻

```python
injury = system.add_injury_news(
    player=player,
    club=club,
    injury_type="hamstring strain",
    duration_weeks=4,
)
```

### 获取新闻

```python
# 最新新闻
latest = system.get_latest_news(count=10)

# 未读新闻
unread = system.get_or_create_feed(club_id).get_unread()

# 突发新闻
breaking = system.get_breaking_news()

# 每日摘要
digest = system.generate_daily_news_digest(club_id, date.today())
```

---

## 新闻生成器

```python
generator = NewsGenerator()

# 生成特定类型新闻
news = generator.generate_match_news(match, home, away)
news = generator.generate_transfer_rumor(player, from_c, to_c)
news = generator.generate_transfer_confirmed(player, from_c, to_c, fee)
news = generator.generate_injury_news(player, club, injury_type, weeks)
news = generator.generate_tactical_analysis(match, home, away)
```

---

## 测试验证

```
Match Result News:
  Headline: Arsenal Triumph in Chelsea Clash
  Category: match_result
  Priority: high

Transfer News:
  Headline: Arsenal Announce Bukayo Saka Signing
  Priority: breaking

Transfer Rumor:
  Headline: Chelsea Interested in Bukayo Saka
  Priority: high

Injury News:
  Headline: Arsenal Confirm Bukayo Saka Injury
  Category: injury

News Feed Summary:
  Total items: 3
    match_result: 1
    transfer_rumor: 1
    transfer_confirmed: 1
```
