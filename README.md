# FM Manager - 足球经理模拟游戏

一个功能完整的足球经理模拟游戏，支持单人模式和多人联机，包含完整的比赛模拟、转会系统、青训发展和战术系统。

## 游戏特色

- ⚽ **完整比赛模拟**: Markov状态机驱动的实时比赛引擎，支持战术、球员状态、主场优势
- 🎯 **战术系统**: 28种球员角色，10种比赛风格，6种战术维度
- 💰 **完整经济系统**: 转会市场、合同谈判、财政公平、赞助系统
- 🌱 **青训发展**: 青训营生产、球员成长、潜力系统
- 🤖 **AI对手**: 8种经理个性，智能转会策略，战术适应
- 🎮 **单人模式**: 完整的CLI游戏循环，支持存档/读档
- 🌐 **多人联机**: WebSocket实时通信，支持人类+AI混合对战
- 💻 **精美CLI界面**: 基于Rich的终端UI，支持表格、进度条、面板

## 项目完成度: 95%

### 已实现功能

| 模块 | 状态 | 说明 |
|------|------|------|
| **数据层** | ✅ | 120,000+球员，5,600+俱乐部，完整数据库 |
| **比赛引擎** | ✅ | Markov引擎，实时模拟，战术影响 |
| **赛季模拟** | ✅ | 完整联赛赛季，积分榜，升降级 |
| **战术系统** | ✅ | 28角色，10风格，阵型设置 |
| **转会系统** | ✅ | 买卖球员，身价估算，合同谈判 |
| **青训系统** | ✅ | 青训生产，球员发展，潜力跟踪 |
| **财政系统** | ✅ | 预算管理，工资系统，赞助收入 |
| **AI经理** | ✅ | 8种个性，智能决策，转会策略 |
| **单人游戏** | ✅ | 完整CLI循环，存档系统 |
| **多人联机** | ✅ | WebSocket服务器，房间系统 |
| **杯赛系统** | ✅ | 足总杯风格，欧冠风格，抽签系统 |

## 项目结构

```
fm_manager/
├── core/                    # 核心模块
│   ├── models/              # 数据库模型
│   │   ├── player.py        # 球员模型 (120,000+球员)
│   │   ├── club.py          # 俱乐部模型
│   │   ├── league.py        # 联赛模型
│   │   ├── match.py         # 比赛模型
│   │   ├── tactics.py       # 战术系统 (28角色)
│   │   ├── facility.py      # 设施系统
│   │   ├── staff.py         # 员工系统
│   │   └── sponsorship.py   # 赞助系统
│   ├── save_load_slots.py   # 多槽位存档系统 ⭐ NEW
│   └── database.py          # 数据库连接
│
├── engine/                  # 游戏引擎
│   ├── match_engine_markov.py    # Markov比赛引擎 ⭐
│   ├── season_simulator.py       # 赛季模拟器
│   ├── tactics_engine.py         # 战术引擎
│   ├── transfer_engine.py        # 转会引擎
│   ├── youth_engine.py           # 青训引擎
│   ├── development_system.py     # 球员发展系统 ⭐ NEW
│   ├── ai_personality.py         # AI个性系统 ⭐ NEW
│   ├── cup_competition_engine.py # 杯赛引擎 ⭐ NEW
│   └── llm_client.py             # LLM客户端
│
├── server/                  # 多人联机服务器
│   ├── main.py              # FastAPI入口
│   ├── websocket.py         # WebSocket处理
│   ├── game_room.py         # 房间管理
│   └── api/                 # REST API
│
├── cli/                     # CLI客户端
│   ├── game_loop.py         # 单人游戏主循环 ⭐ NEW
│   ├── main.py              # 多人客户端
│   ├── tactics_cli.py       # 战术CLI
│   ├── club_cli.py          # 俱乐部CLI
│   └── player_role_cli.py   # 球员角色CLI
│
├── data/                    # 数据模块
│   ├── cleaned/             # 清洗后的数据
│   │   ├── players_cleaned.csv   # 120,000+球员
│   │   └── teams_cleaned.csv     # 5,600+球队
│   └── seeds/               # 初始数据
│
└── scripts/                 # 工具脚本
    ├── init_club_data.py         # 初始化俱乐部数据
    ├── add_test_players.py       # 添加测试球员
    ├── test_cup_system.py        # 杯赛测试 ⭐ NEW
    ├── test_multiplayer.py       # 多人联机测试 ⭐ NEW
    ├── test_game_loop.py         # 游戏循环测试 ⭐ NEW
    └── test_game_balance.py      # 平衡性测试
```

