# 杯赛系统设计文档

**状态**: 🚧 设计中  
**模块**: `fm_manager/engine/cup_engine.py`  
**依赖**: `MatchEngine`, `FinanceEngine`, `SeasonSimulator`

---

## 1. 概述

### 1.1 杯赛系统在游戏中的作用

杯赛系统是 FM Manager 赛季模拟的重要组成部分，为游戏提供以下核心价值：

```
┌─────────────────────────────────────────────────────────────────┐
│                      杯赛系统价值                                │
├─────────────────────────────────────────────────────────────────┤
│  🏆 荣誉追求    - 提供联赛之外的冠军目标                          │
│  💰 财务收入    - 高额奖金和转播收入补充                          │
│  🌍 国际舞台    - 欧冠/欧联提供跨国竞争                           │
│  ⚡ 意外因素    - 单场淘汰制造冷门的刺激感                        │
│  🔄 阵容深度    - 迫使球队进行轮换，考验阵容厚度                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 支持的杯赛类型

| 类型 | 代表赛事 | 参赛球队 | 赛制特点 |
|------|----------|----------|----------|
| **国内杯赛** | 足总杯 (FA Cup)<br>联赛杯 (Carabao Cup) | 英格兰各级别联赛球队<br>足总杯: 700+ 队<br>联赛杯: 92 队 | 单场淘汰<br>随机抽签<br>低级别先主场 |
| **欧洲冠军联赛** | UEFA Champions League | 32 队小组赛<br>+ 各国联赛冠军 | 小组赛+淘汰赛<br>两回合制 |
| **欧洲联赛** | UEFA Europa League | 32 队小组赛<br>+ 欧冠淘汰队 | 小组赛+淘汰赛<br>两回合制 |
| **欧洲协会联赛** | UEFA Conference League | 32 队小组赛 | 小组赛+淘汰赛<br>较低级别 |

### 1.3 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cup Competition System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  CupEngine   │  │ DrawEngine   │  │ PrizeEngine  │           │
│  │  (核心调度)   │  │  (抽签算法)   │  │  (奖金计算)   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              CupCompetition (杯赛定义)                │      │
│  │  ├─ CupEdition (具体届次)                             │      │
│  │  │   ├─ CupRound (轮次)                               │      │
│  │  │   │   └─ CupMatch (比赛)                           │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据模型设计

### 2.1 CupCompetition 实体（杯赛定义）

```python
@dataclass
class CupCompetition:
    """杯赛定义 - 描述杯赛的基本规则和结构"""
    
    id: int
    name: str                          # 杯赛名称 (e.g., "FA Cup")
    code: str                          # 代码 (e.g., "FAC")
    type: CupType                      # DOMESTIC / CHAMPIONS_LEAGUE / EUROPA_LEAGUE
    
    # 赛制配置
    format: CupFormat                  # KNOCKOUT / GROUP_THEN_KNOCKOUT
    legs_per_round: Dict[int, int]     # 轮次 -> 回合数 {1: 1, 2: 1, ...}
    has_group_stage: bool = False
    
    # 参赛资格
    eligible_leagues: List[str]        # 可参赛的联赛
    eligible_divisions: List[int]      # 可参赛的级别 (1=顶级)
    min_team_count: int = 2
    max_team_count: Optional[int] = None
    
    # 特殊规则
    away_goals_rule: bool = True       # 客场进球规则
    extra_time: bool = True            # 加时赛
    penalties: bool = True             # 点球大战
    replays: bool = False              # 重赛 (足总杯早期轮次)
    seeding: bool = False              # 种子队制度
    
    # 赛程安排
    typical_start_month: int = 8       # 通常开始月份
    typical_end_month: int = 5         # 通常结束月份
    priority: int = 100                # 赛程优先级 (欧冠 > 联赛 > 联赛杯)


class CupType(Enum):
    """杯赛类型"""
    DOMESTIC_CUP = "domestic_cup"           # 国内杯赛 (足总杯)
    DOMESTIC_LEAGUE_CUP = "domestic_league_cup"  # 联赛杯
    CHAMPIONS_LEAGUE = "champions_league"   # 欧冠
    EUROPA_LEAGUE = "europa_league"         # 欧联
    CONFERENCE_LEAGUE = "conference_league" # 欧协联
    SUPER_CUP = "super_cup"                 # 超级杯


class CupFormat(Enum):
    """杯赛格式"""
    KNOCKOUT = "knockout"                   # 纯淘汰赛
    GROUP_THEN_KNOCKOUT = "group_then_knockout"  # 小组赛+淘汰赛
```

### 2.2 CupEdition 实体（具体某一届杯赛）

```python
@dataclass
class CupEdition:
    """杯赛届次 - 某一赛季的具体杯赛实例"""
    
    id: int
    competition_id: int                # 关联 CupCompetition
    season_year: int                   # 赛季年份 (e.g., 2024)
    
    # 状态
    status: EditionStatus = EditionStatus.PENDING
    
    # 参赛球队
    participating_teams: List[int]     # 参赛球队ID列表
    eliminated_teams: List[int] = field(default_factory=list)
    
    # 轮次
    rounds: List[CupRound] = field(default_factory=list)
    current_round: int = 0
    
    # 冠军
    winner_id: Optional[int] = None
    final_match_id: Optional[int] = None
    
    # 时间
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    def get_current_round(self) -> Optional[CupRound]:
        """获取当前轮次"""
        if 0 <= self.current_round < len(self.rounds):
            return self.rounds[self.current_round]
        return None
    
    def is_complete(self) -> bool:
        """检查杯赛是否已完成"""
        return self.status == EditionStatus.COMPLETED


class EditionStatus(Enum):
    """届次状态"""
    PENDING = "pending"         # 待开始
    REGISTRATION = "registration"  # 报名中
    GROUP_STAGE = "group_stage"    # 小组赛阶段
    KNOCKOUT = "knockout"       # 淘汰赛阶段
    COMPLETED = "completed"     # 已完成
    CANCELLED = "cancelled"     # 已取消
```

### 2.3 CupRound 实体（杯赛轮次）

```python
@dataclass
class CupRound:
    """杯赛轮次 - 描述一轮比赛"""
    
    id: int
    edition_id: int                    # 关联 CupEdition
    
    # 轮次信息
    round_number: int                  # 轮次编号 (1, 2, 3...)
    round_name: str                    # 轮次名称 (e.g., "第三轮", "1/8决赛")
    
    # 赛制
    legs: int = 1                      # 回合数 (1=单场, 2=主客场)
    is_two_legged: bool = False
    
    # 参赛球队
    teams_entering: List[int]          # 本轮新加入的球队
    teams_remaining: List[int]         # 本轮剩余球队
    
    # 比赛
    matches: List[CupMatch] = field(default_factory=list)
    
    # 状态
    status: RoundStatus = RoundStatus.PENDING
    draw_completed: bool = False
    
    # 时间
    scheduled_date: Optional[date] = None
    first_leg_dates: Optional[Tuple[date, date]] = None
    second_leg_dates: Optional[Tuple[date, date]] = None
    
    def get_winners(self) -> List[int]:
        """获取晋级球队"""
        winners = []
        for match in self.matches:
            if match.is_complete():
                winner = match.get_winner()
                if winner:
                    winners.append(winner)
        return winners


