# 足球数据来源方案

## 方案对比

| 方案 | 数据量 | 质量 | 难度 | 成本 | 推荐指数 |
|-----|-------|-----|-----|-----|---------|
| Football Manager 导出 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 | 需购买游戏 | ⭐⭐⭐⭐⭐ |
| Transfermarkt 爬虫 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 | 免费 | ⭐⭐⭐⭐ |
| API-Football | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 低 | 免费/付费 | ⭐⭐⭐⭐ |
| football-data.org | ⭐⭐⭐ | ⭐⭐⭐⭐ | 低 | 免费 | ⭐⭐⭐ |
| Kaggle 数据集 | ⭐⭐⭐ | ⭐⭐⭐ | 低 | 免费 | ⭐⭐⭐ |
| 开源 FIFA 数据库 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 低 | 免费 | ⭐⭐⭐ |

---

## 方案一：Football Manager 数据库 (推荐)

### 数据规模
- **球员**: 50万+ (全球各级联赛)
- **俱乐部**: 3000+ (100+国家)
- **联赛**: 200+ 
- **属性**: 50+ 详细属性

### 获取方式

#### 方式 A: 使用 FM 编辑器导出
1. 购买 Football Manager 2024 (Steam ~¥200)
2. 下载官方编辑器 (FM Editor)
3. 导出为 CSV/XML
4. 使用我们的导入工具

#### 方式 B: 使用社区工具 (推荐)
- **fmscout** 网站提供数据库导出
- **sortitoutsi** 有数据下载
- **fminside** API

```python
# 示例：从 FM 导出文件读取
import pandas as pd

# FM 导出通常是这种格式
df = pd.read_csv("fm_database.csv")
# 包含字段: Name, Age, CA, PA, Position, Club, Value, Wage, etc.
```

---

## 方案二：Transfermarkt 爬虫

### 数据规模
- **球员**: 100万+
- **俱乐部**: 5000+
- **联赛**: 300+
- **市场价值**: 历史数据

### 实现方式

#### Python 库: `transfermarkt-parser`
```bash
pip install transfermarkt-parser
```

```python
from transfermarkt_parser import TransfermarktClient

client = TransfermarktClient()
players = client.get_league_players("premier-league", season=2024)
```

#### 自定义爬虫 (使用 beautifulsoup4 + requests)
```python
import requests
from bs4 import BeautifulSoup

def scrape_transfermarkt(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0)'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # 解析球员数据...
```

### 注意事项
- 需要设置合适的请求间隔 (避免被封)
- 使用代理池
- 遵守 robots.txt

---

## 方案三：API-Football

### 特点
- RESTful API
- 1200+ 联赛覆盖
- 实时数据
- 球员统计、阵容、赛程

### 定价
- 免费版: 100 请求/天
- 付费版: €19/月起，无限请求

### 代码示例
```python
import requests

url = "https://v3.football.api-sports.io/players"
headers = {
    'x-rapidapi-key': "YOUR_API_KEY",
    'x-rapidapi-host': "v3.football.api-sports.io"
}
params = {"league": 39, "season": 2024, "page": 1}

response = requests.get(url, headers=headers, params=params)
players = response.json()["response"]
```

---

## 方案四：开源数据集

### 1. Kaggle 足球数据集
- **European Soccer Database**: 25,000+ 比赛，10,000+ 球员
- **FIFA 20-24 Complete Player Dataset**: 完整的 FIFA 游戏数据
- **Football Data from Transfermarkt**: 爬取的 Transfermarkt 数据

```bash
# 使用 kaggle API
kaggle datasets download -d hugomathien/soccer
```

### 2. StatsBomb 开放数据
- 免费的比赛事件数据
- JSON 格式
- 需要注册

### 3. FBref / Understat
- 详细的球员统计数据
- 可以使用 `fbref.py` 库

---

## 方案五：FIFA 游戏数据

### FIFA 24/25 球员数据
社区经常导出 FIFA Ultimate Team 数据:
- Futbin
- Futhead

```python
# FIFA 数据结构示例
{
    "name": "Kylian Mbappé",
    "overall": 91,
    "pace": 97,
    "shooting": 90,
    "passing": 80,
    "dribbling": 92,
    "defending": 36,
    "physical": 77,
    # ... 更多属性
}
```

---

## 推荐实施方案

### Phase 1: 快速扩充 (本周)
使用 **FIFA 数据集 + Kaggle 数据** 快速获得 20,000+ 球员

### Phase 2: 精细化数据 (下周)  
使用 **Transfermarkt 爬虫** 补充市场价值、合同等信息

### Phase 3: 完整数据 (可选)
购买 **Football Manager** 导出完整数据库

---

## 数据导入工具

我已经在项目中实现了:
- `data/fetcher.py` - API 获取
- `data/importer.py` - 数据导入
- `scripts/init_db.py` - 初始化脚本

接下来会添加:
- Transfermarkt 爬虫
- FM 数据导入器
- FIFA 数据解析器
