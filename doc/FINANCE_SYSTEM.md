# 财政系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/finance_engine.py`

---

## 核心功能

### 1. 收入系统

#### 收入来源分布
```
总收入构成:
├── 比赛日收入 (30%)      - 门票、季票、餐饮
├── 转播收入 (50%)        - 联赛分成、欧冠
├── 商业收入 (20%)        - 赞助、商品、授权
└── 其他 (5%)             - 奖金、球员出售
```

#### 比赛日收入
```python
matchday_revenue = ticket_revenue + hospitality + merchandise

ticket_revenue = stadium_capacity × attendance_rate × ticket_price
attendance_rate = base(0.85-0.95) × form_factor × match_importance

match_importance:
  - 普通比赛: 1.0
  - 德比: 1.15
  - 争冠关键战: 1.10
```

**示例**:
- 曼城 (53,400容量，€75票价): 普通比赛 €4.8M，德比 €5.5M

#### 转播收入
```python
tv_revenue = base_payment + performance_bonus

base_payment = league_tv_deal / teams
performance_bonus = position_multiplier × merit_payment

position_multiplier (Premier League示例):
  第1名: 1.60  (€18M/场)
  第4名: 1.35  (€15.2M/场)
  第10名: 1.03 (€11.6M/场)
  第17名: 0.59 (€6.6M/场)
```

#### 商业收入
```python
commercial_revenue = (sponsorship + merchandise + licensing) / 52

sponsorship = club_reputation × base_rate
# 曼城 (9500声望): €577K/周
# 普通球队 (5000声望): €144K/周
```

### 2. 支出系统

#### 支出构成
```
总支出:
├── 球员工资 (50-70%)     - 最大支出项
├── 球员摊销 (15-20%)     - 转会费分期
├── 员工工资 (5-10%)      - 教练、球探、职员
├── 青训维护 (3-5%)       - 学院运营
├── 设施维护 (5-8%)       - 球场、训练场
└── 运营成本 (5-10%)      - 旅行、医疗等
```

#### 工资计算
```python
weekly_wage_bill = sum(player.salary for player in squad)

financial_health_ratio = wage_bill / weekly_revenue

健康标准:
  - < 50%: 优秀
  - 50-70%: 健康
  - 70-85%: 警告
  - > 85%: 危险
```

### 3. 财政公平 (FFP) 系统

#### 监测指标
```python
class FFPStatus:
    MONITORING_THRESHOLD = 60_000_000   # 3年滚动亏损上限
    SQUAD_COST_RATIO_LIMIT = 0.70       # 工资占收入比上限
    BREAK_EVEN_TOLERANCE = 30_000_000   # 盈亏平衡容差
```

#### 违规制裁
| 违规程度 | 可能制裁 |
|---------|---------|
| 轻微超标 | 警告、罚款 |
| 严重超标 | 欧战禁赛、转会限制 |
| 持续违规 | 扣分、降级威胁 |

#### 计算示例
```
3年财务汇总:
  Year 1: +€10M (盈利)
  Year 2: -€25M (亏损)
  Year 3: -€30M (亏损)
  
3年净亏损: €45M < €60M (合规)

但如果:
  Year 3: -€50M
3年净亏损: €65M > €60M
制裁: 欧战禁赛风险
```

### 4. 预算系统

#### 预算分配
```python
@dataclass
class BudgetAllocation:
    total: int
    transfer_budget: int       # 60% of surplus
    wage_budget: int           # 40% of surplus
    emergency_reserve: int     # 10% buffer
    
def calculate_budgets(self, club_finances):
    available = club_finances.balance × 0.3  # 30% of balance
    
    self.transfer_budget = available × 0.6
    self.wage_budget = available × 0.4 / 52  # weekly
```

---

## 数据结构