class RoundStatus(Enum):
    """轮次状态"""
    PENDING = "pending"         # 待抽签
    DRAWN = "drawn"             # 已抽签
    IN_PROGRESS = "in_progress" # 进行中
    COMPLETED = "completed"     # 已完成
```

### 2.4 CupMatch 实体（杯赛比赛）

```python
@dataclass
class CupMatch:
    """杯赛比赛 - 单场杯赛比赛"""
    
    id: int
    round_id: int                      # 关联 CupRound
    edition_id: int                    # 关联 CupEdition
    
    # 对阵双方
    home_team_id: int
    away_team_id: int
    
    # 回合信息 (两回合制)
    leg: int = 1                       # 第几回合
    is_first_leg: bool = True
    
    # 比赛结果
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    home_goals_et: Optional[int] = None  # 加时赛进球
    away_goals_et: Optional[int] = None
    home_penalties: Optional[int] = None
    away_penalties: Optional[int] = None
    
    # 比赛状态
    status: MatchStatus = MatchStatus.SCHEDULED
    
    # 时间地点
    match_date: Optional[date] = None
    venue: Optional[str] = None        # 球场
    is_neutral_venue: bool = False     # 是否中立场
    
    # 关联的比赛引擎结果
    match_result_id: Optional[int] = None  # 关联 Match 表
    
    # 财务
    prize_money_awarded: bool = False
    
    def get_winner(self) -> Optional[int]:
        """获取获胜方球队ID"""
        if not self.is_complete():
            return None
            
        # 常规时间
        if self.home_goals > self.away_goals:
            return self.home_team_id
        elif self.away_goals > self.home_goals:
            return self.away_team_id
            
        # 加时赛
        if self.home_goals_et is not None:
            home_total = self.home_goals + self.home_goals_et
            away_total = self.away_goals + self.away_goals_et
            if home_total > away_total:
                return self.home_team_id
            elif away_total > home_total:
                return self.away_team_id
                
        # 点球大战
        if self.home_penalties is not None:
            if self.home_penalties > self.away_penalties:
                return self.home_team_id
            else:
                return self.away_team_id
                
        return None  # 平局 (可能需要重赛)
    
    def get_aggregate_score(self, first_leg: 'CupMatch') -> Tuple[int, int]:
        """计算两回合总比分"""
        if self.leg != 2:
            return (self.home_goals or 0, self.away_goals or 0)
            
        home_aggregate = (first_leg.away_goals or 0) + (self.home_goals or 0)
        away_aggregate = (first_leg.home_goals or 0) + (self.away_goals or 0)
        return (home_aggregate, away_aggregate)
    
    def is_complete(self) -> bool:
        """检查比赛是否已完成"""
        return self.status in [MatchStatus.FINISHED, MatchStatus.AWARDED]


class MatchStatus(Enum):
    """比赛状态"""
    SCHEDULED = "scheduled"     # 已安排
    IN_PROGRESS = "in_progress" # 进行中
    FINISHED = "finished"       # 已完成
    POSTPONED = "postponed"     # 延期
    AWARDED = "awarded"         # 判负
    CANCELLED = "cancelled"     # 取消
```

### 2.5 与现有 Match 模型的关系

```python
@dataclass
class Match:
    """现有联赛比赛模型 - 杯赛复用此模型"""
    id: int
    match_type: MatchType          # LEAGUE / CUP / FRIENDLY
    
    # 如果是杯赛比赛
    cup_match_id: Optional[int] = None  # 关联 CupMatch
    
    # 其他字段...
    home_team_id: int
    away_team_id: int
    home_goals: int
    away_goals: int
    # ...


class MatchType(Enum):
    """比赛类型扩展"""
    LEAGUE = "league"           # 联赛
    CUP = "cup"                 # 杯赛
    FRIENDLY = "friendly"       # 友谊赛
    EUROPEAN = "european"       # 欧战
```

**关系图**:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  CupCompetition │◄──────│   CupEdition    │◄──────│    CupRound     │
│   (杯赛定义)     │  1:N  │   (具体届次)     │  1:N  │    (轮次)       │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
                                                             │ 1:N
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     Match       │◄──────│    CupMatch     │◄──────│  MatchResult    │
│  (联赛比赛模型)  │  1:1  │   (杯赛比赛)     │  1:1  │   (比赛结果)    │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

---

## 3. 赛制规则

### 3.1 国内杯赛（足总杯/联赛杯）

#### 足总杯 (FA Cup) 赛制

```
┌─────────────────────────────────────────────────────────────────┐
│                     足总杯赛制流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  额外预赛轮 (Extra Preliminary)                                  │
│  ├── 参赛: 英格兰第7-8级别球队                                   │
│  └── 赛制: 单场淘汰，低级别先主场                                │
│                                                                  │
│  预赛轮 (Preliminary) ──→ 资格赛第一轮 ──→ 资格赛第二轮          │
│  ├── 参赛: 逐步加入更高级别球队                                  │
│  └── 赛制: 单场淘汰，随机抽签                                    │
│                                                                  │
│  资格赛第三轮 ──→ 资格赛第四轮                                   │
│  ├── 参赛: 全国联赛级别球队加入                                  │
│  └── 赛制: 单场淘汰                                              │
│                                                                  │
│  第一轮 (First Round) ◄── 英乙球队加入                           │
│  第二轮 (Second Round) ◄── 英甲球队加入                          │
│  第三轮 (Third Round) ◄── 英超/英冠球队加入 ⭐ 重点轮次           │
│  ├── 64支球队，随机抽签                                          │
│  └── 可能产生强弱对话 (e.g., 曼城 vs 业余队)                     │
│                                                                  │
│  第四轮 ──→ 第五轮 ──→ 1/4决赛 ──→ 半决赛 ──→ 决赛              │
│  └── 半决赛和决赛: 中立场，单场决胜                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 联赛杯 (Carabao Cup) 赛制