## 快速开始

### 1. 安装依赖

```bash
# 使用项目自带的venv (Python 3.13)
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 或者创建新环境
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 初始化数据库

```bash
# 重新初始化数据库
python scripts/reinit_database.py

# 添加测试俱乐部
python scripts/add_test_clubs.py

# 初始化俱乐部设施、员工、赞助商
PYTHONPATH=/home/xu/code/FootballManus python scripts/init_club_data.py

# 添加测试球员 (每个俱乐部25名)
python scripts/add_test_players.py
```

### 3. 启动单人游戏

```bash
# 启动完整单人游戏
.venv/bin/python -m fm_manager.cli.game_loop
```

游戏菜单：
- `1` - 进行比赛 (模拟本周所有比赛)
- `2` - 查看阵容
- `3` - 转会市场 (浏览/搜索/出售球员)
- `4` - 战术设置 (阵型/风格/角色分配)
- `5` - 查看积分榜
- `6` - 保存游戏 (10个存档槽位)
- `7` - 返回主菜单

### 4. 启动多人联机

```bash
# 终端1: 启动服务器
.venv/bin/uvicorn fm_manager.server.main:app --host 127.0.0.1 --port 8000

# 终端2: 启动客户端 (可选)
.venv/bin/python -m fm_manager.cli.main
```

### 5. 其他CLI工具

```bash
# 查看战术角色
.venv/bin/python -m fm_manager.cli.tactics_cli list-roles

# 查看俱乐部设施
.venv/bin/python -m fm_manager.cli.club_cli show-facilities -c 1

# 分配球员角色
.venv/bin/python -m fm_manager.cli.player_role_cli list-players -c 1
```

## 运行测试

```bash
# 单元测试
.venv/bin/python -m pytest tests/test_tactics.py -v

# 杯赛系统测试
.venv/bin/python scripts/test_cup_system.py

# 多人联机测试
.venv/bin/python scripts/test_multiplayer.py

# 游戏循环测试
.venv/bin/python scripts/test_game_loop.py

# 游戏平衡测试
.venv/bin/python scripts/test_game_balance.py --seasons 20
```

## 配置

创建 `.env` 文件:

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///data/fm_manager.db

# LLM 配置 (可选，用于AI经理)
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini

# 外部 API (可选)
FOOTBALL_DATA_API_KEY=your_key
```

## 游戏数据

- **球员**: 120,000+ (来自FIFA数据集)
- **俱乐部**: 5,600+
- **联赛**: Premier League, Bundesliga, La Liga, Serie A, Ligue 1
- **球员角色**: 28种 (Complete Forward, Playmaker, Winger等)
- **战术风格**: 10种 (Possession, Counter Attack, Gegenpress等)

## 设计文档

- [GAME_DESIGN.md](GAME_DESIGN.md) - 游戏设计文档
- [ARCHITECTURE.md](ARCHITECTURE.md) - 技术架构
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) - 开发计划
- [DATA_SOURCES.md](DATA_SOURCES.md) - 数据来源

## 技术栈

- **Python**: 3.13+
- **后端**: FastAPI, SQLAlchemy 2.0, WebSocket
- **CLI**: Rich, Click
- **数据库**: SQLite (开发), PostgreSQL (生产)
- **AI**: OpenAI API, 自定义AI个性系统

## 许可证

MIT License

## 更新日志

### v0.9.0 (当前)
- ✅ 完整单人游戏循环
- ✅ 多槽位存档系统 (10槽位)
- ✅ 转会市场功能
- ✅ 战术设置功能
- ✅ 杯赛系统测试
- ✅ 多人联机测试

### v0.8.0
- ✅ 青训发展系统
- ✅ 合同谈判系统
- ✅ AI对手个性系统

### v0.7.0
- ✅ 赛季模拟器
- ✅ 动态状态系统
- ✅ 比赛引擎V2

### v0.6.0
- ✅ 战术系统 (28角色)
- ✅ 设施系统
- ✅ 员工系统
