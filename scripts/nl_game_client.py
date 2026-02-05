"""Enhanced Natural Language Game Interface for FM Manager.

Uses Tool-Calling Architecture with LLM for flexible, natural interactions.
"""

import asyncio
import os
import sys
from datetime import date
from typing import Optional, List

from wcwidth import wcswidth
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import confirm as pt_confirm
from prompt_toolkit.formatted_text import HTML

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fm_manager.ai.llm_tool_interface import get_llm_tool_interface
from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull
from fm_manager.engine.llm_client import LLMClient, LLMProvider


class FMManagerCompleter(WordCompleter):
    """Custom completer with context-aware suggestions."""

    def __init__(self):
        commands = [
            # English
            "find",
            "search",
            "show",
            "view",
            "display",
            "buy",
            "sell",
            "transfer",
            "loan",
            "tactics",
            "formation",
            "strategy",
            "squad",
            "team",
            "players",
            "roster",
            "save",
            "exit",
            "quit",
            "help",
            # Chinese
            "找",
            "搜索",
            "查找",
            "查看",
            "显示",
            "购买",
            "出售",
            "转会",
            "租借",
            "战术",
            "阵型",
            "策略",
            "阵容",
            "球队",
            "球员",
            "队员",
            "保存",
            "退出",
            "帮助",
        ]

        attributes = [
            "English",
            "Brazilian",
            "Spanish",
            "French",
            "German",
            "midfielder",
            "striker",
            "defender",
            "goalkeeper",
            "winger",
            "under 23",
            "under 25",
            "young",
            "experienced",
            "high potential",
            "high ability",
            "star",
            "英格兰",
            "巴西",
            "西班牙",
            "法国",
            "德国",
            "中场",
            "前锋",
            "后卫",
            "门将",
            "边锋",
            "23岁以下",
            "25岁以下",
            "年轻",
            "经验丰富",
            "高潜力",
            "高能力",
            "明星",
        ]

        super().__init__(commands + attributes, ignore_case=True)


