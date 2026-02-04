#!/usr/bin/env python3
"""FM Manager CLI Client.

Rich-based terminal interface for multiplayer football manager game.
"""

import asyncio
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from fm_manager.cli.client import GameClient
from fm_manager.core.save_load import SaveLoadManager
from fm_manager.core.database import get_db_session

console = Console()


class FMManagerCLI:
    """Main CLI application."""
    
    def __init__(self, server_url: str = "ws://localhost:8000"):
        self.client = GameClient(server_url)
        self.player_name: Optional[str] = None
        self.room_id: Optional[str] = None
        self.running = True
        
        # Setup event handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup WebSocket event handlers."""
        self.client.on("connected", self._on_connected)
        self.client.on("disconnected", self._on_disconnected)
        self.client.on("system", self._on_system_message)
        self.client.on("chat", self._on_chat_message)
        self.client.on("match_result", self._on_match_result)
        self.client.on("player_list", self._on_player_list)
        self.client.on("matchday_start", self._on_matchday_start)
        self.client.on("matchday_complete", self._on_matchday_complete)
        self.client.on("error", self._on_error)
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def _on_connected(self, data=None):
        console.print("[green]✓ Connected to server[/green]")
    
    def _on_disconnected(self):
        console.print("[red]✗ Disconnected from server[/red]")
    
    def _on_system_message(self, data):
        content = data.get("content", "")
        console.print(f"[dim][System] {content}[/dim]")
    
    def _on_chat_message(self, data):
        name = data.get("player_name", "Unknown")
        content = data.get("content", "")
        console.print(f"[cyan]{name}:[/cyan] {content}")
    
    def _on_match_result(self, data):
        match = data.get("match", {})
        home = match.get("home_club_name", "Home")
        away = match.get("away_club_name", "Away")
        home_score = match.get("home_score", 0)
        away_score = match.get("away_score", 0)
        
        console.print(
            f"[bold]{home}[/bold] {home_score}-{away_score} [bold]{away}[/bold]"
        )
    
    def _on_player_list(self, data):
        players = data.get("players", [])
        table = Table(title="Players")
        table.add_column("Name")
        table.add_column("Role")
        table.add_column("Status")
        
        for p in players:
            name = p.get("name", "Unknown")
            role = p.get("role", "human")
            ready = "✓" if p.get("is_ready") else "○"
            connected = "●" if p.get("is_connected") else "○"
            
            table.add_row(name, role, f"{connected} {ready}")
        
        console.print(table)
    
    def _on_matchday_start(self, data):
        matchday = data.get("matchday", 0)
        console.print(f"[bold yellow]Matchday {matchday} started![/bold yellow]")
    
    def _on_matchday_complete(self, data):
        matchday = data.get("matchday", 0)
        console.print(f"[bold green]Matchday {matchday} complete![/bold green]")
        
        # Show standings
        standings = data.get("standings", [])
        if standings:
            table = Table(title="Standings")
            table.add_column("#", justify="right")
            table.add_column("Club")
            table.add_column("P", justify="right")
            table.add_column("W", justify="right")
            table.add_column("D", justify="right")
            table.add_column("L", justify="right")
            table.add_column("GF", justify="right")
            table.add_column("GA", justify="right")
            table.add_column("GD", justify="right")
            table.add_column("Pts", justify="right")
            
            for s in standings:
                table.add_row(
                    str(s.get("position", "-")),
                    s.get("club_name", "Unknown"),
                    str(s.get("played", 0)),
                    str(s.get("won", 0)),
                    str(s.get("drawn", 0)),
                    str(s.get("lost", 0)),
                    str(s.get("gf", 0)),
                    str(s.get("ga", 0)),
                    str(s.get("gd", 0)),
                    str(s.get("points", 0))
                )
            
            console.print(table)
    
    def _on_error(self, error_msg):
        console.print(f"[red]Error: {error_msg}[/red]")
    
    # ========================================================================
    # Main Menu
    # ========================================================================
    
    async def run(self):
        """Main entry point."""
        console.print(Panel.fit(
            "[bold blue]FM Manager[/bold blue] - [green]Premier League Edition[/green]\n"
            "Manage one of 20 Premier League clubs in multiplayer mode!",
            title="Welcome"
        ))
        
        while self.running:
            choice = Prompt.ask(
                "\nMain Menu",
                choices=["join", "create", "list", "save", "load", "exit"],
                default="list"
            )

            if choice == "list":
                await self._list_rooms()
            elif choice == "join":
                await self._join_room_flow()
            elif choice == "create":
                await self._create_room_flow()
            elif choice == "save":
                self._save_game_flow()
            elif choice == "load":
                self._load_game_flow()
            elif choice == "exit":
                self.running = False
    
    async def _list_rooms(self):
        """List available rooms."""
        console.print("\n[yellow]Fetching rooms...[/yellow]")
        
        rooms = await self.client.list_rooms()
        
        if not rooms:
            console.print("[dim]No active rooms found[/dim]")
            return
        
        table = Table(title="Available Rooms")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Players")
        table.add_column("AI")
        
        for room in rooms:
            table.add_row(
                room.get("id", "-"),
                room.get("name", "Unknown"),
                room.get("status", "-"),
                f"{room.get('player_count', 0)}/{room.get('max_players', 0)}",
                "Yes" if room.get("has_ai") else "No"
            )
        
        console.print(table)
    
    async def _create_room_flow(self):
        """Create a new room."""
        name = Prompt.ask("Room name")
        max_players = IntPrompt.ask("Max players", default=4)
        enable_ai = Confirm.ask("Enable AI managers?", default=True)
        
        console.print("[yellow]Creating room...[/yellow]")
        
        result = await self.client.create_room(name, max_players, enable_ai)
        
        if result:
            console.print(f"[green]✓ Room created: {result['room_id']}[/green]")
            await self._join_room_flow(result['room_id'])
        else:
            console.print("[red]Failed to create room[/red]")
    
    async def _join_room_flow(self, room_id: Optional[str] = None):
        """Join a room."""
        if not room_id:
            room_id = Prompt.ask("Room ID")
        
        self.player_name = Prompt.ask("Your name")
        
        console.print("[yellow]Joining room...[/yellow]")
        
        result = await self.client.join_room(room_id, self.player_name)
        
        if not result:
            console.print("[red]Failed to join room[/red]")
            return
        
        self.room_id = room_id
        
        console.print(f"[green]✓ Joined as {self.player_name}[/green]")
        
        # Connect WebSocket
        ws_url = result.get("ws_url", "")
        if ws_url:
            connected = await self.client.connect(room_id, self.client.player_id)
            if connected:
                await self._game_loop()
            else:
                console.print("[red]Failed to connect WebSocket[/red]")
    
    async def _async_input(self, prompt: str) -> str:
        """Thread-safe async input."""
        return await asyncio.get_event_loop().run_in_executor(None, input, prompt)
    
    async def _game_loop(self):
        """Main game interaction loop."""
        console.print("\n[bold green]=== PREMIER LEAGUE SEASON ===[/bold green]")
        console.print("\n[dim]Step 1: Type 'club' to select your Premier League team[/dim]")
        console.print("[dim]Step 2: Type 'ready' when you're ready[/dim]")
        console.print("[dim]Step 3: Host types 'start' to begin the season[/dim]")
        console.print("[dim]Step 4: Type 'simulate' to play each matchday[/dim]")
        console.print("\n[dim]Commands:[/dim] chat, club, ready, start, simulate, quit\n")
        
        while self.client.connected:
            try:
                cmd = await self._async_input("[Command]: ")
                cmd = cmd.strip().lower()
                
                if not cmd:
                    continue
                
                if cmd == "chat":
                    msg = await self._async_input("  Message: ")
                    if msg:
                        await self.client.send_chat(msg)
                
                elif cmd == "club":
                    await self._select_club()
                
                elif cmd == "ready":
                    await self.client.set_ready(True)
                    console.print("[green]✓ You are ready![/green]")
                
                elif cmd == "start":
                    # Debug info
                    room_info = await self.client.get_room_info()
                    if room_info:
                        console.print(f"[dim]Debug: You are {self.client.player_id}, host is {room_info.get('host_id')}[/dim]")
                    success = await self.client.start_game()
                    if success:
                        console.print("[green]✓ Game started![/green]")
                    else:
                        console.print("[red]✗ Failed to start game (host only?)[/red]")
                
                elif cmd == "simulate":
                    success = await self.client.simulate_matchday()
                    if success:
                        console.print("[yellow]Simulating matchday...[/yellow]")
                    else:
                        console.print("[red]✗ Failed to simulate (host only?)[/red]")
                
                elif cmd == "quit":
                    await self.client.disconnect()
                    break
                
                else:
                    console.print(f"[dim]Unknown command: {cmd}[/dim]")
                
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    def _save_game_flow(self):
        """Save current game state."""
        from fm_manager.core.database import get_db_session

        save_manager = SaveLoadManager()
        save_name = Prompt.ask("Save name")

        current_season = IntPrompt.ask("Current season", default=1)
        current_week = IntPrompt.ask("Current week", default=1)

        with get_db_session() as session:
            try:
                save_path = save_manager.save_game(
                    session,
                    save_name,
                    current_season=current_season,
                    current_week=current_week,
                )
                console.print(f"[green]✓ Game saved to: {save_path}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/red]")

    def _load_game_flow(self):
        """Load a saved game state."""
        from fm_manager.core.database import get_db_session

        save_manager = SaveLoadManager()
        saves = save_manager.get_save_files()

        if not saves:
            console.print("[dim]No saved games found[/dim]")
            return

        table = Table(title="Saved Games")
        table.add_column("#")
        table.add_column("Name")
        table.add_column("Date")
        table.add_column("Season")
        table.add_column("Week")

        for i, save in enumerate(saves, 1):
            table.add_row(
                str(i),
                save.save_name,
                save.save_date.strftime("%Y-%m-%d %H:%M"),
                str(save.current_season),
                str(save.current_week),
            )

        console.print(table)

        choice = IntPrompt.ask("Select save", min=1, max=len(saves))
        selected_save = saves[choice - 1]

        try:
            game_data = save_manager.load_game(selected_save.save_name)
            console.print(f"[green]✓ Loaded save: {selected_save.save_name}[/green]")
            console.print(f"[dim]Season {game_data['current_season']}, Week {game_data['current_week']}[/dim]")
        except Exception as e:
            console.print(f"[red]✗ Failed to load: {e}[/red]")

    async def _select_club(self):
        """Select a club to manage."""
        # Get room info to see available clubs
        room_info = await self.client.get_room_info()
        
        if room_info and room_info.get("available_clubs"):
            from rich.columns import Columns
            
            clubs = room_info["available_clubs"]
            console.print("\n[bold green]Premier League Clubs[/bold green]")
            console.print("[dim]All 20 Premier League teams available:[/dim]\n")
            
            for club in clubs:
                cid = club.get("id", "?")
                name = club.get("name", "Unknown")
                console.print(f"  [cyan]{cid}[/cyan]: {name}")
            
            console.print()
        
        club_id = IntPrompt.ask("Club ID")
        
        success = await self.client.select_club(club_id)
        
        if success:
            console.print(f"[green]✓ Selected club {club_id}[/green]")
        else:
            console.print("[red]Failed to select club (already taken or invalid ID)[/red]")


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FM Manager CLI Client")
    parser.add_argument(
        "--server",
        default="ws://localhost:8000",
        help="Server WebSocket URL"
    )
    
    args = parser.parse_args()
    
    cli = FMManagerCLI(args.server)
    
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
