# FM Manager - 足球经理模拟游戏

一个纯 CLI 界面的多人在线足球经理模拟游戏，支持 LLM 智能体作为球队经理。

## 游戏特色

- 🤖 **LLM 智能体**: 大语言模型扮演球队经理，自动做出战术、转会等决策
- 👤 **玩家扮演老板**: 玩家作为俱乐部老板，设定目标并下达指令
- 🌍 **真实数据**: 基于真实世界的球员、俱乐部和联赛数据
- ⚽ **比赛模拟**: 基于球员能力值的实时比赛模拟引擎
- 💰 **完整经济系统**: 转会、财政公平、青训等完整足球经营要素
- 🎮 **多人联机**: 多个玩家可同时参与同一局游戏
- 💻 **纯 CLI 界面**: 基于 Rich 的精美终端界面

## 项目结构

```
fm_manager/
├── core/               # 核心模块
│   ├── models/         # 数据库模型 (Player, Club, League, Match, Transfer)
│   ├── config.py       # 配置管理
│   └── database.py     # 数据库连接
├── engine/             # 游戏引擎
│   ├── match_engine.py # 比赛模拟
│   ├── finance_engine.py
│   ├── transfer_engine.py
│   └── calendar.py
├── ai/                 # LLM 集成
│   ├── llm_client.py   # LLM API 客户端
│   ├── agent.py        # AI 经理代理
│   └── prompt_builder.py
├── server/             # 游戏服务器
│   ├── main.py         # FastAPI 入口
│   ├── websocket.py    # WebSocket 处理
│   ├── game_room.py    # 房间管理
│   └── api/            # REST API
├── cli/                # CLI 客户端
│   ├── main.py         # CLI 入口
│   ├── ui/             # Rich UI 组件
│   └── client.py       # 服务器连接
└── data/               # 数据模块
    ├── seeds/          # 初始数据
    ├── fetcher.py      # 外部 API 获取
    ├── importer.py     # 数据导入
    └── generators.py   # 数据生成
```

## 设计文档

- [GAME_DESIGN.md](GAME_DESIGN.md) - 完整的游戏设计文档
- [ARCHITECTURE.md](ARCHITECTURE.md) - 技术架构设计
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) - 详细开发计划

## 快速开始

### 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装项目
pip install -e ".[dev]"
```

### 初始化数据库 (选择一种方案)

#### 方案 A: 完整数据集 (推荐)
使用生成的 5 大联赛完整数据 (~2500 球员):

```bash
# 生成并导入紧凑数据集
python scripts/import_compact_data.py

# 或使用原有种子数据
python scripts/init_db.py
```

#### 方案 B: 下载真实 FIFA 数据
从 Kaggle 下载 FIFA 22/23/24 数据集 (~18000 球员):

```bash
# 1. 安装 Kaggle CLI
pip install kaggle

# 2. 配置 API Key (从 https://www.kaggle.com/account 下载)
# 将 kaggle.json 放在 ~/.kaggle/

# 3. 查看可用数据源
python scripts/download_data.py --source list

# 4. 下载并导入 FIFA 数据
python scripts/download_data.py --source kaggle --dataset fifa-24 --import
```

#### 方案 C: Football Manager 数据
如果你有 FM 2024，可以导出数据:

```bash
# 使用 FM Editor 导出为 CSV
# 然后导入
python scripts/download_data.py --source fm --file path/to/fm_export.csv
```

### 启动服务器

```bash
fm-server
```

### 启动客户端

```bash
fm-cli
```

## 配置

创建 `.env` 文件:

```env
# LLM 配置
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini

# 数据库
DATABASE_URL=sqlite+aiosqlite:///data/fm_manager.db

# 外部 API (可选)
FOOTBALL_DATA_API_KEY=your_key
API_FOOTBALL_KEY=your_key
```

## 游戏玩法

1. **创建游戏房间**: 一名玩家作为主机创建房间
2. **选择球队**: 玩家选择要经营的俱乐部
3. **配置 LLM**: 设置 AI 经理的 API 参数
4. **开始游戏**: 服务器推进游戏时间
5. **下达指令**: 老板向 AI 经理发送指令
6. **旁观决策**: 观看 AI 经理做出各种决策
7. **批准转会**: 重要转会需要老板批准

## 开发计划

| 阶段 | 内容 | 时间 |
|-----|------|------|
| Phase 1 | 数据层与基础设施 | 第 1-3 周 |
| Phase 2 | 比赛模拟器 | 第 4-5 周 |
| Phase 3 | 核心系统 (财政/转会/青训) | 第 6-8 周 |
| Phase 4 | LLM 接入与多人联机 | 第 9-10 周 |
| Phase 5 | 完善与迭代 | 第 11 周+ |

## 技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy, WebSocket
- **CLI**: Rich, Textual, Click
- **LLM**: OpenAI API, 兼容其他 LLM
- **数据库**: SQLite (开发), PostgreSQL (生产)

## 许可证

MIT License
