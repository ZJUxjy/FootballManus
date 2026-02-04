#!/usr/bin/env python3
"""FM Manager Game Client - Textual-based TUI version.

A modern terminal UI for FM Manager using the Textual framework.
Features:
- Rich interactive screens
- Data tables for squad/transfer listings
- Forms for player search and transfers
- Progress indicators for match simulation
"""

import sys
from pathlib import Path
from datetime import date
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    DataTable,
    Input,
    Select,
    Label,
    ProgressBar,
    TabbedContent,
    TabPane,
    OptionList,
    RadioSet,
    RadioButton,
    Checkbox,
    TextArea,
)
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.reactive import reactive
from textual.binding import Binding

from fm_manager.core.database import init_db, get_session_maker
from fm_manager.core.save_load_enhanced import EnhancedSaveLoadManager, get_save_manager
from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull


class GameState:
    """Global game state manager."""

    def __init__(self):
        self.current_club: Optional[ClubDataFull] = None
        self.current_season: int = 1
        self.current_week: int = 1
        self.in_game_date: date = date(2024, 8, 1)
        self.save_manager = get_save_manager()
        self.db_session = None

    def format_money(self, amount: int) -> str:
        """Format money with appropriate suffix."""
        if amount >= 1_000_000_000:
            return f"€{amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"€{amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"€{amount / 1_000:.0f}K"
        else:
            return f"€{amount:,}"


# Global game state
game_state = GameState()


class MainMenuScreen(Screen):
    """Main menu screen with game options."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="main-menu"):
            yield Static("⚽ FM MANAGER 2024", classes="title")
            yield Static("", classes="spacer")

            with Grid(classes="menu-grid"):
                yield Button("🎮 开始新生涯", id="new-career", variant="primary")
                yield Button("💾 加载生涯", id="load-career", variant="success")
                yield Button("🌐 多人游戏", id="multiplayer", variant="warning")
                yield Button("⚙️ 设置", id="settings")
                yield Button("🚪 退出", id="exit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle menu button presses."""
        button_id = event.button.id

        if button_id == "new-career":
            self.app.push_screen(ClubSelectionScreen())
        elif button_id == "load-career":
            self.app.push_screen(LoadGameScreen())
        elif button_id == "multiplayer":
            self.app.push_screen(MultiplayerScreen())
        elif button_id == "settings":
            self.app.push_screen(SettingsScreen())
        elif button_id == "exit":
            self.app.exit()


class ClubSelectionScreen(Screen):
    """Screen for selecting a club to manage."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.clubs_data = None
        self.major_clubs = []

    def action_quit(self) -> None:
        self.app.exit()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="club-selection"):
            yield Static("选择俱乐部", classes="screen-title")
            yield Static("正在加载俱乐部数据...", id="loading")

            with Vertical(id="club-list", classes="hidden"):
                yield DataTable(id="clubs-table")

                with Horizontal(classes="button-row"):
                    yield Button("选择", id="select-club", variant="primary")
                    yield Button("返回", id="back", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        """Load clubs when screen mounts."""
        self.load_clubs()

    def load_clubs(self) -> None:
        """Load and display available clubs."""
        clubs, players = load_for_match_engine()
        self.clubs_data = clubs

        # Filter major leagues
        major_leagues = [
            "England Premier League",
            "Spain La Liga",
            "Germany Bundesliga",
            "Italy Serie A",
        ]

        self.major_clubs = [c for c in clubs.values() if c.league in major_leagues][:20]

        # Update UI
        self.query_one("#loading", Static).add_class("hidden")
        self.query_one("#club-list", Vertical).remove_class("hidden")

        table = self.query_one("#clubs-table", DataTable)
        table.add_columns("#", "俱乐部", "联赛", "预算", "声望")

        for i, club in enumerate(self.major_clubs, 1):
            budget = getattr(club, "balance", 0) or getattr(club, "transfer_budget", 0)
            budget_str = game_state.format_money(budget)
            table.add_row(str(i), club.name, club.league, budget_str, str(club.reputation))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "select-club":
            table = self.query_one("#clubs-table", DataTable)
            if table.cursor_row is not None:
                idx = table.cursor_row
                if 0 <= idx < len(self.major_clubs):
                    game_state.current_club = self.major_clubs[idx]
                    self.app.push_screen(CareerDashboardScreen())


class CareerDashboardScreen(Screen):
    """Main career mode dashboard."""

    BINDINGS = [
        Binding("1", "squad", "Squad"),
        Binding("2", "tactics", "Tactics"),
        Binding("3", "transfers", "Transfers"),
        Binding("4", "fixtures", "Fixtures"),
        Binding("5", "finances", "Finances"),
        Binding("s", "save", "Save"),
        Binding("escape", "menu", "Menu"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="dashboard"):
            # Club info header
            with Horizontal(classes="club-header"):
                yield Static(id="club-name", classes="club-title")
                yield Static(id="club-stats", classes="club-stats")

            # Main content area
            with Horizontal(classes="main-content"):
                # Left sidebar - menu
                with Vertical(classes="sidebar"):
                    yield Static("功能菜单", classes="sidebar-title")
                    yield Button("👥 阵容管理", id="btn-squad")
                    yield Button("⚽ 战术设置", id="btn-tactics")
                    yield Button("💰 转会中心", id="btn-transfers")
                    yield Button("📅 赛程", id="btn-fixtures")
                    yield Button("🏆 青训", id="btn-youth")
                    yield Button("💵 财务", id="btn-finances")
                    yield Button("▶️ 进行比赛", id="btn-match")
                    yield Static("", classes="spacer")
                    yield Button("💾 保存", id="btn-save", variant="success")
                    yield Button("📋 主菜单", id="btn-menu")

                # Right area - dashboard info
                with Vertical(classes="dashboard-content"):
                    yield Static("📊 仪表板", classes="section-title")

                    with Grid(classes="info-grid"):
                        with Container(classes="info-card"):
                            yield Static("📅 日期", classes="card-title")
                            yield Static(id="date-display")

                        with Container(classes="info-card"):
                            yield Static("🏆 联赛排名", classes="card-title")
                            yield Static("第 4 名", classes="card-value")

                        with Container(classes="info-card"):
                            yield Static("📈 最近战绩", classes="card-title")
                            yield Static("W-W-D-L-W", classes="card-value")

                        with Container(classes="info-card"):
                            yield Static("⚽ 下场比赛", classes="card-title")
                            yield Static("vs 阿森纳 (主场)", classes="card-value")

                    yield Static("📰 最新消息", classes="section-title")
                    with Vertical(classes="news-list"):
                        yield Static("• 明星球员伤愈复出", classes="news-item")
                        yield Static("• 董事会对近期表现满意", classes="news-item")
                        yield Static("• 转会窗口将在2周后开启", classes="news-item")

        yield Footer()

    def on_mount(self) -> None:
        """Update display when screen mounts."""
        if game_state.current_club:
            self.query_one("#club-name", Static).update(game_state.current_club.name)

            budget = getattr(game_state.current_club, "balance", 0)
            transfer_budget = getattr(game_state.current_club, "transfer_budget", 0)

            stats = f"联赛: {game_state.current_club.league} | "
            stats += f"预算: {game_state.format_money(budget)} | "
            stats += f"转会预算: {game_state.format_money(transfer_budget)}"
            self.query_one("#club-stats", Static).update(stats)

            date_str = f"第 {game_state.current_season} 赛季, 第 {game_state.current_week} 周 - {game_state.in_game_date}"
            self.query_one("#date-display", Static).update(date_str)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation buttons."""
        button_id = event.button.id

        if button_id == "btn-squad":
            self.app.push_screen(SquadScreen())
        elif button_id == "btn-tactics":
            self.app.push_screen(TacticsScreen())
        elif button_id == "btn-transfers":
            self.app.push_screen(TransferScreen())
        elif button_id == "btn-fixtures":
            self.app.push_screen(FixturesScreen())
        elif button_id == "btn-finances":
            self.app.push_screen(FinancesScreen())
        elif button_id == "btn-youth":
            self.app.push_screen(YouthScreen())
        elif button_id == "btn-match":
            self.app.push_screen(MatchScreen())
        elif button_id == "btn-save":
            self.action_save()
        elif button_id == "btn-menu":
            self.app.push_screen(MainMenuScreen())

    def action_squad(self) -> None:
        self.app.push_screen(SquadScreen())

    def action_transfers(self) -> None:
        self.app.push_screen(TransferScreen())

    def action_save(self) -> None:
        """Save the game."""
        # Simplified save - in real implementation would use async
        self.notify("游戏已保存！", severity="information")

    def action_quit(self) -> None:
        self.app.exit()


class SquadScreen(Screen):
    """Squad management screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.all_players = []
        self.filtered_players = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="squad-screen"):
            yield Static("阵容管理", classes="screen-title")

            with Horizontal(classes="toolbar"):
                yield Input(placeholder="搜索球员...", id="search-input")
                yield Select(
                    [
                        ("全部位置", "all"),
                        ("GK", "GK"),
                        ("CB", "CB"),
                        ("CM", "CM"),
                        ("ST", "ST"),
                        ("LW", "LW"),
                        ("RW", "RW"),
                        ("CAM", "CAM"),
                    ],
                    id="position-filter",
                )
                yield Button("🔍 搜索", id="search-btn")

            yield DataTable(id="squad-table")

            with Horizontal(classes="button-row"):
                yield Button("查看详情", id="view-player")
                yield Button("设置阵容", id="set-tactics")
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Load squad data."""
        self.load_squad()

    def load_squad(self) -> None:
        """Load and display squad."""
        table = self.query_one("#squad-table", DataTable)
        table.clear(columns=True)
        table.add_columns("姓名", "位置", "年龄", "CA", "PA", "身价", "状态")

        if game_state.current_club:
            self.all_players = getattr(game_state.current_club, "players", [])
            self.filtered_players = sorted(
                self.all_players, key=lambda p: getattr(p, "current_ability", 0), reverse=True
            )
            self.display_players(self.filtered_players)

    def display_players(self, players):
        """Display players in table."""
        table = self.query_one("#squad-table", DataTable)
        table.clear()

        for player in players:
            name = getattr(player, "full_name", "Unknown")
            pos = getattr(player, "position", "-")
            pos_str = pos if isinstance(pos, str) else str(pos)
            age = str(getattr(player, "age", "-"))
            ca = str(int(getattr(player, "current_ability", 0)))
            pa = str(int(getattr(player, "potential_ability", 0)))
            value = game_state.format_money(getattr(player, "market_value", 0) or 1000000)
        self.display_players(self.filtered_players)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "view-player":
            table = self.query_one("#squad-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.filtered_players):
                player = self.filtered_players[table.cursor_row]
                self.app.push_screen(PlayerDetailScreen(player))
        elif event.button.id == "set-tactics":
            self.notify("阵容设置功能开发中...", severity="warning")


class PlayerDetailScreen(Screen):
    """Player detail view screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, player):
        super().__init__()
        self.player = player

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="player-detail"):
            # Header
            name = getattr(self.player, "full_name", "Unknown")
            pos = getattr(self.player, "position", "-")
            pos_str = pos if isinstance(pos, str) else str(pos)
            age = getattr(self.player, "age", "-")

            yield Static(f"⚽ {name}", classes="player-name")
            yield Static(
                f"{pos_str} | 年龄: {age} | CA: {getattr(self.player, 'current_ability', '-')} | PA: {getattr(self.player, 'potential_ability', '-')}",
                classes="player-subtitle",
            )

            with TabbedContent():
                with TabPane("📊 属性"):
                    yield Static("能力评分", classes="section-title")
                    yield DataTable(id="ratings-table")
                    yield Static("技术属性", classes="section-title")
                    with Grid(classes="tech-attrs-grid"):
                        yield Static(f"CA: {int(getattr(self.player, 'current_ability', 0))}")
                        yield Static(f"PA: {int(getattr(self.player, 'potential_ability', 0))}")
                        yield Static(f"年龄: {getattr(self.player, 'age', '-')}")
                        yield Static(f"国籍: {getattr(self.player, 'nationality', '-')}")

                with TabPane("❤️ 状态"):
                    with Vertical(classes="status-panel"):
                        yield Static(f"疲劳度: {getattr(self.player, 'fatigue', '-')}")
                        yield Static(f"体能: {getattr(self.player, 'stamina', '-')}")
                        yield Static(f"比赛状态: {getattr(self.player, 'match_shape', '-')}")
                        yield Static(f"士气: {getattr(self.player, 'happiness', '-')}")
                        yield Static(f"经验: {getattr(self.player, 'match_experience', '-')}")

                with TabPane("💰 合同"):
                    with Vertical(classes="contract-panel"):
                        value = getattr(self.player, "market_value", 0)
                        wage = getattr(self.player, "weekly_wage", 0)
                        club = getattr(self.player, "club_name", "Unknown")

                        yield Static(f"身价: {game_state.format_money(value)}")
                        yield Static(f"周薪: €{wage:,}")
                        yield Static(f"所属俱乐部: {club}")

            with Horizontal(classes="button-row"):
                yield Button("返回", id="back")
                yield Button("放入转会名单", id="list-for-transfer", variant="warning")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Load player ratings."""
        table = self.query_one("#ratings-table", DataTable)
        table.add_columns("位置", "当前能力", "潜力")

        # Add ratings for each position
        positions = [
            ("GK", "rating_gk", "potential_gk"),
            ("SW", "rating_sw", "potential_sw"),
            ("DL", "rating_dl", "potential_dl"),
            ("DC", "rating_dc", "potential_dc"),
            ("DR", "rating_dr", "potential_dr"),
            ("WBL", "rating_wbl", "potential_wbl"),
            ("WBR", "rating_wbr", "potential_wbr"),
            ("DM", "rating_dm", "potential_dm"),
            ("ML", "rating_ml", "potential_ml"),
            ("MC", "rating_mc", "potential_mc"),
            ("MR", "rating_mr", "potential_mr"),
            ("AML", "rating_aml", "potential_aml"),
            ("AMC", "rating_amc", "potential_amc"),
            ("AMR", "rating_amr", "potential_amr"),
            ("FS", "rating_fs", "potential_fs"),
            ("TS", "rating_ts", "potential_ts"),
        ]

        for pos_name, rating_attr, potential_attr in positions:
            rating = getattr(self.player, rating_attr, 0)
            potential = getattr(self.player, potential_attr, 0)
            if rating > 0 or potential > 0:
                table.add_row(pos_name, str(int(rating)), str(int(potential)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "list-for-transfer":
            self.notify(
                f"{getattr(self.player, 'full_name', '球员')} 已放入转会名单！",
                severity="information",
            )
        elif event.button.id == "quit":
            self.app.exit()


class TransferScreen(Screen):
    """Transfer center screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("b", "buy", "Buy Players"),
        Binding("s", "sell", "Sell Players"),
    ]

    def __init__(self):
        super().__init__()
        self.search_results = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with TabbedContent(classes="transfer-screen"):
            with TabPane("🔍 购买球员", id="tab-buy"):
                with Vertical():
                    yield Static("搜索球员", classes="section-title")

                    with Horizontal(classes="search-form"):
                        yield Input(placeholder="球员姓名...", id="player-name")
                        yield Select(
                            [
                                ("任意位置", "all"),
                                ("前锋", "ST"),
                                ("中场", "CM"),
                                ("后卫", "CB"),
                                ("门将", "GK"),
                            ],
                            id="position-select",
                        )
                        yield Input(placeholder="最低能力", id="min-ability")
                        yield Input(placeholder="最高价格(M)", id="max-price")
                        yield Button("搜索", id="search-btn", variant="primary")

                    yield DataTable(id="search-results")

                    with Horizontal(classes="button-row"):
                        yield Button("出价", id="make-offer")
                        yield Button("加入关注", id="add-watchlist")

            with TabPane("💰 出售球员", id="tab-sell"):
                with Vertical():
                    yield Static("我的球员", classes="section-title")
                    yield DataTable(id="my-squad")

                    with Horizontal(classes="button-row"):
                        yield Button("挂牌出售", id="list-player")
                        yield Button("设置价格", id="set-price")

            with TabPane("📨 报价管理", id="tab-offers"):
                with Vertical():
                    yield Static("收到的报价", classes="section-title")
                    yield Static("暂无报价", classes="empty-state")

            with Horizontal(classes="button-row"):
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        results_table = self.query_one("#search-results", DataTable)
        results_table.add_columns("姓名", "位置", "年龄", "CA", "PA", "身价", "俱乐部")

        squad_table = self.query_one("#my-squad", DataTable)
        squad_table.add_columns("姓名", "位置", "年龄", "CA", "身价", "状态")

        self.load_my_squad()

    def load_my_squad(self) -> None:
        table = self.query_one("#my-squad", DataTable)

        if game_state.current_club:
            players = getattr(game_state.current_club, "players", [])
            for player in players[:20]:
                name = getattr(player, "full_name", "Unknown")
                pos = getattr(player, "position", "-")
                pos_str = pos if isinstance(pos, str) else str(pos)
                age = str(getattr(player, "age", "-"))
                ca = str(getattr(player, "current_ability", "-"))[:4]
                value = game_state.format_money(getattr(player, "market_value", 0) or 1000000)

                table.add_row(name, pos_str, age, ca, value, "-")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            self.search_players()
        elif event.button.id == "make-offer":
            table = self.query_one("#search-results", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.search_results):
                player = self.search_results[table.cursor_row]
                self.app.push_screen(TransferOfferScreen(player))
            else:
                self.notify("请先选择一名球员", severity="warning")
        elif event.button.id == "list-player":
            self.notify("挂牌功能开发中...", severity="warning")

    def search_players(self) -> None:
        clubs, players = load_for_match_engine()

        position = self.query_one("#position-select", Select).value
        min_ability_str = self.query_one("#min-ability", Input).value

        try:
            min_ability = int(min_ability_str) if min_ability_str else 0
        except ValueError:
            min_ability = 0

        filtered = []
        for player in players.values():
            ca = getattr(player, "current_ability", 0)
            if ca >= min_ability:
                player_club_id = getattr(player, "club_id", -1)
                current_club_id = getattr(game_state.current_club, "id", -2)
                if player_club_id != current_club_id and player_club_id > 0:
                    filtered.append(player)

        filtered = sorted(filtered, key=lambda p: getattr(p, "current_ability", 0), reverse=True)[
            :20
        ]
        self.search_results = filtered

        table = self.query_one("#search-results", DataTable)
        table.clear()

        for player in filtered:
            name = getattr(player, "full_name", "Unknown")
            pos = getattr(player, "position", "-")
            pos_str = pos if isinstance(pos, str) else str(pos)
            age = str(getattr(player, "age", "-"))
            ca = str(getattr(player, "current_ability", "-"))[:4]
            pa = str(getattr(player, "potential_ability", "-"))[:4]
            value = game_state.format_money(getattr(player, "market_value", 0) or 1000000)

            club_id = getattr(player, "club_id", None)
            club_name = "Unknown"
            if club_id and club_id in clubs:
                club_name = getattr(clubs[club_id], "name", "Unknown")[:15]

            table.add_row(name, pos_str, age, ca, pa, value, club_name)

        self.notify(f"找到 {len(filtered)} 名球员", severity="information")


class TransferOfferScreen(Screen):
    """Transfer offer dialog screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, player):
        super().__init__()
        self.player = player

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="transfer-offer"):
            yield Static("💰 转会出价", classes="screen-title")

            name = getattr(self.player, "full_name", "Unknown")
            club = getattr(self.player, "club_name", "Unknown")
            value = getattr(self.player, "market_value", 0)

            yield Static(f"球员: {name}", classes="offer-player")
            yield Static(f"所属俱乐部: {club}", classes="offer-club")
            yield Static(f"估计身价: {game_state.format_money(value)}", classes="offer-value")

            yield Static("出价详情", classes="section-title")

            with Vertical(classes="offer-form"):
                yield Input(placeholder="出价金额 (€)", id="offer-amount")
                yield Select(
                    [
                        ("直接购买", "cash"),
                        ("分期付款", "installment"),
                        ("租借", "loan"),
                    ],
                    id="offer-type",
                )
                yield Input(placeholder="备注 (可选)", id="offer-notes")

            with Horizontal(classes="button-row"):
                yield Button("提交报价", id="submit-offer", variant="primary")
                yield Button("取消", id="cancel")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "submit-offer":
            amount_str = self.query_one("#offer-amount", Input).value
            offer_type = self.query_one("#offer-type", Select).value

            try:
                amount = int(amount_str) if amount_str else 0
                if amount <= 0:
                    self.notify("请输入有效的出价金额", severity="error")
                    return

                # Check budget
                budget = getattr(game_state.current_club, "transfer_budget", 0) or getattr(
                    game_state.current_club, "balance", 0
                )
                if amount > budget:
                    self.notify(
                        f"出价超出预算! 预算: {game_state.format_money(budget)}", severity="error"
                    )
                    return

                player_name = getattr(self.player, "full_name", "球员")
                self.notify(
                    f"已向 {getattr(self.player, 'club_name', '俱乐部')} 报价 {game_state.format_money(amount)} 求购 {player_name}！",
                    severity="information",
                )
                self.app.pop_screen()

            except ValueError:
                self.notify("请输入有效的数字金额", severity="error")


class TacticsScreen(Screen):
    """Tactics configuration screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="tactics-screen"):
            yield Static("战术设置", classes="screen-title")

            with Horizontal(classes="tactics-content"):
                # Formation selection
                with Vertical(classes="formation-panel"):
                    yield Static("阵型", classes="panel-title")
                    yield RadioSet(
                        RadioButton("4-3-3 (进攻)", value=True),
                        RadioButton("4-4-2 (平衡)"),
                        RadioButton("3-5-2 (控制)"),
                        RadioButton("4-2-3-1 (现代)"),
                        RadioButton("5-3-2 (防守)"),
                        id="formation-select",
                    )

                # Tactical style
                with Vertical(classes="style-panel"):
                    yield Static("战术风格", classes="panel-title")
                    yield Checkbox("高压逼抢", id="press-high")
                    yield Checkbox("控球打法", id="possession")
                    yield Checkbox("快速反击", id="counter-attack")
                    yield Checkbox("边路进攻", id="wide-play")
                    yield Checkbox("长传冲吊", id="long-ball")

            with Horizontal(classes="button-row"):
                yield Button("保存战术", id="save-tactics", variant="primary")
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "save-tactics":
            self.notify("战术已保存！", severity="information")
        elif event.button.id == "quit":
            self.app.exit()


class FixturesScreen(Screen):
    """Fixtures and results screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="fixtures-screen"):
            yield Static("赛程与结果", classes="screen-title")

            with TabbedContent():
                with TabPane("📅  upcoming"):
                    yield DataTable(id="fixtures-table")

                with TabPane("✅ 已完成"):
                    yield DataTable(id="results-table")

            with Horizontal(classes="button-row"):
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Load fixtures."""
        fixtures_table = self.query_one("#fixtures-table", DataTable)
        fixtures_table.add_columns("周次", "对手", "主/客", "状态")
        fixtures_table.add_row("15", "阿森纳", "主", "未开始")
        fixtures_table.add_row("16", "切尔西", "客", "未开始")
        fixtures_table.add_row("17", "利物浦", "主", "未开始")

        results_table = self.query_one("#results-table", DataTable)
        results_table.add_columns("周次", "对手", "比分", "结果")
        results_table.add_row("14", "热刺", "2-1", "✅ 胜")
        results_table.add_row("13", "埃弗顿", "0-0", "🟡 平")
        results_table.add_row("12", "布莱顿", "3-2", "✅ 胜")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "quit":
            self.app.exit()


class FinancesScreen(Screen):
    """Finances screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="finances-screen"):
            yield Static("财务概览", classes="screen-title")

            with Grid(classes="finance-grid"):
                with Container(classes="finance-card"):
                    yield Static("当前余额", classes="card-title")
                    yield Static(id="balance", classes="card-value money")

                with Container(classes="finance-card"):
                    yield Static("转会预算", classes="card-title")
                    yield Static(id="transfer-budget", classes="card-value money")

                with Container(classes="finance-card"):
                    yield Static("工资预算", classes="card-title")
                    yield Static(id="wage-budget", classes="card-value money")

                with Container(classes="finance-card"):
                    yield Static("每周工资", classes="card-title")
                    yield Static(id="weekly-wages", classes="card-value money")

            yield Static("赛季收入预测", classes="section-title")
            with Grid(classes="income-grid"):
                yield Static("比赛日收入: €25M")
                yield Static("电视转播: €100M")
                yield Static("商业收入: €30M")

            with Horizontal(classes="button-row"):
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Load financial data."""
        if game_state.current_club:
            balance = getattr(game_state.current_club, "balance", 0)
            transfer = getattr(game_state.current_club, "transfer_budget", 0)
            wage = getattr(game_state.current_club, "wage_budget", 0)

            self.query_one("#balance", Static).update(game_state.format_money(balance))
            self.query_one("#transfer-budget", Static).update(game_state.format_money(transfer))
            self.query_one("#wage-budget", Static).update(game_state.format_money(wage))
            self.query_one("#weekly-wages", Static).update("€3.2M")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "quit":
            self.app.exit()


class YouthScreen(Screen):
    """Youth academy screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="youth-screen"):
            yield Static("青训学院", classes="screen-title")

            with Grid(classes="youth-info"):
                with Container(classes="info-card"):
                    yield Static("学院评级", classes="card-title")
                    yield Static("⭐⭐⭐⭐ 优秀", classes="card-value")

                with Container(classes="info-card"):
                    yield Static("青训球员", classes="card-title")
                    yield Static("24 人", classes="card-value")

                with Container(classes="info-card"):
                    yield Static("潜力新星", classes="card-title")
                    yield Static("3 人", classes="card-value")

            yield Static("潜力新星", classes="section-title")
            yield DataTable(id="prospects-table")

            with Horizontal(classes="button-row"):
                yield Button("提拔到一线队", id="promote")
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Load prospects."""
        table = self.query_one("#prospects-table", DataTable)
        table.add_columns("姓名", "位置", "年龄", "潜力")
        table.add_row("James Wilson", "ST", "17", "85")
        table.add_row("Tom Davies", "CM", "16", "82")
        table.add_row("Alex Johnson", "CB", "17", "78")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "promote":
            self.notify("球员已提拔！", severity="information")
        elif event.button.id == "quit":
            self.app.exit()


class MatchScreen(Screen):
    """Match simulation screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("space", "play", "Play/Pause"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="match-screen"):
            yield Static("比赛模拟", classes="screen-title")

            with Horizontal(classes="match-header"):
                yield Static("热刺", classes="team-name home")
                yield Static("2 - 1", classes="score")
                yield Static("阿森纳", classes="team-name away")

            yield ProgressBar(id="match-progress", total=90)

            with Vertical(classes="match-events"):
                yield Static("比赛事件", classes="section-title")
                yield Static("34' ⚽ 进球! 孙兴慜", classes="event")
                yield Static("56' ⚽ 进球! 凯恩", classes="event")
                yield Static("78' ⚽ 进球 阿森纳", classes="event opponent")

            with Horizontal(classes="button-row"):
                yield Button("▶️ 开始比赛", id="play-match", variant="primary")
                yield Button("⏭️ 跳过", id="skip")
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "play-match":
            self.notify("比赛进行中...", severity="information")
        elif event.button.id == "quit":
            self.app.exit()


