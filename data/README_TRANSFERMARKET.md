# Transfermarkt 数据集转换指南

## 数据集概览

你已下载的 Transfermarkt 数据集包含：

| 数据 | 文件 | 大小 | 记录数 |
|------|------|------|--------|
| **球员档案** | player_profiles.csv | 26MB | 92,671 |
| **球员表现** | player_performances.csv | 151MB | 1,878,719 |
| **球队详情** | team_details.csv | 596KB | 2,175 |
| **转会历史** | transfer_history.csv | 78MB | 1,101,441 |
| **市场价值** | player_latest_market_value.csv | 1.7MB | ~90K |
| **球员伤病** | player_injuries.csv | 7.7MB | - |
| **国家队表现** | player_national_performances.csv | 4.9MB | - |

## 快速开始

### 步骤 1: 确认数据位置

数据应该在：
```
/home/xjingyao/code/fm_manager/data/data/football-datasets/
```

### 步骤 2: 运行转换脚本

```bash
cd data
python3 transfermarkt_converter.py
```

选择选项：
- **1** - 仅导入俱乐部
- **2** - 仅导入球员
- **3** - 导入所有数据（推荐）

### 步骤 3: 命令行选项

```bash
# 导入俱乐部
python3 transfermarkt_converter.py --clubs

# 导入球员
python3 transfermarkt_converter.py --players

# 导入所有
python3 transfermarkt_converter.py --all
```

## 数据映射说明

### Clubs 表映射

| Transfermarkt 字段 | FM Manager 字段 | 说明 |
|-------------------|------------------|------|
| club_id | id | 俱乐部ID |
| club_name | name | 俱乐部名称 |
| club_name | short_name | 短名称 |
| country_name | country | 国家 |
| - | city | 默认: "Unknown" |
| - | founded_year | 默认: 1900 |
| club_name | stadium_name | 默认: "{name} Stadium" |
| - | stadium_capacity | 默认: 20000 |
| - | reputation | 默认: 50 |
| - | reputation_level | 默认: "World Class" |
| - | primary_color | 默认: "#FF0000" |
| - | secondary_color | 默认: "#FFFFFF" |
| - | balance | 默认: 50,000,000 |
| - | transfer_budget | 默认: 20,000,000 |
| - | is_ai_controlled | 默认: True |

### Players 表映射

| Transfermarkt 字段 | FM Manager 字段 | 说明 |
|-------------------|------------------|------|
| player_id | id | 球员ID |
| player_name | first_name, last_name | 拆分姓名 |
| date_of_birth | birth_date | 出生日期 |
| country_of_birth | nationality | 国籍 |
| position, main_position | position | 位置映射 |
| foot | preferred_foot | 惯用脚 |
| height | height | 身高 (cm) |
| - | weight | 默认: 70kg |
| - | 技术属性 | 默认: 60 |
| current_club_id | club_id | 当前俱乐部 |
| contract_expires | contract_until | 合同到期 |
| - | salary | 默认: 10,000 |
| value (market value) | market_value | 从最新市场价值获取 |
| - | release_clause | 默认: market_value * 1.5 |
| - | fitness | 默认: 100 |
| - | morale | 默认: 80 |
| - | form | 默认: 75 |
| - | current_ability | 根据市场价值估算 |
| - | potential_ability | 默认: 75 |
| - | career_goals | 等于总进球数 |
| - | career_appearances | 等于总出场数 |

### 从 player_performances 聚合

| 统计字段 | 聚合方式 |
|----------|----------|
| goals | SUM |
| assists | SUM |
| yellow_cards | SUM |
| red_cards | SUM (direct_red + second_yellow) |
| minutes_played | SUM |
| appearances | SUM (nb_on_pitch) |

### 能力值估算

脚本根据市场价值估算球员能力值：

