#!/usr/bin/env python3
"""
League Season Simulation Script.

This script simulates an entire league season and displays the results.
Usage:
    python scripts/simulate_season.py --league "Premier League"
    python scripts/simulate_season.py --league-id 1
"""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.panel import Panel

from fm_manager.core import init_db, close_db, get_session_maker
from fm_manager.engine.season_simulator import (
    SeasonSimulator,
    print_standings,
    print_form_table,
    print_momentum_analysis,
    LeagueTableEntry,
)
from fm_manager.core.models import League
from sqlalchemy import select

console = Console()


async def simulate_league_season(league_name: str | None = None, league_id: int | None = None):
    """Simulate a full season for a league."""
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # Find league
        if league_id:
            league = await session.get(League, league_id)
        elif league_name:
            result = await session.execute(
                select(League).where(League.name == league_name)
            )
            league = result.scalar_one_or_none()
        else:
            # Default to first league
            result = await session.execute(select(League).limit(1))
            league = result.scalar_one_or_none()
        
        if not league:
            console.print("[red]League not found![/]")
            return
        
        console.print(Panel(
            f"[bold green]Simulating {league.name} Season 2024-25[/]\n"
            f"[dim]Format: Double round-robin ({league.teams_count} teams)[/]",
            border_style="green"
        ))
        
        # Create simulator
        simulator = SeasonSimulator(session)
        
        # Progress callback
        def on_progress(current: int, total: int):
            pass  # Rich progress handles this differently
        
        # Simulate season with progress bar
        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Simulating {league.name}...",
                total=(league.teams_count - 1) * 2  # Double round-robin
            )
            
            def progress_callback(current: int, total: int):
                progress.update(task, completed=current)
            
            result = await simulator.simulate_season(
                league_id=league.id,
                season_year=2024,
                start_date=date(2024, 8, 15),
                progress_callback=progress_callback,
            )
        
        # Display results
        console.print("\n")
        print_standings(result.standings, f"Final {league.name} Table 2024-25")
        
        # Dynamic State Analysis
        console.print("\n")
        print_form_table(result)
        print_momentum_analysis(result)
        
        # Champion
        champion = result.get_champion()
        if champion:
            console.print(f"\n[bold gold1]🏆 Champion: {champion.club_name} ({champion.points} points)[/]")
        
        # European qualification
        european_spots = result.get_european_spots(
            cl_spots=league.champions_league_spots,
            el_spots=league.europa_league_spots,
        )
        
        if european_spots["champions_league"]:
            cl_teams = ", ".join([e.club_name for e in european_spots["champions_league"]])
            console.print(f"[bold blue]⭐ Champions League: {cl_teams}[/]")
        
        if european_spots["europa_league"]:
            el_teams = ", ".join([e.club_name for e in european_spots["europa_league"]])
            console.print(f"[bold orange3]🌍 Europa League: {el_teams}[/]")
        
        # Relegation
        relegated = result.get_relegated(league.relegation_count)
        if relegated:
            rel_teams = ", ".join([e.club_name for e in relegated])
            console.print(f"[bold red]⬇️ Relegated: {rel_teams}[/]")
        
        # Season statistics
        console.print("\n[bold]Season Statistics:[/]")
        
        # Total matches and goals
        total_matches = len(result.matches)
        total_goals = sum(m.home_score + m.away_score for m in result.matches)
        avg_goals = total_goals / total_matches if total_matches > 0 else 0
        
        console.print(f"  Total Matches: {total_matches}")
        console.print(f"  Total Goals: {total_goals}")
        console.print(f"  Average Goals per Match: {avg_goals:.2f}")
        
        # Top scorers
        if result.stats.top_scorers:
            console.print("\n[bold]Top Scorers:[/]")
            for i, (player, goals) in enumerate(result.stats.top_scorers[:5], 1):
                console.print(f"  {i}. {player}: {goals} goals")
        
        # Form table (last 5 matches)
        console.print("\n[bold]Current Form (Last 5 Matches):[/]")
        form_table = Table(show_header=True, header_style="bold")
        form_table.add_column("Team", style="white")
        form_table.add_column("Form", style="yellow")
        form_table.add_column("Points", justify="right")
        
        for entry in sorted(result.standings, key=lambda x: x.points, reverse=True)[:5]:
            # Color code form
            colored_form = ""
            for result_code in entry.form:
                if result_code == "W":
                    colored_form += "[green]W[/]"
                elif result_code == "D":
                    colored_form += "[yellow]D[/]"
                else:
                    colored_form += "[red]L[/]"
            
            form_table.add_row(
                entry.club_name[:20],
                colored_form,
                str(entry.points),
            )
        
        console.print(form_table)
        
        # Sample match results
        console.print("\n[bold]Sample Match Results:[/]")
        sample_matches = result.matches[:5]
        for match in sample_matches:
            # Find club names
            home_name = "Unknown"
            away_name = "Unknown"
            for entry in result.standings:
                if entry.club_id == match.home_lineup[0].club_id if match.home_lineup else 0:
                    home_name = entry.club_name
                if entry.club_id == match.away_lineup[0].club_id if match.away_lineup else 0:
                    away_name = entry.club_name
            
            console.print(f"  {home_name} {match.score_string()} {away_name}")


