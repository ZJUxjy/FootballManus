"""League season simulation for FM Manager.

This module provides functionality to simulate an entire league season,
including fixture generation, match simulation, and standings tracking.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import Club, League, Match, MatchStatus, Player, Season
from fm_manager.engine.match_engine_v2 import MatchSimulatorV2, MatchState
from fm_manager.engine.team_state import (
    TeamDynamicState,
    PlayerMatchState,
    TeamStateManager,
    calculate_performance_rating,
)


@dataclass
class LeagueTableEntry:
    """Entry in the league table (standings)."""
    club_id: int
    club_name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    
    # Form tracking
    form: list[str] = field(default_factory=list)  # Last 5 results: W, D, L
    
    # Dynamic state reference
    dynamic_state: TeamDynamicState | None = None
    
    def add_result(self, goals_for: int, goals_against: int) -> None:
        """Add a match result to this entry."""
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        self.goal_difference = self.goals_for - self.goals_against
        
        if goals_for > goals_against:
            self.won += 1
            self.points += 3
            self.form.append("W")
        elif goals_for == goals_against:
            self.drawn += 1
            self.points += 1
            self.form.append("D")
        else:
            self.lost += 1
            self.form.append("L")
        
        # Keep only last 5
        if len(self.form) > 5:
            self.form = self.form[-5:]
    
    def form_string(self) -> str:
        """Get form as string (e.g., 'WWDWL')."""
        return "".join(self.form) if self.form else "-----"


@dataclass
class SeasonStats:
    """Statistics for a season."""
    # Top scorers
    top_scorers: list[tuple[str, int]] = field(default_factory=list)
    
    # Clean sheets
    clean_sheets: dict[int, int] = field(default_factory=dict)
    
    # Biggest wins
    biggest_wins: list[tuple[str, str, int, int]] = field(default_factory=list)
    
    # Highest scoring matches
    highest_scoring: list[tuple[str, str, int, int]] = field(default_factory=list)
    
    # Form statistics
    longest_win_streaks: list[tuple[str, int]] = field(default_factory=list)
    best_home_records: list[tuple[str, int, int, int]] = field(default_factory=list)  # team, W, D, L


@dataclass
class SeasonResult:
    """Complete season result."""
    season_id: int
    league_name: str
    
    # Final standings
    standings: list[LeagueTableEntry] = field(default_factory=list)
    
    # All matches
    matches: list[MatchState] = field(default_factory=list)
    
    # Statistics
    stats: SeasonStats = field(default_factory=lambda: SeasonStats())
    
    # Dynamic states (for analysis)
    team_states: dict[int, TeamDynamicState] = field(default_factory=dict)
    
    def get_champion(self) -> LeagueTableEntry | None:
        """Get the league champion."""
        return self.standings[0] if self.standings else None
    
    def get_relegated(self, num_teams: int = 3) -> list[LeagueTableEntry]:
        """Get relegated teams."""
        if not self.standings:
            return []
        return self.standings[-num_teams:]
    
    def get_european_spots(self, cl_spots: int = 4, el_spots: int = 2) -> dict[str, list[LeagueTableEntry]]:
        """Get teams qualified for European competitions."""
        if not self.standings:
            return {"champions_league": [], "europa_league": []}
        
        return {
            "champions_league": self.standings[:cl_spots],
            "europa_league": self.standings[cl_spots:cl_spots + el_spots],
        }
    
    def get_team_form_summary(self, club_id: int) -> dict | None:
        """Get form summary for a specific team."""
        state = self.team_states.get(club_id)
        if state:
            return state.get_form_summary()
        return None
    
    def get_form_table(self) -> list[tuple[str, int, str]]:
        """Get table sorted by current form (recent performance)."""
        form_data = []
        for entry in self.standings:
            state = self.team_states.get(entry.club_id)
            if state:
                avg_recent = sum(state.recent_performance) / len(state.recent_performance)
                form_data.append((entry.club_name, int(avg_recent), state.form_string()))
        
        return sorted(form_data, key=lambda x: x[1], reverse=True)


class FixtureGenerator:
    """Generate league fixtures using round-robin algorithm.
    
    Uses the "circle method" to generate a double round-robin schedule.
    """
    
    def generate_double_round_robin(
        self,
        clubs: list[Club],
        season_id: int,
        start_date: date,
        matchday_interval: int = 7,
    ) -> list[list[Match]]:
        """Generate a double round-robin fixture list."""
        if len(clubs) < 2:
            return []
        
        n = len(clubs)
        
        # If odd number of teams, add a dummy "bye" team
        has_bye = False
        if n % 2 == 1:
            clubs = clubs + [None]  # type: ignore
            n += 1
            has_bye = True
        
        num_rounds = n - 1
        matches_per_round = n // 2
        
        matchdays = []
        current_date = start_date
        
        # First half of season
        for round_num in range(num_rounds):
            matches = []
            
            for match_num in range(matches_per_round):
                home_idx = (round_num + match_num) % (n - 1)
                away_idx = (n - 1 - match_num + round_num) % (n - 1)
                
                if match_num == 0:
                    away_idx = n - 1
                
                home_club = clubs[home_idx]
                away_club = clubs[away_idx]
                
                if home_club is None or away_club is None:
                    continue
                
                match = Match(
                    season_id=season_id,
                    matchday=round_num + 1,
                    match_date=current_date,
                    home_club_id=home_club.id,
                    away_club_id=away_club.id,
                    home_score=0,
                    away_score=0,
                    status=MatchStatus.SCHEDULED,
                )
                matches.append(match)
            
            matchdays.append(matches)
            current_date += timedelta(days=matchday_interval)
        
        # Second half (reverse fixtures)
        for round_num in range(num_rounds):
            matches = []
            
            for match_num in range(matches_per_round):
                home_idx = (round_num + match_num) % (n - 1)
                away_idx = (n - 1 - match_num + round_num) % (n - 1)
                
                if match_num == 0:
                    away_idx = n - 1
                
                # Swap home and away
                home_club = clubs[away_idx]
                away_club = clubs[home_idx]
                
                if home_club is None or away_club is None:
                    continue
                
                match = Match(
                    season_id=season_id,
                    matchday=num_rounds + round_num + 1,
                    match_date=current_date,
                    home_club_id=home_club.id,
                    away_club_id=away_club.id,
                    home_score=0,
                    away_score=0,
                    status=MatchStatus.SCHEDULED,
                )
                matches.append(match)
            
            matchdays.append(matches)
            current_date += timedelta(days=matchday_interval)
        
        return matchdays


class SeasonSimulator:
    """Simulate an entire league season with dynamic team states."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.fixture_generator = FixtureGenerator()
        self.match_simulator = MatchSimulatorV2()
        self.state_manager = TeamStateManager()
    
    async def simulate_season(
        self,
        league_id: int,
        season_year: int,
        start_date: date | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        use_dynamic_states: bool = True,
    ) -> SeasonResult:
        """Simulate a complete season with dynamic team states.
        
        Args:
            league_id: League ID
            season_year: Starting year
            start_date: Season start date
            progress_callback: Called with (current_matchday, total_matchdays)
            use_dynamic_states: Whether to use dynamic team/player states
        
        Returns:
            SeasonResult with final standings and all match data
        """
        if start_date is None:
            start_date = date(season_year, 8, 1)
        
        # Get league info
        league = await self.session.get(League, league_id)
        if not league:
            raise ValueError(f"League {league_id} not found")
        
        # Get all clubs
        result = await self.session.execute(
            select(Club).where(Club.league_id == league_id)
        )
        clubs = list(result.scalars().all())
        
        if len(clubs) < 2:
            raise ValueError(f"Not enough clubs in league: {len(clubs)}")
        
        # Create season
        season = Season(
            league_id=league_id,
            start_year=season_year,
            end_year=season_year + 1,
            status="active",
            start_date=start_date,
        )
        self.session.add(season)
        await self.session.commit()
        
        # Initialize dynamic states if enabled
        if use_dynamic_states:
            for club in clubs:
                self.state_manager.initialize_team(club.id, club.name)
            
            # Initialize player states
            for club in clubs:
                players = await self._get_all_players(club.id)
                for player in players:
                    self.state_manager.initialize_player(player)
        
        # Generate fixtures
        fixtures = self.fixture_generator.generate_double_round_robin(
            clubs, season.id, start_date
        )
        
        # Initialize standings with dynamic states
        standings: dict[int, LeagueTableEntry] = {}
        for club in clubs:
            state = self.state_manager.get_team_state(club.id) if use_dynamic_states else None
            standings[club.id] = LeagueTableEntry(
                club_id=club.id,
                club_name=club.name,
                dynamic_state=state,
            )
        
        # Track home records for stats
        home_records: dict[int, list[int]] = {c.id: [0, 0, 0] for c in clubs}  # W, D, L
        
        # Simulate all matchdays
        all_matches: list[MatchState] = []
        total_matchdays = len(fixtures)
        
        for matchday_idx, matchday in enumerate(fixtures):
            matchday_num = matchday_idx + 1
            
            if progress_callback:
                progress_callback(matchday_num, total_matchdays)
            
            # Simulate each match
            for match in matchday:
                home_club = await self.session.get(Club, match.home_club_id)
                away_club = await self.session.get(Club, match.away_club_id)
                
                if not home_club or not away_club:
                    continue
                
                # Get lineups (considering dynamic states)
                if use_dynamic_states:
                    home_players = await self._get_lineup_dynamic(home_club.id)
                    away_players = await self._get_lineup_dynamic(away_club.id)
                else:
                    home_players = await self._get_lineup(home_club.id)
                    away_players = await self._get_lineup(away_club.id)
                
                if len(home_players) < 11 or len(away_players) < 11:
                    continue
                
                # Apply form modifiers if using dynamic states
                if use_dynamic_states:
                    home_state = self.state_manager.get_team_state(home_club.id)
                    away_state = self.state_manager.get_team_state(away_club.id)
                    
                    # Store original fitness values
                    original_home_fitness = [p.fitness for p in home_players]
                    original_away_fitness = [p.fitness for p in away_players]
                    
                    # Apply team form modifiers (through morale/fitness adjustments)
                    if home_state:
                        modifier = home_state.get_form_modifier()
                        for p in home_players:
                            p.fitness = min(100.0, (p.fitness or 50) * modifier)
                    
                    if away_state:
                        modifier = away_state.get_form_modifier()
                        for p in away_players:
                            p.fitness = min(100.0, (p.fitness or 50) * modifier)
                
                # Simulate match
                match_state = self.match_simulator.simulate(
                    home_lineup=home_players[:11],
                    away_lineup=away_players[:11],
                )
                
                # Restore original values
                if use_dynamic_states:
                    for i, p in enumerate(home_players):
                        p.fitness = original_home_fitness[i]
                    for i, p in enumerate(away_players):
                        p.fitness = original_away_fitness[i]
                
                # Update match record
                match.home_score = match_state.home_score
                match.away_score = match_state.away_score
                match.status = MatchStatus.FULL_TIME
                match.events = str([
                    {
                        "minute": e.minute,
                        "type": e.event_type.name,
                        "team": e.team,
                        "player": e.player,
                    }
                    for e in match_state.events
                ])
                
                self.session.add(match)
                
                # Update standings
                standings[home_club.id].add_result(
                    match_state.home_score, match_state.away_score
                )
                standings[away_club.id].add_result(
                    match_state.away_score, match_state.home_score
                )
                
                # Update home record
                if match_state.home_score > match_state.away_score:
                    home_records[home_club.id][0] += 1  # Win
                elif match_state.home_score == match_state.away_score:
                    home_records[home_club.id][1] += 1  # Draw
                else:
                    home_records[home_club.id][2] += 1  # Loss
                
                # Update dynamic states
                if use_dynamic_states:
                    self._update_match_states(
                        home_club, away_club, match_state, matchday_num
                    )
                
                all_matches.append(match_state)
            
            # Recover players between matchdays
            if use_dynamic_states:
                self.state_manager.recover_all_players(days=7)
            
            await self.session.commit()
        
        # Sort standings
        sorted_standings = sorted(
            standings.values(),
            key=lambda x: (x.points, x.goal_difference, x.goals_for),
            reverse=True
        )
        
        # Generate stats
        stats = self._generate_stats(all_matches, clubs, home_records)
        
        # Create result
        result = SeasonResult(
            season_id=season.id,
            league_name=league.name,
            standings=sorted_standings,
            matches=all_matches,
            stats=stats,
            team_states=self.state_manager.team_states,
        )
        
        return result
    
    def _update_match_states(
        self,
        home_club: Club,
        away_club: Club,
        match_state: MatchState,
        matchday: int,
    ) -> None:
        """Update dynamic states after a match."""
        home_score = match_state.home_score
        away_score = match_state.away_score
        
        # Determine results
        if home_score > away_score:
            home_result, away_result = "W", "L"
        elif home_score < away_score:
            home_result, away_result = "L", "W"
        else:
            home_result, away_result = "D", "D"
        
        # Calculate performance ratings
        home_perf = calculate_performance_rating(
            home_score, away_score, match_state.home_possession,
            match_state.home_shots_on_target, home_result == "W"
        )
        away_perf = calculate_performance_rating(
            away_score, home_score, 100 - match_state.home_possession,
            match_state.away_shots_on_target, away_result == "W"
        )
        
        # Update team states
        home_team_state = self.state_manager.get_team_state(home_club.id)
        away_team_state = self.state_manager.get_team_state(away_club.id)
        
        if home_team_state:
            home_team_state.update_after_match(
                home_result, True, home_perf, home_score, away_score
            )
        
        if away_team_state:
            away_team_state.update_after_match(
                away_result, False, away_perf, away_score, home_score
            )
        
        # Update player states (mark as played)
        for player in match_state.home_lineup:
            p_state = self.state_manager.get_player_state(player.id)
            if p_state:
                p_state.play_match(90, home_perf)
        
        for player in match_state.away_lineup:
            p_state = self.state_manager.get_player_state(player.id)
            if p_state:
                p_state.play_match(90, away_perf)
    
    async def _get_lineup(self, club_id: int) -> list[Player]:
        """Get starting lineup for a club."""
        result = await self.session.execute(
            select(Player)
            .where(Player.club_id == club_id)
            .order_by(Player.current_ability.desc())
            .limit(11)
        )
        return list(result.scalars().all())
    
    async def _get_all_players(self, club_id: int) -> list[Player]:
        """Get all players for a club."""
        result = await self.session.execute(
            select(Player)
            .where(Player.club_id == club_id)
        )
        return list(result.scalars().all())
    
    async def _get_lineup_dynamic(self, club_id: int) -> list[Player]:
        """Get lineup considering player fitness and form."""
        # Get all players with their states
        result = await self.session.execute(
            select(Player)
            .where(Player.club_id == club_id)
            .order_by(Player.current_ability.desc())
        )
        players = list(result.scalars().all())
        
        # Get available players sorted by effective rating
        available = []
        for player in players:
            state = self.state_manager.get_player_state(player.id)
            if state is None:
                state = self.state_manager.initialize_player(player)
            
            if state.is_available():
                # Calculate effective rating
                base = player.current_ability or 50
                form_factor = (state.form - 50) / 100 * 10  # +/- 10 points
                fitness_penalty = (100 - state.fitness) * 0.2  # Up to 20 point penalty
                
                effective = base + form_factor - fitness_penalty
                available.append((player, effective, state.fitness))
        
        # Sort by effective rating
        available.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 11
        return [p[0] for p in available[:11]]
    
    def _generate_stats(
        self,
        matches: list[MatchState],
        clubs: list[Club],
        home_records: dict[int, list[int]],
    ) -> SeasonStats:
        """Generate season statistics."""
        stats = SeasonStats()
        
        # Track goal scorers
        scorer_counts: dict[str, int] = {}
        
        for match in matches:
            for event in match.events:
                if event.event_type.name == "GOAL" and event.player:
                    scorer_counts[event.player] = scorer_counts.get(event.player, 0) + 1
            
            # Track biggest wins
            goal_diff = abs(match.home_score - match.away_score)
            if goal_diff >= 3:
                stats.biggest_wins.append((
                    "Home", "Away",
                    max(match.home_score, match.away_score),
                    min(match.home_score, match.away_score),
                ))
            
            # Track highest scoring
            total_goals = match.home_score + match.away_score
            if total_goals >= 5:
                stats.highest_scoring.append((
                    "Home", "Away",
                    match.home_score, match.away_score,
                ))
        
        # Sort top scorers
        stats.top_scorers = sorted(
            scorer_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Track longest win streaks
        streak_data = []
        for club in clubs:
            state = self.state_manager.get_team_state(club.id)
            if state:
                streak_data.append((club.name, state.max_win_streak))
        
        stats.longest_win_streaks = sorted(
            streak_data, key=lambda x: x[1], reverse=True
        )[:5]
        
        # Best home records
        home_data = []
        for club in clubs:
            record = home_records[club.id]
            home_data.append((club.name, record[0], record[1], record[2]))
        
        stats.best_home_records = sorted(
            home_data, key=lambda x: (x[1] * 3 + x[2], x[1]), reverse=True
        )[:5]
        
        return stats


def print_standings(standings: list[LeagueTableEntry], title: str = "League Table") -> None:
    """Print league standings in a formatted table."""
    from rich.table import Table
    from rich.console import Console
    
    console = Console()
    table = Table(title=title)
    
    table.add_column("Pos", justify="right", style="cyan", no_wrap=True)
    table.add_column("Team", style="white")
    table.add_column("P", justify="right")
    table.add_column("W", justify="right")
    table.add_column("D", justify="right")
    table.add_column("L", justify="right")
    table.add_column("GF", justify="right")
    table.add_column("GA", justify="right")
    table.add_column("GD", justify="right")
    table.add_column("Pts", justify="right", style="green bold")
    table.add_column("Form", style="yellow")
    
    for i, entry in enumerate(standings, 1):
        # Position with medals
        pos = str(i)
        if i == 1:
            pos = "🥇"
        elif i == 2:
            pos = "🥈"
        elif i == 3:
            pos = "🥉"
        
        # Form string with colors
        form = entry.form_string()
        colored_form = ""
        for char in form:
            if char == "W":
                colored_form += "[green]W[/]"
            elif char == "D":
                colored_form += "[yellow]D[/]"
            else:
                colored_form += "[red]L[/]"
        
        table.add_row(
            pos,
            entry.club_name[:25],
            str(entry.played),
            str(entry.won),
            str(entry.drawn),
            str(entry.lost),
            str(entry.goals_for),
            str(entry.goals_against),
            f"{entry.goal_difference:+d}",
            str(entry.points),
            colored_form,
        )
    
    console.print(table)


def print_form_table(result: SeasonResult) -> None:
    """Print the form table (teams sorted by current form)."""
    from rich.table import Table
    from rich.console import Console
    
    console = Console()
    
    form_data = result.get_form_table()
    if not form_data:
        return
    
    table = Table(title="Current Form Table")
    table.add_column("Rank", justify="right")
    table.add_column("Team", style="white")
    table.add_column("Form", style="yellow")
    table.add_column("Perf. Rating", justify="right")
    
    for i, (team_name, rating, form_str) in enumerate(form_data[:10], 1):
        # Color form string
        colored_form = ""
        for char in form_str:
            if char == "W":
                colored_form += "[green]W[/]"
            elif char == "D":
                colored_form += "[yellow]D[/]"
            else:
                colored_form += "[red]L[/]"
        
        table.add_row(
            str(i),
            team_name[:25],
            colored_form,
            str(rating),
        )
    
    console.print(table)


def print_momentum_analysis(result: SeasonResult) -> None:
    """Print momentum analysis (streaks and morale)."""
    from rich.table import Table
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    if not result.team_states:
        console.print("[dim]Dynamic states not available[/]")
        return
    
    # Hot teams (on a winning streak)
    hot_teams = []
    struggling_teams = []
    
    for club_id, state in result.team_states.items():
        if state.current_streak >= 3:
            hot_teams.append((state.club_name, state.current_streak, state.morale))
        elif state.current_streak <= -3:
            struggling_teams.append((state.club_name, state.current_streak, state.morale))
    
    hot_teams.sort(key=lambda x: x[1], reverse=True)
    struggling_teams.sort(key=lambda x: x[1])
    
    if hot_teams:
        console.print("\n[bold green]🔥 Hot Teams (Winning Streak)[/]")
        for name, streak, morale in hot_teams[:5]:
            console.print(f"  {name}: {streak} wins (Morale: {morale:.0f})")
    
    if struggling_teams:
        console.print("\n[bold red]❄️ Struggling Teams (Losing Streak)[/]")
        for name, streak, morale in struggling_teams[:5]:
            console.print(f"  {name}: {abs(streak)} losses (Morale: {morale:.0f})")
    
    # Longest streaks
    if result.stats.longest_win_streaks:
        console.print("\n[bold]🏆 Longest Win Streaks This Season:[/]")
        for name, streak in result.stats.longest_win_streaks:
            console.print(f"  {name}: {streak} consecutive wins")
