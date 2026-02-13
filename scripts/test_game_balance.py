#!/usr/bin/env python3
"""
游戏平衡测试脚本

运行100赛季模拟来测试游戏平衡性
"""

import asyncio
import sys
sys.path.insert(0, '.')

from fm_manager.core import init_db, get_session_maker, close_db
from fm_manager.core.models.club import Club
from fm_manager.core.models.league import League
from sqlalchemy import select
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from collections import defaultdict
import random

console = Console()


async def run_balance_test(num_seasons: int = 10):
    """运行游戏平衡测试"""
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # 获取联赛
        result = await session.execute(select(League).limit(1))
        league = result.scalar_one_or_none()
        
        if not league:
            console.print("[red]❌ 没有找到联赛数据[/red]")
            return
        
        # 获取所有俱乐部
        result = await session.execute(
            select(Club).where(Club.league_id == league.id)
        )
        clubs = result.scalars().all()
        
        if len(clubs) < 2:
            console.print("[red]❌ 联赛中俱乐部数量不足[/red]")
            return
        
        console.print(Panel(
            f"[cyan]游戏平衡测试[/cyan]\n\n"
            f"联赛: {league.name}\n"
            f"俱乐部数: {len(clubs)}\n"
            f"模拟赛季数: {num_seasons}",
            title="测试配置",
            border_style="cyan"
        ))
        
        # 统计数据
        stats = {
            'champions': defaultdict(int),
            'goals_scored': defaultdict(int),
            'goals_conceded': defaultdict(int),
            'wins': defaultdict(int),
            'draws': defaultdict(int),
            'losses': defaultdict(int),
            'total_matches': 0,
            'total_goals': 0
        }
        
        # 运行多个赛季模拟
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]模拟赛季中...", total=num_seasons)
            
            for season_num in range(num_seasons):
                season_stats = await simulate_season(clubs, session)
                
                # 统计冠军
                if season_stats['champion']:
                    stats['champions'][season_stats['champion']] += 1
                
                # 统计其他数据
                for club_id, club_stats in season_stats['club_stats'].items():
                    stats['goals_scored'][club_id] += club_stats.get('goals_for', 0)
                    stats['goals_conceded'][club_id] += club_stats.get('goals_against', 0)
                    stats['wins'][club_id] += club_stats.get('wins', 0)
                    stats['draws'][club_id] += club_stats.get('draws', 0)
                    stats['losses'][club_id] += club_stats.get('losses', 0)
                    stats['total_matches'] += club_stats.get('matches', 0)
                    stats['total_goals'] += club_stats.get('goals_for', 0)
                
                progress.update(task, advance=1, description=f"[cyan]已完成 {season_num + 1}/{num_seasons} 赛季[/cyan]")
        
        # 显示结果
        display_results(clubs, stats, num_seasons)
    
    await close_db()


async def simulate_season(clubs, session):
    """模拟一个赛季"""
    
    # 创建简单的联赛赛程
    matches = []
    club_list = list(clubs)
    
    for i, home_club in enumerate(club_list):
        for j, away_club in enumerate(club_list):
            if i != j:
                matches.append((home_club, away_club))
    
    # 随机打乱赛程
    random.shuffle(matches)
    
    # 模拟所有比赛
    club_stats = defaultdict(lambda: {
        'wins': 0, 'draws': 0, 'losses': 0,
        'goals_for': 0, 'goals_against': 0,
        'points': 0, 'matches': 0
    })
    
    for home_club, away_club in matches:
        # 简单模拟比赛结果
        home_strength = home_club.reputation / 10000
        away_strength = away_club.reputation / 10000
        
        # 添加随机性
        home_factor = random.uniform(0.8, 1.2)
        away_factor = random.uniform(0.8, 1.2)
        
        # 主场优势
        home_advantage = 1.1
        
        home_score = int(random.gauss(home_strength * 2.5 * home_factor * home_advantage, 1.2))
        away_score = int(random.gauss(away_strength * 2.5 * away_factor, 1.2))
        
        # 确保非负
        home_score = max(0, home_score)
        away_score = max(0, away_score)
        
        # 更新统计
        club_stats[home_club.id]['goals_for'] += home_score
        club_stats[home_club.id]['goals_against'] += away_score
        club_stats[home_club.id]['matches'] += 1
        
        club_stats[away_club.id]['goals_for'] += away_score
        club_stats[away_club.id]['goals_against'] += home_score
        club_stats[away_club.id]['matches'] += 1
        
        if home_score > away_score:
            club_stats[home_club.id]['wins'] += 1
            club_stats[home_club.id]['points'] += 3
            club_stats[away_club.id]['losses'] += 1
        elif home_score < away_score:
            club_stats[away_club.id]['wins'] += 1
            club_stats[away_club.id]['points'] += 3
            club_stats[home_club.id]['losses'] += 1
        else:
            club_stats[home_club.id]['draws'] += 1
            club_stats[away_club.id]['draws'] += 1
            club_stats[home_club.id]['points'] += 1
            club_stats[away_club.id]['points'] += 1
    
    # 找出冠军
    champion = max(club_stats.items(), key=lambda x: x[1]['points'])[0] if club_stats else None
    
    return {
        'champion': champion,
        'club_stats': dict(club_stats)
    }


