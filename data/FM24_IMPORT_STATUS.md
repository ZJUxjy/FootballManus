# FM24 中文 CSV 数据导入指南

## 📊 数据概况

你的 FM24 CSV 文件已成功解析！

- **球员总数**: 112,821
- **独特俱乐部**: 8,822
- **数据格式**: JSON
- **文件位置**: `/home/xu/code/FootballManus/data/players_parsed.json`

## 🏆 数据质量验证

能力最高的 10 名球员：
1. **Kane, Harry** (Bayern Munich) - CA: 193, PA: 194
2. **Haaland, Erling** (Man City) - CA: 192, PA: 192
3. **Saka, Bukayo** (Arsenal) - CA: 192, PA: 192
4. **Bellingham, Jude** (Real Madrid) - CA: 190, PA: 190
5. **Mbappé, Kylian** (Real Madrid) - CA: 190, PA: 191

数据准确！

## 📝 数据特点

### 字段映射

| FM24 字段 | FootballManus 字段 | 说明 |
|----------|------------------|------|
| 姓名 | first_name, last_name | 球员姓名 |
| 国籍 | nationality | 国籍 |
| 位置 | position | 位置（已映射为英文） |
| 俱乐部 | club | 俱乐部名称 |
| 年龄 | age | 年龄 |
| 当前评分 | current_ability | 当前能力值 (1-200) |
| 最高潜力评分 | potential_ability | 潜力能力值 (1-200) |
| 工资 | salary | 周薪 |
| 身价 | market_value | 市场价值 |
| 生日 | birth_date | 出生日期 |

### 推断属性

由于 CSV 没有详细技能属性，我们根据位置和整体评分推断了：

**技术属性** (0-100):
- pace (速度)
- shooting (射门)
- passing (传球)
- dribbling (盘带)
- crossing (传中)
- first_touch (第一脚触球)

**身体属性** (0-100):
- acceleration (加速度)
- stamina (体力)
- strength (力量)

**防守属性** (0-100):
- tackling (抢断)
- marking (盯人)
- positioning (站位)

**心理属性** (0-100):
- vision (视野)
- decisions (决策)
- determination (决心)
- leadership (领导力)
- teamwork (团队合作)
- aggression (侵略性)

**守门员属性** (0-100，GK 专属):
- reflexes (反应)
- handling (手型)
- kicking (开球)
- one_on_one (单刀扑救)

## 🚀 使用方法

### 1. 查看数据（已解析）

```bash
# 解析 CSV 到 JSON
python scripts/parse_fm24_chinese.py data/players.csv

# 查看统计信息
python scripts/parse_fm24_chinese.py data/players.csv
```

### 2. 导入到数据库（需要修复依赖）

```bash
# 暂时依赖问题，需要先修复
# python scripts/import_fm24_chinese.py data/players.csv --limit 1000
```

### 3. 分析数据

```python
import json

# 读取解析的数据
with open('data/players_parsed.json', 'r', encoding='utf-8') as f:
    players = json.load(f)

# 查找特定球员
kane = next(p for p in players if 'Kane' in p['name'])
print(f"Harry Kane: CA {kane['current_ability']}, PA {kane['potential_ability']}")

# 筛选特定俱乐部
arsenal_players = [p for p in players if 'Arsenal' in p['club']]
print(f"Arsenal has {len(arsenal_players)} players")
```

### 4. 创建子集（用于测试）

```python
import json

# 只导入五大联赛俱乐部
big_5_leagues = [
    'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1'
]

with open('data/players_parsed.json', 'r', encoding='utf-8') as f:
    all_players = json.load(f)

# 筛选（这里需要实际的联赛信息）
# 由于 CSV 只有俱乐部名称，需要手动指定俱乐部
target_clubs = [
    'Arsenal', 'Man City', 'Liverpool', 'Chelsea', 'Man Utd',
    'Real Madrid', 'Barcelona', 'Atlético', 'Sevilla',
    'Bayern Munich', 'Dortmund', 'Leipzig',
    'Juventus', 'Inter', 'Milan',
    'PSG', 'Marseille', 'Lyon'
]

filtered = [p for p in all_players if any(club in p['club'] for club in target_clubs)]

with open('data/players_top5.json', 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"筛选后: {len(filtered)} 名球员")
```

## 📁 文件位置

- **原始 CSV**: `data/players.csv`
- **解析后的 JSON**: `data/players_parsed.json`
- **解析脚本**: `scripts/parse_fm24_chinese.py`
- **导入脚本**: `scripts/import_fm24_chinese.py` (需要修复依赖)

## 🔧 下一步

### 选项 1: 修复依赖并导入

需要先解决 Python 依赖问题，然后可以完整导入到数据库。

### 选项 2: 使用 JSON 数据直接工作

解析后的 JSON 文件可以直接用于：
- 数据分析
- 创建测试子集
- 生成示例数据

### 选项 3: 重新导出 CSV 格式

如果需要标准的 CSV 格式（不含中文），可以转换：

```python
import csv
import json

with open('data/players_parsed.json', 'r', encoding='utf-8') as f:
    players = json.load(f)

# 转换为标准 CSV
with open('data/players_standard.csv', 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['name', 'age', 'nationality', 'club', 'position',
                 'current_ability', 'potential_ability', 'pace', 'shooting',
                 'passing', 'dribbling']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows([{k: v for k, v in p.items() if k in fieldnames} for p in players])
```

## ⚠️ 注意事项

1. **编码问题**: 原始 CSV 使用 GBK 编码，已正确处理
2. **评分比例**: 百分比已转换为 1-200 的 FM 标准
3. **属性推算**: 详细技能属性是根据位置推算的，不是原始 FM 数据
4. **数据量**: 88MB 的 JSON 文件，导入到数据库需要一定时间

## 📊 数据分布

位置分布：
- CB (中后卫): 36,070
- CAM (前腰): 32,184
- CDM (后腰): 13,078
- ST (中锋): 12,560
- GK (门将): 11,910
- CM (中前卫): 7,019

---

需要帮助？数据已经成功解析，可以根据你的需求进一步处理！