### ClubFinances
```python
@dataclass
class ClubFinances:
    club_id: int
    balance: int                    # 当前余额
    
    # 预算
    wage_budget: int                # 周工资预算
    transfer_budget: int            # 转会预算
    
    # 财务记录
    weekly_income: int = 0
    weekly_expenses: int = 0
    transactions: list[FinancialTransaction] = field(default_factory=list)
    
    # FFP追踪
    ffp_tracking_period_years: int = 3
    acceptable_deviation: int = 60_000_000
    
    def record_transaction(self, amount: int, type_: str, description: str):
        # 记录财务交易
        
    def get_rolling_balance(self, years: int = 3) -> int:
        # 计算N年滚动盈亏
```

### FinancialTransaction
```python
@dataclass
class FinancialTransaction:
    date: date
    amount: int
    type: RevenueType | ExpenseType
    description: str
    category: str  # "income" | "expense"
```

### RevenueType / ExpenseType
```python
class RevenueType(Enum):
    MATCHDAY = "matchday"           # 比赛日
    TV_BROADCAST = "tv_broadcast"   # 转播
    COMMERCIAL = "commercial"       # 商业
    PRIZE_MONEY = "prize_money"     # 奖金
    TRANSFER = "transfer"           # 球员出售
    
class ExpenseType(Enum):
    WAGES = "wages"                 # 工资
    AMORTIZATION = "amortization"   # 摊销
    STAFF = "staff"                 # 员工
    FACILITIES = "facilities"       # 设施
    YOUTH = "youth"                 # 青训
    TRANSFER = "transfer"           # 转会支出
```

---

## 使用示例

### 处理比赛日
```python
engine = FinanceEngine()
finances = ClubFinances(club_id=1, balance=500_000_000)

# 主场比赛收入
revenue = engine.process_matchday(
    finances=finances,
    club=club,
    is_home=True,
    match_importance="derby"  # 或 "normal", "title_race"
)

print(f"比赛日收入: €{revenue/1e6:.1f}M")
print(f"新余额: €{finances.balance/1e6:.1f}M")
```

### FFP合规检查
```python
# 添加一些交易记录
for i in range(10):
    finances.add_transaction(FinancialTransaction(
        date=date.today() - timedelta(days=i*30),
        amount=5_000_000,
        type=ExpenseType.WAGES,
        description="月度工资",
        category="expense",
    ))

# 检查FFP状态
is_compliant, message, sanctions = engine.check_ffp_status(
    finances, date.today()
)

if not is_compliant:
    print(f"⚠️ {message}")
    for sanction in sanctions:
        print(f"  - {sanction}")
```

### 计算预算
```python
# 获取球队工资
players = [...]  # 球队球员列表
weekly_wages = engine.calculator.calculate_weekly_wage_bill(players)

# 设置预算
finances.wage_budget = weekly_wages * 1.1  # 10%缓冲
finances.transfer_budget = club.balance * 0.3  # 30%余额

print(f"周工资预算: €{finances.wage_budget/1000:.0f}K")
print(f"转会预算: €{finances.transfer_budget/1e6:.1f}M")
```

---

## 测试验证

### 收入测试
```
俱乐部: Manchester City
容量: 53,400 | 票价: €75 | 声望: 9500

收入测试:
  普通比赛: €4.8M
  德比战: €5.5M (1.15倍)
  争冠战: €5.2M (1.10倍)

电视转播 (按排名):
  第1名: €18.0M/场
  第10名: €11.6M/场
  第17名: €6.6M/场

商业收入: €577K/周

赛季奖金:
  冠军: €348M
  第4名: €252M
  第10名: €105M
```

### FFP测试
```
FFP检查:
  3年净亏损: €14.5M (超标)
  状态: 不合规
  制裁: 
    - 罚款 €20-50M
    - 欧战禁赛风险
    - 阵容限制 (23人)
```

---

## 未来扩展

- [ ] 赞助商合同系统
- [ ] 球场扩建/新建
- [ ] 债务/贷款系统
- [ ] 股东投资/分红
- [ ] 保险赔付
- [ ] 季票预订系统
- [ ] 球员肖像权收入
- [ ] 青训球员出售分成
