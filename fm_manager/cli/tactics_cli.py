#!/usr/bin/env python3
"""战术管理CLI - Rich终端界面

提供战术系统相关的命令行界面，包括球员角色查看、比赛风格设置等功能。
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.tree import Tree
from rich.text import Text
from typing import Optional

from fm_manager.core.models.tactics import (
    PlayerRole,
    RoleManager,
    PlayStyle,
    PlayStyleManager,
    Formation,
    TacticalInstructionsValidator,
)

console = Console()


@click.group()
def tactics():
    """战术管理命令 - 管理球队战术、球员角色和比赛风格"""
    pass


@tactics.command()
def show_roles():
    """显示所有球员角色及其详细信息"""
    role_manager = RoleManager()
    
    # 按类别分组显示角色
    categories = {
        "attack": ("进攻型角色", "red"),
        "midfield": ("中场角色", "yellow"),
        "wide": ("边路角色", "cyan"),
        "defense": ("防守型角色", "blue"),
        "goalkeeper": ("门将角色", "green"),
    }
    
    console.print("\n[bold]⚽ 球员角色列表[/bold]\n")
    
    for category, (name, color) in categories.items():
        roles = role_manager.get_roles_by_category(category)
        
        table = Table(
            title=f"[bold {color}]{name}[/bold {color}]",
            show_header=True,
            header_style=f"bold {color}",
            border_style=color,
        )
        table.add_column("角色", style="cyan", no_wrap=True)
        table.add_column("适用位置", style="green")
        table.add_column("关键属性", style="yellow", max_width=30)
        table.add_column("描述", style="white", max_width=40)
        
        for role in roles:
            profile = role_manager.get_role_profile(role)
            if profile:
                # 获取前3个关键属性
                key_attrs = ", ".join(profile.get_primary_attributes(3))
                positions = ", ".join(profile.suitable_positions)
                table.add_row(
                    role.display_name,
                    positions,
                    key_attrs,
                    profile.description[:60] + "..." if len(profile.description) > 60 else profile.description
                )
        
        console.print(table)
        console.print()


@tactics.command()
@click.option("--role", "-r", type=str, help="查看特定角色的详细信息")
def role_detail(role: Optional[str]):
    """查看特定球员角色的详细信息"""
    role_manager = RoleManager()
    
    if role:
        # 查找角色
        found_role = None
        for pr in PlayerRole:
            if pr.value.lower() == role.lower() or pr.display_name == role:
                found_role = pr
                break
        
        if not found_role:
            console.print(f"[red]✗ 未找到角色: {role}[/red]")
            console.print("[dim]使用 'tactics show-roles' 查看所有可用角色[/dim]")
            return
        
        profile = role_manager.get_role_profile(found_role)
        
        # 创建角色详情面板
        content = Text()
        content.append(f"[bold cyan]{profile.display_name}[/bold cyan]\n\n", style="bold")
        content.append(f"[white]{profile.description}[/white]\n\n")
        content.append(f"[yellow]类别:[/yellow] {found_role.category}\n")
        content.append(f"[green]适用位置:[/green] {', '.join(profile.suitable_positions)}\n\n")
        content.append("[bold]关键属性权重:[/bold]\n")
        
        for attr, weight in sorted(profile.key_attributes.items(), key=lambda x: x[1], reverse=True):
            bar_length = int(weight * 50)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            content.append(f"  {attr:20} {bar} {weight:.0%}\n")
        
        content.append("\n[bold]行为修正器:[/bold]\n")
        for modifier, value in profile.behavior_modifiers.items():
            sign = "+" if value > 0 else ""
            color = "green" if value > 0 else "red" if value < 0 else "white"
            content.append(f"  {modifier:25} [{color}]{sign}{value:.1f}[/{color}]\n")
        
        panel = Panel(
            content,
            title=f"[bold]角色详情: {profile.display_name}[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(panel)
    else:
        # 显示所有角色的简要信息
        table = Table(title="所有球员角色")
        table.add_column("角色", style="cyan")
        table.add_column("类别", style="green")
        table.add_column("位置", style="yellow")
        
        for role in PlayerRole:
            profile = role_manager.get_role_profile(role)
            if profile:
                table.add_row(
                    role.display_name,
                    role.category,
                    ", ".join(profile.suitable_positions[:3])
                )
        
        console.print(table)


@tactics.command()
def list_styles():
    """列出所有可用的比赛风格"""
    style_manager = PlayStyleManager()
    styles = style_manager.get_all_styles()
    
    console.print("\n[bold]🎯 比赛风格列表[/bold]\n")
    
    for profile in styles:
        # 创建风格卡片
        tags_text = " ".join([f"[dim]{tag}[/dim]" for tag in profile.tags[:5]])
        
        content = Text()
        content.append(f"[bold]{profile.name}[/bold]\n", style="cyan")
        content.append(f"[white]{profile.description}[/white]\n\n")
        content.append(f"[yellow]标签:[/yellow] {tags_text}\n")
        content.append(f"[green]适用阵型:[/green] {', '.join(f.value for f in profile.suitable_formations[:4])}\n")
        
        # 战术参数摘要
        inst = profile.instructions
        content.append(f"\n[dim]防线:[/dim] {inst.defensive_line.name} | ")
        content.append(f"[dim]逼抢:[/dim] {inst.pressing.name} | ")
        content.append(f"[dim]节奏:[/dim] {inst.tempo.name} | ")
        content.append(f"[dim]传球:[/dim] {inst.passing_style.name}")
        
        panel = Panel(
            content,
            border_style="blue",
            padding=(1, 2),
        )
        console.print(panel)
        console.print()


@tactics.command()
@click.option("--style", "-s", type=click.Choice([s.value for s in PlayStyle], case_sensitive=False), 
              prompt="选择比赛风格", help="要应用的比赛风格")
@click.option("--formation", "-f", type=click.Choice([f.value for f in Formation], case_sensitive=False),
              help="指定阵型（可选）")
def set_style(style: str, formation: Optional[str]):
    """设置比赛风格并预览战术效果"""
    style_manager = PlayStyleManager()
    
    # 获取风格枚举
    try:
        play_style = PlayStyle(style.lower())
    except ValueError:
        console.print(f"[red]✗ 无效的比赛风格: {style}[/red]")
        return
    
    profile = style_manager.get_style_profile(play_style)
    
    # 显示风格详情面板
    tags_text = " • ".join(profile.tags)
    
    panel_content = f"""[bold cyan]{profile.name}[/bold cyan]

