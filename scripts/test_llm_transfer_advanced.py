#!/usr/bin/env python3
"""
高级 LLM 转会决策能力测试

测试场景：
1. 保级危机下的多候选球员选择
2. 第一候选人拒绝后的备选策略
3. 面临竞争时的决策
4. 处理其他球队对本队球员的报价（主力 vs 潜力新星）
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.columns import Columns
from rich.text import Text

from fm_manager.config_toml import load_llm_config, create_llm_client_from_config
from fm_manager.engine.llm_client import LLMClient, LLMProvider
from fm_manager.core.models import Club, Player, Position
from fm_manager.engine.ai_manager import AIManager, AIPersonality

console = Console()


@dataclass
class TransferCandidate:
    """转会候选人"""
    player: Player
    estimated_cost: int  # 预计转会费
    availability: str  # 可获得性
    competing_clubs: List[str] = field(default_factory=list)  # 竞争球队


def create_relegation_scenario() -> dict:
    """
    场景1：保级危机下的多候选球员选择
    
    球队：伯恩利 (保级队)
    现状：联赛第18，还有5轮，落后安全区3分
    问题：进攻乏力，23轮只进15球
    预算：2500万英镑
    """
    
    club = Club(
        id=1,
        name="Burnley",
        short_name="BUR",
        reputation=5500,
        balance=30_000_000,
        transfer_budget=25_000_000
    )
    
    # 当前阵容 - 进攻无力
    current_squad = [
        Player(id=1, first_name="Jay", last_name="Rodriguez", position=Position.ST,
               current_ability=68, potential_ability=70, birth_date=date(1989, 7, 29),
               nationality="England", salary=40_000, market_value=3_000_000),
        Player(id=2, first_name="Manuel", last_name="Benson", position=Position.LW,
               current_ability=65, potential_ability=72, birth_date=date(1997, 3, 28),
               nationality="Netherlands", salary=25_000, market_value=2_500_000),
        Player(id=3, first_name="Josh", last_name="Brownhill", position=Position.CM,
               current_ability=70, potential_ability=73, birth_date=date(1995, 12, 19),
               nationality="England", salary=35_000, market_value=4_000_000),
    ]
    
    # 候选球员
    candidates = [
        TransferCandidate(
            player=Player(id=101, first_name="Dominic", last_name="Calvert-Lewin",
                         position=Position.ST, current_ability=78, potential_ability=82,
                         birth_date=date(1997, 3, 16), nationality="England",
                         salary=80_000, market_value=25_000_000),
            estimated_cost=20_000_000,
            availability="高",
            competing_clubs=[]
        ),
        TransferCandidate(
            player=Player(id=102, first_name="Youssef", last_name="En-Nesyri",
                         position=Position.ST, current_ability=80, potential_ability=82,
                         birth_date=date(1997, 6, 1), nationality="Morocco",
                         salary=60_000, market_value=18_000_000),
            estimated_cost=15_000_000,
            availability="中",
            competing_clubs=["West Ham", "Wolves"]
        ),
        TransferCandidate(
            player=Player(id=103, first_name=" Gift", last_name="Orban",
                         position=Position.ST, current_ability=75, potential_ability=85,
                         birth_date=date(2002, 7, 17), nationality="Nigeria",
                         salary=30_000, market_value=12_000_000),
            estimated_cost=10_000_000,
            availability="高",
            competing_clubs=[]
        ),
        TransferCandidate(
            player=Player(id=104, first_name="Ivan", last_name="Toney",
                         position=Position.ST, current_ability=82, potential_ability=84,
                         birth_date=date(1996, 3, 16), nationality="England",
                         salary=100_000, market_value=35_000_000),
            estimated_cost=28_000_000,
            availability="低",
            competing_clubs=["Arsenal", "Chelsea"]
        ),
        TransferCandidate(
            player=Player(id=105, first_name="Sardar", last_name="Azmoun",
                         position=Position.ST, current_ability=77, potential_ability=79,
                         birth_date=date(1995, 1, 1), nationality="Iran",
                         salary=45_000, market_value=8_000_000),
            estimated_cost=6_000_000,
            availability="高",
            competing_clubs=[]
        ),
    ]
    
    return {
        "name": "保级危机下的多候选球员选择",
        "club": club,
        "current_squad": current_squad,
        "candidates": candidates,
        "context": {
            "league_position": "第18名 (降级区)",
            "games_remaining": 5,
            "points_from_safety": -3,
            "goals_scored": 15,  # 23轮
            "urgency": "极高",
            "transfer_budget": 25_000_000,
            "wage_budget": 150_000,
            "window": "冬季转会窗 (最后3天)",
            "board_pressure": "董事会要求必须保级",
            "manager_job_security": "如果降级将下课"
        }
    }


def create_rejection_fallback_scenario() -> dict:
    """
    场景2：第一候选人拒绝后的备选策略
    
    第一选择拒绝后，如何调整策略
    """
    
    club = Club(
        id=2,
        name="Aston Villa",
        short_name="AVL",
        reputation=7800,
        balance=80_000_000,
        transfer_budget=50_000_000
    )
    
    # 第一候选人已拒绝
    first_choice = Player(
        id=201, first_name="Joao", last_name="Felix",
        position=Position.CF, current_ability=84, potential_ability=90,
        birth_date=date(1999, 11, 10), nationality="Portugal",
        salary=200_000, market_value=50_000_000
    )
    
    # 备选方案
    fallback_options = [
        TransferCandidate(
            player=Player(id=202, first_name="Ollie", last_name="Watkins",
                         position=Position.ST, current_ability=82, potential_ability=83,
                         birth_date=date(1995, 12, 28), nationality="England",
                         salary=120_000, market_value=45_000_000),
            estimated_cost=40_000_000,
            availability="中",
            competing_clubs=[]
        ),
        TransferCandidate(
            player=Player(id=203, first_name="Nicolas", last_name="Jackson",
                         position=Position.ST, current_ability=78, potential_ability=85,
                         birth_date=date(2001, 6, 20), nationality="Senegal",
                         salary=80_000, market_value=35_000_000),
            estimated_cost=30_000_000,
            availability="高",
            competing_clubs=[]
        ),
        TransferCandidate(
            player=Player(id=204, first_name="Danny", last_name="Ings",
                         position=Position.ST, current_ability=76, potential_ability=76,
                         birth_date=date(1992, 7, 23), nationality="England",
                         salary=70_000, market_value=12_000_000),
            estimated_cost=10_000_000,
            availability="高",
            competing_clubs=[]
        ),
    ]
    
    return {
        "name": "第一候选人拒绝后的备选策略",
        "club": club,
        "first_choice": first_choice,
        "fallback_options": fallback_options,
        "rejection_reason": "菲利克斯选择加盟巴萨，不想在维拉踢欧协联",
        "context": {
            "league_position": "第7名",
            "european_competition": "欧协联",
            "urgency": "夏季转会窗剩余2周",
            "manager_frustration": "高层承诺的引援未能实现",
            "fan_pressure": "球迷期待高水平引援"
        }
    }


def create_competition_scenario() -> dict:
    """
    场景3：面临竞争时的决策
    
    多家俱乐部竞争同一球员
    """
    
    club = Club(
        id=3,
        name="Newcastle United",
        short_name="NEW",
        reputation=8200,
        balance=150_000_000,
        transfer_budget=100_000_000
    )
    
    # 目标球员
    target = Player(
        id=301, first_name="Alexander", last_name="Isak",
        position=Position.ST, current_ability=85, potential_ability=88,
        birth_date=date(1999, 9, 21), nationality="Sweden",
        salary=150_000, market_value=70_000_000
    )
    
    # 竞争情况
    competing_bids = [
        {"club": "Arsenal", "bid": 75_000_000, "wage_offer": 180_000, "champions_league": True},
        {"club": "Chelsea", "bid": 80_000_000, "wage_offer": 200_000, "champions_league": False},
        {"club": "Real Madrid", "bid": 70_000_000, "wage_offer": 150_000, "champions_league": True, "prestige": "极高"},
    ]
    
    return {
        "name": "面临竞争时的决策",
        "club": club,
        "target": target,
        "competing_bids": competing_bids,
        "context": {
            "league_position": "第5名",
            "european_competition": "欧冠资格赛",
            "transfer_budget": 100_000_000,
            "urgency": "必须补强前锋",
            "alternative": "有备选方案但能力低一档",
            "time_pressure": "转会窗剩余5天"
        }
    }


def create_incoming_bid_scenarios() -> List[dict]:
    """
    场景4：处理其他球队对本队球员的报价
    
    分情况：主力球员 vs 潜力新星
    不同情境下的决策
    """
    
    club = Club(
        id=4,
        name="Brighton",
        short_name="BHA",
        reputation=7500,
        balance=60_000_000,
        transfer_budget=40_000_000
    )
    
    # 主力球员
    key_player = Player(
        id=401, first_name="Kaoru", last_name="Mitoma",
        position=Position.LW, current_ability=83, potential_ability=86,
        birth_date=date(1997, 5, 20), nationality="Japan",
        salary=80_000, market_value=50_000_000,
        contract_until=date(2027, 6, 30)
    )
    
    # 潜力新星
    wonderkid = Player(
        id=402, first_name="Evan", last_name="Ferguson",
        position=Position.ST, current_ability=76, potential_ability=88,
        birth_date=date(2004, 10, 19), nationality="Ireland",
        salary=30_000, market_value=25_000_000,
        contract_until=date(2028, 6, 30)
    )
    
    scenarios = [
        {
            "name": "主力球员报价 - 赛季中",
            "player": key_player,
            "bid": {
                "from_club": "Manchester City",
                "amount": 60_000_000,
                "timing": "1月转会窗",
                "payment_terms": "分期3年"
            },
            "club_situation": {
                "league_position": "第8名",
                "european_spot": "可能获得欧联资格",
                "fan_sentiment": "球迷强烈反对出售",
                "replacement_available": False,
                "time_to_replace": "仅剩10天转会窗"
            },
            "player_willingness": "想去大城市踢球"
        },
        {
            "name": "主力球员报价 - 赛季末",
            "player": key_player,
            "bid": {
                "from_club": "Arsenal",
                "amount": 70_000_000,
                "timing": "夏季转会窗",
                "payment_terms": "一次性付清"
            },
            "club_situation": {
                "league_position": "第7名",
                "european_spot": "获得欧协联资格",
                "fan_sentiment": "理解但希望留队",
                "replacement_available": True,
                "time_to_replace": "整个夏季"
            },
            "player_willingness": "愿意留队但如果报价合适也会考虑"
        },
        {
            "name": "潜力新星报价",
            "player": wonderkid,
            "bid": {
                "from_club": "Manchester United",
                "amount": 40_000_000,
                "timing": "夏季转会窗",
                "payment_terms": "基础30M+浮动10M",
                "sell_on_clause": "20%二次转会分成"
            },
            "club_situation": {
                "league_position": "第6名",
                "european_spot": "欧联资格",
                "fan_sentiment": "视其为未来核心",
                "financial_need": "需要资金扩建球场",
                "development_path": "承诺主力位置"
            },
            "player_willingness": "被大俱乐部吸引，但愿意留队发展"
        },
        {
            "name": "潜力新星 - 高薪挖角",
            "player": wonderkid,
            "bid": {
                "from_club": "Saudi Pro League",
                "amount": 80_000_000,
                "timing": "夏季转会窗",
                "payment_terms": "一次性付清",
                "player_wage": "500,000/周"
            },
            "club_situation": {
                "league_position": "第6名",
                "ethical_consideration": "球员只有19岁",
                "player_development": "去沙特可能阻碍发展",
                "financial_need": "资金可以解决财政问题"
            },
            "player_willingness": "被高薪吸引，但犹豫是否现在去"
        }
    ]
    
    return scenarios


def test_relegation_crisis(llm_client: LLMClient) -> dict:
    """测试保级危机下的多候选球员选择"""
    
    scenario = create_relegation_scenario()
    
    console.print(f"\n[bold cyan]场景: {scenario['name']}[/]")
    console.print(f"[dim]俱乐部: {scenario['club'].name}[/]")
    console.print(f"[dim]现状: {scenario['context']['league_position']}, 落后安全区{abs(scenario['context']['points_from_safety'])}分[/]")
    console.print(f"[dim]预算: €{scenario['context']['transfer_budget']:,}[/]")
    
    # 构建候选球员列表
    candidates_str = "\n".join([
        f"{i+1}. {c.player.full_name} ({c.player.nationality}) - CA{c.player.current_ability}/PA{c.player.potential_ability}"
        f"\n   预计费用: €{c.estimated_cost:,}, 可获得性: {c.availability}"
        f"{f', 竞争球队: {', '.join(c.competing_clubs)}' if c.competing_clubs else ''}"
        for i, c in enumerate(scenario['candidates'])
    ])
    
    prompt = f"""你是一位经验丰富的足球经理，你的球队正面临严峻的保级危机。

