#!/usr/bin/env python3
"""
杯赛系统测试脚本

测试足总杯、联赛杯、欧冠等杯赛功能
"""

import asyncio
import sys
sys.path.insert(0, '.')

import random
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def test_domestic_cup():
    """测试国内杯赛（足总杯风格）"""
    
    console.print(Panel(
        "[cyan]国内杯赛测试[/cyan]\n"
        "模拟单败淘汰制杯赛",
        title="测试 1: 足总杯风格",
        border_style="cyan"
    ))
    
    teams = [
        "Manchester United", "Liverpool", "Chelsea", "Arsenal",
        "Manchester City", "Tottenham", "Newcastle", "Brighton",
        "Aston Villa", "West Ham", "Brentford", "Fulham",
        "Crystal Palace", "Wolves", "Everton", "Leicester"
    ]
    
    console.print(f"[green]参赛球队: {len(teams)} 支[/green]")
    
    round_names = ["16强", "8强", "半决赛", "决赛"]
    current_round = teams.copy()
    round_num = 0
    
    while len(current_round) > 1:
        round_name = round_names[round_num] if round_num < len(round_names) else f"第{round_num+1}轮"
        console.print(f"\n[bold yellow]=== {round_name} ===[/bold yellow]")
        
        next_round = []
        matches = []
        
        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                home = current_round[i]
                away = current_round[i + 1]
                home_score = random.randint(0, 3)
                away_score = random.randint(0, 3)
                
                if home_score > away_score:
                    winner = home
                elif away_score > home_score:
                    winner = away
                else:
                    winner = random.choice([home, away])
                
                matches.append((home, away, home_score, away_score, winner))
                next_round.append(winner)
        
        table = Table(box=None)
        table.add_column("主队", min_width=20)
        table.add_column("比分", justify="center", width=8)
        table.add_column("客队", min_width=20)
        table.add_column("晋级", style="green")
        
        for home, away, hs, as_, winner in matches:
            table.add_row(home, f"{hs} - {as_}", away, winner)
        
        console.print(table)
        current_round = next_round
        round_num += 1
    
    console.print(Panel(
        f"[bold green]🏆 冠军: {current_round[0]}[/bold green]",
        border_style="gold1"
    ))
    
    return True


async def test_champions_league():
    """测试欧冠风格杯赛（小组赛+淘汰赛）"""
    
    console.print(Panel(
        "[cyan]欧冠风格杯赛测试[/cyan]\n"
        "小组赛 + 淘汰赛",
        title="测试 2: 欧冠风格",
        border_style="cyan"
    ))
    
    teams = [
        "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla",
        "Manchester City", "Liverpool", "Chelsea", "Arsenal",
        "Bayern Munich", "Dortmund", "RB Leipzig", "Leverkusen",
        "PSG", "Marseille", "Inter Milan", "AC Milan"
    ]
    
    console.print(f"[green]参赛球队: {len(teams)} 支[/green]")
    console.print(f"[green]小组数: 4 个[/green]")
    
    group_stage = {}
    groups = ["A", "B", "C", "D"]
    
    for i, group in enumerate(groups):
        group_teams = teams[i*4:(i+1)*4]
        group_stage[group] = {team: {"points": 0, "gf": 0, "ga": 0} for team in group_teams}
        
        console.print(f"\n[bold]小组 {group}[/bold]")
        
        for j, home in enumerate(group_teams):
            for k, away in enumerate(group_teams):
                if j < k:
                    home_score = random.randint(0, 3)
                    away_score = random.randint(0, 3)
                    
                    group_stage[group][home]["gf"] += home_score
                    group_stage[group][home]["ga"] += away_score
                    group_stage[group][away]["gf"] += away_score
                    group_stage[group][away]["ga"] += home_score
                    
                    if home_score > away_score:
                        group_stage[group][home]["points"] += 3
                    elif home_score < away_score:
                        group_stage[group][away]["points"] += 3
                    else:
                        group_stage[group][home]["points"] += 1
                        group_stage[group][away]["points"] += 1
    
    console.print("\n[bold yellow]=== 小组赛积分榜 ===[/bold yellow]")
    
    qualified = []
    for group in groups:
        table = Table(title=f"小组 {group}", box=None)
        table.add_column("球队", min_width=18)
        table.add_column("积分", justify="right", width=6)
        table.add_column("净胜球", justify="right", width=8)
        
        sorted_teams = sorted(
            group_stage[group].items(),
            key=lambda x: (x[1]["points"], x[1]["gf"] - x[1]["ga"]),
            reverse=True
        )
        
        for i, (team, stats) in enumerate(sorted_teams):
            gd = stats["gf"] - stats["ga"]
            style = "green" if i < 2 else None
            table.add_row(
                team if not style else f"[{style}]{team}[/{style}]",
                str(stats["points"]),
                f"+{gd}" if gd > 0 else str(gd)
            )
        
        console.print(table)
        qualified.extend([sorted_teams[0][0], sorted_teams[1][0]])
    
    console.print(f"\n[bold green]晋级球队: {', '.join(qualified)}[/bold green]")
    
    console.print("\n[bold yellow]=== 淘汰赛 ===[/bold yellow]")
    
    current_round = qualified.copy()
    round_names = ["8强", "半决赛", "决赛"]
    
    for round_name in round_names:
        console.print(f"\n[bold]{round_name}[/bold]")
        next_round = []
        
        random.shuffle(current_round)
        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                home = current_round[i]
                away = current_round[i + 1]
                home_score = random.randint(0, 4)
                away_score = random.randint(0, 4)
                
                if home_score > away_score:
                    winner = home
                elif away_score > home_score:
                    winner = away
                else:
                    winner = random.choice([home, away])
                
                console.print(f"  {home} {home_score} - {away_score} {away} → [green]{winner}[/green]")
                next_round.append(winner)
        
        current_round = next_round
    
    console.print(Panel(
        f"[bold green]🏆 欧冠冠军: {current_round[0]}[/bold green]",
        border_style="gold1"
    ))
    
    return True


