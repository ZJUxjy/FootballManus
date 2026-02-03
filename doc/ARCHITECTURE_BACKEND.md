# FM Manager 后端架构设计

## 1. 整体架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (CLI/Web)                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │ WebSocket + HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ HTTP Routes  │  │ WebSocket    │  │ Background Tasks     │   │
│  │ /api/rooms/* │  │ /ws/rooms/*  │  │ match simulation     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘   │
│         │                 │                                     │
│         └─────────────────┼────────────────┐                    │
│                           ▼                ▼                    │
│                  ┌──────────────────┐  ┌──────────────┐         │
│                  │  GameRoom        │  │  AIManager   │         │
│                  │  (room state)    │  │  (AI logic)  │         │
│                  └────────┬─────────┘  └──────────────┘         │
│                           │                                     │
│                  ┌────────▼─────────┐                           │
│                  │ MarkovMatchEngine│                           │
│                  │ (match simulation)│                          │
│                  └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │ Cleaned CSV     │  │ ClubDataFull    │  │ AdaptedPlayer  │   │
│  │ players/teams   │  │ (squad data)    │  │ (match ready)  │   │
│  └─────────────────┘  └─────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心组件详解

### 2.1 服务器入口 (`server/main.py`)

**职责**：HTTP API + WebSocket 端点

```python
# 全局状态管理
rooms: Dict[str, GameRoom] = {}  # 所有游戏房间
llm_client: Optional[LLMClient] = None  # AI 客户端
```

**HTTP 端点**：
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/rooms` | 列出所有房间 |
| POST | `/api/rooms` | 创建房间 |
| GET | `/api/rooms/{id}` | 获取房间详情 |
| POST | `/api/rooms/{id}/join` | 加入房间 |
| POST | `/api/rooms/{id}/start` | 开始游戏（房主） |
| POST | `/api/rooms/{id}/select-club` | 选择俱乐部 |
| POST | `/api/rooms/{id}/simulate-matchday` | 模拟比赛日 |

**WebSocket 端点**：
- `/ws/rooms/{room_id}?player_id={id}` - 实时通信

---

### 2.2 房间管理 (`server/game_room.py`)

**GameRoom 类** - 核心状态容器：

```python
class GameRoom:
    room_id: str              # 房间唯一ID (8位uuid)
    name: str                 # 房间名称
    host_id: str              # 房主ID（第一个加入的玩家）
    status: RoomStatus        # 状态机
    
    players: Dict[str, Player]     # player_id -> Player
    selected_clubs: Dict[str, int] # player_id -> club_id
    available_clubs: List[ClubDataFull]  # 可选俱乐部（默认英超20队）
    
    current_matchday: int     # 当前比赛日
    standings: Dict[int, Dict] # 积分榜
```

**状态机 (RoomStatus)**：
```
WAITING -> SETUP -> READY -> PLAYING -> FINISHED
            ↑______________|
            (可暂停 PAUSED)
```

**关键方法**：
- `add_player()` - 添加玩家，第一个成为房主
- `select_club()` - 选择俱乐部，检查是否已被选
- `start_game()` - 开始赛季，初始化积分榜
- `simulate_matchday()` - 模拟一轮比赛
- `connect_websocket()` - 建立 WebSocket 连接

---

### 2.3 比赛引擎 (`engine/match_engine_markov.py`)

**设计原理**：马尔可夫链状态机

```python
PitchZone = HOME_BOX → HOME_THIRD → MIDFIELD → AWAY_THIRD → AWAY_BOX

# 每分钟的流程
for minute in range(90):
    events_this_minute = random.randint(0, 2)  # 0-2个事件
    for _ in range(events_this_minute):
        event = _determine_event(zone)  # 根据区域决定事件
        if event == "SHOT":
            shooter = _select_shooter()   # 位置权重选择
            outcome = _resolve_shot()     # 射手 vs 门将
```

**关键参数**：
```python
# 区域事件概率
BASE_EVENT_PROBS = {
    PitchZone.AWAY_BOX: {"shot": 0.35, "dribble": 0.25, "foul": 0.05},
    PitchZone.MIDFIELD: {"shot": 0.02, "pass": 0.40, "tackle": 0.25},
    # ...
}

# 位置射门权重（防止一个球员进所有球）
POSITION_SHOT_WEIGHTS = {
    "ST": 1.0, "CF": 0.95,    # 前锋最高
    "CAM": 0.75, "LW": 0.75,  # 攻击中场/边锋
    "CM": 0.3, "CDM": 0.12,   # 中场/后腰较低
}
```

**射门判定算法**（sigmoid 曲线）：
```python
def compute_shot_probabilities(shooter, keeper):
    # 射正概率
    p_in_frame = sigmoid(shooter - keeper, k=0.09)
    
    # 死角概率（与射门能力相关）
    p_in_corner = 0.2 + 0.3 * exp(-0.018 * shooter)
    
    # 扑救概率
    save_prob = 0.08 * sigmoid(keeper - shooter, k=0.12)
    
    # 进球概率
    goal_prob = p_in_frame * (1 - save_prob) - p_in_corner * save_prob
```

---

### 2.4 数据层 (`data/cleaned_data_loader.py`)

**数据流向**：
```
CSV Files → DataLoader → ClubDataFull → MatchEngine
```

**核心数据结构**：

```python
@dataclass
class ClubDataFull:
    id: int
    name: str
    league: str
    reputation: int
    finances: Dict
    players: List[PlayerDataFull]  # 完整阵容

@dataclass  
class AdaptedPlayer:
    # 比赛引擎使用的简化格式
    name: str
    position: str
    attributes: Dict[str, int]  # 关键属性
    current_fitness: int  # 疲劳度 (0-100)
```

**数据过滤**：
- 只加载 `England Premier League` 的 20 支球队
- 每队取能力值最高的 16 名球员
- 按位置构建阵容（4-3-3 默认阵型）

---

## 3. 通信协议

### 3.1 WebSocket 消息格式

**客户端 → 服务器**：
```json
{"type": "chat", "content": "hello"}
{"type": "ready", "ready": true}
{"type": "decision", "decision_type": "tactics", ...}
{"type": "ping"}
```

**服务器 → 客户端**：
```json
// 连接成功
{"type": "connected", "player_id": "...", "room_id": "...", "players": [...]}

// 系统消息
{"type": "system", "content": "Player joined", "timestamp": "..."}

// 聊天消息
{"type": "chat", "player_name": "king", "content": "hi"}

// 比赛结果
{"type": "match_result", "match": {"home_club_name": "Liverpool", ...}}

// 积分榜
{"type": "matchday_complete", "matchday": 1, "standings": [...]}
```

---

## 4. 关键流程

### 4.1 创建房间 & 加入

```
1. POST /api/rooms?name=hello&max_players=4&enable_ai=true
   → 返回 {room_id: "abc123", ...}

2. POST /api/rooms/abc123/join?player_name=king
   → 返回 {player_id: "def456", ws_url: "..."}
   
3. WebSocket /ws/rooms/abc123?player_id=def456
   → 连接建立，第一个加入者为房主
```

### 4.2 开始赛季

```
1. 玩家 select_club → 从 available_clubs 移除
2. 所有玩家 ready → status = READY
3. 房主 start_game → status = PLAYING
   - 初始化积分榜
   - 广播 game_started
```

### 4.3 模拟比赛日

```
1. 房主调用 simulate-matchday
2. Background task: room.simulate_matchday()
3. 配对算法：
   - 随机打乱俱乐部列表
   - 两两配对 (clubs[0] vs clubs[1], ...)
4. 每场比赛：
   - MarkovMatchEngine.simulate()
   - 返回比分和事件
   - 更新积分榜
   - 广播 match_result
5. 广播 matchday_complete + 积分榜
```

---

## 5. 扩展点

### 5.1 添加新联赛

在 `GameRoom._load_data()` 中修改：
```python
major_leagues = ["England Premier League", "La Liga", "Bundesliga"]
```

### 5.2 修改比赛参数

在 `match_engine_markov.py` 调整：
```python
BASE_EVENT_PROBS = {...}        # 事件频率
POSITION_SHOT_WEIGHTS = {...}   # 射门分布
FRAME_K = 0.09                  # 射正难度
SAVE_K = 0.12                   # 扑救难度
```

### 5.3 添加新消息类型

1. `server/main.py` websocket_endpoint 添加 handler
2. `server/game_room.py` 添加处理方法
3. `cli/main.py` 添加客户端处理

---

## 6. 文件索引

| 文件 | 职责 |
|------|------|
| `server/main.py` | FastAPI 服务器入口 |
| `server/game_room.py` | 房间状态管理、比赛调度 |
| `engine/match_engine_markov.py` | 比赛模拟核心 |
| `engine/match_engine_adapter.py` | 数据格式转换 |
| `data/cleaned_data_loader.py` | CSV 数据加载 |
| `cli/client.py` | WebSocket 客户端 |
| `cli/main.py` | CLI 交互界面 |

---

## 7. 调试技巧

```bash
# 查看服务器日志
python -m fm_manager.server.main

# 查看 API 文档
open http://localhost:8000/docs

# 测试 HTTP API
curl http://localhost:8000/api/rooms
curl -X POST "http://localhost:8000/api/rooms?name=test&max_players=4"

# 查看数据
python -c "from fm_manager.data.cleaned_data_loader import load_for_match_engine; ..."
```

有任何具体问题随时问我！