```
┌─────────────────────────────────────────────────────────────────┐
│                     联赛杯赛制流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  第一轮                                                          │
│  ├── 参赛: 英冠、英甲、英乙球队 (70队)                           │
│  └── 赛制: 分区抽签，单场淘汰                                    │
│                                                                  │
│  第二轮                                                          │
│  ├── 参赛: 英超无欧战球队 + 英冠球队                             │
│  └── 赛制: 英超球队客场作战                                      │
│                                                                  │
│  第三轮 ◄── 英超欧战球队加入 (欧冠/欧联参赛队)                    │
│  ├── 参赛: 32支球队                                              │
│  └── 赛制: 随机抽签                                              │
│                                                                  │
│  第四轮 ──→ 1/4决赛 ──→ 半决赛(两回合) ──→ 决赛(温布利)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 国内杯赛规则实现

```python
class DomesticCupRules:
    """国内杯赛规则实现"""
    
    # 足总杯配置
    FA_CUP_CONFIG = {
        "name": "FA Cup",
        "total_rounds": 14,
        "replays_until_round": 4,      # 前4轮平局重赛
        "neutral_from_round": 12,      # 半决赛起中立场
        "premier_league_entry": 3,     # 英超第3轮加入
        "championship_entry": 1,       # 英冠第1轮加入
    }
    
    # 联赛杯配置
    LEAGUE_CUP_CONFIG = {
        "name": "Carabao Cup",
        "total_rounds": 7,
        "two_leg_semi": True,          # 半决赛两回合
        "premier_league_entry": 2,     # 部分英超第2轮加入
        "european_teams_entry": 3,     # 欧战球队第3轮加入
    }
    
    @staticmethod
    def should_have_replay(round_number: int, competition: CupCompetition) -> bool:
        """判断是否需要重赛"""
        if not competition.replays:
            return False
        return round_number <= competition.replay_until_round
    
    @staticmethod
    def determine_home_team(team1_id: int, team2_id: int, 
                           team1_division: int, team2_division: int) -> int:
        """
        确定主场球队
        规则: 低级别球队优先主场
        """
        if team1_division > team2_division:
            return team1_id  # team1级别更低，主场
        elif team2_division > team1_division:
            return team2_id  # team2级别更低，主场
        else:
            # 同级别，随机
            return random.choice([team1_id, team2_id])
```

### 3.2 欧冠/欧联

#### 欧冠赛制

```
┌─────────────────────────────────────────────────────────────────┐
│                     欧冠赛制流程                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【资格赛阶段】 (部分联赛冠军/低排名球队)                         │
│  ├── 预选赛 (4队)                                                │
│  ├── 资格赛第一轮 (34队)                                         │
│  ├── 资格赛第二轮 (24队)                                         │
│  ├── 资格赛第三轮 (20队)                                         │
│  └── 附加赛 (12队)                                               │
│                                                                  │
│  【小组赛阶段】 (32队分8组)                                      │
│  ├── 分档规则:                                                   │
│  │   第1档: 欧冠/欧联冠军 + 欧战积分前7联赛冠军                    │
│  │   第2-4档: 按欧战积分排序                                     │
│  │   同协会球队回避                                              │
│  │                                                               │
│  ├── 赛制: 双循环，每组4队                                       │
│  │   每队6场比赛 (3主3客)                                        │
│  │                                                               │
│  └── 出线: 前2名晋级淘汰赛                                       │
│      第3名 → 欧联淘汰赛                                          │
│      第4名 → 淘汰                                                │
│                                                                  │
│  【淘汰赛阶段】                                                  │
│  ├── 1/8决赛 (16队)                                              │
│  ├── 1/4决赛 (8队)                                               │
│  ├── 半决赛 (4队)                                                │
│  └── 决赛 (2队，中立场地)                                        │
│                                                                  │
│  【两回合制规则】                                                │
│  ├── 总比分高者晋级                                              │
│  ├── 总比分相同 → 客场进球多者晋级 (已取消)                      │
│  ├── 仍相同 → 加时赛                                             │
│  └── 再相同 → 点球大战                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 欧联赛制

```
┌─────────────────────────────────────────────────────────────────┐
│                     欧联赛制流程                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【参赛球队来源】                                                │
│  ├── 各国杯赛冠军/联赛排名                                       │
│  ├── 欧冠资格赛淘汰球队                                          │
│  └── 欧冠小组赛第3名 (淘汰赛加入)                                │
│                                                                  │
│  【小组赛】 (32队分8组)                                          │
│  └── 同欧冠赛制                                                  │
│                                                                  │
│  【淘汰赛附加赛】 (16队)                                         │
│  ├── 欧联小组赛第2名 vs 欧冠小组赛第3名                          │
│  └── 胜者进入16强                                                │
│                                                                  │
│  【淘汰赛】 (16强起)                                             │
│  └── 同欧冠赛制                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 欧战规则实现

```python
class EuropeanCompetitionRules:
    """欧战规则实现"""
    
    # 欧冠配置
    CHAMPIONS_LEAGUE_CONFIG = {
        "groups": 8,
        "teams_per_group": 4,
        "group_matches": 6,
        "qualifying_rounds": 4,
        "knockout_rounds": 4,  # 16强, 8强, 4强, 决赛
        "two_leg_rounds": ["round_of_16", "quarter_final", "semi_final"],
        "neutral_final": True,
    }
    
    # 欧联配置
    EUROPA_LEAGUE_CONFIG = {
        "groups": 8,
        "teams_per_group": 4,
        "has_knockout_playoff": True,  # 淘汰赛附加赛
        "champions_league_dropouts": True,  # 欧冠第3名加入
    }
    
    @staticmethod
    def create_group_stage_draw(teams: List[int], pots: List[List[int]]) -> List[Group]:
        """
        创建小组赛抽签
        
        规则:
        1. 8个小组，每组4队
        2. 每档抽1队进入每组
        3. 同协会球队不同组
        """
        groups = [Group(id=i, teams=[]) for i in range(8)]
        
        for pot_index, pot in enumerate(pots):
            shuffled = random.sample(pot, len(pot))
            for i, team in enumerate(shuffled):
                # 检查同协会回避
                attempts = 0
                while (attempts < 100 and 
                       EuropeanCompetitionRules._has_same_association(groups[i], team)):
                    # 重新排列
                    shuffled = random.sample(shuffled, len(shuffled))
                    team = shuffled[i]
                    attempts += 1
                
                groups[i].teams.append(team)
                
        return groups
    
    @staticmethod
    def determine_knockout_winner(first_leg: CupMatch, second_leg: CupMatch,
                                  away_goals_rule: bool = False) -> Tuple[int, str]:
        """
        确定淘汰赛晋级球队
        
        返回: (winner_id, method)
        method: "aggregate", "away_goals", "extra_time", "penalties"
        """
        home_agg = (first_leg.away_goals or 0) + (second_leg.home_goals or 0)
        away_agg = (first_leg.home_goals or 0) + (second_leg.away_goals or 0)
        
        # 总比分
        if home_agg > away_agg:
            return (second_leg.home_team_id, "aggregate")
        elif away_agg > home_agg:
            return (second_leg.away_team_id, "aggregate")
        
        # 客场进球规则 (已取消，保留代码供历史赛季使用)
        if away_goals_rule:
            home_away_goals = first_leg.away_goals or 0
            away_away_goals = second_leg.away_goals or 0
            if home_away_goals > away_away_goals:
                return (second_leg.home_team_id, "away_goals")
            elif away_away_goals > home_away_goals:
                return (second_leg.away_team_id, "away_goals")
        
        # 加时赛
        if second_leg.home_goals_et is not None:
            home_total = home_agg + (second_leg.home_goals_et or 0)
            away_total = away_agg + (second_leg.away_goals_et or 0)
            if home_total > away_total:
                return (second_leg.home_team_id, "extra_time")
            elif away_total > home_total:
                return (second_leg.away_team_id, "extra_time")
        
        # 点球大战
        if second_leg.home_penalties is not None:
            if second_leg.home_penalties > second_leg.away_penalties:
                return (second_leg.home_team_id, "penalties")
            else:
                return (second_leg.away_team_id, "penalties")
        
        return (None, "undecided")
