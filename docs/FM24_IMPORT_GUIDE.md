# Football Manager 2024 数据导入指南

## 快速开始

### 方法一：使用 Sortitoutsi 数据库（推荐新手）

这是最简单的方式，只需要下载和导入一个 CSV 文件。

#### 步骤：

1. **下载数据库**
   - 访问：https://sortitoutsi.net/downloads/view/66832/football-manager-2024-database
   - 下载 "Preview Database" (通常是 Excel 或 CSV 格式)
   - 或者下载完整的数据库文件

2. **转换为 CSV**（如果是 Excel）
   ```bash
   # 使用 Python 转换
   pip install pandas openpyxl
   python -c "
   import pandas as pd
   df = pd.read_excel('sortitoutsi_database.xlsx', sheet_name='players')
   df.to_csv('fm24_players.csv', index=False)
   "
   ```

3. **导入到项目**
   ```bash
   # 导入所有球员
   python scripts/import_fm_data.py fm24_players.csv

   # 只导入前 1000 名球员（快速测试）
   python scripts/import_fm_data.py fm24_players.csv --limit 1000
   ```

---

### 方法二：使用 FM 编辑器导出（推荐高级用户）

这种方式可以获得最完整、最准确的数据。

#### 步骤：

1. **打开 FM Editor**
   - FM24 安装目录：`C:/Program Files (x86)/Steam/steamapps/common/Football Manager 2024/fm_editor.exe`
   - 或在 Steam 库中右键 FM24 → 管理工具 → FM Editor

2. **加载数据库**
   - File → Load
   - 选择数据库文件：
     ```
     documents/Sports Interactive/Football Manager 2024/db/verfm24.db
     ```

3. **配置导出**
   - File → Export → CSV
   - 选择要导出的表：
     - **Players**（必须）
     - Clubs（可选）
     - Leagues（可选）
   - 设置导出文件名和位置

4. **导入到项目**
   ```bash
   python scripts/import_fm_data.py fm_players_export.csv
   ```

---

### 方法三：使用 FM Scout（在线）

适合快速查看和导出部分数据。

#### 步骤：

1. 访问：https://www.fmscout.com/

2. 搜索你要的球员或俱乐部

3. 使用导出功能下载 CSV

4. 导入到项目

---

### 方法四：直接读取游戏数据库（高级）

需要使用第三方解析库。

#### 步骤：

1. 安装解析库
   ```bash
   pip install fminside-api
   ```

2. 读取游戏数据库
   ```python
   from fminside import FMDatabase

   db = FMDatabase("verfm24.db")
   players = db.get_players()
   ```

---

## 数据对比

| 数据源       | 数据量  | 质量 | 难度 | 推荐场景 |
|------------|--------|------|------|---------|
| FM Editor  | 50万+  | ⭐⭐⭐⭐⭐ | 中   | 完整项目 |
| Sortitoutsi| 10万+  | ⭐⭐⭐⭐ | 低   | 快速原型 |
| FM Scout   | 预览数据 | ⭐⭐⭐ | 低   | 测试 |
| 直接读取   | 50万+  | ⭐⭐⭐⭐⭐ | 高   | 高级用户 |

---

## FM24 数据字段说明

### 基本信息字段
| 字段 | 说明 | 示例 |
|-----|------|------|
| UID | 球员唯一 ID | 123456 |
| Name | 球员姓名 | Kylian Mbappé |
| Age | 年龄 | 24 |
| Nation | 国籍 | France |
| Club | 俱乐部 | Paris Saint-Germain |
| Pos | 位置 | ST |

### 能力值
| 字段 | 说明 | 范围 |
|-----|------|------|
| CA | Current Ability（当前能力） | 1-200 |
| PA | Potential Ability（潜力能力） | 1-200 |

### 技术属性（14个）
- Corners, Crossing, Dribbling, Finishing, First Touch
- Free Kicks, Heading, Long Shots, Marking, Passing
- Penalty Taking, Tackling, Technique

### 心理属性（14个）
- Aggression, Anticipation, Bravery, Composure, Concentration
- Decisions, Determination, Flair, Leadership, Off the Ball
- Positioning, Teamwork, Vision, Work Rate

### 身体属性（8个）
- Acceleration, Agility, Balance, Jumping
- Natural Fitness, Pace, Stamina, Strength

### 守门员专属（11个）
- Aerial Reach, Command of Area, Communication, Eccentricity
- Handling, Kicking, One on Ones, Reflexes
- Rushing Out, Throwing, Technique

---

## 导入命令示例

### 基本导入
```bash
# 导入所有球员
python scripts/import_fm_data.py fm24_players.csv

# 只导入前 1000 名
python scripts/import_fm_data.py fm24_players.csv --limit 1000

# 只导入英超球员（需要俱乐部数据）
python scripts/import_fm_data.py fm24_players.csv --league "Premier League"
```

### 查看导入指南
```bash
python scripts/import_fm_data.py --info
```

---

## 常见问题

### Q: CSV 文件在哪里？
A:
- FM Editor 导出：你自己选择的位置
- Sortitoutsi：下载的 ZIP 文件中
- FM Scout：导出时选择的位置

### Q: 导入失败怎么办？
A:
1. 检查 CSV 文件格式是否正确
2. 确保文件编码为 UTF-8
3. 查看错误信息，可能是字段名不匹配

### Q: 如何只导入特定联赛？
A:
```bash
# 先查看可用的联赛
python fm_manager/data/fm_importer.py fm24_players.csv

# 然后过滤导入
python scripts/import_fm_data.py fm24_players.csv --league "Premier League"
```

### Q: 数据更新了怎么办？
A:
直接重新运行导入脚本，已存在的球员会被更新。

---

## 推荐流程

### Phase 1: 快速原型（本周）
使用 Sortitoutsi 数据快速导入 5 大联赛
```bash
python scripts/import_fm_data.py sortitoutsi_top5.csv --limit 2000
```

### Phase 2: 完整数据（下周）
使用 FM Editor 导出完整数据库
```bash
python scripts/import_fm_data.py fm_full_database.csv
```

---

## 相关资源

- **FM Editor 下载**: Steam 库 → FM24 → 管理工具
- **Sortitoutsi**: https://sortitoutsi.net/
- **FM Scout**: https://www.fmscout.com/
- **FMInside**: https://fminside.net/

---

## 需要帮助？

如果遇到问题，请检查：
1. Python 虚拟环境是否激活
2. 依赖是否安装：`pip install -e ".[dev]"`
3. 数据库是否初始化：`python scripts/init_db.py`
