#!/usr/bin/env python3
"""
导入真实的大型球员数据库

从 data/cleaned/ 目录读取:
- players_cleaned.csv (120,000+ 球员)
- teams_cleaned.csv (5,600+ 俱乐部)
"""

import asyncio
import sys
import random
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from typing import Optional

sys.path.insert(0, '.')

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.core.models.player import Player, Position, Foot
from fm_manager.core.models.club import Club
from fm_manager.core.models.league import League
from sqlalchemy import select
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()

POSITION_MAPPING = {
    "门将": Position.GK,
    "GK": Position.GK,
    "后卫 中": Position.CB,
    "后卫 左": Position.LB,
    "后卫 右": Position.RB,
    "后卫 右中": Position.CB,
    "后卫 左中": Position.CB,
    "翼卫 左": Position.LB,
    "翼卫 右": Position.RB,
    "后腰": Position.CDM,
    "CDM": Position.CDM,
    "中场 中": Position.CM,
    "中场 左": Position.LM,
    "中场 右": Position.RM,
    "CM": Position.CM,
    "攻击型中场 中": Position.CAM,
    "攻击型中场 左": Position.LW,
    "攻击型中场 右": Position.RW,
    "CAM": Position.CAM,
    "前锋": Position.ST,
    "中锋": Position.ST,
    "ST": Position.ST,
}


def parse_position(pos_str: str) -> Position:
    """解析位置字符串"""
    if pd.isna(pos_str):
        return Position.CM
    
    pos_str = str(pos_str).strip()
    
    if pos_str in POSITION_MAPPING:
        return POSITION_MAPPING[pos_str]
    
    for cn_pos, enum_pos in POSITION_MAPPING.items():
        if cn_pos in pos_str:
            return enum_pos
    
    return Position.CM


def parse_birth_date(date_str: str) -> Optional[date]:
    """解析出生日期"""
    if pd.isna(date_str):
        return None
    
    try:
        if '.' in str(date_str):
            parts = str(date_str).split('.')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                return date(year, month, day)
    except:
        pass
    
    return None


def parse_nationality(nat_str: str) -> str:
    """解析国籍，取第一个"""
    if pd.isna(nat_str):
        return "Unknown"
    
    nat_str = str(nat_str).strip()
    if ' / ' in nat_str:
        return nat_str.split(' / ')[0]
    return nat_str


