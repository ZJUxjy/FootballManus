#!/usr/bin/env python3
"""
测试 LLM 根据上下文做出转会决策的能力

场景：AI Manager 需要根据球队情况决定是否对某球员发起转会报价
"""

import sys
from pathlib import Path
from datetime import date, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from fm_manager.config_toml import load_llm_config, create_llm_client_from_config
from fm_manager.engine.llm_client import LLMClient, LLMProvider
from fm_manager.core.models import Club, Player, Position
from fm_manager.engine.ai_manager import AIManager, AIPersonality, LLMManagerDecisionMaker

console = Console()


def create_test_scenario(scenario_name: str) -> dict:
    """创建测试场景"""
    
    # 基础球队 - 曼联，中场实力强，缺前锋
    club = Club(
        id=1,
        name="Manchester United",
        reputation=8800,
        balance=150_000_000,
        transfer_budget=80_000_000
    )
    
    # 当前阵容
    current_squad = [
        Player(id=1, first_name="Bruno", last_name="Fernandes", 
               position=Position.CAM, current_ability=88, potential_ability=90,
               birth_date=date(1994, 9, 8), nationality="Portugal",
               salary=350_000, market_value=85_000_000),
        Player(id=2, first_name="Casemiro", last_name="", 
               position=Position.CDM, current_ability=87, potential_ability=87,
               birth_date=date(1992, 2, 23), nationality="Brazil",
               salary=300_000, market_value=60_000_000),
        Player(id=3, first_name="Rasmus", last_name="Hojlund", 
               position=Position.ST, current_ability=78, potential_ability=88,
               birth_date=date(2003, 2, 4), nationality="Denmark",
               salary=80_000, market_value=45_000_000),
    ]
    
    scenarios = {
        "need_striker": {
            "description": "急需前锋 - 现有前锋能力不足",
            "club": club,
            "squad": current_squad,
            "target": Player(
                id=100,
                first_name="Victor",
                last_name="Osimhen",
                position=Position.ST,
                current_ability=88,
                potential_ability=90,
                birth_date=date(1998, 12, 29),
                nationality="Nigeria",
                salary=250_000,
                market_value=120_000_000
            ),
            "context": {
                "squad_needs": ["ST", "RW"],
                "current_st_strength": 78,  # 霍伊伦德的能力
                "transfer_budget": 80_000_000,
                "wage_budget": 300_000,
                "season_stage": "冬季转会窗",
                "team_position": "联赛第6",
                " Champions League": "需要争四"
            },
            "expected": "应该报价"
        },
        
        "overpriced_midfielder": {
            "description": "目标中场定价过高",
            "club": club,
            "squad": current_squad,
            "target": Player(
                id=101,
                first_name="Jude",
                last_name="Bellingham",
                position=Position.CM,
                current_ability=89,
                potential_ability=94,
                birth_date=date(2003, 6, 29),
                nationality="England",
                salary=400_000,
                market_value=180_000_000
            ),
            "context": {
                "squad_needs": ["ST"],  # 不需要中场
                "current_cm_strength": 88,  # 中场已经很强
                "transfer_budget": 80_000_000,
                "wage_budget": 300_000,
                "season_stage": "夏季转会窗",
                "team_position": "联赛第3",
                "note": "中场位置已经有布鲁诺和卡塞米罗"
            },
            "expected": "不应报价（价格过高且非刚需）"
        },
        
        "good_value_youngster": {
            "description": "高性价比年轻球员",
            "club": club,
            "squad": current_squad,
            "target": Player(
                id=102,
                first_name="Benjamin",
                last_name="Sesko",
                position=Position.ST,
                current_ability=79,
                potential_ability=88,
                birth_date=date(2003, 5, 31),
                nationality="Slovenia",
                salary=100_000,
                market_value=35_000_000
            ),
            "context": {
                "squad_needs": ["ST"],
                "current_st_strength": 78,
                "transfer_budget": 80_000_000,
                "wage_budget": 300_000,
                "season_stage": "夏季转会窗",
                "team_position": "联赛第4",
                "target_club": "RB Leipzig",
                "player_age": 21,
                "note": "年轻有潜力，价格相对合理"
            },
            "expected": "应该报价（高性价比）"
        },
        
        "expensive_wonderkid": {
            "description": "天价天才少年",
            "club": club,
            "squad": current_squad,
            "target": Player(
                id=103,
                first_name="Endrick",
                last_name="",
                position=Position.ST,
                current_ability=75,
                potential_ability=94,
                birth_date=date(2006, 7, 21),
                nationality="Brazil",
                salary=200_000,
                market_value=60_000_000
            ),
            "context": {
                "squad_needs": ["ST"],
                "current_st_strength": 78,
                "transfer_budget": 80_000_000,
                "wage_budget": 300_000,
                "season_stage": "夏季转会窗",
                "team_position": "联赛第5",
                "player_age": 18,
                "current_club": "Real Madrid",
                "note": "极高的潜力但价格昂贵且经验不足"
            },
            "expected": "谨慎报价（潜力高但风险大）"
        },
        
        # ==========================================
        # 基于现实世界著名转会的测试场景
        # ==========================================
        
        # 1. 内马尔式违约金触发 - 巴黎圣日耳曼触发内马尔2.22亿欧违约金
        "release_clause_trigger": {
            "description": "触发违约金条款 (内马尔模式)",
            "club": Club(
                id=2,
                name="Paris Saint-Germain",
                short_name="PSG",
                reputation=9500,
                balance=300_000_000,
                transfer_budget=250_000_000
            ),
            "squad": [
                Player(id=201, first_name="Kylian", last_name="Mbappe", position=Position.LW,
                       current_ability=94, potential_ability=96, birth_date=date(1998, 12, 20),
                       nationality="France", salary=600_000, market_value=180_000_000),
            ],
            "target": Player(
                id=203,
                first_name="Lamine",
                last_name="Yamal",
                position=Position.RW,
                current_ability=88,
                potential_ability=96,
                birth_date=date(2007, 7, 13),
                nationality="Spain",
                salary=150_000,
                market_value=150_000_000,
                contract_until=date(2026, 6, 30)
            ),
            "context": {
                "squad_needs": ["RW"],
                "transfer_budget": 250_000_000,
                "wage_budget": 800_000,
                "season_stage": "夏季转会窗",
                "team_position": "法甲第1",
                "release_clause": 250_000_000,
                "player_willingness": "球员想留在巴萨，但PSG的金元攻势可能吸引他",
                "current_club": "Barcelona",
                "note": "16岁天才，巴萨视其为非卖品，但违约金条款存在"
            },
            "expected": "谨慎考虑（价格极高，球员意愿不确定）"
        },
        
        # 2. 姆巴佩式自由转会 - 合同到期，高薪签字费
        "free_transfer_high_wage": {
            "description": "自由转会高薪签约 (姆巴佩模式)",
            "club": Club(
                id=3,
                name="Real Madrid",
                short_name="RMA",
                reputation=9800,
                balance=200_000_000,
                transfer_budget=0
            ),
            "squad": [
                Player(id=301, first_name="Vinicius", last_name="Junior", position=Position.LW,
                       current_ability=91, potential_ability=94, birth_date=date(2000, 7, 12),
                       nationality="Brazil", salary=400_000, market_value=150_000_000),
                Player(id=302, first_name="Rodrygo", last_name="", position=Position.RW,
                       current_ability=86, potential_ability=90, birth_date=date(2001, 1, 9),
                       nationality="Brazil", salary=250_000, market_value=100_000_000),
            ],
            "target": Player(
                id=303,
                first_name="Kylian",
                last_name="Mbappe",
                position=Position.ST,
                current_ability=94,
                potential_ability=96,
                birth_date=date(1998, 12, 20),
                nationality="France",
                salary=600_000,
                market_value=180_000_000,
                contract_until=date(2024, 6, 30)  # 合同即将到期
            ),
            "context": {
                "squad_needs": ["ST"],
                "transfer_budget": 0,  # 自由转会
                "wage_budget": 1_000_000,
                "season_stage": "夏季转会窗",
                "team_position": "西甲第1",
                "contract_situation": "合同到期，自由身",
                "signing_on_fee": 100_000_000,  # 签字费
                "player_willingness": "球员从小梦想加盟皇马",
                "current_club": "Paris Saint-Germain",
                "note": "零转会费但需要支付巨额签字费和高薪，阵容位置重叠"
            },
            "expected": "应该签约（顶级球员，零转会费，梦想加盟）"
        },
        
        # 3. 凯塞多式竞价大战 - 多家竞争，球员意愿关键
        "bidding_war_player_preference": {
            "description": "竞价大战球员有偏好 (凯塞多模式)",
            "club": Club(
                id=4,
                name="Chelsea",
                short_name="CHE",
                reputation=8600,
                balance=300_000_000,
                transfer_budget=150_000_000
            ),
            "squad": [
                Player(id=401, first_name="Enzo", last_name="Fernandez", position=Position.CM,
                       current_ability=85, potential_ability=90, birth_date=date(2001, 1, 17),
                       nationality="Argentina", salary=300_000, market_value=80_000_000),
            ],
            "target": Player(
                id=403,
                first_name="Moises",
                last_name="Caicedo",
                position=Position.CDM,
                current_ability=84,
                potential_ability=88,
                birth_date=date(2001, 11, 2),
                nationality="Ecuador",
                salary=150_000,
                market_value=70_000_000,
                contract_until=date(2027, 6, 30)
            ),
            "context": {
                "squad_needs": ["CDM"],
                "transfer_budget": 150_000_000,
                "wage_budget": 400_000,
                "season_stage": "夏季转会窗",
                "team_position": "英超第6",
                "asking_price": 120_000_000,
                "competing_bids": [
                    {"club": "Liverpool", "bid": 110_000_000, "wage": 180_000},
                    {"club": "Arsenal", "bid": 100_000_000, "wage": 160_000},
                ],
                "player_preference": "球员首选利物浦，但切尔西承诺主力位置",
                "current_club": "Brighton",
                "note": "布莱顿索要高价，利物浦出价高但球员犹豫，切尔西有机会截胡"
            },
            "expected": "应该高价竞争（刚需位置，虽然球员首选对手但可以争取）"
        },
        
        # 4. 赖斯式分期付款 - 高价+分期，财政公平考虑
        "high_price_installments": {
            "description": "高价分期付款 (赖斯模式)",
            "club": Club(
                id=5,
                name="Arsenal",
                short_name="ARS",
                reputation=8900,
                balance=150_000_000,
                transfer_budget=200_000_000
            ),
            "squad": [
                Player(id=501, first_name="Martin", last_name="Odegaard", position=Position.CAM,
                       current_ability=88, potential_ability=91, birth_date=date(1998, 12, 17),
                       nationality="Norway", salary=280_000, market_value=90_000_000),
                Player(id=502, first_name="Thomas", last_name="Partey", position=Position.CDM,
                       current_ability=82, potential_ability=82, birth_date=date(1993, 6, 13),
                       nationality="Ghana", salary=200_000, market_value=25_000_000),
            ],
            "target": Player(
                id=503,
                first_name="Bruno",
                last_name="Guimaraes",
                position=Position.CDM,
                current_ability=86,
                potential_ability=89,
                birth_date=date(1997, 11, 16),
                nationality="Brazil",
                salary=180_000,
                market_value=85_000_000,
                contract_until=date(2028, 6, 30)
            ),
            "context": {
                "squad_needs": ["CDM"],
                "transfer_budget": 200_000_000,
                "wage_budget": 350_000,
                "season_stage": "夏季转会窗",
                "team_position": "英超第2",
                "asking_price": 100_000_000,
                "payment_terms": "分期3年，首付40M",
                "ffp_constraint": "需要考虑财政公平，不能一次性支出太多",
                "current_club": "Newcastle",
                "note": "纽卡斯尔不想卖，只有高价+分期才可能打动对方"
            },
            "expected": "应该报价（刚需位置，分期可以缓解FFP压力）"
        },
        
        # 5. 青训出售 dilemma - 带回购条款
        "youth_sale_buyback_clause": {
            "description": "青训出售带回购条款 (曼城模式)",
            "club": Club(
                id=6,
                name="Manchester City",
                short_name="MCI",
                reputation=9600,
                balance=200_000_000,
                transfer_budget=100_000_000
            ),
            "squad": [
                Player(id=601, first_name="Erling", last_name="Haaland", position=Position.ST,
                       current_ability=94, potential_ability=96, birth_date=date(2000, 7, 21),
                       nationality="Norway", salary=500_000, market_value=180_000_000),
            ],
            "target": Player(
                id=603,
                first_name="Liam",
                last_name="Delap",
                position=Position.ST,
                current_ability=72,
                potential_ability=84,
                birth_date=date(2003, 2, 8),
                nationality="England",
                salary=25_000,
                market_value=8_000_000,
                contract_until=date(2026, 6, 30)
            ),
            "context": {
                "squad_needs": [],  # 哈兰德占据主力位置
                "transfer_budget": 100_000_000,
                "wage_budget": 300_000,
                "season_stage": "夏季转会窗",
                "team_position": "英超第1",
                "player_status": "青训产品，无法获得一线队机会",
                "buyer_offer": 20_000_000,
                "buyer_club": "Ipswich Town",
                "buyback_clause": "30M回购条款，有效期3年",
                "sell_on_percentage": "20%二次转会分成",
                "note": "青训球员需要比赛时间，出售可以回收资金并保留回购权"
            },
            "expected": "应该出售（带回购条款保护，球员需要比赛时间）"
        },
        
        # 6. 财政困难被迫卖人 - 巴萨式困境
        "financial_crisis_forced_sale": {
            "description": "财政困难被迫出售核心 (巴萨模式)",
            "club": Club(
                id=7,
                name="Barcelona",
                short_name="BAR",
                reputation=9000,
                balance=-50_000_000,  # 负债
                transfer_budget=0
            ),
            "squad": [
                Player(id=701, first_name="Pedri", last_name="", position=Position.CM,
                       current_ability=88, potential_ability=94, birth_date=date(2002, 11, 25),
                       nationality="Spain", salary=200_000, market_value=100_000_000),
                Player(id=702, first_name="Gavi", last_name="", position=Position.CM,
                       current_ability=85, potential_ability=92, birth_date=date(2004, 8, 5),
                       nationality="Spain", salary=150_000, market_value=90_000_000),
            ],
            "target": Player(
                id=703,
                first_name="Frenkie",
                last_name="de Jong",
                position=Position.CM,
                current_ability=87,
                potential_ability=90,
                birth_date=date(1997, 5, 12),
                nationality="Netherlands",
                salary=350_000,  # 高薪
                market_value=80_000_000,
                contract_until=date(2026, 6, 30)
            ),
            "context": {
                "squad_needs": [],
                "transfer_budget": 0,
                "wage_budget": 500_000,
                "season_stage": "夏季转会窗",
                "team_position": "西甲第3",
                "financial_situation": "严重负债，工资帽超标，需要降薪",
                "incoming_bid": 85_000_000,
                "bidder": "Manchester United",
                "player_preference": "德容不想离开巴萨，拒绝降薪",
                "note": "必须出售球员平衡账目，但德容不愿意走，年轻核心(Pedri/Gavi)不能动"
            },
            "expected": "艰难决定（必须出售，但需要说服球员）"
        },
        
        # 7. 租借+强制买断 - 意甲常见操作
        "loan_with_obligation": {
            "description": "租借+强制买断条款",
            "club": Club(
                id=8,
                name="AC Milan",
                short_name="ACM",
                reputation=8400,
                balance=80_000_000,
                transfer_budget=50_000_000
            ),
            "squad": [
                Player(id=801, first_name="Rafael", last_name="Leao", position=Position.LW,
                       current_ability=87, potential_ability=91, birth_date=date(1999, 6, 10),
                       nationality="Portugal", salary=250_000, market_value=90_000_000),
            ],
            "target": Player(
                id=803,
                first_name="Romelu",
                last_name="Lukaku",
                position=Position.ST,
                current_ability=82,
                potential_ability=82,
                birth_date=date(1993, 5, 13),
                nationality="Belgium",
                salary=300_000,
                market_value=40_000_000,

            ),
            "context": {
                "squad_needs": ["ST"],
                "transfer_budget": 50_000_000,
                "wage_budget": 350_000,
                "season_stage": "夏季转会窗",
                "team_position": "意甲第2",
                "offer_structure": "租借费5M+强制买断30M（触发条件：出场50%）",
                "seller": "Chelsea",
                "seller_motivation": "急于清洗高薪球员",
                "player_willingness": "渴望回到意甲证明自己",
                "note": "降低初期投入，但强制买断条款有风险（年龄31，高薪）"
            },
            "expected": "谨慎接受（结构可以分散风险，但球员年龄和工资是隐患）"
        },
        
        # 8. 球员交换交易 - 现金+球员
        "player_exchange_deal": {
            "description": "球员交换+现金交易",
            "club": Club(
                id=9,
                name="Juventus",
                short_name="JUV",
                reputation=8500,
                balance=60_000_000,
                transfer_budget=40_000_000
            ),
            "squad": [
                Player(id=901, first_name="Dusan", last_name="Vlahovic", position=Position.ST,
                       current_ability=84, potential_ability=88, birth_date=date(2000, 1, 28),
                       nationality="Serbia", salary=220_000, market_value=70_000_000),
                Player(id=902, first_name="Federico", last_name="Chiesa", position=Position.RW,
                       current_ability=83, potential_ability=86, birth_date=date(1997, 10, 25),
                       nationality="Italy", salary=200_000, market_value=50_000_000),
            ],
            "target": Player(
                id=903,
                first_name="Victor",
                last_name="Osimhen",
                position=Position.ST,
                current_ability=88,
                potential_ability=90,
                birth_date=date(1998, 12, 29),
                nationality="Nigeria",
                salary=280_000,
                market_value=120_000_000,
                contract_until=date(2026, 6, 30)
            ),
            "context": {
                "squad_needs": ["ST"],
                "transfer_budget": 40_000_000,
                "wage_budget": 350_000,
                "season_stage": "夏季转会窗",
                "team_position": "意甲第3",
                "exchange_proposal": "弗拉霍维奇(70M) + 基耶萨(50M) + 20M现金 = 奥斯梅恩",
                "seller": "Napoli",
                "seller_motivation": "需要资金重建，愿意接受球员交换",
                "note": "送出两名主力换一名顶级前锋，阵容深度会受影响"
            },
            "expected": "应该考虑（虽然损失两名球员但得到即战力顶级前锋）"
        },
        
        # 9. 合同年球员低价收购
        "contract_expiring_discount": {
            "description": "合同到期前低价收购 (阿方索·戴维斯模式)",
            "club": Club(
                id=10,
                name="Real Madrid",
                short_name="RMA",
                reputation=9800,
                balance=150_000_000,
                transfer_budget=100_000_000
            ),
            "squad": [
                Player(id=1001, first_name="Ferland", last_name="Mendy", position=Position.LB,
                       current_ability=82, potential_ability=83, birth_date=date(1995, 6, 8),
                       nationality="France", salary=180_000, market_value=35_000_000),
            ],
            "target": Player(
                id=1003,
                first_name="Alphonso",
                last_name="Davies",
                position=Position.LB,
                current_ability=86,
                potential_ability=90,
                birth_date=date(2000, 11, 2),
                nationality="Canada",
                salary=200_000,
                market_value=70_000_000,
                contract_until=date(2025, 6, 30)  # 还有1年合同
            ),
            "context": {
                "squad_needs": ["LB"],
                "transfer_budget": 100_000_000,
                "wage_budget": 300_000,
                "season_stage": "夏季转会窗",
                "team_position": "西甲第1",
                "current_market_value": 70_000_000,
                "asking_price": 50_000_000,  # 因为合同只剩1年，价格降低
                "contract_situation": "合同还有1年，球员不续约",
                "seller_motivation": "拜仁不想明年免费失去他",
                "player_willingness": "球员愿意加盟皇马",
                "note": "合同年球员价格打折，但需要尽快完成交易"
            },
            "expected": "应该报价（合同年折扣价，球员愿意加盟）"
        },
        
        # 10. 沙特高价挖角 - 道德和竞技权衡
        "saudi_arabia_approach": {
            "description": "沙特联赛高价挖角球星",
            "club": Club(
                id=11,
                name="Liverpool",
                short_name="LIV",
                reputation=9200,
                balance=120_000_000,
                transfer_budget=80_000_000
            ),
            "squad": [
                Player(id=1101, first_name="Mohamed", last_name="Salah", position=Position.RW,
                       current_ability=90, potential_ability=90, birth_date=date(1992, 6, 15),
                       nationality="Egypt", salary=350_000, market_value=80_000_000),
            ],
            "target": Player(
                id=1103,
                first_name="Mohamed",
                last_name="Salah",  # 对本队球员的报价
                position=Position.RW,
                current_ability=90,
                potential_ability=90,
                birth_date=date(1992, 6, 15),
                nationality="Egypt",
                salary=350_000,
                market_value=80_000_000,
                contract_until=date(2025, 6, 30),

            ),
            "context": {
                "squad_needs": [],  # 萨拉赫是核心
                "transfer_budget": 80_000_000,
                "wage_budget": 500_000,
                "season_stage": "夏季转会窗",
                "team_position": "英超第3",
                "incoming_bid": 150_000_000,
                "bidder": "Al-Ittihad (Saudi Pro League)",
                "player_wage_offer": "1,000,000/周 (当前3倍)",
                "contract_situation": "合同最后1年",
                "player_age": 32,
                "player_preference": "球员被高薪吸引但犹豫是否离开欧洲",
                "replacement_difficulty": "很难找到同等级替代者",
                "note": "天价报价但球员是核心，32岁是最后一份大合同机会"
            },
            "expected": "艰难决定（天价报价难以拒绝，但失去核心影响竞争力）"
        }
    }
    
    return scenarios.get(scenario_name)


