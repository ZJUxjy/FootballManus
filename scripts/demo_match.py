#!/usr/bin/env python3
"""
Interactive match simulation demo.

This script demonstrates the match engine with real database players
and provides a live commentary-style output.
"""

import asyncio
import random
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
import time

from fm_manager.core import get_session_maker, init_db
from fm_manager.core.models import Player, Club
from fm_manager.engine.match_engine import MatchSimulator, MatchState, MatchEventType
from sqlalchemy import select

console = Console()


def format_match_display(state: MatchState, home_club: Club, away_club: Club) -> Layout:
    """Create a rich layout for match display."""
    layout = Layout()
    
    # Scoreboard
    score_table = Table(show_header=False, box=None)
    score_table.add_row(
        f"[bold blue]{home_club.name}[/]",
        f"[bold yellow]{state.score_string()}[/]",
        f"[bold red]{away_club.name}[/]"
    )
    score_table.add_row(
        f"[dim]{state.home_shots} shots ({state.home_shots_on_target} on target)[/]",
        f"[dim]{state.minute}'[/]",
        f"[dim]{state.away_shots} shots ({state.away_shots_on_target} on target)[/]"
    )
    
    # Events
    events_text = "\n".join([
        f"{e.minute}': {e.description}"
        for e in state.events[-5:]  # Last 5 events
    ])
    
    layout.split_column(
        Layout(Panel(score_table, title="Scoreboard", border_style="green"), size=8),
        Layout(Panel(events_text, title="Match Events", border_style="blue"), size=15),
    )
    
    return layout


async def run_live_match():
    """Run a live match simulation with commentary."""
    console.print("[bold green]FM Manager - Match Simulation Demo[/]\n")
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # Get two top clubs
        result = await session.execute(
            select(Club).order_by(Club.reputation.desc()).limit(2)
        )
        clubs = result.scalars().all()
        
        if len(clubs) < 2:
            console.print("[red]Not enough clubs in database[/]")
            return
        
        home_club, away_club = clubs[0], clubs[1]
        
        # Get players
        result = await session.execute(
            select(Player).where(Player.club_id == home_club.id).limit(11)
        )
        home_players = result.scalars().all()
        
        result = await session.execute(
            select(Player).where(Player.club_id == away_club.id).limit(11)
        )
        away_players = result.scalars().all()
        
        console.print(f"[bold]Match: {home_club.name} vs {away_club.name}[/]")
        console.print(f"[dim]Venue: {home_club.stadium_name}[/]\n")
        
        # Simulate match
        simulator = MatchSimulator(random_seed=random.randint(1, 1000))
        
        events_log = []
        
        def on_minute(state: MatchState):
            """Callback for each minute."""
            # Check if there's a new event
            if state.events and state.events[-1] not in events_log:
                event = state.events[-1]
                events_log.append(event)
                
                if event.event_type == MatchEventType.GOAL:
                    console.print(f"\n[bold yellow]{event.minute}': ⚽ {event.description}[/]")
                    console.print(f"[bold]Score: {state.score_string()}[/]\n")
                elif event.event_type in (MatchEventType.YELLOW_CARD, MatchEventType.RED_CARD):
                    emoji = "🟥" if event.event_type == MatchEventType.RED_CARD else "🟨"
                    console.print(f"[bold]{event.minute}': {emoji} {event.description}[/]")
        
        # Run simulation
        state = simulator.simulate(
            home_lineup=list(home_players),
            away_lineup=list(away_players),
            callback=on_minute,
        )
        
        # Final result
        console.print("\n" + "="*60)
        console.print(f"[bold green]FULL TIME: {home_club.name} {state.score_string()} {away_club.name}[/]")
        console.print("="*60)
        
        # Match stats
        stats_table = Table(title="Match Statistics")
        stats_table.add_column("", style="cyan")
        stats_table.add_column(home_club.name, justify="center")
        stats_table.add_column(away_club.name, justify="center")
        
        stats_table.add_row(
            "Possession",
            f"{state.home_possession:.1f}%",
            f"{100-state.home_possession:.1f}%"
        )
        stats_table.add_row(
            "Shots (on target)",
            f"{state.home_shots} ({state.home_shots_on_target})",
            f"{state.away_shots} ({state.away_shots_on_target})"
        )
        stats_table.add_row(
            "Yellow Cards",
            str(state.home_yellows),
            str(state.away_yellows)
        )
        stats_table.add_row(
            "Red Cards",
            str(state.home_reds),
            str(state.away_reds)
        )
        
        console.print(stats_table)
        
        # Goal scorers
        goals = [e for e in state.events if e.event_type == MatchEventType.GOAL]
        if goals:
            console.print("\n[bold]Goal Scorers:[/]")
            for goal in goals:
                team_emoji = "🔵" if goal.team == "home" else "🔴"
                console.print(f"  {team_emoji} {goal.minute}' - {goal.player}")


async def run_quick_simulations():
    """Run multiple simulations to show statistics."""
    console.print("\n[bold green]Running Multiple Simulations...[/]\n")
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        result = await session.execute(
            select(Club).order_by(Club.reputation.desc()).limit(2)
        )
        clubs = result.scalars().all()
        home_club, away_club = clubs[0], clubs[1]
        
        # Get players
        result = await session.execute(
            select(Player).where(Player.club_id == home_club.id).limit(11)
        )
        home_players = list(result.scalars().all())
        
        result = await session.execute(
            select(Player).where(Player.club_id == away_club.id).limit(11)
        )
        away_players = list(result.scalars().all())
        
        # Run 50 simulations
        results = {"home": 0, "draw": 0, "away": 0}
        score_counts = {}
        
        for i in range(50):
            # Use random seed for true randomness each run
            simulator = MatchSimulator(random_seed=random.randint(1, 100000))
            state = simulator.simulate(home_lineup=home_players, away_lineup=away_players)
            
            if state.home_score > state.away_score:
                results["home"] += 1
            elif state.away_score > state.home_score:
                results["away"] += 1
            else:
                results["draw"] += 1
            
            score = f"{state.home_score}-{state.away_score}"
            score_counts[score] = score_counts.get(score, 0) + 1
        
        # Display results
        console.print(f"[bold]50 Simulations: {home_club.name} vs {away_club.name}[/]\n")
        
        results_table = Table(title="Results Distribution")
        results_table.add_column("Result", style="cyan")
        results_table.add_column("Count", justify="right")
        results_table.add_column("Percentage", justify="right")
        
        results_table.add_row(
            f"{home_club.name} Win",
            str(results["home"]),
            f"{results['home']/50*100:.0f}%"
        )
        results_table.add_row("Draw", str(results["draw"]), f"{results['draw']/50*100:.0f}%")
        results_table.add_row(
            f"{away_club.name} Win",
            str(results["away"]),
            f"{results['away']/50*100:.0f}%"
        )
        
        console.print(results_table)
        
        # Most common scores
        console.print("\n[bold]Most Common Scores:[/]")
        for score, count in sorted(score_counts.items(), key=lambda x: -x[1])[:5]:
            bar = "█" * count
            console.print(f"  {score:5} | {bar} {count}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Match Simulation Demo")
    parser.add_argument(
        "--mode",
        choices=["live", "sim", "both"],
        default="both",
        help="Demo mode: live match, simulations, or both"
    )
    
    args = parser.parse_args()
    
    if args.mode in ("live", "both"):
        asyncio.run(run_live_match())
    
    if args.mode in ("sim", "both"):
        asyncio.run(run_quick_simulations())


if __name__ == "__main__":
    main()