[white]{profile.description}[/white]

[yellow]风格标签:[/yellow] {tags_text}

[green]推荐阵型:[/green] {', '.join(f.value for f in profile.suitable_formations)}

[bold]核心战术指令:[/bold]
"""
    
    inst = profile.instructions
    panel_content += f"""
  • 防线高度: [cyan]{inst.defensive_line.name}[/cyan]
  • 逼抢强度: [cyan]{inst.pressing.name}[/cyan]
  • 球队宽度: [cyan]{inst.width.name}[/cyan]
  • 比赛节奏: [cyan]{inst.tempo.name}[/cyan]
  • 传球风格: [cyan]{inst.passing_style.name}[/cyan]
  • 拖延时间: [cyan]{inst.time_wasting.name}[/cyan]
"""
    
    if inst.counter_attack:
        panel_content += "  • [yellow]启用反击战术[/yellow]\n"
    if inst.hold_shape:
        panel_content += "  • [yellow]保持阵型[/yellow]\n"
    if inst.play_out_of_defence:
        panel_content += "  • [yellow]从后场组织[/yellow]\n"
    
    panel = Panel(
        panel_content,
        title="[bold]比赛风格配置[/bold]",
        border_style="green",
        padding=(1, 2),
    )
    console.print("\n", panel)
    
    # 显示推荐角色
    console.print("\n[bold]推荐球员角色配置:[/bold]")
    roles_tree = Tree("[cyan]阵型位置[/cyan]")
    
    for position, roles in list(profile.recommended_roles.items())[:6]:
        pos_branch = roles_tree.add(f"[yellow]{position}[/yellow]")
        for role in roles[:2]:
            pos_branch.add(f"[dim]{role}[/dim]")
    
    console.print(roles_tree)
    
    # 验证战术合理性
    validator = TacticalInstructionsValidator()
    is_valid = validator.validate(inst)
    
    if validator.warnings:
        console.print("\n[yellow]⚠ 战术警告:[/yellow]")
        for warning in validator.warnings:
            console.print(f"  [yellow]• {warning}[/yellow]")
    
    if validator.suggestions:
        console.print("\n[blue]💡 战术建议:[/blue]")
        for suggestion in validator.suggestions:
            console.print(f"  [blue]• {suggestion}[/blue]")
    
    if is_valid and not validator.warnings:
        console.print("\n[green]✓ 战术配置合理[/green]")
    
    # 应用风格
    console.print(f"\n[green]✓ 已应用比赛风格: {profile.name}[/green]")
    
    if formation:
        console.print(f"[dim]  使用阵型: {formation}[/dim]")


@tactics.command()
@click.argument("position", type=str)
def suggest_roles(position: str):
    """根据位置推荐合适的球员角色"""
    role_manager = RoleManager()
    
    suitable_roles = role_manager.get_suitable_roles(position.upper())
    
    if not suitable_roles:
        console.print(f"[red]✗ 未找到适合位置 '{position}' 的角色[/red]")
        console.print("[dim]有效位置: ST, CF, CAM, CM, CDM, LW, RW, LB, RB, CB, GK, 等[/dim]")
        return
    
    console.print(f"\n[bold]适合位置 '[cyan]{position.upper()}[/cyan]' 的角色:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("角色", style="cyan")
    table.add_column("类别", style="green")
    table.add_column("关键属性", style="yellow")
    table.add_column("描述", style="white", max_width=40)
    
    for role in suitable_roles:
        profile = role_manager.get_role_profile(role)
        if profile:
            key_attrs = ", ".join(profile.get_primary_attributes(3))
            table.add_row(
                role.display_name,
                role.category,
                key_attrs,
                profile.description[:50] + "..." if len(profile.description) > 50 else profile.description
            )
    
    console.print(table)


@tactics.command()
@click.option("--category", "-c", 
              type=click.Choice(["possession", "pressing", "counter", "defensive", "flexible"]),
              help="按类别筛选风格")
def styles_by_category(category: Optional[str]):
    """按类别查看比赛风格"""
    style_manager = PlayStyleManager()
    
    if category:
        profiles = style_manager.get_styles_by_category(category)
        title = f"{category.title()} 类别风格"
    else:
        profiles = style_manager.get_all_styles()
        title = "所有比赛风格"
    
    console.print(f"\n[bold]{title}[/bold]\n")
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("风格", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("防线", style="yellow")
    table.add_column("逼抢", style="yellow")
    table.add_column("节奏", style="yellow")
    table.add_column("传球", style="yellow")
    
    for profile in profiles:
        inst = profile.instructions
        table.add_row(
            profile.style.value,
            profile.name,
            inst.defensive_line.name,
            inst.pressing.name,
            inst.tempo.name,
            inst.passing_style.name,
        )
    
    console.print(table)


# 导出命令组
__all__ = ["tactics"]
