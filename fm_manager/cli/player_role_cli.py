#!/usr/bin/env python3
"""
球员角色分配CLI

提供命令行界面用于为球员分配战术角色
"""

import asyncio
import click
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.models.player import Player
from fm_manager.core.models.club import Club
from fm_manager.core.models.tactics import (
    PlayerRole, RoleManager, TacticalFormation, TacticalInstructions
)
from sqlalchemy import select

console = Console()


@click.group()
def player_role():
    """球员角色分配管理"""
    pass


@player_role.command()
@click.option("-c", "--club-id", type=int, required=True, help="俱乐部ID")
def list_players(club_id: int):
    """列出俱乐部的所有球员"""
    asyncio.run(_list_players(club_id))


async def _list_players(club_id: int):
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # 获取俱乐部信息
        club_result = await session.execute(
            select(Club).where(Club.id == club_id)
        )
        club = club_result.scalar_one_or_none()
        
        if not club:
            console.print(f"[red]❌ 未找到ID为 {club_id} 的俱乐部[/red]")
            return
        
        # 获取球员列表
        result = await session.execute(
            select(Player).where(Player.club_id == club_id)
        )
        players = result.scalars().all()
        
        if not players:
            console.print(f"[yellow]⚠️  {club.name} 没有球员[/yellow]")
            return
        
        # 显示球员表格
        table = Table(
            title=f"{club.name} 球员列表",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("ID", style="dim", width=6)
        table.add_column("姓名", min_width=20)
        table.add_column("位置", width=8)
        table.add_column("能力", justify="right", width=6)
        table.add_column("潜力", justify="right", width=6)
        table.add_column("年龄", justify="right", width=6)
        table.add_column("角色", min_width=25)
        
        for player in players:
            role_display = player.role if player.role else "[dim]未分配[/dim]"
            table.add_row(
                str(player.id),
                f"{player.first_name} {player.last_name}",
                player.position.value if player.position else "-",
                str(getattr(player, 'current_ability', 50)),
                str(getattr(player, 'potential_ability', 60)),
                str(getattr(player, 'age', 25)),
                role_display
            )
        
        console.print(table)
        console.print(f"\n[green]总计: {len(players)} 名球员[/green]")
    
    await close_db()


@player_role.command()
def list_roles():
    """列出所有可用的球员角色"""
    manager = RoleManager()
    
    table = Table(
        title="可用球员角色",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("角色代码", min_width=25)
    table.add_column("类别", width=12)
    table.add_column("适合位置", min_width=30)
    table.add_column("描述", min_width=40)
    
    for role in PlayerRole:
        profile = manager.get_role_profile(role)
        if profile:
            table.add_row(
                role.value,
                role.category,
                ", ".join(profile.suitable_positions[:5]),
                profile.description[:50] + "..." if len(profile.description) > 50 else profile.description
            )
    
    console.print(table)
    console.print(f"\n[green]总计: {len(list(PlayerRole))} 种角色[/green]")


@player_role.command()
@click.option("-p", "--player-id", type=int, required=True, help="球员ID")
@click.option("-r", "--role", type=str, required=True, help="角色代码 (如: playmaker, winger)")
def assign(player_id: int, role: str):
    """为球员分配角色"""
    asyncio.run(_assign_role(player_id, role))


async def _assign_role(player_id: int, role_str: str):
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # 获取球员
        result = await session.execute(
            select(Player).where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()
        
        if not player:
            console.print(f"[red]❌ 未找到ID为 {player_id} 的球员[/red]")
            return
        
        # 验证角色
        try:
            role = PlayerRole(role_str.lower())
        except ValueError:
            console.print(f"[red]❌ 无效的角色: {role_str}[/red]")
            console.print("[yellow]可用角色:[/yellow]")
            for r in PlayerRole:
                console.print(f"  - {r.value}")
            return
        
        # 检查角色是否适合球员位置
        manager = RoleManager()
        profile = manager.get_role_profile(role)
        
        if profile and player.position:
            position_str = player.position.value
            suitable_positions = profile.suitable_positions
            
            if position_str not in suitable_positions:
                console.print(f"[yellow]⚠️  警告: {role.value} 通常不适合 {position_str} 位置[/yellow]")
                console.print(f"[dim]适合位置: {', '.join(suitable_positions)}[/dim]")
                
                if not click.confirm("是否仍要分配此角色?"):
                    return
        
        # 分配角色
        player.role = role.value
        await session.commit()
        
        console.print(Panel(
            f"[green]✅ 成功为 {player.first_name} {player.last_name} 分配角色[/green]\n\n"
            f"球员: {player.first_name} {player.last_name}\n"
            f"位置: {player.position.value if player.position else 'N/A'}\n"
            f"新角色: [cyan]{role.value}[/cyan]\n"
            f"类别: {role.category}",
            title="角色分配成功",
            border_style="green"
        ))
    
    await close_db()


@player_role.command()
@click.option("-p", "--player-id", type=int, required=True, help="球员ID")
def suggest(player_id: int):
    """为球员推荐适合的角色"""
    asyncio.run(_suggest_roles(player_id))


async def _suggest_roles(player_id: int):
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        result = await session.execute(
            select(Player).where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()
        
        if not player:
            console.print(f"[red]❌ 未找到ID为 {player_id} 的球员[/red]")
            return
        
        manager = RoleManager()
        
        # 获取适合该位置的所有角色
        if player.position:
            suitable_roles = manager.get_suitable_roles(player.position.value)
        else:
            suitable_roles = list(PlayerRole)
        
        console.print(Panel(
            f"[cyan]{player.first_name} {player.last_name}[/cyan] 的角色推荐\n"
            f"位置: {player.position.value if player.position else 'N/A'}",
            title="角色推荐",
            border_style="cyan"
        ))
        
        table = Table(box=box.ROUNDED)
        table.add_column("角色", min_width=25)
        table.add_column("类别", width=12)
        table.add_column("描述", min_width=50)
        
        for role in suitable_roles[:10]:  # 只显示前10个
            profile = manager.get_role_profile(role)
            if profile:
                table.add_row(
                    role.value,
                    role.category,
                    profile.description[:60] + "..." if len(profile.description) > 60 else profile.description
                )
        
        console.print(table)
        console.print(f"\n[dim]使用: fm-manager player-role assign -p {player_id} -r <角色代码>[/dim]")
    
    await close_db()


@player_role.command()
@click.option("-c", "--club-id", type=int, required=True, help="俱乐部ID")
@click.option("-f", "--formation", type=str, default="4-3-3", help="阵型 (如: 4-3-3, 4-2-3-1)")
def auto_assign(club_id: int, formation: str):
    """自动为俱乐部所有球员分配推荐角色"""
    asyncio.run(_auto_assign_roles(club_id, formation))


async def _auto_assign_roles(club_id: int, formation: str):
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        club_result = await session.execute(
            select(Club).where(Club.id == club_id)
        )
        club = club_result.scalar_one_or_none()
        
        if not club:
            console.print(f"[red]❌ 未找到ID为 {club_id} 的俱乐部[/red]")
            return
        
        result = await session.execute(
            select(Player).where(Player.club_id == club_id)
        )
        players = result.scalars().all()
        
        if not players:
            console.print(f"[yellow]⚠️  {club.name} 没有球员[/yellow]")
            return
        
        manager = RoleManager()
        assigned_count = 0
        
        with console.status("[cyan]正在自动分配角色...[/cyan]"):
            for player in players:
                if player.position:
                    suitable_roles = manager.get_suitable_roles(player.position.value)
                    if suitable_roles:
                        # 分配第一个适合的角色
                        player.role = suitable_roles[0].value
                        assigned_count += 1
        
        await session.commit()
        
        console.print(Panel(
            f"[green]✅ 自动角色分配完成[/green]\n\n"
            f"俱乐部: {club.name}\n"
            f"总球员: {len(players)}\n"
            f"已分配: {assigned_count}\n"
            f"阵型: {formation}",
            title="批量分配完成",
            border_style="green"
        ))
    
    await close_db()


if __name__ == "__main__":
    player_role()