| 市场价值 | 能力值 |
|----------|--------|
| < €100K | 50 |
| €100K-500K | 55 |
| €500K-1M | 60 |
| €1M-5M | 65 |
| €5M-10M | 70 |
| €10M-20M | 75 |
| €20M-40M | 80 |
| €40M-70M | 85 |
| €70M-100M | 90 |
| > €100M | 95 |

## 位置映射

| Transfermarkt 位置 | FM Manager 位置 |
|-----------------|-----------------|
| GK, Goalkeeper | GK |
| CB, Centre-Back | CB |
| RB, Right-Back | RB |
| LB, Left-Back | LB |
| CDM, Defensive-Midfield | CDM |
| CM, Central-Midfield | CM |
| CAM, Attacking-Midfield | CAM |
| RM, Right-Midfield | RM |
| LM, Left-Midfield | LM |
| RW, Right-Winger | RW |
| LW, Left-Winger | LW |
| CF, Centre-Forward | CF |
| ST, Striker | ST |

## 导入后的数据

导入完成后，数据库将包含：
- **2,175 家俱乐部**
- **92,671 名球员**
- 每名球员的：
  - 基本信息（姓名、国籍、生日）
  - 技术属性（默认值60）
  - 统计数据（出场、进球、助攻等）
  - 合同信息
  - 市场价值

## 验证导入

导出部分数据查看：

```bash
python3 export_players.py
```

查看导出的 CSV 文件：
```bash
head -20 players_export.csv
```

查询数据库：
```bash
sqlite3 fm_manager.db "SELECT COUNT(*) FROM players;"
sqlite3 fm_manager.db "SELECT COUNT(*) FROM clubs;"
```

## 注意事项

### 技术属性
Transfermarkt 数据集不包含详细的技术属性（如速度、射门、传球等）。
脚本使用默认值 60。
**改进建议**：
- 从其他数据源（如 FIFA/FC）获取技术属性
- 根据位置和年龄估算属性
- 使用算法生成合理的属性分布

### 球员体重
数据集中不包含体重，脚本使用默认值 70kg。

### 合同和薪资
数据集中包含部分合同信息，但可能不完整。脚本使用合理的默认值。

### 技术属性改进方案

如果需要更真实的技术属性，可以：

1. **使用 FIFA/FC 数据**：
   ```python
   # 从 Kaggle 下载 EA Sports FC 数据
   # 按球员姓名匹配，导入技术属性
   ```

2. **基于位置估算**：
   ```python
   # 前锋: 射门 75, 速度 70
   # 中场: 传球 70, 盘带 70
   # 后卫: 铲断 70, 标记 70
   # 门将: 反应 70, 扑救 70
   ```

3. **基于市场价值调整**：
   ```python
   # 高价值球员 → 更高的技术属性
   base_attribute = self.estimate_ability(market_value)
   pace = base_attribute + random.randint(-10, 10)
   ```

## 数据源参考

- **Kaggle 数据集**: https://www.kaggle.com/datasets/xfkzujqjvx97n/football-datasets
- **GitHub 仓库**: https://github.com/salimt/football-datasets
- **Transfermarkt**: https://www.transfermarkt.com/

## 故障排除

### 问题: 内存不足
如果导入时内存不足，可以分批导入：

```bash
# 仅导入俱乐部
python3 transfermarkt_converter.py --clubs

# 然后导入球员
python3 transfermarkt_converter.py --players
```

### 问题: 导入速度慢
导入 92K+ 球员需要时间，请耐心等待。
进度每 100 条记录会打印一次。

### 问题: 数据缺失
某些球员可能缺少统计数据（goals, assists等），脚本使用默认值 0。

## 后续步骤

1. **验证数据**：检查导入的数据是否合理
2. **添加联赛**：从 team_competitions_seasons.csv 导入联赛数据
3. **添加比赛**：从 player_performances 生成比赛记录
4. **完善属性**：使用 FIFA/FC 数据或算法生成技术属性
5. **测试游戏**：使用真实数据测试模拟引擎