def display_results(clubs, stats, num_seasons):
    """显示测试结果"""
    
    console.print("\n" + "="*70)
    console.print("[bold cyan]游戏平衡测试结果[/bold cyan]")
    console.print("="*70)
    
    # 冠军分布
    console.print("\n[bold green]冠军分布:[/bold green]")
    champion_table = Table(box=None)
    champion_table.add_column("俱乐部", min_width=25)
    champion_table.add_column("夺冠次数", justify="right")
    champion_table.add_column("夺冠率", justify="right")
    
    club_map = {c.id: c.name for c in clubs}
    sorted_champions = sorted(stats['champions'].items(), key=lambda x: x[1], reverse=True)
    
    for club_id, count in sorted_champions:
        rate = count / num_seasons * 100
        champion_table.add_row(
            club_map.get(club_id, f"Club {club_id}"),
            str(count),
            f"{rate:.1f}%"
        )
    
    console.print(champion_table)
    
    # 进攻统计
    console.print("\n[bold green]进攻统计 (平均每赛季):[/bold green]")
    offense_table = Table(box=None)
    offense_table.add_column("俱乐部", min_width=25)
    offense_table.add_column("总进球", justify="right")
    offense_table.add_column("场均进球", justify="right")
    
    sorted_offense = sorted(stats['goals_scored'].items(), key=lambda x: x[1], reverse=True)
    
    for club_id, goals in sorted_offense[:5]:
        matches = stats['wins'][club_id] + stats['draws'][club_id] + stats['losses'][club_id]
        avg_goals = goals / matches if matches > 0 else 0
        offense_table.add_row(
            club_map.get(club_id, f"Club {club_id}"),
            str(goals),
            f"{avg_goals:.2f}"
        )
    
    console.print(offense_table)
    
    # 总体统计
    avg_goals_per_match = stats['total_goals'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
    
    console.print(Panel(
        f"总比赛场数: {stats['total_matches']}\n"
        f"总进球数: {stats['total_goals']}\n"
        f"场均进球: {avg_goals_per_match:.2f}\n\n"
        f"[dim]平衡性评估:[/dim]\n"
        f"- 场均进球在 2.5-3.5 之间为正常范围\n"
        f"- 夺冠分布相对均匀表示平衡性良好",
        title="总体统计",
        border_style="blue"
    ))
    
    # 平衡性评级
    if 2.0 <= avg_goals_per_match <= 3.5:
        balance_rating = "[green]✅ 平衡性良好[/green]"
    elif 1.5 <= avg_goals_per_match < 2.0 or 3.5 < avg_goals_per_match <= 4.5:
        balance_rating = "[yellow]⚠️  需要微调[/yellow]"
    else:
        balance_rating = "[red]❌ 需要调整[/red]"
    
    console.print(f"\n{balance_rating}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="游戏平衡测试")
    parser.add_argument("--seasons", type=int, default=10, help="模拟赛季数 (默认: 10)")
    args = parser.parse_args()
    
    console.print(f"[cyan]开始运行 {args.seasons} 赛季平衡测试...[/cyan]\n")
    asyncio.run(run_balance_test(args.seasons))
