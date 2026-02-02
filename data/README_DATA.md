# 真实足球数据下载与导入指南

本文件夹包含从互联网下载真实世界足球数据并导入到 FM Manager 数据库的脚本。

## 文件说明

- `download_football_data.py` - 从网上下载真实球员数据
- `import_football_data.py` - 将下载的数据导入到数据库
- `fm_manager.db` - 本地数据库
- `export_players.py` - 导出球员数据到CSV

## 数据来源

### 1. Transfermarkt 数据集 ⭐ 推荐
- **来源**: https://github.com/salimt/football-datasets
- **格式**: CSV
- **球员数**: 93,000+
- **包含**: 球员档案、市场价值、转会历史、出场数据、俱乐部信息
- **特点**: 数据最全面，包含转会信息，适合FM模拟

### 2. EA Sports FC 数据集
- **来源**: https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset
- **格式**: CSV
- **球员数**: 17,326+
- **包含**: 姓名、国籍、俱乐部、位置、年龄、评分、属性（速度、射门、传球等48个属性）
- **特点**: 原生CSV格式，属性详细，但基于游戏评分

### 3. Football.db 赛程数据
- **来源**: https://github.com/openfootball/football.json
- **格式**: JSON / SQLite
- **包含**: 五大联赛2025/26赛季赛程、球队信息
- **特点**: 免费开源，持续更新

### 4. StatsBomb Open Data
- **来源**: https://github.com/statsbomb/open-data
- **格式**: JSON
- **包含**: 事件级数据（传球、射门、铲断等）
- **特点**: 高级分析数据，适合研究

## 使用方法

### 步骤 1: 下载数据

```bash
cd data
python3 download_football_data.py
```

选择数据源：
- **选项 1**: Transfermarkt 数据集（推荐）
- **选项 2**: Football.db 赛程数据
- **选项 3**: StatsBomb 样本
- **选项 4**: Kaggle 数据集（需要手动下载）
- **选项 5**: 下载所有推荐数据

### 步骤 2: 导入数据库

```bash
python3 import_football_data.py
```

选择要导入的数据：
- **选项 1**: Transfermarkt 球员数据
- **选项 2**: Transfermarkt 俱乐部数据
- **选项 3**: Kaggle FC 球员数据
- **选项 4**: 导入所有 Transfermarkt 数据

### 步骤 3: 验证数据

导出并查看导入的数据：

```bash
python3 export_players.py
```

## 推荐工作流

### 方案 A: 快速原型开发
1. 下载 Kaggle FC 数据集（手动）
2. 导入到数据库
3. 立即开始开发

### 方案 B: 完整真实数据
1. 运行 `download_football_data.py` 选择选项 5
2. 运行 `import_football_data.py` 选择选项 4
3. 获得93K+球员的完整数据集

### 方案 C: 研究分析
1. 下载 StatsBomb 数据
2. 使用 Python/R 进行事件级数据分析

## Kaggle 手动下载

由于 Kaggle 需要 API 认证，部分数据集需要手动下载：

1. 访问 Kaggle 网站并登录
2. 下载数据集并解压
3. 将 CSV 文件复制到 `data/` 文件夹
4. 运行 `import_football_data.py` 导入

主要 Kaggle 数据集：
- EA Sports FC 24: https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset
- Football Players Stats: https://www.kaggle.com/datasets/georgescristianpopescu/football-players-stats-2024-2025
- Club Match Data: https://www.kaggle.com/datasets/adamgbor/club-football-match-data-2000-2025

## 数据字段映射

脚本会自动将外部数据字段映射到 FM Manager 数据库结构：

### Players 表字段
- 基本信息: id, first_name, last_name, nationality, position
- 身体特征: height, weight, preferred_foot
- 技术属性: pace, shooting, passing, dribbling, tackling, marking, reflexes, handling
- 心理属性: work_rate, determination, leadership, teamwork, aggression
- 能力值: current_ability, potential_ability
- 合同信息: market_value, contract_until, salary
- 统计数据: appearances, goals, assists, yellow_cards, red_cards, minutes_played

### Clubs 表字段
- 基本信息: id, name, league, country
- 其他: stadium, founded, budget, reputation

## 注意事项

1. **数据类型区分**:
   - Transfermarkt: 真实世界数据
   - EA Sports FC: 游戏评分数据
   - StatsBomb: 事件级专业数据

2. **版权和使用条款**:
   - Transfermarkt: 遵守网站使用条款
   - Kaggle: 遵守数据集许可证
   - Football Manager 数据: 注意 SEGA 版权限制

3. **数据质量**:
   - Transfermarkt 和 StatsBomb 质量最高
   - Kaggle 数据集质量取决于维护者
   - 导入后建议检查数据完整性

## 故障排除

### 问题: 下载失败
- 检查网络连接
- 某些文件可能需要代理

### 问题: 导入失败
- 确保数据库已创建（运行 `init_db.py`）
- 检查 CSV 文件格式是否正确

### 问题: 字段缺失
- 脚本会为缺失字段提供默认值
- 检查日志查看警告信息

## 更多资源

- Football-Data.org API: https://www.football-data.org/
- API-Football: https://www.api-football.com/
- StatsBomb Open Data: https://github.com/statsbomb/open-data
- openfootball: https://github.com/openfootball/football.json
