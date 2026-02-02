# 足球经理模拟游戏 - 完整设计文档

## 一、游戏概述

### 1.1 核心概念
- **游戏类型**: CLI多人在线足球经理模拟游戏
- **核心玩法**: 玩家扮演球队老板，LLM扮演球队经理，共同经营足球俱乐部
- **技术特色**: 纯CLI界面 + LLM智能体 + 多人联机 + 真实足球数据

### 1.2 游戏角色
1. **球队老板 (玩家)**: 
   - 设定俱乐部长期目标
   - 下达指令（如签特定球员、财务约束等）
   - 批准/拒绝重大决策
   - 观察经理表现

2. **球队经理 (LLM)**:
   - 日常阵容调整
   - 战术安排
   - 转会谈判
   - 青训选拔
   - 与媒体/球员互动

3. **系统管理员**:
   - 游戏服务器控制
   - 比赛结果模拟
   - 规则执行

### 1.3 游戏流程
```
创建游戏房间 → 玩家加入 → 选择/分配球队 → 配置LLM → 游戏开始
                                              ↓
比赛日 ← 模拟比赛 ← 赛季进行 ← 执行决策 ← 经理决策周期
  ↓
赛季结束 → 结算 → 新赛季
```

---

## 二、核心系统设计

### 2.1 数据层设计

#### 2.1.1 实体关系
```
League (联赛) ───< Season (赛季) ───< Match (比赛)
    │
    └──< Club (俱乐部) ───< Squad (阵容)
            │               │
            │               └──< Player (球员)
            │
            ├──< Finance (财政)
            ├──< YouthAcademy (青训)
            └──< TransferRecord (转会记录)
```

#### 2.1.2 核心数据表

**球员数据 (players)**
- id, name, age, nationality, position
- attributes: 速度、射门、传球、防守、体能、技术
- potential, current_ability
- contract_until, salary, market_value
- club_id

**俱乐部数据 (clubs)**
- id, name, country, city
- reputation, stadium_capacity
- balance (资金), wage_budget, transfer_budget
- league_id

**联赛数据 (leagues)**
- id, name, country, tier
- format: 参赛球队数、升降级规则
- schedule_rules

**比赛数据 (matches)**
- id, season_id, matchday
- home_club_id, away_club_id
- home_score, away_score
- events: 进球、红黄牌、换人

**转会数据 (transfers)**
- id, player_id, from_club_id, to_club_id
- fee, wage, contract_length
- status: pending/accepted/rejected/completed

### 2.2 比赛模拟器

#### 2.2.1 模拟算法
基于球员能力值和战术的加权概率系统：

```python
def simulate_match(home_squad, away_squad, tactics):
    # 1. 计算各队实力指数
    home_strength = calculate_team_strength(home_squad, tactics['home'])
    away_strength = calculate_team_strength(away_squad, tactics['away'])
    
    # 2. 主场优势加成
    home_strength *= 1.1
    
    # 3. 模拟90分钟，每分钟判断是否有进球事件
    for minute in range(1, 91):
        if random() < probability_of_goal(home_strength, away_strength):
            scorer = select_scorer(home_squad if attacking_team == 'home' else away_squad)
            record_goal(minute, scorer)
    
    # 4. 返回比赛结果和事件列表
    return MatchResult(home_goals, away_goals, events)
```

#### 2.2.2 实力计算因素
- 首发11人平均能力值 (40%)
- 阵容平衡度 (位置覆盖) (15%)
- 战术匹配度 (20%)
- 球员体能状态 (15%)
- 士气/连胜连败影响 (10%)

### 2.3 财政系统

#### 2.3.1 收入来源
- 比赛日收入: 门票 × 上座率
- 转播分成: 根据联赛排名
- 商业赞助: 基于球队声望
- 球员出售
- 欧冠/欧联奖金

#### 2.3.2 支出项目
- 球员工资
- 转会支出
- 青训投入
- 球场维护
- 球探网络

#### 2.3.3 财政公平原则 (FFP)
- 三年内亏损不得超过指定限额
- 违规惩罚: 罚款、欧战禁赛、转会限制

### 2.4 转会系统

#### 2.4.1 转会窗口
- **夏窗**: 7月1日 - 8月31日
- **冬窗**: 1月1日 - 1月31日

#### 2.4.2 转会流程
```
1. 发起报价 (Buying Club)
   ↓
2. 收到报价 (Selling Club Manager通知)
   ↓
3. 接受/拒绝/还价
   ↓
4. 开始个人条款谈判 (Buying Club)
   ↓
5. 球员同意/拒绝
   ↓
6. 完成转会 (系统执行)
```

#### 2.4.3 合同谈判
- 工资要求 (基于球员能力和声望)
- 合同年限 (1-5年)
- 签字费、忠诚奖金
- 解约金条款
- 出场时间承诺

### 2.5 青训系统

#### 2.5.1 青训机制
- 每赛季青年队生成新球员 (16-18岁)
- 青训质量取决于: 青训投入、球探网络、历史声望
- 潜力新星随机生成

#### 2.5.2 球员成长
- 比赛出场获得经验
- 年龄与成长曲线
- 训练重点分配
- 受伤影响发展

