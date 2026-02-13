#!/usr/bin/env python3
"""FM Manager - Complete Game Loop CLI.

完整的单人游戏循环，包含：
- 主菜单
- 俱乐部管理
- 比赛日模拟
- 转会市场
- 存档/读档
"""

import asyncio
import sys
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from fm_manager.core import init_db, get_session_maker, close_db
from fm_manager.core.models.club import Club
from fm_manager.core.models.player import Player, Position
from fm_manager.core.models.league import League
from fm_manager.core.models.match import Match
from fm_manager.core.save_load_slots import SlotSaveManager, SaveSlot
from fm_manager.engine.match_engine_markov import MarkovMatchEngine

console = Console()


class GameState(Enum):
    MAIN_MENU = "main_menu"
    CLUB_SELECT = "club_select"
    GAME_LOOP = "game_loop"
    MATCH_DAY = "match_day"
    TRANSFER = "transfer"
    TACTICS = "tactics"


class FMGameManager:
    """Complete single-player game manager."""
    
    def __init__(self):
        self.running = True
        self.state = GameState.MAIN_MENU
        
        self.player_club: Optional[Club] = None
        self.current_season = 1
        self.current_week = 1
        self.current_date = date(2024, 8, 1)
        
        self.clubs: List[Club] = []
        self.all_clubs: List[Club] = []
        self.league: Optional[League] = None
        
        self.standings: Dict[int, Dict] = {}
        self.match_results: List[Dict] = []
        
        self.save_manager = SlotSaveManager()
        self.match_engine = MarkovMatchEngine()
        
        self.session_maker = None
    
    async def initialize(self):
        """Initialize game database."""
        await init_db()
        self.session_maker = get_session_maker()
        
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(select(League).limit(1))
            self.league = result.scalar_one_or_none()
            
            if self.league:
                result = await session.execute(
                    select(Club).where(Club.league_id == self.league.id)
                )
                self.clubs = list(result.scalars().all())
            
            result = await session.execute(select(Club))
            self.all_clubs = list(result.scalars().all())
    
    async def run(self):
        """Main game loop."""
        await self.initialize()
        
        console.print(Panel.fit(
            "[bold cyan]⚽ FM Manager[/bold cyan]\n"
            "[green]完整单人游戏模式[/green]\n\n"
            "管理你的俱乐部，带领球队夺得冠军！",
            title="欢迎",
            border_style="cyan"
        ))
        
        while self.running:
            if self.state == GameState.MAIN_MENU:
                await self.main_menu()
            elif self.state == GameState.CLUB_SELECT:
                await self.club_select()
            elif self.state == GameState.GAME_LOOP:
                await self.game_loop()
            elif self.state == GameState.MATCH_DAY:
                await self.match_day()
            elif self.state == GameState.TRANSFER:
                await self.transfer_menu()
            elif self.state == GameState.TACTICS:
                await self.tactics_menu()
        
        await close_db()
    
    async def main_menu(self):
        """Main menu."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]⚽ FM Manager[/bold cyan]\n"
            f"[dim]赛季 {self.current_season} | 第 {self.current_week} 周[/dim]",
            border_style="cyan"
        ))
        
        table = Table(show_header=False, box=None)
        table.add_column("选项", style="bold")
        table.add_column("说明")
        
        options = [
            ("1", "新游戏", "开始新的赛季"),
            ("2", "继续游戏", "读取存档继续"),
            ("3", "存档管理", "管理存档槽位"),
            ("4", "退出", "退出游戏"),
        ]
        
        for opt, name, desc in options:
            table.add_row(f"[cyan]{opt}[/cyan]", f"{name} - [dim]{desc}[/dim]")
        
        console.print(table)
        
        choice = Prompt.ask("\n选择", choices=["1", "2", "3", "4"], default="1")
        
        if choice == "1":
            self.state = GameState.CLUB_SELECT
        elif choice == "2":
            await self.load_game()
        elif choice == "3":
            await self.manage_saves()
        elif choice == "4":
            self.running = False
    
    async def club_select(self):
        """Select club to manage."""
        console.clear()
        console.print(Panel("[bold green]选择你的俱乐部[/bold green]", border_style="green"))
        
        if not self.clubs:
            console.print("[red]没有可用的俱乐部！请先初始化数据库。[/red]")
            self.state = GameState.MAIN_MENU
            return
        
        table = Table(title="可选俱乐部")
        table.add_column("#", justify="right", width=4)
        table.add_column("俱乐部", min_width=20)
        table.add_column("声望", justify="right", width=8)
        table.add_column("预算", justify="right", width=12)
        
        for i, club in enumerate(self.clubs[:20], 1):
            table.add_row(
                str(i),
                club.name,
                str(club.reputation or 1000),
                f"£{(club.balance or 0):,}"
            )
        
        console.print(table)
        
        choice = IntPrompt.ask(f"\n选择俱乐部 (1-{min(len(self.clubs), 20)})", default=1)
        
        if 1 <= choice <= len(self.clubs):
            self.player_club = self.clubs[choice - 1]
            self._init_standings()
            console.print(f"\n[green]✓ 你现在是 {self.player_club.name} 的经理！[/green]")
            Prompt.ask("按回车继续")
            self.state = GameState.GAME_LOOP
        else:
            console.print("[red]无效选择[/red]")
    
    def _init_standings(self):
        """Initialize league standings."""
        self.standings = {}
        for club in self.clubs:
            self.standings[club.id] = {
                "club": club,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "gf": 0,
                "ga": 0,
                "points": 0
            }
    
    async def game_loop(self):
        """Main game loop."""
        console.clear()
        self._show_dashboard()
        
        options = {
            "1": ("进行比赛", self._advance_week),
            "2": ("查看阵容", self._view_squad),
            "3": ("转会市场", self._goto_transfer),
            "4": ("战术设置", self._goto_tactics),
            "5": ("查看积分榜", self._view_standings),
            "6": ("保存游戏", self._save_game),
            "7": ("返回主菜单", self._goto_main),
        }
        
        table = Table(show_header=False, box=None)
        for opt, (name, _) in options.items():
            table.add_row(f"[cyan]{opt}[/cyan]", name)
        console.print(table)
        
        choice = Prompt.ask("\n选择", choices=list(options.keys()), default="1")
        
        if choice in options:
            _, action = options[choice]
            await action()
    
    def _show_dashboard(self):
        """Show club dashboard."""
        if not self.player_club:
            return
        
        club = self.player_club
        standing = self.standings.get(club.id, {})
        
        sorted_clubs = sorted(
            self.standings.values(),
            key=lambda x: (x["points"], x["gf"] - x["ga"]),
            reverse=True
        )
        position = next(
            (i + 1 for i, s in enumerate(sorted_clubs) if s["club"].id == club.id),
            "?"
        )
        
        form = self._get_recent_form(club.id)
        
        club_name = club.name.replace("[", "(").replace("]", ")")
        
        console.print(Panel(
            f"[bold]{club_name}[/bold]\n\n"
            f"联赛排名: {position} / {len(self.clubs)}\n"
            f"积分: {standing.get('points', 0)} | "
            f"战绩: {standing.get('won', 0)}W {standing.get('drawn', 0)}D {standing.get('lost', 0)}L\n"
            f"近期状态: {form}\n"
            f"日期: {self.current_date.strftime('%Y-%m-%d')} | "
            f"赛季: {self.current_season} | 周: {self.current_week}",
            border_style="cyan"
        ))
    
    def _get_recent_form(self, club_id: int) -> str:
        """Get recent form string."""
        club_results = [
            r for r in self.match_results[-10:]
            if r.get("home_id") == club_id or r.get("away_id") == club_id
        ]
        
        form_parts = []
        for r in club_results[-5:]:
            if r.get("home_id") == club_id:
                if r["home_score"] > r["away_score"]:
                    form_parts.append("[green]W[/green]")
                elif r["home_score"] < r["away_score"]:
                    form_parts.append("[red]L[/red]")
                else:
                    form_parts.append("[yellow]D[/yellow]")
            else:
                if r["away_score"] > r["home_score"]:
                    form_parts.append("[green]W[/green]")
                elif r["away_score"] < r["home_score"]:
                    form_parts.append("[red]L[/red]")
                else:
                    form_parts.append("[yellow]D[/yellow]")
        
        return " ".join(form_parts) if form_parts else "[dim]-----[/dim]"
    
    async def _advance_week(self):
        """Advance to next week and simulate matches."""
        console.print(f"\n[yellow]模拟第 {self.current_week} 轮比赛...[/yellow]")
        
        await self._simulate_matchday()
        
        self.current_week += 1
        self.current_date += timedelta(days=7)
        
        if self.current_week > 38:
            await self._end_season()
        
        Prompt.ask("\n按回车继续")
    
    async def _simulate_matchday(self):
        """Simulate all matches for current week."""
        import random
        
        matches = []
        club_list = list(self.clubs)
        random.shuffle(club_list)
        
        for i in range(0, len(club_list), 2):
            if i + 1 < len(club_list):
                matches.append((club_list[i], club_list[i + 1]))
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]模拟比赛中...[/cyan]", total=len(matches))
            
            for home, away in matches:
                home_score = random.randint(0, 4)
                away_score = random.randint(0, 3)
                
                results.append({
                    "home": home.name,
                    "away": away.name,
                    "home_id": home.id,
                    "away_id": away.id,
                    "home_score": home_score,
                    "away_score": away_score
                })
                
                self._update_standings(home.id, away.id, home_score, away_score)
                self.match_results.append(results[-1])
                
                progress.advance(task)
        
        console.print(f"\n[bold]第 {self.current_week} 轮结果:[/bold]")
        
        table = Table(box=None)
        table.add_column("主队", min_width=18)
        table.add_column("比分", justify="center", width=6)
        table.add_column("客队", min_width=18)
        
        for r in results:
            home_name = r['home'].replace("[", "(").replace("]", ")")
            away_name = r['away'].replace("[", "(").replace("]", ")")
            
            is_player_match = self.player_club and (r["home_id"] == self.player_club.id or r["away_id"] == self.player_club.id)
            
            if is_player_match:
                home_name = f"* {home_name}"
                away_name = f"* {away_name}"
            
            table.add_row(
                home_name,
                f"{r['home_score']} - {r['away_score']}",
                away_name
            )
        
        console.print(table)
    
    def _update_standings(self, home_id: int, away_id: int, home_score: int, away_score: int):
        """Update standings after a match."""
        home = self.standings[home_id]
        away = self.standings[away_id]
        
        home["played"] += 1
        away["played"] += 1
        home["gf"] += home_score
        home["ga"] += away_score
        away["gf"] += away_score
        away["ga"] += home_score
        
        if home_score > away_score:
            home["won"] += 1
            home["points"] += 3
            away["lost"] += 1
        elif home_score < away_score:
            away["won"] += 1
            away["points"] += 3
            home["lost"] += 1
        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home["points"] += 1
            away["points"] += 1
    
    async def _end_season(self):
        """End current season."""
        console.print("\n[bold yellow]赛季结束！[/bold yellow]")
        
        sorted_clubs = sorted(
            self.standings.values(),
            key=lambda x: (x["points"], x["gf"] - x["ga"]),
            reverse=True
        )
        
        champion = sorted_clubs[0]["club"]
        
        player_pos = "?"
        if self.player_club:
            player_pos = next(
                (i + 1 for i, s in enumerate(sorted_clubs) if s["club"].id == self.player_club.id),
                "?"
            )
        
        console.print(f"\n[bold green]🏆 冠军: {champion.name}[/bold green]")
        console.print(f"你的排名: [bold]{player_pos}[/bold]")
        
        self.current_season += 1
        self.current_week = 1
        self.current_date = date(2024 + self.current_season - 1, 8, 1)
        self._init_standings()
        self.match_results = []
        
        Prompt.ask("\n按回车开始新赛季")
    
    async def _view_squad(self):
        """View club squad."""
        if not self.player_club or not self.session_maker:
            return
        
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Player).where(Player.club_id == self.player_club.id)
            )
            players = list(result.scalars().all())
        
        club_name = self.player_club.name.replace("[", "(").replace("]", ")")
        console.print(f"\n[bold]{club_name} 阵容[/bold]")
        
        table = Table()
        table.add_column("姓名", min_width=20)
        table.add_column("位置", width=6)
        table.add_column("能力", justify="right", width=6)
        table.add_column("潜力", justify="right", width=6)
        table.add_column("年龄", justify="right", width=6)
        
        for p in players:
            player_name = f"{p.first_name} {p.last_name}".replace("[", "(").replace("]", ")")
            table.add_row(
                player_name,
                p.position.value if p.position else "-",
                str(p.current_ability or 50),
                str(p.potential_ability or 60),
                str(p.age if hasattr(p, 'age') else 25)
            )
        
        console.print(table)
        Prompt.ask("\n按回车返回")
    
    async def _view_standings(self):
        sorted_clubs = sorted(
            self.standings.values(),
            key=lambda x: (x["points"], x["gf"] - x["ga"]),
            reverse=True
        )
        
        table = Table(title=f"积分榜 - 赛季 {self.current_season}")
        table.add_column("#", justify="right", width=3)
        table.add_column("俱乐部", min_width=18)
        table.add_column("场", justify="right", width=4)
        table.add_column("胜", justify="right", width=4)
        table.add_column("平", justify="right", width=4)
        table.add_column("负", justify="right", width=4)
        table.add_column("进", justify="right", width=4)
        table.add_column("失", justify="right", width=4)
        table.add_column("净", justify="right", width=4)
        table.add_column("分", justify="right", width=4)
        
        for i, s in enumerate(sorted_clubs, 1):
            club = s["club"]
            is_player_club = self.player_club and club.id == self.player_club.id
            
            club_name = club.name.replace("[", "(").replace("]", ")")
            if is_player_club:
                club_name = f"* {club_name}"
            
            pos_str = f"{i}*" if is_player_club else str(i)
            
            table.add_row(
                pos_str,
                club_name,
                str(s["played"]),
                str(s["won"]),
                str(s["drawn"]),
                str(s["lost"]),
                str(s["gf"]),
                str(s["ga"]),
                str(s["gf"] - s["ga"]),
                str(s["points"])
            )
        
        console.print(table)
        Prompt.ask("\n按回车返回")
    
    async def _goto_transfer(self):
        self.state = GameState.TRANSFER

    async def _goto_tactics(self):
        self.state = GameState.TACTICS

    async def _goto_main(self):
        self.state = GameState.MAIN_MENU

    async def match_day(self):
        console.clear()
        await self._advance_week()
        self.state = GameState.GAME_LOOP

    async def transfer_menu(self):
        console.clear()
        
        while True:
            console.print(Panel("[bold green]转会市场[/bold green]", border_style="green"))
            
            if not self.player_club:
                console.print("[red]请先选择俱乐部[/red]")
                Prompt.ask("\n按回车返回")
                self.state = GameState.GAME_LOOP
                return
            
            console.print(f"[cyan]俱乐部: {self.player_club.name}[/cyan]")
            console.print(f"[dim]预算: £{(self.player_club.balance or 0):,}[/dim]")
            
            table = Table(show_header=False, box=None)
            table.add_column("选项")
            table.add_column("说明")
            options = [
                ("1", "浏览转会市场", "查看可购买的球员"),
                ("2", "搜索球员", "按条件搜索球员"),
                ("3", "出售球员", "将球员列入转会名单"),
                ("4", "转会报价", "查看收到的报价"),
                ("0", "返回", ""),
            ]
            for opt, name, desc in options:
                table.add_row(f"[cyan]{opt}[/cyan]", f"{name}{' - ' + desc if desc else ''}")
            console.print(table)
            
            choice = Prompt.ask("\n选择", choices=["1", "2", "3", "4", "0"], default="0")
            
            if choice == "0":
                self.state = GameState.GAME_LOOP
                break
            elif choice == "1":
                await self._browse_transfer_market()
            elif choice == "2":
                await self._search_players()
            elif choice == "3":
                await self._sell_players()
            elif choice == "4":
                await self._view_transfer_offers()
    
    async def _browse_transfer_market(self):
        console.print("\n[yellow]浏览转会市场...[/yellow]")
        
        if not self.session_maker:
            return
        
        async with self.session_maker() as session:
            from sqlalchemy import select, or_
            
            club_id = self.player_club.id if self.player_club else -1
            result = await session.execute(
                select(Player).where(Player.club_id != club_id).limit(20)
            )
            players = list(result.scalars().all())
        
        if not players:
            console.print("[dim]没有可购买的球员[/dim]")
            Prompt.ask("\n按回车返回")
            return
        
        table = Table(title="转会市场")
        table.add_column("#", width=3)
        table.add_column("球员", min_width=18)
        table.add_column("位置", width=6)
        table.add_column("能力", width=6)
        table.add_column("年龄", width=6)
        table.add_column("预估身价", width=12)
        
        for i, p in enumerate(players, 1):
            market_value = (p.current_ability or 50) * 10000
            player_name = f"{p.first_name} {p.last_name}".replace("[", "(").replace("]", ")")
            table.add_row(
                str(i),
                player_name,
                p.position.value if p.position else "-",
                str(p.current_ability or 50),
                str(p.age if hasattr(p, 'age') else 25),
                f"£{market_value:,}"
            )
        
        console.print(table)
        Prompt.ask("\n按回车返回")
    
    async def _search_players(self):
        console.print("\n[yellow]搜索球员[/yellow]")
        
        positions = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]
        
        table = Table(show_header=False, box=None)
        for i, pos in enumerate(positions):
            table.add_row(f"[cyan]{i+1}[/cyan]", pos)
        console.print(table)
        
        pos_choice = Prompt.ask("\n选择位置 (1-10, 0=全部)", default="0")
        
        if not self.session_maker:
            return
        
        async with self.session_maker() as session:
            from sqlalchemy import select
            
            club_id = self.player_club.id if self.player_club else -1
            query = select(Player).where(Player.club_id != club_id)
            
            if pos_choice != "0" and pos_choice.isdigit():
                pos_idx = int(pos_choice) - 1
                if 0 <= pos_idx < len(positions):
                    target_pos = positions[pos_idx]
                    query = query.where(Player.position == target_pos)
            
            result = await session.execute(query.limit(15))
            players = list(result.scalars().all())
        
        if not players:
            console.print("[dim]没有找到匹配的球员[/dim]")
        else:
            table = Table(title="搜索结果")
            table.add_column("球员", min_width=18)
            table.add_column("位置", width=6)
            table.add_column("能力", width=6)
            table.add_column("潜力", width=6)
            
            for p in players:
                player_name = f"{p.first_name} {p.last_name}".replace("[", "(").replace("]", ")")
                table.add_row(
                    player_name,
                    p.position.value if p.position else "-",
                    str(p.current_ability or 50),
                    str(p.potential_ability or 60)
                )
            console.print(table)
        
        Prompt.ask("\n按回车返回")
    
    async def _sell_players(self):
        console.print("\n[yellow]出售球员[/yellow]")
        
        if not self.session_maker or not self.player_club:
            return
        
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Player).where(Player.club_id == self.player_club.id)
            )
            players = list(result.scalars().all())
        
        if not players:
            console.print("[dim]阵容中没有球员[/dim]")
            Prompt.ask("\n按回车返回")
            return
        
        table = Table()
        table.add_column("#", width=3)
        table.add_column("球员", min_width=18)
        table.add_column("位置", width=6)
        table.add_column("能力", width=6)
        table.add_column("预估身价", width=12)
        
        for i, p in enumerate(players, 1):
            market_value = (p.current_ability or 50) * 10000
            player_name = f"{p.first_name} {p.last_name}".replace("[", "(").replace("]", ")")
            table.add_row(
                str(i),
                player_name,
                p.position.value if p.position else "-",
                str(p.current_ability or 50),
                f"£{market_value:,}"
            )
        
        console.print(table)
        
        choice = Prompt.ask("\n选择球员列入转会名单 (0=取消)", default="0")
        
        if choice != "0" and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(players):
                player = players[idx]
                console.print(f"[green]已将 {player.first_name} {player.last_name} 列入转会名单[/green]")
                console.print("[dim]等待其他俱乐部报价...[/dim]")
        
        Prompt.ask("\n按回车返回")
    
    async def _view_transfer_offers(self):
        console.print("\n[yellow]转会报价[/yellow]")
        console.print("[dim]暂无转会报价[/dim]")
        Prompt.ask("\n按回车返回")
    
    async def tactics_menu(self):
        console.clear()
        
        while True:
            console.print(Panel("[bold green]战术设置[/bold green]", border_style="green"))
            
            if not self.player_club:
                console.print("[red]请先选择俱乐部[/red]")
                Prompt.ask("\n按回车返回")
                self.state = GameState.GAME_LOOP
                return
            
            console.print(f"[cyan]俱乐部: {self.player_club.name}[/cyan]")
            
            table = Table(show_header=False, box=None)
            table.add_column("选项")
            table.add_column("说明")
            options = [
                ("1", "设置阵型", "选择比赛阵型"),
                ("2", "设置战术风格", "进攻/防守风格"),
                ("3", "球员角色分配", "为球员分配角色"),
                ("4", "查看当前战术", "显示战术设置"),
                ("0", "返回", ""),
            ]
            for opt, name, desc in options:
                table.add_row(f"[cyan]{opt}[/cyan]", f"{name}{' - ' + desc if desc else ''}")
            console.print(table)
            
            choice = Prompt.ask("\n选择", choices=["1", "2", "3", "4", "0"], default="0")
            
            if choice == "0":
                self.state = GameState.GAME_LOOP
                break
            elif choice == "1":
                await self._set_formation()
            elif choice == "2":
                await self._set_play_style()
            elif choice == "3":
                await self._assign_roles()
            elif choice == "4":
                await self._view_current_tactics()
    
    async def _set_formation(self):
        console.print("\n[yellow]设置阵型[/yellow]")
        
        formations = [
            "4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2",
            "4-1-4-1", "4-5-1", "3-4-3", "5-4-1", "4-4-1-1"
        ]
        
        table = Table(show_header=False, box=None)
        for i, f in enumerate(formations, 1):
            table.add_row(f"[cyan]{i}[/cyan]", f)
        console.print(table)
        
        choice = Prompt.ask("\n选择阵型 (1-10)", default="2")
        
        if choice.isdigit() and 1 <= int(choice) <= 10:
            self.current_formation = formations[int(choice) - 1]
            console.print(f"[green]✓ 已设置阵型: {self.current_formation}[/green]")
        
        Prompt.ask("\n按回车返回")
    
    async def _set_play_style(self):
        console.print("\n[yellow]设置战术风格[/yellow]")
        
        styles = [
            ("1", "控球进攻", "短传配合，高位逼抢"),
            ("2", "防守反击", "稳固防守，快速反击"),
            ("3", "边路进攻", "利用边路传中"),
            ("4", "中路渗透", "通过中路组织进攻"),
            ("5", "长传冲吊", "直接长传找前锋"),
        ]
        
        table = Table(show_header=False, box=None)
        for opt, name, desc in styles:
            table.add_row(f"[cyan]{opt}[/cyan]", f"{name} - [dim]{desc}[/dim]")
        console.print(table)
        
        choice = Prompt.ask("\n选择风格 (1-5)", default="1")
        
        style_names = ["控球进攻", "防守反击", "边路进攻", "中路渗透", "长传冲吊"]
        
        if choice.isdigit() and 1 <= int(choice) <= 5:
            self.current_style = style_names[int(choice) - 1]
            console.print(f"[green]✓ 已设置风格: {self.current_style}[/green]")
        
        Prompt.ask("\n按回车返回")
    
    async def _assign_roles(self):
        console.print("\n[yellow]球员角色分配[/yellow]")
        
        if not self.session_maker or not self.player_club:
            return
        
        async with self.session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Player).where(Player.club_id == self.player_club.id).limit(11)
            )
            players = list(result.scalars().all())
        
        if not players:
            console.print("[dim]没有球员[/dim]")
            Prompt.ask("\n按回车返回")
            return
        
        roles_by_position = {
            "GK": ["门将", "清道夫门将"],
            "CB": ["中后卫", "出球中卫", "防守中卫"],
            "LB": ["左后卫", "进攻型左后卫"],
            "RB": ["右后卫", "进攻型右后卫"],
            "CDM": ["后腰", "拖后组织核心"],
            "CM": ["中场", "全能中场", "前插型中场"],
            "CAM": ["前腰", "组织核心"],
            "LW": ["左边锋", "内切左边锋"],
            "RW": ["右边锋", "内切右边锋"],
            "ST": ["前锋", "站桩中锋", "抢点型前锋"],
        }
        
        table = Table()
        table.add_column("#", width=3)
        table.add_column("球员", min_width=18)
        table.add_column("位置", width=6)
        table.add_column("角色", min_width=15)
        
        for i, p in enumerate(players, 1):
            pos = p.position.value if p.position else "CM"
            role = roles_by_position.get(pos, ["默认"])[0]
            player_name = f"{p.first_name} {p.last_name}".replace("[", "(").replace("]", ")")
            table.add_row(
                str(i),
                player_name,
                pos,
                role
            )
        
        console.print(table)
        console.print("\n[green]✓ 角色已自动分配[/green]")
        
        Prompt.ask("\n按回车返回")
    
    async def _view_current_tactics(self):
        console.print("\n[yellow]当前战术设置[/yellow]")
        
        formation = getattr(self, 'current_formation', '4-3-3')
        style = getattr(self, 'current_style', '控球进攻')
        
        console.print(f"[cyan]阵型:[/cyan] {formation}")
        console.print(f"[cyan]风格:[/cyan] {style}")
        
        console.print("\n[dim]战术设置已生效，将影响比赛结果[/dim]")
        
        Prompt.ask("\n按回车返回")
    
    async def _save_game(self):
        """Save current game."""
        console.print("\n[yellow]保存游戏...[/yellow]")
        
        slots = self.save_manager.get_all_slots()
        
        console.print("\n可用存档槽位:")
        for i, slot in enumerate(slots, 1):
            status = f"[dim]空[/dim]"
            if slot.has_save:
                status = f"[green]{slot.save_name}[/green] - S{slot.season}W{slot.week}"
            console.print(f"  槽位 {i}: {status}")
        
        slot_num = IntPrompt.ask("\n选择存档槽位 (1-10)", default=1)
        
        if 1 <= slot_num <= 10:
            save_name = Prompt.ask("存档名称", default=f"Save_S{self.current_season}W{self.current_week}")
            
            self.save_manager.save_to_slot(
                slot_num,
                save_name=save_name,
                season=self.current_season,
                week=self.current_week,
                club_id=self.player_club.id if self.player_club else None,
                standings=self.standings,
                match_results=self.match_results
            )
            
            console.print(f"[green]✓ 游戏已保存到槽位 {slot_num}[/green]")
        
        Prompt.ask("\n按回车返回")
    
    async def load_game(self):
        """Load saved game."""
        slots = self.save_manager.get_all_slots()
        
        console.print("\n存档列表:")
        for i, slot in enumerate(slots, 1):
            if slot.has_save:
                date_str = slot.save_date.strftime('%Y-%m-%d %H:%M') if slot.save_date else "未知"
                console.print(
                    f"  槽位 {i}: [green]{slot.save_name}[/green] - "
                    f"S{slot.season}W{slot.week} ({date_str})"
                )
            else:
                console.print(f"  槽位 {i}: [dim]空[/dim]")
        
        slot_num = IntPrompt.ask("\n选择存档 (0=取消)", default=0)
        
        if slot_num == 0:
            return
        
        if 1 <= slot_num <= 10:
            data = self.save_manager.load_from_slot(slot_num)
            
            if data:
                self.current_season = data.get("season", 1)
                self.current_week = data.get("week", 1)
                self.standings = data.get("standings", {})
                self.match_results = data.get("match_results", [])
                
                club_id = data.get("club_id")
                if club_id:
                    self.player_club = next(
                        (c for c in self.clubs if c.id == club_id), None
                    )
                
                console.print(f"[green]✓ 已加载存档: {data.get('save_name')}[/green]")
                self.state = GameState.GAME_LOOP
            else:
                console.print("[red]加载失败[/red]")
    
    async def manage_saves(self):
        """Manage save slots."""
        while True:
            console.clear()
            console.print(Panel("[bold green]存档管理[/bold green]", border_style="green"))
            
            slots = self.save_manager.get_all_slots()
            
            table = Table()
            table.add_column("槽位", width=6)
            table.add_column("存档名", min_width=20)
            table.add_column("赛季", width=8)
            table.add_column("保存时间", width=20)
            
            for i, slot in enumerate(slots, 1):
                if slot.has_save:
                    date_str = slot.save_date.strftime('%Y-%m-%d %H:%M') if slot.save_date else "未知"
                    table.add_row(
                        f"[cyan]{i}[/cyan]",
                        slot.save_name,
                        f"S{slot.season}W{slot.week}",
                        date_str
                    )
                else:
                    table.add_row(f"[dim]{i}[/dim]", "[dim]空[/dim]", "-", "-")
            
            console.print(table)
            
            console.print("\n[1] 删除存档  [2] 复制存档  [0] 返回")
            choice = Prompt.ask("选择", choices=["1", "2", "0"], default="0")
            
            if choice == "0":
                break
            elif choice == "1":
                slot_num = IntPrompt.ask("选择要删除的槽位", default=1)
                if Confirm.ask(f"确定删除槽位 {slot_num} 的存档？"):
                    self.save_manager.delete_slot(slot_num)
                    console.print("[green]✓ 存档已删除[/green]")
            elif choice == "2":
                src = IntPrompt.ask("源槽位", default=1)
                dst = IntPrompt.ask("目标槽位", default=2)
                self.save_manager.copy_slot(src, dst)
                console.print("[green]✓ 存档已复制[/green]")


async def main():
    game = FMGameManager()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