async def simulate_multiple_seasons(league_name: str, num_seasons: int = 10):
    """Simulate multiple seasons to check for variety."""
    console.print(f"\n[bold]Simulating {num_seasons} seasons for statistical analysis...[/]\n")
    
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # Find league
        result = await session.execute(
            select(League).where(League.name == league_name)
        )
        league = result.scalar_one_or_none()
        
        if not league:
            console.print(f"[red]League '{league_name}' not found![/]")
            return
        
        # Track champions
        champion_counts: dict[str, int] = {}
        all_positions: dict[str, list[int]] = {}
        
        for season_num in range(num_seasons):
            simulator = SeasonSimulator(session)
            
            season_result = await simulator.simulate_season(
                league_id=league.id,
                season_year=2024 + season_num,
                start_date=date(2024 + season_num, 8, 15),
            )
            
            # Track champion
            champion = season_result.get_champion()
            if champion:
                champion_counts[champion.club_name] = champion_counts.get(champion.club_name, 0) + 1
            
            # Track positions for each team
            for pos, entry in enumerate(season_result.standings, 1):
                if entry.club_name not in all_positions:
                    all_positions[entry.club_name] = []
                all_positions[entry.club_name].append(pos)
            
            console.print(f"Season {season_num + 1}: 🏆 {champion.club_name if champion else 'Unknown'}")
        
        # Display statistics
        console.print("\n[bold]Championship Distribution:[/]")
        champ_table = Table()
        champ_table.add_column("Team", style="white")
        champ_table.add_column("Titles", justify="right")
        champ_table.add_column("Percentage", justify="right")
        
        for team, count in sorted(champion_counts.items(), key=lambda x: -x[1]):
            percentage = (count / num_seasons) * 100
            champ_table.add_row(team, str(count), f"{percentage:.1f}%")
        
        console.print(champ_table)
        
        # Average positions
        console.print("\n[bold]Average Finishing Position:[/]")
        pos_table = Table()
        pos_table.add_column("Team", style="white")
        pos_table.add_column("Avg Position", justify="right")
        pos_table.add_column("Best", justify="right")
        pos_table.add_column("Worst", justify="right")
        
        for team, positions in sorted(all_positions.items(), key=lambda x: sum(x[1])/len(x[1])):
            avg_pos = sum(positions) / len(positions)
            pos_table.add_row(
                team,
                f"{avg_pos:.1f}",
                str(min(positions)),
                str(max(positions)),
            )
        
        console.print(pos_table)


def main():
    parser = argparse.ArgumentParser(description="Simulate a league season")
    parser.add_argument(
        "--league",
        type=str,
        help="League name (e.g., 'Premier League')"
    )
    parser.add_argument(
        "--league-id",
        type=int,
        help="League ID"
    )
    parser.add_argument(
        "--multi",
        type=int,
        metavar="N",
        help="Simulate N seasons for statistical analysis"
    )
    
    args = parser.parse_args()
    
    if args.multi:
        asyncio.run(simulate_multiple_seasons(
            args.league or "Premier League",
            args.multi
        ))
    else:
        asyncio.run(simulate_league_season(args.league, args.league_id))


if __name__ == "__main__":
    main()