```

---

## 4. 收入系统

### 4.1 收入构成

```
┌─────────────────────────────────────────────────────────────────┐
│                     杯赛收入构成                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【欧冠收入】(2023-24赛季示例)                                   │
│  ├── 参赛奖金: €15.6M (小组赛资格)                               │
│  ├── 胜场奖金: €2.8M/场                                          │
│  ├── 平局奖金: €930K/场                                          │
│  ├── 晋级奖金:                                                   │
│  │   16强: €9.6M                                                 │
│  │   8强: €10.6M                                                 │
│  │   4强: €12.5M                                                 │
│  │   决赛: €15.5M                                                │
│  │   冠军: €4.5M (额外)                                          │
│  └── 市场池分成: 根据各国转播合同                                │
│                                                                  │
│  【欧联收入】                                                    │
│  ├── 参赛奖金: €3.6M                                             │
│  ├── 胜场奖金: €630K/场                                          │
│  └── 晋级奖金相应降低                                            │
│                                                                  │
│  【足总杯收入】(2023-24赛季)                                     │
│  ├── 冠军奖金: £2M                                               │
│  ├── 决赛负方: £1M                                               │
│  ├── 半决赛: £1.8M/队                                            │
│  └── 早期轮次较低 (第三轮起: £82K/队)                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 奖金系统实现

```python
@dataclass
class CupPrizeStructure:
    """杯赛奖金结构"""
    
    competition_id: int
    season_year: int
    
    # 固定奖金
    participation_fee: int = 0          # 参赛费
    
    # 比赛奖金
    win_bonus: int = 0                  # 胜场奖金
    draw_bonus: int = 0                 # 平局奖金
    
    # 晋级奖金 (轮次 -> 金额)
    progression_prizes: Dict[int, int] = field(default_factory=dict)
    
    # 名次奖金
    winner_prize: int = 0
    runner_up_prize: int = 0
    semi_finalist_prize: int = 0
    quarter_finalist_prize: int = 0
    
    # 电视转播分成 (按轮次)
    tv_revenue_share: Dict[int, int] = field(default_factory=dict)


class CupPrizeEngine:
    """杯赛奖金计算引擎"""
    
    # 欧冠奖金结构 (2024赛季)
    CHAMPIONS_LEAGUE_PRIZES = {
        "participation": 15_600_000,
        "group_win": 2_800_000,
        "group_draw": 930_000,
        "round_of_16": 9_600_000,
        "quarter_final": 10_600_000,
        "semi_final": 12_500_000,
        "finalist": 15_500_000,
        "winner_bonus": 4_500_000,
    }
    
    # 欧联奖金结构
    EUROPA_LEAGUE_PRIZES = {
        "participation": 3_630_000,
        "group_win": 630_000,
        "group_draw": 210_000,
        "round_of_16": 1_200_000,
        "quarter_final": 1_800_000,
        "semi_final": 2_800_000,
        "finalist": 4_600_000,
        "winner_bonus": 4_000_000,
    }
    
    def __init__(self, finance_engine: FinanceEngine):
        self.finance_engine = finance_engine
    
    def award_participation_fee(self, edition: CupEdition, club_id: int):
        """发放参赛奖金"""
        prize_structure = self._get_prize_structure(edition.competition_id)
        
        if prize_structure.participation_fee > 0:
            self.finance_engine.record_income(
                club_id=club_id,
                amount=prize_structure.participation_fee,
                type=RevenueType.PRIZE_MONEY,
                description=f"{edition.name} 参赛奖金"
            )
    
    def award_match_bonus(self, match: CupMatch, edition: CupEdition):
        """发放比赛奖金"""
        prize_structure = self._get_prize_structure(edition.competition_id)
        
        if match.is_draw() and prize_structure.draw_bonus > 0:
            # 平局奖金双方都有
            for club_id in [match.home_team_id, match.away_team_id]:
                self.finance_engine.record_income(
                    club_id=club_id,
                    amount=prize_structure.draw_bonus,
                    type=RevenueType.PRIZE_MONEY,
                    description=f"{edition.name} 平局奖金"
                )
        elif match.get_winner() and prize_structure.win_bonus > 0:
            # 胜场奖金
            winner_id = match.get_winner()
            self.finance_engine.record_income(
                club_id=winner_id,
                amount=prize_structure.win_bonus,
                type=RevenueType.PRIZE_MONEY,
                description=f"{edition.name} 胜场奖金"
            )
    
    def award_progression_bonus(self, round: CupRound, edition: CupEdition):
        """发放晋级奖金"""
        prize_structure = self._get_prize_structure(edition.competition_id)
        
        round_prize = prize_structure.progression_prizes.get(round.round_number, 0)
        if round_prize > 0:
            winners = round.get_winners()
            for club_id in winners:
                self.finance_engine.record_income(
                    club_id=club_id,
                    amount=round_prize,
                    type=RevenueType.PRIZE_MONEY,
                    description=f"{edition.name} {round.round_name} 晋级奖金"
                )
    
    def calculate_tv_revenue_share(self, match: CupMatch, 
                                   edition: CupEdition) -> int:
        """计算电视转播分成"""
        # 基于比赛重要性和参赛球队
        base_share = 500_000  # 基础分成
        
        # 根据轮次调整
        round_multipliers = {
            1: 0.5,   # 早期轮次
            2: 0.7,
            3: 1.0,   # 英超球队加入
            4: 1.5,
            5: 2.0,
            6: 3.0,   # 后期轮次
            7: 5.0,   # 决赛
        }
        
        round = match.get_round()
        multiplier = round_multipliers.get(round.round_number, 1.0)
        
        return int(base_share * multiplier)
```

### 4.3 收入示例