class RealDataImporter:
    """真实数据导入器"""
    
    def __init__(self, data_dir: str = "data/cleaned"):
        self.data_dir = Path(data_dir)
        self.players_df = None
        self.teams_df = None
        self.club_id_map = {}  # CSV club_id -> DB club_id
        
    def load_data(self):
        """加载CSV数据"""
        console.print(Panel("[bold cyan]加载真实数据[/bold cyan]", border_style="cyan"))
        
        players_path = self.data_dir / "players_cleaned.csv"
        console.print(f"[yellow]加载球员数据...[/yellow] {players_path}")
        self.players_df = pd.read_csv(players_path)
        console.print(f"[green]✓[/green] 加载了 {len(self.players_df):,} 名球员")
        
        teams_path = self.data_dir / "teams_cleaned.csv"
        console.print(f"[yellow]加载球队数据...[/yellow] {teams_path}")
        self.teams_df = pd.read_csv(teams_path)
        console.print(f"[green]✓[/green] 加载了 {len(self.teams_df):,} 个俱乐部")
        
        console.print(f"\n[dim]球员数据列: {', '.join(self.players_df.columns[:5])}...[/dim]")
        console.print(f"[dim]球队数据列: {', '.join(self.teams_df.columns)}[/dim]")
    
    async def import_leagues(self, session):
        """导入联赛"""
        console.print(Panel("[bold cyan]导入联赛[/bold cyan]", border_style="cyan"))
        
        leagues_data = self.teams_df[['league', 'country']].drop_duplicates()
        
        major_leagues = [
            "Premier League", "Bundesliga", "La Liga", "Serie A", "Ligue 1",
            "England Premier League",  # CSV中的名称
        ]
        
        imported_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]导入联赛...", total=len(leagues_data))
            
            for _, row in leagues_data.iterrows():
                league_name = str(row['league']) if pd.notna(row['league']) else "Unknown League"
                country = str(row['country']) if pd.notna(row['country']) else "Unknown"
                
                result = await session.execute(
                    select(League).where(League.name == league_name)
                )
                existing = result.first()
                if existing:
                    progress.advance(task)
                    continue
                
                league = League(
                    name=league_name,
                    short_name=league_name[:10] if len(league_name) > 10 else league_name,
                    country=country,
                    tier=1
                )
                session.add(league)
                imported_count += 1
                
                if imported_count % 100 == 0:
                    await session.flush()
                
                progress.advance(task)
        
        await session.commit()
        console.print(f"[green]✓[/green] 导入了 {imported_count} 个联赛")
    
    async def import_clubs(self, session):
        """导入俱乐部"""
        console.print(Panel("[bold cyan]导入俱乐部[/bold cyan]", border_style="cyan"))
        
        result = await session.execute(select(League))
        leagues = {l.name: l for l in result.scalars().all()}
        
        imported_count = 0
        skipped_count = 0
        seen_names = set()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]导入俱乐部...", total=len(self.teams_df))
            
            for _, row in self.teams_df.iterrows():
                csv_club_id = int(row['club_id'])
                name = str(row['name']) if pd.notna(row['name']) else f"Club {csv_club_id}"
                country = str(row['country']) if pd.notna(row['country']) else "Unknown"
                league_name = str(row['league']) if pd.notna(row['league']) else None
                
                if name in seen_names:
                    skipped_count += 1
                    progress.advance(task)
                    continue
                seen_names.add(name)
                
                league_id = None
                if league_name and league_name in leagues:
                    league_id = leagues[league_name].id
                
                reputation = int(row['reputation']) if pd.notna(row['reputation']) else 1000
                balance = int(row['balance']) if pd.notna(row['balance']) else 1000000
                transfer_budget = int(row['transfer_budget']) if pd.notna(row['transfer_budget']) else 500000
                
                club = Club(
                    name=name,
                    short_name=name[:6] if len(name) > 6 else name,
                    country=country,
                    league_id=league_id,
                    reputation=reputation,
                    balance=balance,
                    transfer_budget=transfer_budget,
                    wage_budget=transfer_budget // 2,
                )
                session.add(club)
                await session.flush()
                
                self.club_id_map[csv_club_id] = club.id
                imported_count += 1
                
                if imported_count % 500 == 0:
                    await session.commit()
                
                progress.advance(task)
        
        await session.commit()
        console.print(f"[green]✓[/green] 导入了 {imported_count} 个俱乐部")
        console.print(f"[dim]跳过了 {skipped_count} 个重复俱乐部[/dim]")
    
    async def import_players(self, session, limit: Optional[int] = None):
        """导入球员"""
        console.print(Panel("[bold cyan]导入球员[/bold cyan]", border_style="cyan"))
        
        df = self.players_df
        if limit:
            df = df.head(limit)
            console.print(f"[yellow]限制导入前 {limit} 名球员[/yellow]")
        
        imported_count = 0
        skipped_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]导入球员...", total=len(df))
            
            for _, row in df.iterrows():
                name_str = str(row['name']) if pd.notna(row['name']) else "Unknown"
                if ', ' in name_str:
                    last_name, first_name = name_str.split(', ', 1)
                else:
                    first_name = name_str
                    last_name = ""
                
                first_name = first_name.strip().replace('"', '')
                last_name = last_name.strip().replace('"', '')
                
                if not first_name:
                    first_name = "Unknown"
                
                nationality = parse_nationality(row.get('nationality'))
                birth_date = parse_birth_date(row.get('birth_date'))
                position = parse_position(row.get('position'))
                
                ca = int(float(row['current_ability'])) if pd.notna(row['current_ability']) else 50
                pa = int(float(row['potential_ability'])) if pd.notna(row['potential_ability']) else 60
                
                club_id = None
                if 'club_id' in row and pd.notna(row['club_id']):
                    csv_club_id = int(row['club_id'])
                    club_id = self.club_id_map.get(csv_club_id)
                
                if club_id is None:
                    skipped_count += 1
                    progress.advance(task)
                    continue
                
                player = Player(
                    first_name=first_name,
                    last_name=last_name,
                    nationality=nationality,
                    birth_date=birth_date,
                    position=position,
                    club_id=club_id,
                    current_ability=max(1, min(200, ca)),
                    potential_ability=max(1, min(200, pa)),
                    preferred_foot=random.choice([Foot.LEFT, Foot.RIGHT]),
                    pace=int(float(row['rating_pace'])) if 'rating_pace' in row and pd.notna(row['rating_pace']) else random.randint(40, 80),
                    acceleration=int(float(row['rating_acceleration'])) if 'rating_acceleration' in row and pd.notna(row['rating_acceleration']) else random.randint(40, 80),
                    stamina=random.randint(40, 90),
                    strength=random.randint(40, 90),
                    shooting=random.randint(40, 90),
                    passing=random.randint(40, 90),
                    dribbling=random.randint(40, 90),
                    crossing=random.randint(40, 90),
                    first_touch=random.randint(40, 90),
                    tackling=random.randint(40, 90),
                    marking=random.randint(40, 90),
                    positioning=random.randint(40, 90),
                    vision=random.randint(40, 90),
                    decisions=random.randint(40, 90),
                )
                session.add(player)
                imported_count += 1
                
                if imported_count % 1000 == 0:
                    await session.commit()
                
                progress.advance(task)
        
        await session.commit()
        console.print(f"[green]✓[/green] 导入了 {imported_count:,} 名球员")
        console.print(f"[dim]跳过了 {skipped_count:,} 名球员 (无对应俱乐部)[/dim]")