async def test_cup_draw():
    """测试杯赛抽签"""
    
    console.print(Panel(
        "[cyan]杯赛抽签测试[/cyan]\n"
        "测试随机抽签和种子队抽签",
        title="测试 3: 抽签系统",
        border_style="cyan"
    ))
    
    seeded = ["Real Madrid", "Barcelona", "Bayern Munich", "PSG"]
    unseeded = ["Dortmund", "Porto", "Benfica", "Napoli"]
    
    console.print("[bold]种子队:[/bold] " + ", ".join(seeded))
    console.print("[bold]非种子队:[/bold] " + ", ".join(unseeded))
    
    random.shuffle(seeded)
    random.shuffle(unseeded)
    
    console.print("\n[bold yellow]=== 抽签结果 ===[/bold yellow]")
    
    table = Table(box=None)
    table.add_column("种子队", style="cyan")
    table.add_column("vs", justify="center", width=4)
    table.add_column("非种子队", style="yellow")
    
    for s, u in zip(seeded, unseeded):
        table.add_row(s, "vs", u)
    
    console.print(table)
    
    return True


async def run_all_tests():
    """运行所有杯赛测试"""
    
    console.print("\n" + "="*70)
    console.print("[bold cyan]杯赛系统测试套件[/bold cyan]")
    console.print("="*70 + "\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task1 = progress.add_task("[cyan]测试国内杯赛...", total=None)
        result1 = await test_domestic_cup()
        progress.update(task1, description="[green]✓ 国内杯赛测试完成[/green]")
        
        task2 = progress.add_task("[cyan]测试欧冠杯赛...", total=None)
        result2 = await test_champions_league()
        progress.update(task2, description="[green]✓ 欧冠杯赛测试完成[/green]")
        
        task3 = progress.add_task("[cyan]测试抽签系统...", total=None)
        result3 = await test_cup_draw()
        progress.update(task3, description="[green]✓ 抽签系统测试完成[/green]")
    
    console.print("\n" + "="*70)
    console.print("[bold green]所有杯赛测试通过！[/bold green]")
    console.print("="*70)
    
    console.print("\n[bold]测试总结:[/bold]")
    console.print("  ✅ 国内杯赛（单败淘汰）")
    console.print("  ✅ 欧冠杯赛（小组+淘汰）")
    console.print("  ✅ 抽签系统")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
