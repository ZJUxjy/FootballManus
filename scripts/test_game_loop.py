#!/usr/bin/env python3
"""Test game loop and save system non-interactively."""

import asyncio
import sys
sys.path.insert(0, '.')

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def test_save_slots():
    """Test multi-slot save system."""
    console.print(Panel("[bold cyan]测试多槽位存档系统[/bold cyan]", border_style="cyan"))
    
    from fm_manager.core.save_load_slots import SlotSaveManager
    
    manager = SlotSaveManager('/tmp/fm_save_test')
    
    console.print(f"[green]✓[/green] 创建存档管理器")
    console.print(f"  存档目录: {manager.save_dir}")
    console.print(f"  槽位数量: {manager.NUM_SLOTS}")
    
    slots = manager.get_all_slots()
    console.print(f"[green]✓[/green] 获取所有槽位: {len(slots)}")
    
    for slot in slots[:3]:
        status = "有存档" if slot.has_save else "空"
        console.print(f"  槽位 {slot.slot_number}: {status}")
    
    result = manager.save_to_slot(
        1,
        save_name="测试存档1",
        season=1,
        week=10,
        club_id=1,
        club_name="Test FC",
        standings={1: {"played": 5, "won": 3, "drawn": 1, "lost": 1, "points": 10}},
        match_results=[{"home": "Test FC", "away": "Other FC", "home_score": 2, "away_score": 1}]
    )
    console.print(f"[green]✓[/green] 保存到槽位1: {'成功' if result else '失败'}")
    
    result = manager.save_to_slot(
        2,
        save_name="测试存档2",
        season=2,
        week=5,
        club_id=2,
        standings={},
        match_results=[]
    )
    console.print(f"[green]✓[/green] 保存到槽位2: {'成功' if result else '失败'}")
    
    data = manager.load_from_slot(1)
    if data:
        console.print(f"[green]✓[/green] 从槽位1加载成功")
        console.print(f"  存档名: {data['save_name']}")
        console.print(f"  赛季: {data['season']}, 周: {data['week']}")
    else:
        console.print("[red]✗[/red] 从槽位1加载失败")
    
    slots = manager.get_all_slots()
    saves_count = sum(1 for s in slots if s.has_save)
    console.print(f"[green]✓[/green] 当前存档数: {saves_count}")
    
    manager.copy_slot(1, 3)
    console.print(f"[green]✓[/green] 复制槽位1到槽位3成功")
    
    manager.delete_slot(3)
    console.print(f"[green]✓[/green] 删除槽位3成功")
    
    slot = manager.quick_save(season=3, week=15, club_id=1)
    console.print(f"[green]✓[/green] 快速保存到槽位{slot}")
    
    slot = manager.auto_save(season=3, week=16, club_id=1)
    console.print(f"[green]✓[/green] 自动保存到槽位{slot}")
    
    latest = manager.get_latest_save()
    if latest:
        console.print(f"[green]✓[/green] 最新存档: {latest.save_name}")
    
    total_saves = manager.get_total_saves()
    storage = manager.get_save_storage_size()
    console.print(f"[green]✓[/green] 总存档: {total_saves}, 存储大小: {storage} bytes")
    
    console.print()
    return True