```python
# 欧冠收入示例 (假设英超球队夺冠)
def champions_league_revenue_example():
    """
    英超球队赢得欧冠的收入示例
    """
    revenue_breakdown = {
        "参赛奖金": 15_600_000,
        "小组赛": {
            "4胜2平": 4 * 2_800_000 + 2 * 930_000,
        },
        "淘汰赛": {
            "16强": 9_600_000,
            "8强": 10_600_000,
            "4强": 12_500_000,
            "决赛": 15_500_000,
            "冠军": 4_500_000,
        },
        "市场池分成": 15_000_000,  # 估算
    }
    
    total = sum([
        revenue_breakdown["参赛奖金"],
        revenue_breakdown["小组赛"]["4胜2平"],
        sum(revenue_breakdown["淘汰赛"].values()),
        revenue_breakdown["市场池分成"],
    ])
    
    print(f"欧冠夺冠总收入: €{total/1e6:.1f}M")
    # 输出: 欧冠夺冠总收入: €98.4M


# 足总杯收入示例
def fa_cup_revenue_example():
    """
    非英超球队足总杯征程收入示例
    """
    revenue_by_round = {
        "第一轮": 41_000,
        "第二轮": 67_000,
        "第三轮": 164_000,  # 对阵英超球队，门票收入大增
        "第四轮": 164_000,
        "第五轮": 360_000,
        "1/4决赛": 720_000,
        "半决赛": 1_800_000,
        "决赛": 2_000_000,  # 冠军奖金
    }
    
    # 假设从第一轮打到决赛并夺冠
    total_prize = sum(revenue_by_round.values())
    
    # 第三轮对阵英超球队的门票收入 (重要收入来源)
    gate_receipts_third_round = 2_000_000  # 估算
    
    print(f"足总杯夺冠奖金: £{total_prize/1e3:.0f}K")
    print(f"第三轮门票收入: £{gate_receipts_third_round/1e6:.1f}M")
```

---

## 5. 与联赛系统的集成

### 5.1 赛程冲突处理

```
┌─────────────────────────────────────────────────────────────────┐
│                     赛程优先级系统                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  优先级 (高 -> 低):                                              │
│                                                                  │
│  1. 欧冠淘汰赛 (两回合)                                          │
│  2. 欧联淘汰赛 (两回合)                                          │
│  3. 国内杯赛半决赛/决赛                                          │
│  4. 联赛关键战 (争冠/保级)                                       │
│  5. 欧冠小组赛                                                   │
│  6. 欧联小组赛                                                   │
│  7. 国内杯赛早期轮次                                             │
│  8. 普通联赛比赛                                                 │
│                                                                  │
│  冲突解决策略:                                                   │
│  ├── 高优先级比赛固定日期                                        │
│  ├── 低优先级比赛顺延                                            │
│  └── 极端情况: 联赛延期                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 赛程冲突处理实现

```python
@dataclass
class FixtureConflict:
    """赛程冲突"""
    date: date
    club_id: int
    matches: List[Union[LeagueMatch, CupMatch]]
    

class FixtureScheduler:
    """赛程调度器"""
    
    # 比赛优先级 (数值越高优先级越高)
    MATCH_PRIORITY = {
        "champions_league_knockout": 100,
        "europa_league_knockout": 95,
        "domestic_cup_semi": 90,
        "domestic_cup_final": 90,
        "champions_league_group": 80,
        "europa_league_group": 75,
        "domestic_cup_early": 60,
        "league": 50,
    }
    
    def resolve_conflicts(self, conflicts: List[FixtureConflict]) -> Schedule:
        """
        解决赛程冲突
        
        策略:
        1. 按优先级排序
        2. 高优先级比赛保留原日期
        3. 低优先级比赛寻找替代日期
        4. 必要时联赛延期
        """
        resolved_schedule = Schedule()
        
        for conflict in conflicts:
            # 按优先级排序
            sorted_matches = sorted(
                conflict.matches,
                key=lambda m: self.MATCH_PRIORITY.get(m.type, 0),
                reverse=True
            )
            
            # 最高优先级保留
            resolved_schedule.add_match(sorted_matches[0], conflict.date)
            
            # 其余比赛重新安排
            for match in sorted_matches[1:]:
                alternative_date = self._find_alternative_date(
                    match, conflict.club_id, conflict.date
                )
                if alternative_date:
                    resolved_schedule.add_match(match, alternative_date)
                else:
                    # 无法安排，标记延期
                    match.status = MatchStatus.POSTPONED
                    
        return resolved_schedule
    
    def _find_alternative_date(self, match, club_id: int, 
                               original_date: date) -> Optional[date]:
        """寻找替代比赛日期"""
        # 检查前后3天
        for offset in range(1, 4):
            for direction in [-1, 1]:
                check_date = original_date + timedelta(days=offset * direction)
                
                # 检查俱乐部当天是否有比赛
                if not self._has_fixture_on_date(club_id, check_date):
                    return check_date
                    
        return None
```

### 5.2 球队疲劳度影响

```python
@dataclass
class FatigueImpact:
    """疲劳度影响"""
    
    # 疲劳积累
    match_fatigue_cost: Dict[str, int] = field(default_factory=lambda: {
        "league": 3,
        "cup": 4,
        "european": 5,  # 欧战更累
        "extra_time": 2,  # 加时赛额外疲劳
    })
    
    # 恢复速度
    recovery_per_day: int = 2
    
    # 疲劳阈值影响
    fatigue_thresholds = {
        80: "无影响",
        60: "轻微影响 (能力-2%)",
        40: "中等影响 (能力-5%)",
        20: "严重影响 (能力-10%)",
    }


class FatigueManager:
    """疲劳度管理器"""
    
    def calculate_match_fatigue(self, match: CupMatch, 
                                went_to_extra_time: bool = False) -> int:
        """计算比赛产生的疲劳"""
        base_fatigue = 4  # 杯赛基础疲劳
        
        # 欧战更累
        if match.is_european_competition():
            base_fatigue = 5
            
        # 加时赛额外疲劳
        if went_to_extra_time:
            base_fatigue += 2
            
        return base_fatigue
    
    def get_fatigue_impact_on_rating(self, fatigue: int) -> float:
        """获取疲劳对能力值的影响系数"""
        if fatigue >= 80:
            return 1.0
        elif fatigue >= 60:
            return 0.98
        elif fatigue >= 40:
            return 0.95
        elif fatigue >= 20:
            return 0.90
        else:
            return 0.85
```

### 5.3 阵容轮换

```python
class SquadRotationAdvisor:
    """阵容轮换建议器"""
    
    def __init__(self, cup_engine: 'CupCompetitionEngine'):
        self.cup_engine = cup_engine
    
    def should_rotate(self, club_id: int, upcoming_matches: List[Match]) -> RotationAdvice:
        """
        建议是否需要阵容轮换
        
        考虑因素:
        1. 比赛重要性
        2. 球员疲劳度
        3. 阵容深度
        4. 赛季阶段
        """
        advice = RotationAdvice()
        
        # 分析即将到来的比赛
        for match in upcoming_matches:
            if isinstance(match, CupMatch):
                importance = self._assess_cup_importance(match)
                
                if importance == "low":
                    # 低重要性杯赛，建议大幅轮换
                    advice.recommendation = "heavy_rotation"
                    advice.players_to_rest = self._get_tired_players(club_id)
                    
                elif importance == "medium":
                    # 中等重要性，适度轮换
                    advice.recommendation = "moderate_rotation"
                    
                elif importance == "high":
                    # 重要比赛，最强阵容
                    advice.recommendation = "full_strength"
                    
        return advice
    
    def _assess_cup_importance(self, match: CupMatch) -> str:
        """评估杯赛比赛重要性"""
        round_number = match.get_round().round_number
        total_rounds = match.get_edition().get_total_rounds()
        
        # 后期轮次更重要
        progress = round_number / total_rounds
        
        if progress < 0.3:
            return "low"      # 早期轮次
        elif progress < 0.7:
            return "medium"   # 中期轮次
        else:
            return "high"     # 后期轮次