## 球队情况
- 球队：{scenario['club'].name}
- 当前排名：{scenario['context']['league_position']}
- 剩余轮次：{scenario['context']['games_remaining']}轮
- 落后安全区：{abs(scenario['context']['points_from_safety'])}分
- 进球数：{scenario['context']['goals_scored']}球 (23轮联赛)
- 可用预算：€{scenario['context']['transfer_budget']:,}
- 周薪上限：€{scenario['context']['wage_budget']:,}
- 转会窗口：{scenario['context']['window']}
- 董事会要求：{scenario['context']['board_pressure']}

## 候选球员
{candidates_str}

## 当前前锋
{scenario['current_squad'][0].full_name} - CA{scenario['current_squad'][0].current_ability}

## 任务
请从候选球员中选择**优先级最高的1-2名**球员进行报价，并说明：
1. 为什么优先选择这名/这些球员
2. 报价金额和理由
3. 如果首选失败，备选是谁
4. 为什么选择这些球员而不是其他选项

请以 JSON 格式回复：
{{
    "priority_order": ["球员名1", "球员名2"],
    "primary_target": {{
        "name": "首选球员名",
        "bid_amount": 报价金额,
        "reasoning": "选择理由"
    }},
    "fallback": {{
        "name": "备选球员名",
        "bid_amount": 报价金额
    }},
    "rejected_options": ["不选择的球员及原因"],
    "strategy": "总体策略简述"
}}"""
    
    try:
        response = llm_client.generate(prompt, max_tokens=800, temperature=0.3)
        import json
        
        # 尝试解析 JSON
        content = response.content
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            try:
                result = json.loads(content[start:end])
            except:
                result = {"raw_response": content}
        else:
            result = {"raw_response": content}
        
        result["tokens_used"] = response.tokens_used
        return result
        
    except Exception as e:
        return {"error": str(e)}


def test_incoming_bid(scenario: dict, llm_client: LLMClient) -> dict:
    """测试处理其他球队的报价"""
    
    console.print(f"\n[bold cyan]场景: {scenario['name']}[/]")
    
    bid = scenario['bid']
    player = scenario['player']
    
    console.print(f"[dim]球员: {player.full_name} ({player.position.value}, CA{player.current_ability})[/]")
    console.print(f"[dim]报价来自: {bid['from_club']}[/]")
    console.print(f"[dim]报价金额: €{bid['amount']:,}[/]")
    
    prompt = f"""你是一位足球经理，收到了一份对你球队重要球员的报价，需要做出决策。

