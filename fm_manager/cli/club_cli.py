#!/usr/bin/env python3
"""俱乐部管理CLI - Rich终端界面

提供俱乐部管理相关的命令行界面，包括设施管理、财务报告等功能。
"""

import click
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from typing import Optional

from fm_manager.core.models.facility import (
    FacilityType,
    get_level_config,
)
from fm_manager.engine.facility_manager import FacilityManager
from fm_manager.engine.finance_engine import FinancialManager, FinancialWarning
from fm_manager.core.database import get_session_maker

console = Console()


@click.group()
def club():
    """俱乐部管理命令 - 管理设施、财务和俱乐部运营"""
    pass


async def _show_facilities_async(club_id: int):
    """异步显示设施状态的内部函数"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        facility_manager = FacilityManager(session)
        
        # 获取所有设施
        facilities = await facility_manager.get_all_facilities(club_id)
        
        if not facilities:
            console.print(f"[yellow]⚠ 未找到俱乐部 ID {club_id} 的设施信息[/yellow]")
            return
        
        # 创建设施表格
        table = Table(
            title=f"[bold blue]俱乐部设施概览[/bold blue]",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("设施类型", style="cyan", no_wrap=True)
        table.add_column("等级", style="yellow", justify="center")
        table.add_column("效果", style="green")
        table.add_column("维护费/周", style="red", justify="right")
        table.add_column("升级成本", style="magenta", justify="right")
        table.add_column("状态", style="white")
        
        total_maintenance = 0
        
        for facility in facilities:
            config = get_level_config(facility.facility_type, facility.level)
            
            # 计算效果描述
            if facility.facility_type == FacilityType.STADIUM:
                effect = f"容量: {facility.stadium_capacity:,}"
            else:
                effect_pct = facility.effect_percentage * 100
                effect = f"+{effect_pct:.1f}%"
            
            # 状态指示
            if facility.is_max_level:
                status = "[green]✓ 已满级[/green]"
            else:
                status = f"[dim]可升级[/dim]"
            
            # 获取设施类型的显示名称
            type_names = {
                FacilityType.YOUTH_ACADEMY: "🏫 青训学院",
                FacilityType.TRAINING_GROUND: "🏃 训练场",
                FacilityType.DATA_ANALYTICS: "📊 数据分析",
                FacilityType.MEDICAL_CENTER: "🏥 医疗中心",
                FacilityType.SCOUTING_NETWORK: "🔍 球探网络",
                FacilityType.STADIUM: "🏟️ 球场",
            }
            type_display = type_names.get(facility.facility_type, facility.facility_type.value)
            
            table.add_row(
                type_display,
                f"{facility.level}/20",
                effect,
                f"€{facility.weekly_maintenance:,}",
                f"€{facility.upgrade_cost:,}" if not facility.is_max_level else "-",
                status,
            )
            
            total_maintenance += facility.weekly_maintenance
        
        console.print(table)
        console.print(f"\n[dim]总维护费用: [red]€{total_maintenance:,}/周[/red][/dim]")


@club.command()
@click.option("--club-id", "-c", type=int, required=True, help="俱乐部ID")
def show_facilities(club_id: int):
    """显示俱乐部设施状态"""
    asyncio.run(_show_facilities_async(club_id))


async def _show_facility_detail_async(club_id: int, facility_type_str: str):
    """异步显示设施详情的内部函数"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        facility_manager = FacilityManager(session)
        
        # 解析设施类型
        try:
            facility_type = FacilityType(facility_type_str.lower())
        except ValueError:
            console.print(f"[red]✗ 无效的设施类型: {facility_type_str}[/red]")
            valid_types = ", ".join([ft.value for ft in FacilityType])
            console.print(f"[dim]有效类型: {valid_types}[/dim]")
            return
        
        facility = await facility_manager.get_facility(club_id, facility_type)
        
        if not facility:
            console.print(f"[red]✗ 未找到设施: {facility_type.value}[/red]")
            return
        
        # 获取当前等级配置
        current_config = get_level_config(facility.facility_type, facility.level)
        
        # 创建详情面板
        type_names = {
            FacilityType.YOUTH_ACADEMY: "青训学院",
            FacilityType.TRAINING_GROUND: "训练场",
            FacilityType.DATA_ANALYTICS: "数据分析中心",
            FacilityType.MEDICAL_CENTER: "医疗中心",
            FacilityType.SCOUTING_NETWORK: "球探网络",
            FacilityType.STADIUM: "球场",
        }
        
        content = Text()
        content.append(f"[bold cyan]{type_names.get(facility.facility_type, facility.facility_type.value)}[/bold cyan]\n\n")
        content.append(f"[yellow]当前等级:[/yellow] {facility.level}/20\n")
        content.append(f"[yellow]等级描述:[/yellow] {current_config.description}\n\n")
        
        # 效果详情
        content.append("[bold]当前效果:[/bold]\n")
        if facility.facility_type == FacilityType.STADIUM:
            content.append(f"  球场容量: [green]{facility.stadium_capacity:,}[/green] 人\n")
        else:
            for effect_key, effect_value in current_config.effects.items():
                content.append(f"  {effect_key}: [green]+{effect_value*100:.1f}%[/green]\n")
        
        content.append(f"\n[red]每周维护费:[/red] €{facility.weekly_maintenance:,}\n")
        
        if facility.is_max_level:
            content.append("\n[green]✓ 该设施已达到最高等级[/green]")
        else:
            content.append(f"\n[yellow]升级到下一级需要:[/yellow] €{facility.upgrade_cost:,}")
            
            # 显示下一级预览
            next_config = get_level_config(facility.facility_type, facility.level + 1)
            content.append(f"\n[dim]下一级效果预览:[/dim]\n")
            if facility.facility_type == FacilityType.STADIUM:
                min_capacity = 5000
                max_capacity = 150000
                next_capacity = min_capacity + int((facility.level) / 19 * (max_capacity - min_capacity))
                content.append(f"  容量: ~{next_capacity:,} 人\n")
            else:
                for effect_key, effect_value in next_config.effects.items():
                    content.append(f"  {effect_key}: +{effect_value*100:.1f}%\n")
        
        panel = Panel(
            content,
            title="[bold]设施详情[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(panel)


@club.command()
@click.option("--club-id", "-c", type=int, required=True, help="俱乐部ID")
@click.option("--type", "-t", "facility_type", required=True, 
              type=click.Choice([ft.value for ft in FacilityType], case_sensitive=False),
              help="设施类型")
def facility_detail(club_id: int, facility_type: str):
    """查看特定设施的详细信息"""
    asyncio.run(_show_facility_detail_async(club_id, facility_type))


async def _show_finances_async(club_id: int):
    """异步显示财务状况的内部函数"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        from fm_manager.core.models.club import Club
        
        club = await session.get(Club, club_id)
        
        if not club:
            console.print(f"[red]✗ 未找到俱乐部 ID: {club_id}[/red]")
            return
        
        # 创建财务经理
        financial_manager = FinancialManager(club)
        
        # 获取财务摘要
        summary = financial_manager.get_financial_summary()
        
        # 显示俱乐部基本信息
        header_content = f"""[bold cyan]{summary['club_name']}[/bold cyan]

[yellow]当前资金:[/yellow] €{summary['current_balance']:,}
[green]转会预算:[/green] €{summary['transfer_budget']:,}
[blue]工资预算:[/blue] €{summary['wage_budget']:,}
"""
        
        header_panel = Panel(
            header_content,
            title="[bold]俱乐部财务概览[/bold]",
            border_style="blue",
            padding=(1, 2),
        )
        console.print(header_panel)
        
        # 创建收入支出表格
        weekly = summary['weekly_finances']
        
        # 收入树
        income_tree = Tree("[green]📈 收入来源[/green]")
        income_tree.add(f"赞助收入: [green]€{weekly['income']['sponsor']:,}/周[/green]")
        income_tree.add(f"商业收入: [green]€{weekly['income']['commercial']:,}/周[/green]")
        income_tree.add(f"比赛日预估: [green]€{weekly['income']['matchday_estimate']:,}/场[/green]")
        income_tree.add(f"[bold]收入总计: €{weekly['income']['total']:,}/周[/bold]")
        
        # 支出树
        expenses_tree = Tree("[red]📉 支出项目[/red]")
        expenses_tree.add(f"球员工资: [red]€{weekly['expenses']['player_wages']:,}/周[/red]")
        expenses_tree.add(f"职员工资: [red]€{weekly['expenses']['staff_wages']:,}/周[/red]")
        expenses_tree.add(f"设施维护: [red]€{weekly['expenses']['facility_maintenance']:,}/周[/red]")
        expenses_tree.add(f"[bold]支出总计: €{weekly['expenses']['total_expenses']:,}/周[/bold]")
        
        # 显示收支
        console.print("\n")
        console.print(Columns([income_tree, expenses_tree]))
        
        # 净利润
        net = weekly['net']
        net_color = "green" if net >= 0 else "red"
        net_sign = "+" if net >= 0 else ""
        console.print(f"\n[bold]每周净收支: [{net_color}]{net_sign}€{net:,}[/{net_color}][/bold]")
        
        # 财务警告
        warnings = summary['warnings']
        if warnings:
            console.print("\n[yellow]⚠ 财务警告:[/yellow]")
            for warning in warnings:
                warning_text = {
                    "bankruptcy_risk": "[red]• 破产风险 - 资金为负[/red]",
                    "low_cash": "[yellow]• 资金不足 - 现金流紧张[/yellow]",
                    "high_wage_bill": "[yellow]• 工资过高 - 工资支出占比过大[/yellow]",
                    "low_transfer_budget": "[yellow]• 转会预算偏低[/yellow]",
                    "facility_maintenance_high": "[yellow]• 设施维护费用过高[/yellow]",
                }.get(warning, f"• {warning}")
                console.print(warning_text)
        else:
            console.print("\n[green]✓ 财务状况良好[/green]")
        
        # 预算分配建议
        allocation = summary['recommended_allocation']
        console.print("\n[dim]💡 建议预算分配:[/dim]")
        alloc_table = Table(show_header=False, box=None)
        alloc_table.add_column("项目", style="cyan")
        alloc_table.add_column("金额", style="green", justify="right")
        alloc_table.add_row("球员工资", f"€{allocation['player_wages']:,}/周")
        alloc_table.add_row("职员工资", f"€{allocation['staff_wages']:,}/周")
        alloc_table.add_row("设施维护", f"€{allocation['facility_maintenance']:,}/周")
        alloc_table.add_row("转会储备", f"€{allocation['transfer_budget']:,}/周")
        alloc_table.add_row("应急资金", f"€{allocation['emergency_fund']:,}/周")
        console.print(alloc_table)


@club.command()
@click.option("--club-id", "-c", type=int, required=True, help="俱乐部ID")
def finances(club_id: int):
    """显示俱乐部财务状况"""
    asyncio.run(_show_finances_async(club_id))


async def _upgrade_facility_async(club_id: int, facility_type_str: str):
    """异步升级设施的内部函数"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        facility_manager = FacilityManager(session)
        
        # 解析设施类型
        try:
            facility_type = FacilityType(facility_type_str.lower())
        except ValueError:
            console.print(f"[red]✗ 无效的设施类型: {facility_type_str}[/red]")
            return
        
        # 检查是否可以升级
        can_upgrade, reason = await facility_manager.can_upgrade(club_id, facility_type)
        
        if not can_upgrade:
            console.print(f"[red]✗ 无法升级: {reason}[/red]")
            return
        
        # 获取设施信息
        facility = await facility_manager.get_facility(club_id, facility_type)
        
        # 确认升级
        console.print(f"\n[yellow]即将升级设施:[/yellow]")
        console.print(f"  设施: {facility_type.value}")
        console.print(f"  从等级 {facility.level} 升级到 {facility.level + 1}")
        console.print(f"  升级费用: [red]€{facility.upgrade_cost:,}[/red]")
        
        # 执行升级
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="正在升级设施...", total=None)
            
            success, message, updated_facility = await facility_manager.upgrade_facility(
                club_id, facility_type
            )
        
        if success:
            console.print(f"\n[green]✓ {message}[/green]")
            
            # 显示升级后的效果
            new_config = get_level_config(facility_type, updated_facility.level)
            console.print(f"\n[dim]新效果:[/dim]")
            if facility_type == FacilityType.STADIUM:
                console.print(f"  球场容量: {updated_facility.stadium_capacity:,} 人")
            else:
                for effect_key, effect_value in new_config.effects.items():
                    console.print(f"  {effect_key}: +{effect_value*100:.1f}%")
        else:
            console.print(f"\n[red]✗ 升级失败: {message}[/red]")


