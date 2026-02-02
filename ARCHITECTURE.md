# 技术架构设计

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         客户端层 (CLI)                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Player 1    │  │  Player 2    │  │  Player N    │              │
│  │  CLI + LLM   │  │  CLI + LLM   │  │  CLI + LLM   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
└─────────┼─────────────────┼─────────────────┼──────────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │ WebSocket / HTTP
┌───────────────────────────▼─────────────────────────────────────────┐
│                        服务器层                                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Game Server (FastAPI)                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │  │
│  │  │ Room     │  │ Match    │  │ Transfer │  │ LLM          │ │  │
│  │  │ Manager  │  │ Engine   │  │ Handler  │  │ Interface    │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Scheduler        │  │ Event Bus        │  │ State Manager    │  │
│  │ (APScheduler)    │  │ (Redis/内存)      │  │ (游戏状态管理)    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                        数据层                                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  SQLite/     │  │  配置文件    │  │  External APIs           │  │
│  │  PostgreSQL  │  │  (JSON/YAML) │  │  - Football-Data.org     │  │
│  │              │  │              │  │  - API-Football          │  │
│  │  - Players   │  │  - Leagues   │  │  - Custom LLM API        │  │
│  │  - Clubs     │  │  - Rules     │  │                          │  │
│  │  - Matches   │  │  - Tactics   │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 模块设计

### 1. Core 模块 (core/)

```python
core/
├── __init__.py
├── models/           # 数据模型
│   ├── __init__.py
│   ├── player.py     # 球员模型
│   ├── club.py       # 俱乐部模型
│   ├── match.py      # 比赛模型
│   ├── transfer.py   # 转会模型
│   └── league.py     # 联赛模型
├── database.py       # 数据库连接
├── config.py         # 配置管理
└── exceptions.py     # 自定义异常
```

### 2. Engine 模块 (engine/)

```python
engine/
├── __init__.py
├── match_engine.py   # 比赛模拟引擎
├── finance_engine.py # 财政计算
├── transfer_engine.py# 转会处理
└── calendar.py       # 游戏日历
```

### 3. AI 模块 (ai/)

```python
ai/
├── __init__.py
├── llm_client.py     # LLM API 客户端
├── prompt_builder.py # 提示词构建
├── decision_parser.py# 决策解析器
└── agent.py          # AI经理代理
```

### 4. Server 模块 (server/)

```python
server/
├── __init__.py
├── main.py           # FastAPI 应用入口
├── websocket.py      # WebSocket 处理
├── game_room.py      # 游戏房间管理
├── state_manager.py  # 状态同步
└── api/
    ├── __init__.py
    ├── clubs.py      # 俱乐部接口
    ├── transfers.py  # 转会接口
    └── matches.py    # 比赛接口
```

### 5. CLI 模块 (cli/)

```python
cli/
├── __init__.py
├── main.py           # CLI 入口
├── ui/
│   ├── __init__.py
│   ├── dashboard.py  # 主界面
│   ├── match_view.py # 比赛视图
│   └── transfer_view.py
├── commands.py       # 命令处理
└── client.py         # 服务器连接
```

### 6. Data 模块 (data/)

```python
data/
├── __init__.py
├── fetcher.py        # 数据获取
├── importer.py       # 数据导入
├── generators.py     # 数据生成器
└── seeds/            # 初始数据
    ├── clubs.json
    ├── leagues.json
    └── tactics.json
```

## 数据库 Schema