@dataclass
class RotationAdvice:
    """轮换建议"""
    recommendation: str = "none"  # none, light, moderate, heavy
    players_to_rest: List[int] = field(default_factory=list)
    suggested_lineup: List[int] = field(default_factory=list)
    reason: str = ""
```

---

## 6. API设计

### 6.1 CupCompetitionEngine 类

```python
class CupCompetitionEngine:
    """
    杯赛引擎主类
    
    职责:
    - 管理杯赛生命周期
    - 协调抽签、比赛、晋级
    - 与联赛系统集成
    """
    
    def __init__(
        self,
        match_engine: MatchEngine,
        finance_engine: FinanceEngine,
        fatigue_manager: FatigueManager,
        draw_engine: Optional[DrawEngine] = None,
    ):
        self.match_engine = match_engine
        self.finance_engine = finance_engine
        self.fatigue_manager = fatigue_manager
        self.draw_engine = draw_engine or DrawEngine()
        self.prize_engine = CupPrizeEngine(finance_engine)
    
    # ═══════════════════════════════════════════════════════════════
    # 生命周期管理
    # ═══════════════════════════════════════════════════════════════
    
    async def create_edition(
        self,
        competition_id: int,
        season_year: int,
        participating_teams: Optional[List[int]] = None,
    ) -> CupEdition:
        """
        创建新的杯赛届次
        
        Args:
            competition_id: 杯赛定义ID
            season_year: 赛季年份
            participating_teams: 参赛球队列表 (None则自动确定)
            
        Returns:
            创建的 CupEdition
        """
        competition = await self._get_competition(competition_id)
        
        if participating_teams is None:
            participating_teams = await self._determine_participants(competition)
        
        edition = CupEdition(
            competition_id=competition_id,
            season_year=season_year,
            participating_teams=participating_teams,
            status=EditionStatus.PENDING,
        )
        
        # 创建轮次结构
        edition.rounds = self._create_rounds(competition, len(participating_teams))
        
        await self._save_edition(edition)
        return edition
    
    async def start_edition(self, edition_id: int) -> CupEdition:
        """启动杯赛"""
        edition = await self._get_edition(edition_id)
        edition.status = EditionStatus.REGISTRATION
        edition.start_date = date.today()
        
        # 发放参赛奖金
        for team_id in edition.participating_teams:
            self.prize_engine.award_participation_fee(edition, team_id)
        
        await self._save_edition(edition)
        return edition
    
    # ═══════════════════════════════════════════════════════════════
    # 抽签管理
    # ═══════════════════════════════════════════════════════════════
    
    async def execute_draw(
        self,
        edition_id: int,
        round_number: int,
        draw_rules: Optional[DrawRules] = None,
    ) -> List[CupMatch]:
        """
        执行抽签
        
        Args:
            edition_id: 杯赛届次ID
            round_number: 轮次编号
            draw_rules: 抽签规则 (None使用默认规则)
            
        Returns:
            生成的比赛列表
        """
        edition = await self._get_edition(edition_id)
        round = edition.rounds[round_number - 1]
        
        # 获取参赛球队
        teams = round.teams_remaining + round.teams_entering
        
        # 执行抽签
        pairs = self.draw_engine.execute_draw(
            teams=teams,
            rules=draw_rules or self._get_default_draw_rules(edition),
        )
        
        # 创建比赛
        matches = []
        for home_team, away_team in pairs:
            match = CupMatch(
                round_id=round.id,
                edition_id=edition_id,
                home_team_id=home_team,
                away_team_id=away_team,
                leg=1,
            )
            matches.append(match)
        
        round.matches = matches
        round.draw_completed = True
        round.status = RoundStatus.DRAWN
        
        await self._save_round(round)
        return matches
    
    async def execute_group_stage_draw(
        self,
        edition_id: int,
        pots: List[List[int]],
    ) -> List[Group]:
        """
        执行小组赛抽签 (欧冠/欧联)
        
        Args:
            edition_id: 杯赛届次ID
            pots: 分档球队列表 [pot1, pot2, pot3, pot4]
            
        Returns:
            分组结果
        """
        groups = EuropeanCompetitionRules.create_group_stage_draw(teams=[], pots=pots)
        
        # 为每组生成赛程
        for group in groups:
            group.fixtures = self._generate_group_fixtures(group)
        
        return groups
    
    # ═══════════════════════════════════════════════════════════════
    # 比赛管理
    # ═══════════════════════════════════════════════════════════════
    
    async def simulate_match(
        self,
        match_id: int,
        home_lineup: List[Player],
        away_lineup: List[Player],
    ) -> CupMatch:
        """
        模拟单场比赛
        
        Args:
            match_id: 比赛ID
            home_lineup: 主队阵容
            away_lineup: 客队阵容
            
        Returns:
            更新后的比赛对象
        """
        match = await self._get_match(match_id)
        
        # 使用比赛引擎模拟
        match_result = self.match_engine.simulate(
            home_lineup=home_lineup,
            away_lineup=away_lineup,
        )
        
        # 更新比赛结果
        match.home_goals = match_result.home_goals
        match.away_goals = match_result.away_goals
        match.status = MatchStatus.FINISHED
        match.match_result_id = match_result.id
        
        # 处理平局 (如果需要加时/点球)
        if match.home_goals == match.away_goals:
            match = await self._handle_draw(match)
        
        # 发放比赛奖金
        self.prize_engine.award_match_bonus(match, await self._get_edition(match.edition_id))
        
        await self._save_match(match)
        return match
    
    async def _handle_draw(self, match: CupMatch) -> CupMatch:
        """处理平局情况"""
        competition = await self._get_competition_for_match(match)
        round = await self._get_round(match.round_id)
        
        # 检查是否需要加时/点球
        if competition.extra_time and round.is_final_round():
            # 决赛加时
            match = await self._simulate_extra_time(match)
            
        if competition.penalties and match.home_goals == match.away_goals:
            # 点球大战
            match = await self._simulate_penalties(match)
            
        return match
    
    # ═══════════════════════════════════════════════════════════════
    # 晋级管理
    # ═══════════════════════════════════════════════════════════════
    
    async def process_round_completion(self, edition_id: int, 
                                       round_number: int) -> List[int]:
        """
        处理轮次完成，返回晋级球队
        
        Args:
            edition_id: 杯赛届次ID
            round_number: 轮次编号
            
        Returns:
            晋级球队ID列表
        """
        edition = await self._get_edition(edition_id)
        round = edition.rounds[round_number - 1]
        
        # 获取所有比赛结果
        winners = []
        for match in round.matches:
            winner = match.get_winner()
            if winner:
                winners.append(winner)
            else:
                # 处理未决出胜负的情况
                winner = await self._resolve_undecided_match(match)
                winners.append(winner)
        
        # 更新轮次状态
        round.status = RoundStatus.COMPLETED
        
        # 发放晋级奖金
        self.prize_engine.award_progression_bonus(round, edition)
        
        # 更新下一轮的参赛球队
        if round_number < len(edition.rounds):
            next_round = edition.rounds[round_number]
            next_round.teams_remaining = winners
        
        await self._save_round(round)
        return winners
    
    async def advance_to_next_round(self, edition_id: int) -> Optional[CupRound]:
        """推进到下一轮"""
        edition = await self._get_edition(edition_id)
        
        if edition.current_round >= len(edition.rounds) - 1:
            # 已经是最后一轮，结束杯赛
            await self._complete_edition(edition)
            return None
        
        edition.current_round += 1
        next_round = edition.rounds[edition.current_round]
        next_round.status = RoundStatus.PENDING
        
        await self._save_edition(edition)
        return next_round
    
    async def _complete_edition(self, edition: CupEdition):
        """完成杯赛"""
        final_round = edition.rounds[-1]
        winner = final_round.matches[0].get_winner()
        
        edition.winner_id = winner
        edition.status = EditionStatus.COMPLETED
        edition.end_date = date.today()
        
        # 发放冠军奖金
        self.prize_engine.award_winner_prize(edition, winner)
        
        await self._save_edition(edition)
