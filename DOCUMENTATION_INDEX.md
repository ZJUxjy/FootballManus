# 文档索引

## 📁 项目根目录（规划文档）

| 文档 | 描述 | 状态 |
|-----|------|------|
| [README.md](README.md) | 项目简介、快速开始、使用说明 | ✅ 核心文档 |
| [plan.md](plan.md) | 原始项目计划 | ✅ 保留 |
| [GAME_DESIGN.md](GAME_DESIGN.md) | 游戏设计文档（核心玩法、规则） | ✅ 核心文档 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 技术架构设计 | ✅ 核心文档 |
| [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) | 分阶段开发计划 | ✅ 核心文档 |
| [DATA_SOURCES.md](DATA_SOURCES.md) | 数据来源方案（Kaggle/Transfermarkt/FM） | ✅ 核心文档 |

---

## 📁 doc/ 目录（技术实现文档）

| 文档 | 描述 | 相关代码 |
|-----|------|---------|
| [doc/MATCH_ENGINE.md](doc/MATCH_ENGINE.md) | 比赛引擎 V1 文档 | `engine/match_engine.py` |
| [doc/MATCH_SIMULATION_ANALYSIS.md](doc/MATCH_SIMULATION_ANALYSIS.md) | 比赛模拟维度分析（5大维度） | `engine/match_engine_v2.py` |
| [doc/DYNAMIC_STATE.md](doc/DYNAMIC_STATE.md) | 动态状态系统（连胜/连败/士气） | `engine/team_state.py` |
| [doc/SEASON_SIMULATION.md](doc/SEASON_SIMULATION.md) | 联赛赛季模拟系统 | `engine/season_simulator.py` |

---

## 📁 其他重要目录

```
fm_manager/
├── core/               # 核心模块
│   ├── models/         # 数据库模型
│   ├── config.py       # 配置管理
│   └── database.py     # 数据库连接
├── engine/             # 游戏引擎 ⭐
│   ├── match_engine.py      # 比赛引擎 V1
│   ├── match_engine_v2.py   # 比赛引擎 V2 (当前使用)
│   ├── season_simulator.py  # 赛季模拟
│   ├── team_state.py        # 动态状态
│   └── ...
├── ai/                 # LLM 集成
├── server/             # 游戏服务器
├── cli/                # CLI 客户端
├── data/               # 数据模块
└── scripts/            # 工具脚本 ⭐
    ├── simulate_season.py
    ├── demo_match.py
    └── test_match_engine_v2.py
```

---

## 🚀 快速导航

### 想了解项目？
→ 从 [README.md](README.md) 开始

### 想了解游戏设计？
→ 看 [GAME_DESIGN.md](GAME_DESIGN.md)

### 想了解技术架构？
→ 看 [ARCHITECTURE.md](ARCHITECTURE.md)

### 想了解比赛模拟？
→ 看 [doc/MATCH_SIMULATION_ANALYSIS.md](doc/MATCH_SIMULATION_ANALYSIS.md)

### 想了解动态状态？
→ 看 [doc/DYNAMIC_STATE.md](doc/DYNAMIC_STATE.md)

---

## 📝 文档更新记录

| 日期 | 变更 |
|-----|------|
| 2024-02-02 | 整理文档结构，创建 doc/ 目录 |