class EnhancedNLGameInterface:
    """Enhanced chat-style natural language interface with Tool Calling."""

    def __init__(self):
        """Initialize the enhanced NL game interface."""
        self.console = Console()
        self.session = self._create_prompt_session()

        # NEW: Use LLM Tool Interface instead of IntentParser + CommandExecutor
        self.tool_interface = None

        # Game state
        self.current_club: Optional[ClubDataFull] = None
        self.current_season = 1
        self.current_week = 1
        self.in_game_date = date(2024, 8, 1)
        self.running = False

        # Detect locale
        self.locale = self._detect_locale()

        # Initialize LLM and tool interface
        self._init_llm()

    def _create_prompt_session(self) -> PromptSession:
        """Create Prompt Toolkit session with custom settings."""
        history_file = os.path.expanduser("~/.fm_manager_history")

        style = Style.from_dict(
            {
                "prompt": "#00aa00 bold",
                "input": "#ffffff",
            }
        )

        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            event.app.exit(exception=KeyboardInterrupt)

        @kb.add("c-d")
        def _(event):
            event.app.exit(exception=EOFError)

        return PromptSession(
            completer=FMManagerCompleter(),
            history=FileHistory(history_file),
            style=style,
            key_bindings=kb,
            multiline=False,
            wrap_lines=True,
            complete_while_typing=True,
        )

    def _detect_locale(self) -> str:
        """Detect system locale for multi-language support."""
        import locale

        env_lang = os.getenv("LANG", "")
        if "zh" in env_lang.lower():
            return "zh"

        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale and "zh" in system_locale.lower():
                return "zh"
        except:
            pass

        return "en"

    def _t(self, key: str, **kwargs) -> str:
        """Get translated message."""
        messages = {
            "en": {
                "welcome_title": "FM MANAGER 2024 - AI ASSISTANT",
                "welcome_desc": "Control the game with natural language",
                "examples": "Examples",
                "help_tip": "Type 'help' for more options",
                "exit_tip": "Type 'exit' or 'quit' to leave",
                "ai_thinking": "AI is thinking...",
                "ai_assistant": "AI Assistant",
                "you": "You",
                "loading": "Loading",
                "success": "Success",
                "error": "Error",
                "tip": "Tip",
                "press_tab": "Press TAB for suggestions",
            },
            "zh": {
                "welcome_title": "FM MANAGER 2024 - AI 助手",
                "welcome_desc": "使用自然语言控制游戏",
                "examples": "示例",
                "help_tip": "输入 'help' 查看更多选项",
                "exit_tip": "输入 'exit' 或 'quit' 退出游戏",
                "ai_thinking": "AI 正在思考...",
                "ai_assistant": "AI 助手",
                "you": "你",
                "loading": "加载中",
                "success": "成功",
                "error": "错误",
                "tip": "提示",
                "press_tab": "按 TAB 键查看建议",
            },
        }

        msg = messages.get(self.locale, messages["en"]).get(key, key)
        return msg.format(**kwargs) if kwargs else msg

    def _init_llm(self):
        """Initialize LLM client and tool interface."""
        from pathlib import Path

        try:
            config_path = Path("config/config.toml")
            if config_path.exists():
                import tomllib

                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

                llm_config = config.get("llm", {})
                model = llm_config.get("model", "GLM-4.7")
                base_url = llm_config.get("base_url")
                api_key = llm_config.get("api_key")

                if api_key and base_url:
                    llm_client = LLMClient(
                        provider=LLMProvider.OPENAI,
                        model=model,
                        api_key=api_key,
                        base_url=base_url,
                        temperature=llm_config.get("temperature", 0.3),
                        max_tokens=llm_config.get("max_tokens", 1000),
                    )
                    self.tool_interface = get_llm_tool_interface(llm_client)
                    self.console.print(f"[green]✓ AI Assistant initialized with {model}[/green]")
                else:
                    self._init_mock()
            else:
                self._init_mock()
        except Exception as e:
            self.console.print(f"[yellow]⚠ LLM initialization failed: {e}[/yellow]")
            self._init_mock()

    def _init_mock(self):
        """Initialize with mock LLM for testing."""
        llm_client = LLMClient(provider=LLMProvider.MOCK)
        self.tool_interface = get_llm_tool_interface(llm_client)
        self.console.print("[yellow]⚠ Using rule-based mode (LLM not available)[/yellow]")

    def show_welcome(self):
        """Display welcome message."""
        title = Text(self._t("welcome_title"), justify="center", style="bold cyan")
        self.console.print(Panel(title, border_style="cyan"))

        self.console.print(f"\n[green]{self._t('welcome_desc')}[/green]\n")

        examples_text = """  • "Find English midfielders under 23 with high potential"
  • "Show me my squad sorted by value"
  • "Who is the best young goalkeeper?"
  • "Compare Son and Kane"
  • "Save game"
  
  • "找英格兰中场球员，23岁以下，潜力高"
  • "查看我的阵容按身价排序"
  • "保存游戏"""

        self.console.print(Panel(examples_text, title=self._t("examples"), border_style="yellow"))

        self.console.print(f"\n[cyan]{self._t('help_tip')}[/cyan]")
        self.console.print(f"[cyan]{self._t('exit_tip')}[/cyan]")
        self.console.print(f"[dim]{self._t('press_tab')}[/dim]\n")

    async def start_career(self):
        """Start a new career."""
        self.console.print(f"\n[bold cyan]{self._t('loading')}...[/bold cyan]\n")

        with self.console.status("[bold green]Loading clubs...[/bold green]", spinner="dots"):
            clubs, _ = load_for_match_engine()

        major_leagues = [
            "England Premier League",
            "Spain La Liga",
            "Germany Bundesliga",
            "Italy Serie A",
        ]
        available_clubs = [c for c in clubs.values() if c.league in major_leagues]

        self.console.print(f"[bold green]Select a club to manage:[/bold green]\n")

        for i, club in enumerate(available_clubs[:20], 1):
            budget = getattr(club, "balance", 0) or getattr(club, "transfer_budget", 0)
            self.console.print(
                f"{i:2d}. {club.name:<30} {club.league:<25} Budget: £{budget / 1_000_000:.1f}M"
            )

        while True:
            choice = await self._prompt_async("\nSelect club (number or name): ")

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(available_clubs[:20]):
                    self.current_club = available_clubs[idx]
                    break
                else:
                    self.console.print("[red]Invalid selection[/red]")
            else:
                matches = [c for c in clubs.values() if choice.lower() in c.name.lower()]
                if matches:
                    if len(matches) == 1:
                        self.current_club = matches[0]
                        break
                    else:
                        self.console.print(f"\nFound {len(matches)} clubs:")
                        for i, c in enumerate(matches[:5], 1):
                            self.console.print(f"  {i}. {c.name}")
                        sub_choice = await self._prompt_async("Select: ")
                        if sub_choice.isdigit():
                            sub_idx = int(sub_choice) - 1
                            if 0 <= sub_idx < len(matches[:5]):
                                self.current_club = matches[sub_idx]
                                break
                else:
                    self.console.print(f"[red]No clubs found[/red]")

        # Set club context for tool interface
        if self.tool_interface:
            self.tool_interface.set_club(self.current_club)

        budget = getattr(self.current_club, "balance", 0) or getattr(
            self.current_club, "transfer_budget", 0
        )

        welcome_msg = (
            f"[bold green]✓ Welcome to {self.current_club.name}![/bold green]\n"
            f"  League: {self.current_club.league}\n"
            f"  Budget: £{budget:,.0f}"
        )
        self.console.print(Panel(welcome_msg, border_style="green"))
        self.console.print()

    async def _prompt_async(self, message: str) -> str:
        """Async wrapper for prompt."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.session.prompt(message))

    async def run(self):
        """Main game loop."""
        self.show_welcome()
        await self.start_career()

        # Welcome message
        club_name = self.current_club.name if self.current_club else "your club"
        ai_welcome = f"Hello! I'm your AI assistant. How can I help you manage {club_name} today?"
        if self.locale == "zh":
            ai_welcome = f"你好！我是你的AI助手。今天我能如何帮助你管理{club_name}？"

        self.console.print(f"[bold cyan]{self._t('ai_assistant')}:[/bold cyan] {ai_welcome}\n")

        self.running = True

        while self.running:
            try:
                user_input = await self._prompt_async(f"{self._t('you')}: ")

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "bye", "goodbye", "退出", "再见"]:
                    await self._handle_exit()
                    break

                # NEW: Use tool interface instead of intent parser + command executor
                await self._process_query(user_input)

            except KeyboardInterrupt:
                self.console.print(f"\n\n[yellow]Game interrupted.[/yellow]")
                break
            except EOFError:
                self.console.print(f"\n\n[yellow]Game exited.[/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n[red]{self._t('error')}: {str(e)}[/red]")

    async def _process_query(self, user_input: str):
        """Process user query using tool-calling architecture."""
        if not self.tool_interface:
            self.console.print("[red]Error: AI interface not initialized[/red]")
            return

        with self.console.status(
            f"[bold cyan]{self._t('ai_thinking')}[/bold cyan]", spinner="dots"
        ):
            # NEW: Use LLM tool interface for flexible query handling
            response = await self.tool_interface.process_query(user_input)

        # Display LLM-generated response
        self.console.print(f"[bold cyan]{self._t('ai_assistant')}:[/bold cyan]")
        self.console.print(response)
        self.console.print()

    async def _handle_exit(self):
        """Handle game exit."""
        if self.locale == "zh":
            self.console.print(f"\n[cyan]AI 助手:[/cyan] 退出前是否保存游戏？")
            options = [("1", "保存并退出"), ("2", "直接退出"), ("3", "取消")]
        else:
            self.console.print(f"\n[cyan]AI Assistant:[/cyan] Save before exiting?")
            options = [("1", "Save and Exit"), ("2", "Exit without Saving"), ("3", "Cancel")]

        for key, label in options:
            self.console.print(f"  {key}. {label}")

        choice = await self._prompt_async("\nChoice (1-3): ")

        if choice == "1":
            self.console.print(f"\n[green]✓ {self._t('success')}! Goodbye![/green]\n")
        elif choice == "2":
            self.console.print(f"\n[green]Goodbye![/green]\n")
        elif choice == "3":
            self.running = True


async def main():
    """Entry point."""
    interface = EnhancedNLGameInterface()
    await interface.run()


if __name__ == "__main__":
    asyncio.run(main())