async def main():
    """主函数"""
    console.print("\n" + "="*70)
    console.print("[bold cyan]FM Manager - 真实数据导入工具[/bold cyan]")
    console.print("="*70 + "\n")
    
    console.print("[yellow]选择导入模式:[/yellow]")
    console.print("  1. 快速导入 (前10,000名球员)")
    console.print("  2. 标准导入 (前50,000名球员)")
    console.print("  3. 完整导入 (全部120,000+球员)")
    console.print("  4. 仅导入俱乐部")
    
    choice = "1"
    
    limit_map = {
        "1": 10000,
        "2": 50000,
        "3": None,
        "4": 0,  # 仅俱乐部
    }
    
    player_limit = limit_map.get(choice, 10000)
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        importer = RealDataImporter()
        
        try:
            importer.load_data()
            
            await importer.import_leagues(session)
            
            await importer.import_clubs(session)
            
            if player_limit != 0:
                await importer.import_players(session, limit=player_limit)
            
            console.print("\n" + "="*70)
            console.print("[bold green]✓ 数据导入完成！[/bold green]")
            console.print("="*70)
            
            result = await session.execute(select(League))
            league_count = len(result.scalars().all())
            
            result = await session.execute(select(Club))
            club_count = len(result.scalars().all())
            
            result = await session.execute(select(Player))
            player_count = len(result.scalars().all())
            
            console.print(f"\n[bold]数据库统计:[/bold]")
            console.print(f"  联赛: {league_count:,}")
            console.print(f"  俱乐部: {club_count:,}")
            console.print(f"  球员: {player_count:,}")
            
        except Exception as e:
            console.print(f"\n[red]✗ 导入失败: {e}[/red]")
            import traceback
            console.print(traceback.format_exc())
    
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