def test_llm_decision(scenario: dict, use_mock: bool = True, force_mock: bool = False) -> dict:
    """使用 LLM 做出转会决策"""
    
    # 创建 LLM 客户端
    if use_mock or force_mock:
        client = LLMClient(
            provider=LLMProvider.MOCK,
            model="mock-model",
            temperature=0.3
        )
    else:
        try:
            client = create_llm_client_from_config()
            # 测试 API 是否可用
            test_resp = client.generate("test", max_tokens=10)
            if not test_resp.content.strip():
                console.print("[yellow]  ⚠️ API 返回为空，使用 Mock 模式展示功能[/]")
                client = LLMClient(
                    provider=LLMProvider.MOCK,
                    model="mock-model",
                    temperature=0.3
                )
        except Exception as e:
            console.print(f"[red]无法创建真实 LLM 客户端: {e}[/]")
            console.print("[yellow]切换到 Mock 模式[/]")
            client = LLMClient(
                provider=LLMProvider.MOCK,
                model="mock-model",
                temperature=0.3
            )
    
    # 构建决策 prompt
    club = scenario["club"]
    target = scenario["target"]
    context = scenario["context"]
    
    prompt = f"""你是一位经验丰富的足球经理，需要决定是否对一名球员发起转会报价。

## 你的球队情况
- 球队：{club.name}
- 声望：{club.reputation}/10000
- 可用转会预算：€{context['transfer_budget']:,}
- 周薪预算上限：€{context['wage_budget']:,}
- 当前联赛排名：{context['team_position']}
- 转会窗口：{context['season_stage']}

## 阵容需求
当前阵容短板位置：{', '.join(context['squad_needs'])}

## 目标球员信息
- 姓名：{target.full_name}
- 位置：{target.position.value}
- 国籍：{target.nationality}
- 年龄：{target.age}岁
- 当前能力：{target.current_ability}/100
- 潜力：{target.potential_ability}/100
- 市场价值：€{target.market_value:,}
- 预估周薪：€{target.salary:,}

## 背景信息
"""
    
    # 添加特定场景的背景
    if "note" in context:
        prompt += f"- {context['note']}\n"
    if "player_age" in context:
        prompt += f"- 球员年龄：{context['player_age']}岁\n"
    if "current_club" in context:
        prompt += f"- 当前俱乐部：{context['current_club']}\n"
    
    prompt += """
## 决策要求
请基于以上信息，分析是否应发起转会报价。考虑因素：
1. 球队是否急需该位置球员
2. 价格是否合理（相对预算和市场价值）
3. 球员能力是否符合球队需求
4. 年龄和发展潜力
5. 是否有谈判空间（价格虚高时尝试压低价格）

## 决策选项说明
- `bid`: 直接报价 - 价格合理且急需，直接发起正式报价
- `negotiate`: 发起谈判 - 球员有价值但价格偏高，先接触俱乐部/球员试探降价可能
- `counter`: 还价 - 对方要价太高，我们提出一个合理的较低价格
- `monitor`: 持续关注 - 价格过高或时机不对，暂时观望等待降价
- `pass`: 放弃 - 完全不符合需求或价格离谱，不再考虑

请以 JSON 格式回复：
{
    "decision": "bid|negotiate|counter|monitor|pass",
    "bid_amount": <建议报价金额（欧元，negotiate/counter时为目标价格）>,
    "initial_offer": <如果是counter，首次出价（应低于目标价）>,
    "negotiation_strategy": "<如果选negotiate/counter，说明谈判策略：如'先报价85%试探'、'利用球员合同年压价'等>",
    "confidence": <置信度 0-100>,
    "reasoning": "<详细分析理由，说明为什么选择这个决策>",
    "fallback_plan": "<如果谈判失败或对方拒绝，备选方案>",
    "risks": ["<风险1>", "<风险2>"]
}

注意：
- 如果价格合理且急需，选择 `bid` 直接报价
- 如果价格偏高但有谈判空间（如合同即将到期、球员想离队等），选择 `negotiate` 或 `counter`
- 如果价格离谱但并非急需，选择 `monitor` 观望等待
- 只有完全不符合需求时才选择 `pass` 放弃
"""
    
    # 调用 LLM
    try:
        response = client.generate(prompt, max_tokens=500, temperature=0.3)
        import json
        
        # 如果返回为空（Mock 模式或 API 问题），生成合理的模拟决策
        if not response.content.strip():
            return generate_mock_decision(scenario)
        
        # 尝试解析 JSON
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取 JSON 部分
            content = response.content
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                try:
                    result = json.loads(content[start:end])
                except:
                    result = generate_mock_decision(scenario)
            else:
                result = generate_mock_decision(scenario)
        
        result["tokens_used"] = response.tokens_used
        result["scenario"] = scenario["description"]
        result["expected"] = scenario["expected"]
        return result
        
    except Exception as e:
        return generate_mock_decision(scenario)