```sql
-- 球员表
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    nationality TEXT,
    position TEXT,  -- GK, DEF, MID, FWD
    -- 能力值 (0-100)
    pace INTEGER DEFAULT 50,
    shooting INTEGER DEFAULT 50,
    passing INTEGER DEFAULT 50,
    dribbling INTEGER DEFAULT 50,
    defending INTEGER DEFAULT 50,
    physical INTEGER DEFAULT 50,
    -- 精神属性
    mentality INTEGER DEFAULT 50,
    work_rate TEXT, -- High/Medium/Low
    -- 潜力
    current_ability INTEGER DEFAULT 50,
    potential_ability INTEGER DEFAULT 50,
    -- 合同
    club_id INTEGER,
    contract_until DATE,
    salary INTEGER,
    market_value INTEGER,
    -- 状态
    fitness INTEGER DEFAULT 100,
    morale INTEGER DEFAULT 50,
    form INTEGER DEFAULT 50,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

-- 俱乐部表
CREATE TABLE clubs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT,
    city TEXT,
    country TEXT,
    stadium_name TEXT,
    stadium_capacity INTEGER,
    -- 声望 (0-10000)
    reputation INTEGER DEFAULT 1000,
    -- 财政
    balance INTEGER DEFAULT 0,
    wage_budget INTEGER DEFAULT 0,
    transfer_budget INTEGER DEFAULT 0,
    -- 关联
    league_id INTEGER,
    owner_user_id TEXT,  -- 玩家ID，NULL则为AI控制
    llm_config TEXT,     -- AI配置JSON
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

-- 联赛表
CREATE TABLE leagues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT,
    tier INTEGER,  -- 1=顶级
    teams_count INTEGER,
    -- 赛制
    promotion_count INTEGER,
    relegation_count INTEGER,
    has_playoff BOOLEAN DEFAULT FALSE,
    -- 时间表
    season_start_month INTEGER,
    season_end_month INTEGER
);

-- 赛季表
CREATE TABLE seasons (
    id INTEGER PRIMARY KEY,
    league_id INTEGER,
    year INTEGER,
    status TEXT, -- upcoming/active/completed
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

-- 比赛表
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    season_id INTEGER,
    matchday INTEGER,
    match_date DATE,
    home_club_id INTEGER,
    away_club_id INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    status TEXT, -- scheduled/live/finished
    -- 比赛事件 JSON
    events TEXT,
    FOREIGN KEY (season_id) REFERENCES seasons(id),
    FOREIGN KEY (home_club_id) REFERENCES clubs(id),
    FOREIGN KEY (away_club_id) REFERENCES clubs(id)
);

-- 联赛积分榜视图
CREATE VIEW league_standings AS
SELECT 
    season_id,
    club_id,
    COUNT(*) as played,
    SUM(CASE WHEN home_club_id = club_id AND home_score > away_score THEN 1
             WHEN away_club_id = club_id AND away_score > home_score THEN 1 ELSE 0 END) as won,
    SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) as drawn,
    SUM(CASE WHEN home_club_id = club_id AND home_score < away_score THEN 1
             WHEN away_club_id = club_id AND away_score < home_score THEN 1 ELSE 0 END) as lost,
    SUM(CASE WHEN home_club_id = club_id THEN home_score ELSE away_score END) as gf,
    SUM(CASE WHEN home_club_id = club_id THEN away_score ELSE home_score END) as ga
FROM matches
WHERE status = 'finished'
GROUP BY season_id, club_id;

-- 转会表
CREATE TABLE transfers (
    id INTEGER PRIMARY KEY,
    player_id INTEGER,
    from_club_id INTEGER,
    to_club_id INTEGER,
    fee INTEGER,
    -- 条款
    wage INTEGER,
    contract_length INTEGER,
    -- 状态
    status TEXT, -- offered/accepted/rejected/completed/cancelled
    offered_at TIMESTAMP,
    responded_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (from_club_id) REFERENCES clubs(id),
    FOREIGN KEY (to_club_id) REFERENCES clubs(id)
);

-- 游戏房间表
CREATE TABLE game_rooms (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT, -- waiting/playing/paused/finished
    current_date DATE,
    speed INTEGER DEFAULT 1, -- 游戏速度
    config TEXT -- 游戏配置JSON
);

-- 房间玩家关联
CREATE TABLE room_players (
    room_id TEXT,
    user_id TEXT,
    club_id INTEGER,
    joined_at TIMESTAMP,
    is_host BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (room_id, user_id),
    FOREIGN KEY (room_id) REFERENCES game_rooms(id),
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

-- 操作日志
CREATE TABLE action_logs (
    id INTEGER PRIMARY KEY,
    room_id TEXT,
    club_id INTEGER,
    action_type TEXT,
    action_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API 设计

### REST API

```
GET    /api/rooms              # 列出房间
POST   /api/rooms              # 创建房间
GET    /api/rooms/{id}         # 房间详情
POST   /api/rooms/{id}/join    # 加入房间
POST   /api/rooms/{id}/start   # 开始游戏

GET    /api/clubs              # 俱乐部列表
GET    /api/clubs/{id}         # 俱乐部详情
GET    /api/clubs/{id}/squad   # 阵容
GET    /api/clubs/{id}/finance # 财政

GET    /api/leagues/{id}/standings  # 积分榜
GET    /api/leagues/{id}/fixtures   # 赛程

GET    /api/transfers          # 转会列表
POST   /api/transfers          # 发起转会
PUT    /api/transfers/{id}     # 回应转会

GET    /api/matches/{id}       # 比赛详情
```

### WebSocket 事件

```javascript
// 客户端 -> 服务器
{
  "type": "command",
  "action": "instruct_manager",
  "data": { "message": "这赛季必须保级" }
}

// 服务器 -> 客户端 (广播)
{
  "type": "event",
  "event": "match_started",
  "data": { "match_id": 123, "home": "曼联", "away": "利物浦" }
}

{
  "type": "event", 
  "event": "transfer_offered",
  "data": { "transfer_id": 456, "player": "张三", "fee": 5000000 }
}

{
  "type": "event",
  "event": "day_advanced",
  "data": { "date": "2024-08-16", "events": [...] }
}
```

## LLM 集成设计

### 决策流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  游戏事件     │────▶│  构建上下文   │────▶│  发送给LLM   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  执行决策     │◀────│  解析响应     │◀────│  LLM回复    │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 决策类型

1. **阵容决策** - 选择首发11人
2. **战术决策** - 选择阵型和策略
3. **转会决策** - 买卖球员
4. **合同决策** - 续约谈判
5. **青训决策** - 提拔年轻球员
6. **回应决策** - 回复老板指令

### 提示词结构

```
[系统角色定义]
你是{club_name}的经理...

[固定规则]
- 你只能控制{club_name}
- 转会预算: {transfer_budget}
- 工资预算: {wage_budget}

[当前状态]
{game_state_summary}

[老板最新指令]
{owner_instruction}

[待决策事项]
{pending_decisions}

请以JSON格式回复你的决策...
```
