# 转会系统设计文档

**状态**: ✅ 已实现  
**模块**: `fm_manager/engine/transfer_engine.py`

---

## 核心功能

### 1. 球员估值系统

#### 基础价值计算
```python
Value = base_value × age_factor × contract_factor × club_factor

base_value = market_value × ability_weight
age_factor = 0.6 (16) → 1.0 (25-28) → 0.4 (35+)
contract_factor = 1.0 (5年) → 2.0 (<1年)
```

#### 影响因素
| 因素 | 影响 | 说明 |
|-----|------|------|
| 能力 (CA) | + | 每点CA约+1%价值 |
| 潜力 (PA) | + | 年轻球员PA高则溢价 |
| 年龄 | - | 30岁后快速贬值 |
| 合同剩余 | - | 少于1年大幅降价 |
| 球员声望 | + | 知名度溢价 |

### 2. 报价系统

#### 报价类型
```python
class OfferType(Enum):
    TRANSFER = "transfer"      # 永久转会
    LOAN = "loan"              # 租借
    LOAN_TO_BUY = "loan_to_buy"  # 租借+买断
    EXCHANGE = "exchange"      # 球员交换
```

#### 报价评估算法
```
score = min(100, (offer_fee / player_value) × 50 + modifiers)

modifiers:
  + 需求紧迫度 (急需球员 +10)
  + 买家声望 (豪门 +5)
  - 替代成本 (寻找替代难度 -5~-15)
  - 战术重要性 (核心球员 -10)

decision:
  score >= 90 → ACCEPT
  75 <= score < 90 → COUNTER
  score < 75 → REJECT
```

### 3. 合同谈判系统

#### 工资计算
```python
base_wage = player.current_ability × 1000
reputation_premium = buying_club.reputation × 20
champions_bonus = 50_000 if CL else 0
ambition_factor = 0.8 ~ 1.5 (球员野心)

wage_demand = (base_wage + reputation_premium + champions_bonus) × ambition_factor
```

#### 合同接受度
```python
wage_ratio = offered_wage / wage_demand

acceptance_criteria:
  wage_ratio >= 1.0 → 非常满意
  0.9 <= wage_ratio < 1.0 → 满意
  0.8 <= wage_ratio < 0.9 → 考虑中
  wage_ratio < 0.8 → 拒绝
```

### 4. 转会窗口

#### 窗口时间表
| 窗口 | 开始 | 结束 | 备注 |
|-----|------|------|------|
| 夏季 | 6月1日 | 9月1日 | 主要转会期 |
| 冬季 | 1月1日 | 2月1日 | 补强迫切 |

#### Deadline Day 特性
- 最后时刻报价增加
- 时间压力影响决策
- 紧急租借增多

---

## 数据结构

### TransferOffer
```python
@dataclass
class TransferOffer:
    player_id: int
    from_club_id: int
    to_club_id: int
    fee: int
    offer_type: OfferType
    
    # 条件
    add_ons: dict           # 附加条款
    loan_duration: int      # 租借月数
    buy_option: bool        # 买断选项
    
    # 状态
    status: TransferStatus  # pending/accepted/rejected
    response_deadline: date
```

### ContractOffer
```python
@dataclass
class ContractOffer:
    player_id: int
    club_id: int
    wage: int               # 周薪
    contract_length_years: int
    squad_role: str         # key_player/first_team/squad/backup
    
    # 奖金
    signing_on_fee: int
    appearance_bonus: int
    goal_bonus: int
    clean_sheet_bonus: int
    
    # 特殊条款
    release_clause: int
    minimum_fee_clause: int
    yearly_wage_rise: float
```

---

## 使用示例

### 创建转会报价
```python
engine = TransferEngine()

offer = engine.create_transfer_offer(
    player=player,
    from_club=buying_club,
    to_club=selling_club,
    fee=80_000_000,
)

# 评估报价
evaluation = engine.evaluate_transfer_offer(
    offer, player, selling_club, buying_club
)

if evaluation['decision'] == 'accept':
    engine.accept_offer(offer)
elif evaluation['decision'] == 'counter':
    counter = engine.generate_counter_offer(offer, player)
```

### 合同谈判
```python
# 计算球员要求
wage_demand = engine.contract_negotiator.calculate_player_wage_demand(
    player, buying_club.reputation, is_champions_league=True
)

# 评估合同
contract = ContractOffer(
    player_id=player.id,
    club_id=club.id,
    wage=wage_demand + 50_000,
    contract_length_years=5,
    signing_on_fee=5_000_000,
    squad_role="first_team",
)

evaluation = engine.contract_negotiator.evaluate_contract_offer(
    player, contract
)

if evaluation['will_accept']:
    engine.sign_contract(player, contract)
```

---

## 测试验证

### 测试用例结果
```
球员: Bukayo Saka
  年龄: 24
  能力: 85
  市场价值: €100.0M

估值: €9.8M (基础) → €11.2M (建议要价)

报价: €80.0M
  评估分数: 60/100
  决策: COUNTER (还价)
  费/值比: 8.18x

合同谈判:
  球员要求: €367K/周
  提供: €417K/周
  接受度: 100%
  原因: 工资大幅上涨, 长期合同, 签字费丰厚
```

---

## 未来扩展

- [ ] 球员交换估值
- [ ] 经纪人中介费
- [ ] 分期付款条款
- [ ] 二次转会分成
- [ ] 强制买断条款
- [ ] 租借期间的工资分担