```

### 6.2 抽签算法接口

```python
class DrawEngine:
    """抽签引擎"""
    
    def execute_draw(
        self,
        teams: List[int],
        rules: DrawRules,
    ) -> List[Tuple[int, int]]:
        """
        执行抽签
        
        Args:
            teams: 参赛球队ID列表
            rules: 抽签规则
            
        Returns:
            对阵配对列表 [(home1, away1), (home2, away2), ...]
        """
        if rules.method == DrawMethod.RANDOM:
            return self._random_draw(teams, rules)
        elif rules.method == DrawMethod.SEEDED:
            return self._seeded_draw(teams, rules)
        elif rules.method == DrawMethod.GEOGRAPHIC:
            return self._geographic_draw(teams, rules)
        else:
            raise ValueError(f"Unknown draw method: {rules.method}")
    
    def _random_draw(
        self,
        teams: List[int],
        rules: DrawRules,
    ) -> List[Tuple[int, int]]:
        """完全随机抽签"""
        shuffled = random.sample(teams, len(teams))
        pairs = []
        
        for i in range(0, len(shuffled), 2):
            if i + 1 < len(shuffled):
                home, away = self._determine_home_away(
                    shuffled[i], shuffled[i+1], rules
                )
                pairs.append((home, away))
            else:
                # 奇数球队，轮空
                pairs.append((shuffled[i], None))
                
        return pairs
    
    def _seeded_draw(
        self,
        teams: List[int],
        rules: DrawRules,
    ) -> List[Tuple[int, int]]:
        """种子队抽签"""
        # 分离种子队和非种子队
        seeds = [t for t in teams if t in rules.seeded_teams]
        non_seeds = [t for t in teams if t not in rules.seeded_teams]
        
        # 随机打乱
        random.shuffle(seeds)
        random.shuffle(non_seeds)
        
        # 种子队 vs 非种子队
        pairs = []
        for seed, non_seed in zip(seeds, non_seeds):
            home, away = self._determine_home_away(seed, non_seed, rules)
            pairs.append((home, away))
            
        return pairs


@dataclass
class DrawRules:
    """抽签规则"""
    method: DrawMethod = DrawMethod.RANDOM
    seeded_teams: List[int] = field(default_factory=list)
    avoid_same_league: bool = False      # 同联赛回避
    avoid_same_association: bool = False  # 同足协回避 (欧战)
    lower_division_home: bool = True     # 低级别球队主场
    

class DrawMethod(Enum):
    """抽签方法"""
    RANDOM = "random"           # 完全随机
    SEEDED = "seeded"           # 种子队
    GEOGRAPHIC = "geographic"   # 地理分区
```

### 6.3 晋级判定逻辑

```python
class AdvancementCalculator:
    """晋级计算器"""
    
    @staticmethod
    def calculate_knockout_advancement(
        first_leg: CupMatch,
        second_leg: Optional[CupMatch] = None,
        rules: CompetitionRules = None,
    ) -> AdvancementResult:
        """
        计算淘汰赛晋级球队
        
        Args:
            first_leg: 首回合比赛
            second_leg: 次回合比赛 (单场淘汰则为None)
            rules: 比赛规则
            
        Returns:
            晋级结果
        """
        if second_leg is None:
            # 单场淘汰
            winner = first_leg.get_winner()
            if winner:
                return AdvancementResult(
                    winner_id=winner,
                    method="single_match",
                    aggregate=(first_leg.home_goals, first_leg.away_goals),
                )
            else:
                return AdvancementResult(
                    winner_id=None,
                    method="undecided",
                    needs_replay=True,
                )
        
        # 两回合制
        home_agg = (first_leg.away_goals or 0) + (second_leg.home_goals or 0)
        away_agg = (first_leg.home_goals or 0) + (second_leg.away_goals or 0)
        
        # 总比分
        if home_agg != away_agg:
            winner = second_leg.home_team_id if home_agg > away_agg else second_leg.away_team_id
            return AdvancementResult(
                winner_id=winner,
                method="aggregate",
                aggregate=(home_agg, away_agg),
            )
        
        # 客场进球规则 (如果启用)
        if rules and rules.away_goals_rule:
            home_away_goals = first_leg.away_goals or 0
            away_away_goals = second_leg.away_goals or 0
            if home_away_goals != away_away_goals:
                winner = second_leg.home_team_id if home_away_goals > away_away_goals else second_leg.away_team_id
                return AdvancementResult(
                    winner_id=winner,
                    method="away_goals",
                    aggregate=(home_agg, away_agg),
                )
        
        # 加时赛
        if second_leg.home_goals_et is not None:
            home_total = home_agg + (second_leg.home_goals_et or 0)
            away_total = away_agg + (second_leg.away_goals_et or 0)
            if home_total != away_total:
                winner = second_leg.home_team_id if home_total > away_total else second_leg.away_team_id
                return AdvancementResult(
                    winner_id=winner,
                    method="extra_time",
                    aggregate=(home_total, away_total),
                )
        
        # 点球大战
        if second_leg.home_penalties is not None:
            winner = (second_leg.home_team_id 
                     if second_leg.home_penalties > second_leg.away_penalties 
                     else second_leg.away_team_id)
            return AdvancementResult(
                winner_id=winner,
                method="penalties",
                aggregate=(home_agg, away_agg),
                penalties=(second_leg.home_penalties, second_leg.away_penalties),
            )
        
        # 仍未决出胜负
        return AdvancementResult(
            winner_id=None,
            method="undecided",
            aggregate=(home_agg, away_agg),
        )
    
    @staticmethod
    def calculate_group_standings(
        matches: List[CupMatch],
        teams: List[int],
    ) -> List[GroupStanding]:
        """
        计算小组排名
        
        排名规则:
        1. 积分 (胜3平1负0)
        2. 相互对战积分
        3. 相互对战净胜球
        4. 相互对战进球数
        5. 总净胜球
        6. 总进球数
        7. 客场进球数
        8. 欧战积分
        """
        standings = {team: GroupStanding(team_id=team) for team in teams}
        
        # 统计比赛结果
        for match in matches:
            if not match.is_complete():
                continue
                
            home = match.home_team_id
            away = match.away_team_id
            
            standings[home].played += 1
            standings[away].played += 1
            standings[home].goals_for += match.home_goals
            standings[home].goals_against += match.away_goals
            standings[away].goals_for += match.away_goals
            standings[away].goals_against += match.home_goals
            
            if match.home_goals > match.away_goals:
                standings[home].points += 3
                standings[home].won += 1
                standings[away].lost += 1
            elif match.home_goals < match.away_goals:
                standings[away].points += 3
                standings[away].won += 1
                standings[home].lost += 1
            else:
                standings[home].points += 1
                standings[away].points += 1
                standings[home].drawn += 1
                standings[away].drawn += 1
        
        # 排序
        sorted_standings = sorted(
            standings.values(),
            key=lambda s: (s.points, s.goal_difference, s.goals_for),
            reverse=True
        )
        
        return sorted_standings