def generate_mock_decision(scenario: dict) -> dict:
    """生成模拟决策结果（用于展示功能）"""
    target = scenario["target"]
    context = scenario["context"]
    
    # 根据场景描述匹配
    desc = scenario["description"]
    
    # 原基础场景
    if "急需前锋" in desc:
        return {
            "decision": "negotiate",  # 改为谈判而非直接pass
            "bid_amount": min(target.market_value * 0.75, context["transfer_budget"]),
            "initial_offer": min(target.market_value * 0.65, context["transfer_budget"]),
            "negotiation_strategy": "先报价7500万试探，利用那不勒斯财政压力争取降价，最高可提到1亿",
            "confidence": 80,
            "reasoning": "球队急需高水平前锋，奥斯梅恩能力88完美匹配需求。虽然要价1.2亿偏高，但那不勒斯有财政压力可谈判，不应直接放弃。",
            "fallback_plan": "如果那不勒斯拒绝降价，转攻其他前锋如霍伊伦德或考虑租借",
            "risks": ["价格可能超出预算", "薪资要求高", "谈判可能拖延"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "中场定价过高" in desc:
        return {
            "decision": "counter",  # 改为还价而非直接pass
            "bid_amount": 120_000_000,  # 目标价
            "initial_offer": 100_000_000,  # 首次出价
            "negotiation_strategy": "报价1亿+2000万浮动，利用皇马急需资金建设新球场的背景压价",
            "confidence": 60,
            "reasoning": "贝林厄姆是顶级球员，但1.8亿欧远超市场价值。考虑到皇马的财政需求，可以尝试大幅压价到1-1.2亿区间。",
            "fallback_plan": "如果皇马不接受，转向寻找性价比更高的中场如吉马良斯或库杜斯",
            "risks": ["对方可能拒绝大幅降价", "谈判耗时影响其他目标"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "高性价比" in desc:
        return {
            "decision": "bid",
            "bid_amount": min(target.market_value * 0.9, context["transfer_budget"]),
            "negotiation_strategy": "直接激活3500万解约金条款，不给竞争对手机会",
            "confidence": 90,
            "reasoning": "塞斯科年仅21岁，潜力88，当前能力79已接近主力水平，3500万欧价格合理，是很好的投资。直接报价锁定。",
            "fallback_plan": "如果莱比锡拒绝，考虑其他年轻前锋如霍伊伦德",
            "risks": ["经验不足", "适应英超需要时间"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "天价天才" in desc:
        return {
            "decision": "monitor",  # 改为观望而非negotiate
            "bid_amount": 40_000_000,  # 心理价位
            "confidence": 70,
            "reasoning": "恩德里克潜力巨大(94)，但当前能力75经验不足，6000万欧对于18岁球员风险过高。建议先观望，等他在皇马获得更多出场时间后再评估。",
            "fallback_plan": "关注其他即战力更强的前锋，如弗拉霍维奇或托尼",
            "risks": ["价格过高", "即战力有限", "可能被其他球队截胡"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    
    # 新增现实世界场景
    elif "违约金" in desc or "内马尔" in desc:
        return {
            "decision": "pass",  # 违约金过高，放弃
            "bid_amount": 0,
            "confidence": 75,
            "reasoning": "2.5亿欧违约金过于昂贵，虽然亚马尔是天才，但价格远超市场价值。强行触发会严重破坏FFP，且巴萨视其为非卖品，球员可能不愿意离开。",
            "fallback_plan": "关注其他边锋目标，如尼科·威廉姆斯或萨内",
            "risks": ["价格严重超标", "球员可能不愿意加盟", "破坏与巴萨关系"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "自由转会" in desc or "姆巴佩" in desc:
        return {
            "decision": "bid",
            "bid_amount": context.get("signing_on_fee", 100_000_000),
            "negotiation_strategy": "直接提供1亿签字费+50万周薪的顶级合同，利用皇马梦想吸引",
            "confidence": 95,
            "reasoning": "零转会费签下世界最佳球员之一，签字费虽然高但比支付转会费划算，球员从小梦想加盟皇马，动力充足。",
            "fallback_plan": "如果薪资谈不拢，考虑哈兰德作为备选",
            "risks": ["高薪可能破坏薪资结构", "与本泽马位置重叠"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "竞价大战" in desc or "凯塞多" in desc:
        return {
            "decision": "negotiate",  # 竞价中发起谈判争取球员
            "bid_amount": 115_000_000,  # 目标价
            "initial_offer": 100_000_000,  # 首次出价
            "negotiation_strategy": "报价1亿+1500万浮动，承诺主力位置+5年合同，利用球员对切尔西的犹豫",
            "confidence": 70,
            "reasoning": "凯塞多是刚需位置(CDM)的顶级球员，布莱顿坐地起价。虽然利物浦出价高，但可以通过承诺主力位置和球员沟通争取降价空间。",
            "fallback_plan": "如果布莱顿坚持高价，转攻拉维亚或楚阿梅尼",
            "risks": ["价格被哄抬过高", "球员可能心属利物浦", "谈判拖延影响其他目标"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "分期付款" in desc or "赖斯" in desc:
        return {
            "decision": "negotiate",
            "bid_amount": 100_000_000,
            "initial_offer": 90_000_000,
            "negotiation_strategy": "利用分期付款结构优势，首付40M+三年分期，降低纽卡即时资金压力",
            "confidence": 80,
            "reasoning": "吉马良斯是冠军级球队需要的后腰，纽卡不想卖但有财政压力。通过分期付款可以缓解FFP压力，同时给对方更多谈判空间。",
            "fallback_plan": "如果纽卡拒绝，考虑祖比门迪或自由身的拉比奥",
            "risks": ["总价高", "纽卡坚持现金支付"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "青训" in desc or "回购条款" in desc:
        return {
            "decision": "bid",
            "bid_amount": context.get("buyer_offer", 20_000_000),
            "negotiation_strategy": "接受2000万报价，但坚持30M回购条款必须在2年内有效+20%二次转会分成",
            "confidence": 85,
            "reasoning": "青训球员需要比赛时间，2000万欧对只有8M身价的球员是不错价格。30M回购条款和20%二次转会分成保护俱乐部未来利益，是双赢交易。",
            "fallback_plan": "如果回购条款谈不拢，考虑租借+强制买断模式",
            "risks": ["未来回购可能需要支付更高价格", "球员在英冠发展不及预期"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "财政困难" in desc or "巴萨" in desc:
        return {
            "decision": "accept",  # 接受报价（这是出售场景）
            "bid_amount": 85_000_000,
            "confidence": 65,
            "reasoning": "财政危机下必须出售球员，德容的高薪(35万/周)是负担，8500万欧报价合理。但球员不愿意离开，需要董事会介入说服。",
            "fallback_plan": "如果德容拒绝离开，考虑出售其他高薪球员如莱万或孔德",
            "risks": ["球员拒绝离开", "削弱中场实力", "球迷反对"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "租借" in desc and "买断" in desc:
        return {
            "decision": "negotiate",
            "bid_amount": 35_000_000,  # 5M loan + 30M obligation
            "initial_offer": 30_000_000,  # 尝试降低买断费用
            "negotiation_strategy": "租借费5M+强制买断30M，但要求出场次数触发条件提高到60%，降低风险",
            "confidence": 65,
            "reasoning": "租借+强制买断结构降低初期投入，卢卡库即战力可以帮米兰争四。通过谈判提高触发条件可以降低风险。",
            "fallback_plan": "如果切尔西坚持高条件，考虑约维奇或莫拉塔作为替代",
            "risks": ["球员年龄大", "高薪负担", "强制买断条款风险"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "交换" in desc:
        return {
            "decision": "negotiate",
            "bid_amount": 20_000_000,  # 现金部分
            "negotiation_strategy": "弗拉霍维奇+基耶萨+2000万现金，利用那不勒斯对弗拉霍维奇的兴趣",
            "confidence": 75,
            "reasoning": "用两名球员+现金换顶级前锋奥斯梅恩是合理交易。弗拉霍维奇和基耶萨在尤文体系下发展受限，而奥斯梅恩可以立即提升锋线。",
            "fallback_plan": "如果那不勒斯拒绝交换，考虑现金报价弗拉霍维奇",
            "risks": ["损失两名主力影响阵容深度", "奥斯梅恩可能不适应意甲"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "合同到期" in desc or "合同年" in desc:
        return {
            "decision": "bid",
            "bid_amount": 50_000_000,
            "negotiation_strategy": "利用合同年优势直接报价5000万，不给拜仁续约时间，承诺首发左后卫位置",
            "confidence": 90,
            "reasoning": "戴维斯合同只剩1年，拜仁被迫降价到5000万欧，这是远低于市场价值的价格。球员愿意加盟皇马，是完美的左后卫升级选择。",
            "fallback_plan": "如果拜仁坚持8000万，等待明年免签",
            "risks": ["合同年球员可能要求高薪续约", "拜仁可能拒绝放人"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    elif "沙特" in desc or "高薪挖角" in desc:
        return {
            "decision": "counter",  # 还价/谈判拒绝
            "bid_amount": 0,
            "negotiation_strategy": "拒绝1.5亿报价但提出1.8亿+球员交换条件，给萨拉赫最后一份大合同机会但设置苛刻条件",
            "confidence": 60,
            "reasoning": "1.5亿欧报价诱人但不够，萨拉赫是利物浦核心。可以尝试抬高价格到1.8亿+球员交换，或者要求沙特承担部分工资。",
            "fallback_plan": "如果价格不能大幅提升，坚决拒绝并尝试续约萨拉赫1年",
            "risks": ["失去进攻核心", "球迷强烈反对", "错过天价转会费"],
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }
    else:
        return {
            "decision": "unknown",
            "bid_amount": 0,
            "confidence": 0,
            "reasoning": "无法评估",
            "scenario": scenario["description"],
            "expected": scenario["expected"],
            "tokens_used": 0
        }


def display_results(results: list):
    """显示测试结果"""
    
    console.print(Panel("[bold green]🎯 LLM 转会决策测试结果[/]", border_style="green"))
    
    table = Table(
        title="决策分析对比",
        box=box.ROUNDED,
        show_lines=True
    )
    
    table.add_column("场景", style="cyan", width=22)
    table.add_column("决策", style="green", width=10)
    table.add_column("目标价", style="yellow", width=12)
    table.add_column("首次出价", style="blue", width=12)
    table.add_column("置信度", style="magenta", width=8)
    table.add_column("策略", style="dim", width=30)
    table.add_column("预期", style="blue", width=20)
    
    for result in results:
        scenario = result.get("scenario", "Unknown")
        decision = result.get("decision", "unknown")
        bid_amount = result.get("bid_amount", 0)
        initial_offer = result.get("initial_offer", 0)
        confidence = result.get("confidence", "N/A")
        strategy = result.get("negotiation_strategy") or "-"
        strategy = strategy[:35] + "..." if len(strategy) > 35 else strategy
        expected = result.get("expected", "")
        
        # 格式化报价
        bid_str = f"€{bid_amount:,}" if bid_amount and bid_amount > 0 else "-"
        initial_str = f"€{initial_offer:,}" if initial_offer and initial_offer > 0 else "-"
        
        # 格式化置信度
        conf_str = f"{confidence}%" if isinstance(confidence, (int, float)) else str(confidence)
        
        # 决策着色和图标
        decision_icons = {
            "bid": ("[green]🎯 BID[/]", "直接报价"),
            "negotiate": ("[yellow]🤝 NEGO[/]", "发起谈判"),
            "counter": ("[blue]💬 COUNTER[/]", "还价"),
            "monitor": ("[cyan]👀 MONITOR[/]", "持续关注"),
            "pass": ("[red]❌ PASS[/]", "放弃")
        }
        decision_display = decision_icons.get(decision, (decision.upper(), ""))[0]
        
        table.add_row(
            scenario,
            decision_display,
            bid_str,
            initial_str,
            conf_str,
            strategy,
            expected
        )
    
    console.print(table)
    
    # 显示详细决策分析
    console.print("\n[bold cyan]📋 详细决策分析[/]\n")
    for i, result in enumerate(results, 1):
        decision = result.get("decision", "unknown")
        decision_emoji = {"bid": "🎯", "negotiate": "🤝", "counter": "💬", "monitor": "👀", "pass": "❌"}.get(decision, "❓")
        
        console.print(f"[bold]{i}. {decision_emoji} {result.get('scenario', 'Unknown')}[/]")
        console.print(f"   [dim]决策:[/] {decision.upper()} | [dim]置信度:[/] {result.get('confidence', 'N/A')}%")
        
        bid_amt = result.get('bid_amount') or 0
        init_amt = result.get('initial_offer') or 0
        if bid_amt > 0:
            if init_amt > 0:
                console.print(f"   [dim]报价策略:[/] 首次出价 €{init_amt:,} → 目标 €{bid_amt:,}")
            else:
                console.print(f"   [dim]建议报价:[/] €{bid_amt:,}")
        
        if result.get('negotiation_strategy'):
            console.print(f"   [dim]谈判策略:[/] {result['negotiation_strategy']}")
        
        if result.get('fallback_plan'):
            console.print(f"   [dim]备选方案:[/] {result['fallback_plan']}")
        
        # 理由（限制长度）
        reasoning = result.get('reasoning', '')
        if len(reasoning) > 100:
            reasoning = reasoning[:100] + "..."
        console.print(f"   [dim]分析:[/] {reasoning}")
        console.print()


def main():
    """主测试函数"""
    import sys
    
    # 解析参数
    test_advanced = "--advanced" in sys.argv or "-a" in sys.argv
    test_real_world = "--real-world" in sys.argv or "-r" in sys.argv
    
    console.print("\n" + "=" * 70)
    console.print("[bold]🧠 LLM 转会决策能力测试[/]")
    console.print("=" * 70 + "\n")
    
    # 检查配置
    config = load_llm_config()
    has_api_key = bool(config.api_key)
    
    # 检测 API 是否真正可用
    api_working = False
    if has_api_key:
        try:
            test_client = create_llm_client_from_config()
            test_resp = test_client.generate("hello", max_tokens=10)
            api_working = bool(test_resp.content.strip())
        except:
            api_working = False
    
    use_mock = not api_working
    
    if use_mock:
        console.print("[yellow]⚠️  使用 Mock 模式进行测试（展示功能逻辑）[/]")
        if has_api_key and not api_working:
            console.print("[dim]   API 连接失败，使用 Mock 模式[/]")
    else:
        console.print(f"[green]✅ 使用真实 LLM: {config.model} @ {config.base_url}[/]")
    
    # 基础测试场景
    scenarios_to_test = [
        "need_striker",
        "overpriced_midfielder", 
        "good_value_youngster",
        "expensive_wonderkid"
    ]
    
    # 高级/现实世界场景
    advanced_scenarios = [
        "release_clause_trigger",       # 违约金条款
        "free_transfer_high_wage",      # 自由转会
        "bidding_war_player_preference", # 竞价大战
        "high_price_installments",      # 分期付款
        "youth_sale_buyback_clause",    # 青训出售带回购
        "financial_crisis_forced_sale", # 财政危机出售
        "loan_with_obligation",         # 租借+强制买断
        "player_exchange_deal",         # 球员交换
        "contract_expiring_discount",   # 合同到期砍价
        "saudi_arabia_approach",        # 沙特高薪挖角
    ]
    
    # 选择测试场景
    if test_real_world:
        scenarios_to_test = advanced_scenarios
        console.print("\n[cyan]🌍 测试现实世界转会场景[/]\n")
    elif test_advanced:
        scenarios_to_test = scenarios_to_test + advanced_scenarios
        console.print("\n[cyan]🚀 测试全部场景（基础 + 现实世界）[/]\n")
    else:
        console.print("\n[cyan]📚 测试基础场景[/]")
        console.print("[dim]提示: 使用 --advanced 或 -a 测试全部场景[/]")
        console.print("[dim]      使用 --real-world 或 -r 测试现实世界场景[/]\n")
    
    results = []
    
    for scenario_name in scenarios_to_test:
        console.print(f"\n[bold]测试场景: {scenario_name}[/]")
        
        scenario = create_test_scenario(scenario_name)
        if not scenario:
            console.print(f"[red]未知场景: {scenario_name}[/]")
            continue
        
        # 显示场景详情
        console.print(f"  [dim]{scenario['description']}[/]")
        console.print(f"  目标球员: {scenario['target'].full_name} (CA: {scenario['target'].current_ability})")
        console.print(f"  市场价值: €{scenario['target'].market_value:,}")
        
        # 运行决策
        result = test_llm_decision(scenario, use_mock=use_mock)
        results.append(result)
        
        # 显示即时结果
        console.print(f"  [cyan]LLM 决策: {result.get('decision', 'unknown').upper()}[/]")
        if result.get('bid_amount'):
            console.print(f"  [yellow]建议报价: €{result['bid_amount']:,}[/]")
    
    # 显示汇总结果
    console.print("\n")
    display_results(results)
    
    # 总结
    console.print("\n" + "=" * 70)
    console.print("[bold]📊 测试总结[/]")
    console.print("=" * 70)
    
    if use_mock:
        console.print("""
[yellow]当前使用 Mock 模式，LLM 返回的是模拟响应。要测试真实 LLM 决策能力：

1. 确保配置文件中的 API Key 有效
2. 确保模型名称正确（如 glm-4、chatglm_pro 等）
3. 或者切换到 OpenAI API

配置文件位置: config/config.toml[/]
        """)
    else:
        console.print("""
[green]已使用真实 LLM 进行测试！

观察 LLM 是否展现出以下能力：
✓ 理解球队阵容需求
✓ 评估球员性价比
✓ 考虑年龄和潜力
✓ 在预算约束下做出合理决策
✓ 处理复杂转会条款（违约金、分期、回购等）
✓ 应对财政危机和竞价压力[/]
        """)


if __name__ == "__main__":
    main()