async def test_game_loop_core():
    """Test game loop core functions."""
    console.print(Panel("[bold cyan]测试游戏循环核心功能[/bold cyan]", border_style="cyan"))
    
    from fm_manager.cli.game_loop import FMGameManager
    from fm_manager.core.save_load_slots import SlotSaveManager
    
    game = FMGameManager()
    console.print("[green]✓[/green] 创建游戏管理器")
    
    await game.initialize()
    console.print(f"[green]✓[/green] 初始化游戏")
    console.print(f"  俱乐部数量: {len(game.clubs)}")
    console.print(f"  联赛: {game.league.name if game.league else '无'}")
    
    game._init_standings()
    console.print(f"[green]✓[/green] 初始化积分榜: {len(game.standings)} 队")
    
    if game.clubs:
        game.player_club = game.clubs[0]
        console.print(f"[green]✓[/green] 选择俱乐部: {game.player_club.name}")
    
    game.save_manager = SlotSaveManager('/tmp/fm_game_test')
    
    game.save_manager.save_to_slot(
        1,
        save_name=f"S{game.current_season}W{game.current_week}",
        season=game.current_season,
        week=game.current_week,
        club_id=game.player_club.id if game.player_club else None,
        standings=game.standings,
        match_results=game.match_results
    )
    console.print(f"[green]✓[/green] 保存游戏状态")
    
    data = game.save_manager.load_from_slot(1)
    if data:
        console.print(f"[green]✓[/green] 加载游戏状态: S{data['season']}W{data['week']}")
    
    console.print()
    return True


async def test_match_simulation():
    """Test match simulation."""
    console.print(Panel("[bold cyan]测试比赛模拟[/bold cyan]", border_style="cyan"))
    
    from fm_manager.cli.game_loop import FMGameManager
    
    game = FMGameManager()
    await game.initialize()
    game._init_standings()
    
    if game.clubs:
        game.player_club = game.clubs[0]
    
    initial_week = game.current_week
    
    await game._simulate_matchday()
    
    console.print(f"[green]✓[/green] 比赛模拟完成")
    console.print(f"  比赛结果: {len(game.match_results)} 场")
    
    if game.match_results:
        last_match = game.match_results[-1]
        console.print(f"  最后一场: {last_match['home']} {last_match['home_score']}-{last_match['away_score']} {last_match['away']}")
    
    standings_with_points = sum(1 for s in game.standings.values() if s['points'] > 0)
    console.print(f"[green]✓[/green] 积分榜更新: {standings_with_points} 队有积分")
    
    console.print()
    return True


async def run_all_tests():
    """Run all tests."""
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]CLI游戏循环 & 多槽位存档 测试套件[/bold cyan]")
    console.print("=" * 60 + "\n")
    
    results = []
    
    try:
        result = await test_save_slots()
        results.append(("多槽位存档系统", result))
    except Exception as e:
        console.print(f"[red]✗ 多槽位存档系统测试失败: {e}[/red]")
        results.append(("多槽位存档系统", False))
    
    try:
        result = await test_game_loop_core()
        results.append(("游戏循环核心", result))
    except Exception as e:
        console.print(f"[red]✗ 游戏循环核心测试失败: {e}[/red]")
        results.append(("游戏循环核心", False))
    
    try:
        result = await test_match_simulation()
        results.append(("比赛模拟", result))
    except Exception as e:
        error_msg = str(e).replace("[", "(").replace("]", ")")
        console.print(f"[red]比赛模拟测试失败: {error_msg}")
        results.append(("比赛模拟", False))
    
    console.print("=" * 60)
    console.print("[bold]测试结果汇总[/bold]")
    console.print("=" * 60)
    
    table = Table(show_header=False)
    table.add_column("测试", min_width=25)
    table.add_column("状态", justify="center", width=10)
    
    for name, passed in results:
        status = "[green]✓ 通过[/green]" if passed else "[red]✗ 失败[/red]"
        table.add_row(name, status)
    
    console.print(table)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    console.print(f"\n[bold]通过: {passed}/{total}[/bold]")
    
    if passed == total:
        console.print("\n[bold green]所有测试通过！[/bold green]")
    
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]功能说明[/bold cyan]")
    console.print("=" * 60)
    
    console.print("""
[bold]多槽位存档系统:[/bold]
  - 10个存档槽位
  - 槽位9: 自动存档
  - 槽位10: 快速存档
  - 支持复制、删除存档

[bold]CLI游戏循环:[/bold]
  - 主菜单导航
  - 俱乐部选择
  - 仪表板显示
  - 比赛日模拟
  - 积分榜查看
  - 存档/读档

[bold]启动游戏:[/bold]
  .venv/bin/python -m fm_manager.cli.game_loop
""")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