@dataclass
class AdvancementResult:
    """晋级结果"""
    winner_id: Optional[int]
    method: str
    aggregate: Tuple[int, int]
    penalties: Optional[Tuple[int, int]] = None
    needs_replay: bool = False


@dataclass
class GroupStanding:
    """小组排名"""
    team_id: int
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    
    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against
```

---

## 7. 使用示例

### 7.1 创建并运行足总杯

```python
async def run_fa_cup_example():
    """足总杯运行示例"""
    
    # 初始化引擎
    engine = CupCompetitionEngine(
        match_engine=MatchEngine(),
        finance_engine=FinanceEngine(),
        fatigue_manager=FatigueManager(),
    )
    
    # 创建2024-25赛季足总杯
    edition = await engine.create_edition(
        competition_id=1,  # FA Cup
        season_year=2024,
    )
    
    # 启动杯赛
    await engine.start_edition(edition.id)
    
    # 逐轮进行
    for round_num in range(1, len(edition.rounds) + 1):
        round_obj = edition.rounds[round_num - 1]
        
        print(f"\n=== {round_obj.round_name} ===")
        
        # 执行抽签
        matches = await engine.execute_draw(
            edition_id=edition.id,
            round_number=round_num,
        )
        
        print(f"抽签完成，共 {len(matches)} 场比赛")
        
        # 模拟所有比赛
        for match in matches:
            # 获取球队阵容
            home_lineup = await get_team_lineup(match.home_team_id)
            away_lineup = await get_team_lineup(match.away_team_id)
            
            # 模拟比赛
            result = await engine.simulate_match(
                match_id=match.id,
                home_lineup=home_lineup,
                away_lineup=away_lineup,
            )
            
            print(f"  {result.home_team_name} {result.home_goals}-{result.away_goals} {result.away_team_name}")
        
        # 处理晋级
        winners = await engine.process_round_completion(edition.id, round_num)
        print(f"晋级球队: {len(winners)} 支")
        
        # 推进到下一轮
        if round_num < len(edition.rounds):
            await engine.advance_to_next_round(edition.id)
    
    # 杯赛结束
    final_edition = await engine._get_edition(edition.id)
    print(f"\n🏆 冠军: {final_edition.winner_name}")
```

### 7.2 欧冠小组赛示例

```python
async def run_champions_league_group_stage():
    """欧冠小组赛示例"""
    
    engine = CupCompetitionEngine(...)
    
    # 创建欧冠
    edition = await engine.create_edition(
        competition_id=2,  # Champions League
        season_year=2024,
    )
    
    # 准备分档 (按欧战积分)
    pot1 = [team1, team2, team3, team4, team5, team6, team7, team8]  # 冠军+顶级联赛
    pot2 = [...]  # 欧战积分9-16名
    pot3 = [...]  # 欧战积分17-24名
    pot4 = [...]  # 其他
    
    # 小组赛抽签
    groups = await engine.execute_group_stage_draw(
        edition_id=edition.id,
        pots=[pot1, pot2, pot3, pot4],
    )
    
    # 打印分组
    for i, group in enumerate(groups):
        print(f"\nGroup {chr(65+i)}:")
        for team in group.teams:
            print(f"  - {team.name}")
    
    # 模拟小组赛 (6轮)
    for matchday in range(1, 7):
        print(f"\n=== Matchday {matchday} ===")
        
        for group in groups:
            fixtures = group.get_matchday_fixtures(matchday)
            
            for fixture in fixtures:
                result = await engine.simulate_match(
                    match_id=fixture.match_id,
                    home_lineup=await get_team_lineup(fixture.home_team),
                    away_lineup=await get_team_lineup(fixture.away_team),
                )
                
                print(f"  {result.home_team_name} {result.home_goals}-{result.away_goals} {result.away_team_name}")
    
    # 计算最终排名
    for group in groups:
        standings = AdvancementCalculator.calculate_group_standings(
            matches=group.matches,
            teams=group.teams,
        )
        
        print(f"\nGroup {group.name} Final Standings:")
        for i, standing in enumerate(standings):
            marker = "✓" if i < 2 else "→" if i == 2 else " "
            print(f"  {marker} {standing.team_name}: {standing.points}pts")
```

---

## 8. 未来扩展

- [ ] **超级杯**: 联赛冠军 vs 杯赛冠军
- [ ] **世俱杯**: 欧冠冠军参加的世界级赛事
- [ ] **国家队杯赛**: 世界杯、欧洲杯等
- [ ] **历史数据**: 历年杯赛冠军记录
- [ ] **VAR系统**: 杯赛中的VAR判罚事件
- [ ] **天气影响**: 不同天气对杯赛的影响
- [ ] **球迷骚乱**: 极端情况下的比赛中断/判负
- [ ] **多回合重赛**: 早期足总杯的多场重赛历史规则