---

## 三、AI/LLM 接口设计

### 3.1 LLM 角色定义

#### 3.1.1 系统提示词模板
```
你是一位经验丰富的足球经理，目前执教 {club_name}。

【俱乐部信息】
- 联赛: {league_name}
- 声望: {reputation}
- 财政状况: {finance_status}
- 本赛季目标: {season_objective}

【球队阵容】
{ squad_list }

【老板指令】
{ owner_directives }

【当前情况】
- 联赛排名: {league_position}
- 最近5场: {recent_form}
- 伤病情况: {injuries}
- 下一场对手: {next_opponent}

请根据以上信息，做出你的管理决策。你需要：
1. 回复老板的指令
2. 提出阵容/战术建议
3. 说明转会计划
```

### 3.2 LLM 交互接口

#### 3.2.1 决策触发点
- 每轮比赛前 (战术安排)
- 转会窗口期间 (买卖决策)
- 收到报价时 (接受/拒绝)
- 赛季关键节点 (目标评估)
- 老板发送指令时

#### 3.2.2 决策输出格式
```json
{
  "type": "decision_type",
  "reasoning": "决策理由",
  "actions": [
    {
      "action": "具体行动",
      "target": "目标对象",
      "parameters": {}
    }
  ]
}
```

### 3.3 多人协作机制

#### 3.3.1 游戏服务器架构
```
GameServer
├── GameRoom (房间)
│   ├── GameState (游戏状态)
│   ├── MatchScheduler (赛程)
│   └── PlayerConnections (玩家连接)
└── AIManager (AI管理)
    └── LLMClients (各球队LLM连接)
```

#### 3.3.2 通信协议
- WebSocket 实时通信
- 游戏事件广播
- 私密指令通道

---

## 四、游戏规则

### 4.1 五大联赛规则

#### 4.1.1 英超
- 20支球队，双循环
- 升3降3
- 没有冬歇期

#### 4.1.2 西甲
- 20支球队
- 升3降3
- 同分先看相互战绩

#### 4.1.3 德甲
- 18支球队
- 升2降2 + 附加赛

#### 4.1.4 意甲
- 20支球队
- 升3降3
- 同分加赛

#### 4.1.5 法甲
- 18支球队
- 升2降2 + 附加赛

### 4.2 欧冠规则
- 小组赛: 32队分8组
- 淘汰赛: 主客场两回合
- 决赛: 中立场地单场

### 4.3 赛季时间表
```
7月-8月: 季前赛、夏窗转会
8月: 联赛开始
12月-1月: 冬歇期(部分联赛)、冬窗转会
5月: 联赛结束
5月底: 欧冠决赛
```

---

## 五、CLI 界面设计

### 5.1 主界面布局
```
┌─────────────────────────────────────────────────────────┐
│  足球经理模拟器 v1.0                    [房间: ABC123]   │
├──────────────────┬──────────────────────────────────────┤
│                  │                                       │
│  菜单            │            主显示区                    │
│  ────            │            ────────                   │
│  [D] 仪表板      │                                       │
│  [S] 球队        │  当前日期: 2024-08-15                │
│  [M] 比赛        │  下一场: vs 曼城 (3天后)              │
│  [T] 转会        │                                       │
│  [F] 财政        │  最近战绩: WWDLW                     │
│  [L] 联赛        │  排名: 5/20                           │
│  [Y] 青训        │                                       │
│  [I] 指令经理    │                                       │
│  ────            │                                       │
│  [Q] 退出        │                                       │
│                  │                                       │
├──────────────────┴──────────────────────────────────────┤
│  系统消息: 收到来自利物浦的转会报价...                    │
└─────────────────────────────────────────────────────────┘
```

### 5.2 关键命令
- `watch` - 观看比赛直播模拟
- `instruct "消息"` - 向经理发送指令
- `approve <transfer_id>` - 批准转会
- `reject <transfer_id>` - 拒绝转会
- `save` - 保存游戏
- `pause` - 暂停游戏

---

## 六、技术栈

### 6.1 后端
- **语言**: Python 3.11+
- **框架**: FastAPI (WebSocket支持)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **ORM**: SQLAlchemy
- **任务调度**: APScheduler

### 6.2 CLI客户端
- **框架**: Rich (终端UI)
- **HTTP**: httpx
- **WebSocket**: websockets

### 6.3 数据获取
- **球员数据**: Football-Data.org API / Transfermarkt
- **比赛数据**: API-Football

---

## 七、风险与应对

### 7.1 技术风险
| 风险 | 应对 |
|-----|------|
| 数据获取受限 | 设计本地数据生成方案 |
| LLM响应延迟 | 异步处理 + 决策缓存 |
| 并发性能问题 | 乐观锁 + 事件队列 |

### 7.2 游戏平衡
- 定期调整经济参数
- AI难度分级
- 手动干预接口

---

## 八、未来扩展

1. **可视化**: Web界面版本
2. **更多联赛**: 中超、MLS、J联赛等
3. **历史模式**: 重演经典赛季
4. **卡牌系统**: 特殊事件卡
5. **成就系统**: 长期目标追踪