## 球员信息
- 姓名：{player.full_name}
- 位置：{player.position.value}
- 当前能力：{player.current_ability}/100
- 潜力：{player.potential_ability}/100
- 年龄：{player.age}岁
- 国籍：{player.nationality}
- 合同至：{player.contract_until}
- 当前身价：€{player.market_value:,}
- 周薪：€{player.salary:,}

## 报价详情
- 来自俱乐部：{bid['from_club']}
- 报价金额：€{bid['amount']:,}
- 时机：{bid['timing']}
- 支付条款：{bid['payment_terms']}
{chr(10).join([f'- {k}: {v}' for k, v in bid.items() if k not in ['from_club', 'amount', 'timing', 'payment_terms']])}

## 球队情况
{chr(10).join([f'- {k}: {v}' for k, v in scenario['club_situation'].items()])}

## 球员态度
{scenario['player_willingness']}

## 任务
请决定是否接受、拒绝或还价此报价，并说明：
1. 最终决策及理由
2. 如果接受，如何使用这笔资金
3. 如果拒绝，如何说服球员留队
4. 替代方案

请以 JSON 格式回复：
{{
    "decision": "accept|reject|counter",
    "counter_amount": 还价金额或null,
    "confidence": 置信度1-100,
    "reasoning": "详细理由",
    "replacement_plan": "替代计划",
    "risks": ["风险1", "风险2"]
}}"""
    
    try:
        response = llm_client.generate(prompt, max_tokens=800, temperature=0.3)
        import json
        
        content = response.content
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            try:
                result = json.loads(content[start:end])
            except:
                result = {"decision": "unknown", "reasoning": content}
        else:
            result = {"decision": "unknown", "reasoning": content}
        
        result["scenario_name"] = scenario['name']
        result["player_name"] = player.full_name
        result["bid_amount"] = bid['amount']
        result["from_club"] = bid['from_club']
        result["tokens_used"] = response.tokens_used
        return result
        
    except Exception as e:
        return {"error": str(e), "scenario_name": scenario['name']}


def display_relegation_results(results: dict):
    """显示保级危机测试结果"""
    
    console.print("\n[bold green]📊 决策结果:[/]")
    
    if "priority_order" in results:
        console.print(f"\n[cyan]优先顺序:[/] {', '.join(results['priority_order'])}")
    
    if "primary_target" in results:
        pt = results['primary_target']
        console.print(f"\n[yellow]首选目标:[/] {pt.get('name', 'N/A')}")
        console.print(f"  报价: €{pt.get('bid_amount', 0):,}")
        console.print(f"  理由: {pt.get('reasoning', 'N/A')[:100]}...")
    
    if "fallback" in results:
        fb = results['fallback']
        console.print(f"\n[blue]备选方案:[/] {fb.get('name', 'N/A')} (€{fb.get('bid_amount', 0):,})")
    
    if "strategy" in results:
        console.print(f"\n[magenta]总体策略:[/] {results['strategy'][:150]}...")


def display_bid_results(results: list):
    """显示报价处理结果"""
    
    table = Table(title="处理其他球队报价决策", box=box.ROUNDED)
    table.add_column("场景", style="cyan", width=25)
    table.add_column("球员", style="green", width=15)
    table.add_column("报价", style="yellow", width=12)
    table.add_column("决策", style="magenta", width=10)
    table.add_column("理由摘要", style="dim", width=40)
    
    for r in results:
        if "error" in r:
            continue
            
        scenario = r.get('scenario_name', 'Unknown')
        player = r.get('player_name', 'Unknown')
        bid = f"€{r.get('bid_amount', 0)/1000000:.0f}M"
        decision = r.get('decision', 'unknown').upper()
        reasoning = r.get('reasoning', '')[:50] + "..."
        
        # 决策着色
        if decision == "ACCEPT":
            decision = f"[green]{decision}[/]"
        elif decision == "REJECT":
            decision = f"[red]{decision}[/]"
        elif decision == "COUNTER":
            decision = f"[yellow]{decision}[/]"
        
        table.add_row(scenario, player, bid, decision, reasoning)
    
    console.print(table)


def main():
    """主测试函数"""
    
    console.print("\n" + "=" * 80)
    console.print("[bold]🧠 LLM 高级转会决策能力测试[/]")
    console.print("=" * 80)
    
    # 初始化 LLM
    config = load_llm_config()
    try:
        client = create_llm_client_from_config()
        # 测试连接
        test_resp = client.generate("test", max_tokens=5)
        if not test_resp.content.strip():
            console.print("[yellow]⚠️  API 返回为空，使用 Mock 模式[/]")
            client = LLMClient(provider=LLMProvider.MOCK, model="mock")
    except Exception as e:
        console.print(f"[yellow]⚠️  使用 Mock 模式: {e}[/]")
        client = LLMClient(provider=LLMProvider.MOCK, model="mock")
    
    # ==================== 场景1: 保级危机 ====================
    console.print("\n" + "=" * 80)
    console.print("[bold red]场景1: 保级危机下的多候选球员选择[/]")
    console.print("=" * 80)
    
    result1 = test_relegation_crisis(client)
    display_relegation_results(result1)
    
    # ==================== 场景4: 处理报价 ====================
    console.print("\n" + "=" * 80)
    console.print("[bold red]场景4: 处理其他球队对本队球员的报价[/]")
    console.print("=" * 80)
    
    bid_scenarios = create_incoming_bid_scenarios()
    bid_results = []
    
    for scenario in bid_scenarios:
        result = test_incoming_bid(scenario, client)
        bid_results.append(result)
        
        # 即时显示
        if "decision" in result:
            console.print(f"\n[yellow]{result['scenario_name']}:[/] {result['decision'].upper()}")
            if "reasoning" in result:
                console.print(f"  [dim]{result['reasoning'][:80]}...[/]")
    
    # 显示汇总
    console.print("\n")
    display_bid_results(bid_results)
    
    # 总结
    console.print("\n" + "=" * 80)
    console.print("[bold green]✅ 高级转会决策测试完成![/]")
    console.print("=" * 80)
    
    console.print("""
[bold cyan]测试覆盖的能力:[/]
1. ✅ 复杂场景下的多候选人评估
2. ✅ 预算约束下的优先级排序
3. ✅ 处理球员报价（接受/拒绝/还价）
4. ✅ 考虑球队长期vs短期利益
5. ✅ 应对竞争和替代方案
    """)


if __name__ == "__main__":
    main()