class LoadGameScreen(Screen):
    """Load saved game screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.saves = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="load-screen"):
            yield Static("加载游戏", classes="screen-title")

            yield DataTable(id="saves-table")

            with Horizontal(classes="button-row"):
                yield Button("加载", id="load-btn", variant="primary")
                yield Button("删除", id="delete-btn", variant="error")
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#saves-table", DataTable)
        table.add_columns("存档名", "日期", "赛季", "周次")

        self.saves = game_state.save_manager.get_save_files()
        for metadata, path in self.saves[:10]:
            date_str = metadata.save_date.strftime("%Y-%m-%d %H:%M")
            table.add_row(
                metadata.save_name,
                date_str,
                f"第{metadata.current_season}赛季",
                f"第{metadata.current_week}周",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "load-btn":
            table = self.query_one("#saves-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.saves):
                metadata, path = self.saves[table.cursor_row]
                self.load_game(metadata)
            else:
                self.notify("请先选择一个存档", severity="warning")
        elif event.button.id == "delete-btn":
            table = self.query_one("#saves-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.saves):
                metadata, path = self.saves[table.cursor_row]
                self.delete_save(metadata)
        elif event.button.id == "quit":
            self.app.exit()

    def load_game(self, metadata):
        try:
            loaded_metadata, game_state_data = game_state.save_manager.load_game(metadata.save_name)

            # Update game state
            game_state.current_season = loaded_metadata.current_season
            game_state.current_week = loaded_metadata.current_week
            if loaded_metadata.in_game_date:
                game_state.in_game_date = loaded_metadata.in_game_date

            # Load club from CSV data
            if loaded_metadata.player_club_id:
                clubs, _ = load_for_match_engine()
                if loaded_metadata.player_club_id in clubs:
                    game_state.current_club = clubs[loaded_metadata.player_club_id]
                else:
                    # Fallback: find by name
                    for club in clubs.values():
                        if club.name == loaded_metadata.player_club_name:
                            game_state.current_club = club
                            break

            self.notify(f"存档 '{metadata.save_name}' 加载成功！", severity="information")
            self.app.push_screen(CareerDashboardScreen())

        except Exception as e:
            self.notify(f"加载失败: {e}", severity="error")

    def delete_save(self, metadata):
        try:
            game_state.save_manager.delete_save(metadata.save_name)
            self.notify(f"存档 '{metadata.save_name}' 已删除", severity="information")
            self.on_mount()
        except Exception as e:
            self.notify(f"删除失败: {e}", severity="error")


class MultiplayerScreen(Screen):
    """Multiplayer screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="multiplayer-screen"):
            yield Static("多人游戏", classes="screen-title")

            with Vertical(classes="mp-options"):
                yield Button("🎮 创建房间", id="create-room", variant="primary")
                yield Button("🔗 加入房间", id="join-room", variant="success")
                yield Static("", classes="spacer")
                yield Static("多人游戏功能即将推出！", classes="coming-soon")

            with Horizontal(classes="button-row"):
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id in ("create-room", "join-room"):
            self.notify("多人游戏功能开发中...", severity="warning")
        elif event.button.id == "quit":
            self.app.exit()