@club.command()
@click.option("--club-id", "-c", type=int, required=True, help="俱乐部ID")
@click.option("--type", "-t", "facility_type", required=True,
              type=click.Choice([ft.value for ft in FacilityType], case_sensitive=False),
              help="要升级的设施类型")
def upgrade(club_id: int, facility_type: str):
    """升级俱乐部设施"""
    asyncio.run(_upgrade_facility_async(club_id, facility_type))


async def _finances_projection_async(club_id: int, weeks: int):
    """异步显示财务预测的内部函数"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        from fm_manager.core.models.club import Club
        
        club = await session.get(Club, club_id)
        
        if not club:
            console.print(f"[red]✗ 未找到俱乐部 ID: {club_id}[/red]")
            return
        
        financial_manager = FinancialManager(club)
        projection = financial_manager.project_financial_position(weeks)
        
        # 创建预测面板
        content = Text()
        content.append(f"[bold]财务预测 ({weeks} 周)[/bold]\n\n")
        
        content.append(f"[dim]起始资金:[/dim] €{projection['starting_balance']:,}\n")
        
        projected = projection['projected_balance']
        proj_color = "green" if projected >= projection['starting_balance'] else "red"
        content.append(f"[dim]预计资金:[/dim] [{proj_color}]€{projected:,}[/{proj_color}]\n\n")
        
        content.append(f"[dim]每周收入:[/dim] €{projection['weekly_income']:,}\n")
        content.append(f"[dim]每周支出:[/dim] €{projection['weekly_expenses']:,}\n")
        
        net = projection['weekly_net']
        net_color = "green" if net >= 0 else "red"
        net_sign = "+" if net >= 0 else ""
        content.append(f"[dim]每周净收入:[/dim] [{net_color}]{net_sign}€{net:,}[/{net_color}]\n\n")
        
        if projection['will_be_profitable']:
            content.append("[green]✓ 预计盈利[/green]\n")
        else:
            content.append("[red]⚠ 预计亏损[/red]\n")
        
        if projection['bankruptcy_risk']:
            content.append("[red bold]⚠ 警告: 有破产风险![/red bold]\n")
        
        panel = Panel(
            content,
            title="[bold]财务预测[/bold]",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(panel)


@club.command()
@click.option("--club-id", "-c", type=int, required=True, help="俱乐部ID")
@click.option("--weeks", "-w", type=int, default=52, help="预测周数（默认52周）")
def projection(club_id: int, weeks: int):
    """显示财务预测"""
    asyncio.run(_finances_projection_async(club_id, weeks))


async def _upgrade_recommendations_async(club_id: int):
    """异步显示升级建议的内部函数"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        facility_manager = FacilityManager(session)
        
        recommendations = await facility_manager.get_upgrade_recommendations(club_id)
        
        if not recommendations:
            console.print("[dim]暂无升级建议[/dim]")
            return
        
        console.print("\n[bold]💡 设施升级建议[/bold]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("优先级", style="yellow", justify="center")
        table.add_column("设施", style="cyan")
        table.add_column("当前等级", style="white")
        table.add_column("升级费用", style="red", justify="right")
        table.add_column("新维护费", style="yellow", justify="right")
        table.add_column("状态", style="green")
        
        for i, rec in enumerate(recommendations[:5], 1):
            status = "[green]可升级[/green]" if rec['can_upgrade'] else "[red]不可[/red]"
            
            table.add_row(
                str(i),
                rec['facility_type'].replace('_', ' ').title(),
                f"{rec['current_level']}/20",
                f"€{rec['upgrade_cost']:,}",
                f"€{rec['new_maintenance']:,}/周",
                status,
            )
        
        console.print(table)
        console.print("\n[dim]提示: 使用 'club upgrade' 命令升级设施[/dim]")


@club.command()
@click.option("--club-id", "-c", type=int, required=True, help="俱乐部ID")
def recommendations(club_id: int):
    """显示设施升级建议"""
    asyncio.run(_upgrade_recommendations_async(club_id))


# 导出命令组
__all__ = ["club"]
