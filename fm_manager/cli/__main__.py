#!/usr/bin/env python3
"""FM Manager CLI entry point.

Usage:
    python -m fm_manager.cli [command]
    python -m fm_manager.cli tactics show-roles
    python -m fm_manager.cli club show-facilities
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel

console = Console()


# Import command groups
from fm_manager.cli.tactics_cli import tactics
from fm_manager.cli.club_cli import club


@click.group()
def cli():
    """FM Manager - 足球经理游戏命令行工具
    
    管理你的足球俱乐部，包括战术设置、设施升级、员工管理等。
    
    示例:
        fm_manager.cli tactics show-roles     # 显示球员角色
        fm_manager.cli club show-facilities   # 显示设施
        fm_manager.cli club finances          # 查看财务
    """
    pass


# Add command groups
cli.add_command(tactics)
cli.add_command(club)


@cli.command()
def version():
    """显示版本信息"""
    console.print(Panel(
        "[bold cyan]FM Manager CLI[/bold cyan]\n"
        "版本: 1.0.0\n"
        "作者: AI Assistant",
        title="版本信息"
    ))


@cli.command()
def menu():
    """显示主菜单"""
    console.print(Panel(
        "[bold cyan]足球经理游戏 - 主菜单[/bold cyan]\n\n"
        "[yellow]战术管理:[/yellow]\n"
        "  tactics show-roles    - 查看球员角色\n"
        "  tactics show-styles   - 查看比赛风格\n\n"
        "[yellow]俱乐部管理:[/yellow]\n"
        "  club show-facilities  - 查看设施\n"
        "  club show-staff       - 查看员工\n"
        "  club finances         - 查看财务\n\n"
        "使用 [cyan]--help[/cyan] 查看详细帮助",
        title="主菜单"
    ))


if __name__ == "__main__":
    cli()
