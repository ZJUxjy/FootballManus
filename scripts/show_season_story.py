#!/usr/bin/env python3
"""
Show the story of a season - demonstrating dynamic state effects.

This script shows how team form, momentum, and morale change throughout a season.
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.engine.season_simulator import SeasonSimulator
from fm_manager.core.models import League
from sqlalchemy import select

console = Console()


async def show_season_story():
    """Simulate a season and show the story of how form affects results."""
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # Get a league
        result = await session.execute(select(League).limit(1))
        league = result.scalar_one()
        
        console.print(Panel(
            f"[bold green]Season Story: {league.name} 2024-25[/]\n"
            "Tracking how momentum and form affect the season",
            border_style="green"
        ))
        
        simulator = SeasonSimulator(session)
        
        # Simulate with progress tracking
        result = await simulator.simulate_season(
            league_id=league.id,
            season_year=2024,
            start_date=date(2024, 8, 15),
        )
        
        # Show champion's journey
        champion = result.get_champion()
        if champion and champion.club_id in result.team_states:
            state = result.team_states[champion.club_id]
            
            console.print(f"\n[bold gold1]🏆 Champion's Journey: {champion.club_name}[/]")
            console.print(f"  Final Points: {champion.points}")
            console.print(f"  Record: W{champion.won} D{champion.drawn} L{champion.lost}")
            console.print(f"  Longest Win Streak: {state.max_win_streak} games")
            console.print(f"  Worst Losing Streak: {state.max_loss_streak} games")
            console.print(f"  Final Morale: {state.morale:.0f}/100")
            console.print(f"  Home Form: {state.home_form:.0f}/100")
            console.print(f"  Away Form: {state.away_form:.0f}/100")
        
        # Show comeback stories (teams that were down but recovered)
        console.print("\n[bold green]📈 Biggest Improvements[/]")
        improvements = []
        for entry in result.standings:
            if entry.club_id in result.team_states:
                state = result.team_states[entry.club_id]
                # Calculate form improvement (compare start vs end)
                if len(state.recent_performance) >= 5:
                    early_avg = sum(state.recent_performance[:3]) / 3
                    recent_avg = sum(state.recent_performance[-3:]) / 3
                    improvement = recent_avg - early_avg
                    improvements.append((entry.club_name, improvement, state.current_streak))
        
        improvements.sort(key=lambda x: x[1], reverse=True)
        for name, imp, streak in improvements[:3]:
            console.print(f"  {name}: +{imp:.1f} form improvement")
        
        # Show collapses (teams that were doing well but fell off)
        console.print("\n[bold red]📉 Biggest Drops[/]")
        collapses = []
        for entry in result.standings:
            if entry.club_id in result.team_states:
                state = result.team_states[entry.club_id]
                if len(state.recent_performance) >= 5:
                    early_avg = sum(state.recent_performance[:3]) / 3
                    recent_avg = sum(state.recent_performance[-3:]) / 3
                    drop = early_avg - recent_avg
                    if drop > 0:
                        collapses.append((entry.club_name, drop))
        
        collapses.sort(key=lambda x: x[1], reverse=True)
        for name, drop in collapses[:3]:
            console.print(f"  {name}: -{drop:.1f} form drop")
        
        # Show close title race if any
        console.print("\n[bold blue]🏁 Title Race[/]")
        top_3 = result.standings[:3]
        if len(top_3) >= 2:
            gap = top_3[0].points - top_3[1].points
            if gap <= 5:
                console.print(f"  Close finish! Gap between 1st and 2nd: {gap} points")
                for i, team in enumerate(top_3, 1):
                    state = result.team_states.get(team.club_id)
                    streak = f"({state.current_streak:+d} streak)" if state else ""
                    console.print(f"    {i}. {team.club_name}: {team.points} pts {streak}")
            else:
                console.print(f"  Dominant win by {top_3[0].club_name} (+{gap} points)")
        
        # Relegation battle
        console.print("\n[bold red]⚠️ Relegation Battle[/]")
        bottom_3 = result.standings[-3:]
        for team in reversed(bottom_3):
            state = result.team_states.get(team.club_id)
            if state:
                status = "🔥 Escaped" if state.current_streak > 0 else "❄️ In trouble"
                console.print(f"  {team.club_name}: {team.points} pts - {status}")
        
        # Key moments (biggest upsets)
        console.print("\n[bold yellow]⚡ Key Moments[/]")
        upsets = []
        for match in result.matches:
            # An upset is when a lower-rated team beats a higher-rated one by a lot
            if match.home_score > match.away_score + 2:
                upsets.append((
                    "Home upset", match.home_score, match.away_score
                ))
            elif match.away_score > match.home_score + 2:
                upsets.append((
                    "Away upset", match.away_score, match.home_score
                ))
        
        if upsets:
            console.print(f"  Biggest upsets this season: {len(upsets)} matches with 3+ goal margins")


if __name__ == "__main__":
    asyncio.run(show_season_story())