class SettingsScreen(Screen):
    """Settings screen."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(classes="settings-screen"):
            yield Static("游戏设置", classes="screen-title")

            with Vertical(classes="settings-list"):
                yield Checkbox("自动保存", id="auto-save", value=True)
                yield Checkbox("显示动画", id="show-animations", value=True)
                yield Checkbox("音效", id="sound", value=False)

                yield Static("", classes="spacer")

                yield RadioSet(
                    RadioButton("英语", value=True),
                    RadioButton("简体中文"),
                    RadioButton("繁体中文"),
                    id="language",
                )

            with Horizontal(classes="button-row"):
                yield Button("保存设置", id="save-settings", variant="primary")
                yield Button("返回", id="back")
                yield Button("🚪 退出游戏", id="quit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "save-settings":
            self.notify("设置已保存！", severity="information")
        elif event.button.id == "quit":
            self.app.exit()


class FMManagerApp(App):
    """Main FM Manager Textual Application."""

    CSS = """
    /* Main App Styles */
    Screen {
        align: center middle;
    }
    
    /* Main Menu */
    .main-menu {
        width: 60;
        height: auto;
        border: solid green;
        padding: 1 2;
    }
    
  .title {
    text-align: center;
    text-style: bold;
    color: green;
  }
    
    .spacer {
        height: 1;
    }
    
    .menu-grid {
        grid-size: 1;
        grid-gutter: 1;
        height: auto;
    }
    
    .menu-grid Button {
        width: 100%;
    }
    
    /* Screen Titles */
  .screen-title {
    text-align: center;
    text-style: bold;
    color: blue;
    margin: 1 0;
  }
    
    .section-title {
        text-style: bold;
        color: yellow;
        margin: 1 0;
    }
    
    /* Club Selection */
    .club-selection {
        width: 80;
        height: auto;
        border: solid blue;
        padding: 1 2;
    }
    
    .hidden {
        display: none;
    }
    
    /* Dashboard */
    .dashboard {
        width: 100%;
        height: 100%;
    }
    
    .club-header {
        height: 3;
        background: blue;
        color: white;
        padding: 0 2;
    }
    
  .club-title {
    text-style: bold;
  }
    
    .club-stats {
        text-align: right;
    }
    
    .main-content {
        height: 1fr;
    }
    
    .sidebar {
        width: 20;
        background: $surface-darken-1;
        padding: 1;
    }
    
    .sidebar-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    
    .sidebar Button {
        width: 100%;
        margin: 1 0;
    }
    
    .dashboard-content {
        padding: 1 2;
    }
    
    .info-grid {
        grid-size: 2;
        grid-gutter: 1;
        margin: 1 0;
    }
    
    .info-card {
        border: solid $primary;
        padding: 1;
        height: auto;
    }
    
    .card-title {
        text-style: bold;
        color: yellow;
    }
    
  .card-value {
    text-align: center;
    margin-top: 1;
  }
    
    .news-list {
        margin-top: 1;
    }
    
    .news-item {
        margin: 1 0;
    }
    
    /* Screens */
    .squad-screen, .transfer-screen, .tactics-screen, 
    .fixtures-screen, .finances-screen, .youth-screen,
    .match-screen, .load-screen, .multiplayer-screen,
    .settings-screen {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    /* Tables */
    DataTable {
        height: 1fr;
        margin: 1 0;
    }
    
    /* Toolbars */
    .toolbar {
        height: auto;
        margin: 1 0;
    }
    
    .toolbar Input, .toolbar Select {
        width: auto;
        margin-right: 1;
    }
    
    /* Button Rows */
    .button-row {
        height: auto;
        margin-top: 1;
    }
    
    .button-row Button {
        margin-right: 1;
    }
    
    /* Search Forms */
    .search-form {
        height: auto;
        margin: 1 0;
    }
    
    .search-form Input, .search-form Select {
        width: auto;
        margin-right: 1;
    }
    
    /* Finance Cards */
    .finance-grid {
        grid-size: 2;
        grid-gutter: 1;
        margin: 1 0;
    }
    
    .finance-card {
        border: solid green;
        padding: 1;
    }
    
    .money {
        color: green;
    }
    
    /* Match Screen */
    .match-header {
        height: 5;
        align: center middle;
        margin: 2 0;
    }
    
  .team-name {
    text-style: bold;
    width: 1fr;
    text-align: center;
  }
  
  .score {
    text-style: bold;
    color: yellow;
    width: auto;
    text-align: center;
  }
    
    .match-events {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }
    
    .event {
        margin: 1 0;
    }
    
    .opponent {
        color: red;
    }
    
    /* Tactics */
    .tactics-content {
        height: 1fr;
    }
    
    .formation-panel, .style-panel {
        width: 1fr;
        border: solid $primary;
        padding: 1;
        margin: 0 1;
    }
    
    .panel-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    
    /* Youth */
    .youth-info {
        grid-size: 3;
        grid-gutter: 1;
        margin: 1 0;
    }
    
    /* Multiplayer */
    .mp-options {
        align: center middle;
        height: 1fr;
    }
    
    .mp-options Button {
        width: 40;
        margin: 1 0;
    }
    
    .coming-soon {
        text-align: center;
        color: yellow;
        text-style: italic;
    }
    
    /* Settings */
    .settings-list {
        padding: 1;
    }
    
    .settings-list Checkbox, .settings-list RadioSet {
        margin: 1 0;
    }
    
    /* Empty State */
    .empty-state {
        text-align: center;
        color: gray;
        text-style: italic;
        margin: 2 0;
    }

    /* Player Detail Screen */
    .player-detail {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    .player-name {
        text-align: center;
        text-style: bold;
        color: yellow;
    }

    .player-subtitle {
        text-align: center;
        color: gray;
        margin-bottom: 1;
    }

    .status-panel, .contract-panel {
        padding: 1;
        border: solid $primary;
        margin: 1 0;
    }

    /* Transfer Offer Screen */
    .transfer-offer {
        width: 60;
        height: auto;
        padding: 1 2;
        border: solid green;
    }

    .offer-player {
        text-style: bold;
        color: yellow;
        text-align: center;
    }

    .offer-club {
        text-align: center;
        color: gray;
    }

    .offer-value {
        text-align: center;
        color: green;
        text-style: bold;
        margin-bottom: 1;
    }

    .offer-form {
        padding: 1;
        border: solid $primary;
        margin: 1 0;
    }
    """

    def on_mount(self) -> None:
        """Initialize the app."""
        self.push_screen(MainMenuScreen())


def main():
    """Main entry point."""
    app = FMManagerApp()
    app.run()


if __name__ == "__main__":
    main()
