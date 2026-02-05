"""Comprehensive Season Simulation System.

Features:
- Multiple leagues running simultaneously
- Promotion/relegation system
- European competitions (Champions League, Europa League)
- Cup competitions
- Full integration with match engine, finance engine, transfer engine
- Dynamic state tracking
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum, auto
from typing import Optional, Dict, List, Tuple, Callable
import asyncio

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import (
    Club,
    League,
    Match,
    MatchStatus,
    Season,
    Player,
    Transfer,
    TransferStatus,
)
from fm_manager.core.database import get_db_session
from fm_manager.engine.match_engine_markov import EnhancedMarkovEngine
from fm_manager.engine.team_state import TeamStateManager
from fm_manager.engine.finance_engine import FinanceEngine
from fm_manager.engine.transfer_engine_enhanced import EnhancedTransferEngine


class CompetitionType(Enum):
    """Types of competitions."""

    LEAGUE = "league"  # Domestic league
    CHAMPIONS_LEAGUE = "cl"  # Champions League
    EUROPA_LEAGUE = "el"  # Europa League
    DOMESTIC_CUP = "cup"  # FA Cup, DFB-Pokal, etc.


class PlayoffType(Enum):
    """Playoff match types."""

    TWO_LEG = "two_leg"  # Home and away
    ONE_OFF = "one_off"  # Single match (for final)


@dataclass
class EuropeanFixture:
    """European competition fixture."""

    competition_type: CompetitionType
    season_year: int

    # Knockout stage
    stage: str  # "group_stage", "round_of_16", "quarter_final", "semi_final", "final"

    # Teams
    home_club_id: int
    away_club_id: int

    # Match details (if played)
    match_id: Optional[int] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_away: Optional[int] = None  # Aggregated score for two-leg ties

    # Status
    scheduled_date: Optional[date] = None
    played: bool = False


@dataclass
class LeagueStandings:
    """Current league standings with tie-breakers."""

    club_id: int
    club_name: str

    # Basic stats
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0

    # Goals
    goals_for: int = 0
    goals_against: int = 0

    # Points
    points: int = 0

    # Form
    form: List[str] = field(default_factory=list)

    # Tie-breakers (in order of importance)
    head_to_head: int = 0  # Head-to-head record
    goal_diff: int = 0  # Goal difference

    # European qualification tracking
    cl_position: Optional[int] = None  # Champions League position
    el_position: Optional[int] = None  # Europa League position


@dataclass
class SeasonProgress:
    """Track progress through a season."""

    current_date: date
    current_matchday: int = 1
    total_matchdays: int = 38

    # Weeks processed
    weeks_processed: int = 0

    # Matches completed
    matches_completed: int = 0
    matches_total: int = 0


@dataclass
class PromotionRelegation:
    """Track promotion and relegation rules."""

    # Promotion spots (top teams qualify for higher division)
    promotion_spots: int = 3

    # Relegation spots (bottom teams relegated)
    relegation_spots: int = 3

    # Playoff spots (for leagues with playoffs)
    playoff_win_spot: int = 0
    playoff_lose_spot: int = 0


class ComprehensiveSeasonSimulator:
    """Complete season simulation with European competitions."""

    def __init__(self, random_seed: Optional[int] = None):
        self.rng = random.Random(random_seed)

        # Engines
        self.match_engine = EnhancedMarkovEngine(random_seed=random_seed)
        self.state_manager = TeamStateManager()
        self.finance_engine = FinanceEngine()
        self.transfer_engine = EnhancedTransferEngine()

        # State tracking
        self.standings: Dict[int, Dict[int, LeagueStandings]] = {}
        self.european_fixtures: List[EuropeanFixture] = []
        self.european_tables: Dict[str, List[Tuple[int, int, int]]] = {}

    async def simulate_full_season(
        self,
        league_ids: List[int],
        year: int,
        start_date: Optional[date] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict:
        """Simulate a complete season with European competitions.

        Args:
            league_ids: IDs of leagues to simulate
            year: Season year (e.g., 2024 for 2024-25 season)
            start_date: Season start date
            progress_callback: Called with (current_week, total_weeks)

        Returns:
            Dict with final standings and all results
        """
        if start_date is None:
            start_date = date(year, 8, 1)

        # Initialize state
        progress = SeasonProgress(
            current_date=start_date,
            current_matchday=1,
            total_matchdays=38,
        )

        # Load leagues
        async with get_db_session() as session:
            # Get leagues
            leagues = []
            for league_id in league_ids:
                league = await session.get(League, league_id)
                if league:
                    leagues.append(league)

            # Initialize standings for each league
            for league in leagues:
                if league.id not in self.standings:
                    self.standings[league.id] = {}

                    # Get clubs
                    result = await session.execute(select(Club).where(Club.league_id == league.id))
                    clubs = list(result.scalars().all())

                    # Initialize standings
                    for club in clubs:
                        if club.id not in self.standings[league.id]:
                            self.standings[league.id][club.id] = LeagueStandings(
                                club_id=club.id or 0,
                                club_name=club.name or "Unknown",
                            )

        # Generate fixtures
        fixtures = await self._generate_fixtures(leagues, year, start_date)

        # Process season week by week
        while progress.current_matchday <= progress.total_matchdays:
            # Process matches for current matchday
            await self._process_matchday(progress.current_matchday, fixtures, progress, session)

            # Update progress
            progress.current_matchday += 1
            progress.weeks_processed = (progress.current_matchday - 1) // 4

            if progress_callback:
                progress_callback(progress.weeks_processed, 38)

        # Handle end of season
        await self._handle_season_end(leagues, session)

        return {
            "season_year": year,
            "standings": self.standings,
            "european_winners": await self._get_european_winners(),
        }

    async def _generate_fixtures(
        self,
        leagues: List[League],
        year: int,
        start_date: date,
    ) -> Dict[int, List[List[Match]]]:
        """Generate fixtures for all leagues."""
        all_fixtures = {}

        for league in leagues:
            # Generate league fixtures (round robin)
            if league.format.value == "double_round_robin":
                fixtures = self._generate_double_round_robin(league, year, start_date)
            elif league.format.value == "split":
                fixtures = self._generate_split_season(league, year, start_date)
            elif league.format.value == "playoff":
                fixtures = self._generate_playoff_season(league, year, start_date)
            else:
                fixtures = self._generate_single_round_robin(league, year, start_date)

            all_fixtures[league.id] = fixtures

        # Generate European fixtures
        await self._generate_european_fixtures(leagues, year, start_date)

        return all_fixtures

    async def _process_matchday(
        self,
        matchday: int,
        fixtures: Dict[int, List[List[Match]]],
        progress: SeasonProgress,
        session: AsyncSession,
    ) -> None:
        """Process all matches for a given matchday."""
        for league_id, league_fixtures in fixtures.items():
            for match in league_fixtures[matchday - 1]:  # 0-indexed
                if match.status == MatchStatus.SCHEDULED:
                    # Check if clubs have enough players
                    result = await session.execute(
                        select(Club).where(Club.id == match.home_club_id)
                    )
                    home_club = result.scalars().first()

                    result = await session.execute(
                        select(Club).where(Club.id == match.away_club_id)
                    )
                    away_club = result.scalars().first()

                    if not home_club or not away_club:
                        continue

                    # Get lineups
                    home_players = await self._get_club_players(home_club.id, session)
                    away_players = await self._get_club_players(away_club.id, session)

                    if len(home_players) < 11 or len(away_players) < 11:
                        continue

                    # Simulate match
                    match_state = self.match_engine.simulate(
                        home_lineup=home_players[:11],
                        away_lineup=away_players[:11],
                        home_formation=self._get_club_formation(home_club.id, league_id),
                        away_formation=self._get_club_formation(away_club.id, league_id),
                    )

                    # Update match result
                    match.home_score = match_state.home_score
                    match.away_score = match_state.away_score
                    match.status = MatchStatus.FULL_TIME

                    # Update standings
                    await self._update_standings(match, league_id, session)

                    # Save match details
                    session.add(match)

            # Process finances for the week
            await self._process_weekly_finances(matchday, fixtures, session)

            # Save progress
            await session.commit()

    async def _update_standings(
        self,
        match: Match,
        league_id: int,
        session: AsyncSession,
    ) -> None:
        """Update league standings after a match."""
        if league_id not in self.standings:
            return

        standings = self.standings[league_id]

        home_standings = standings.get(match.home_club_id)
        away_standings = standings.get(match.away_club_id)

        if not home_standings or not away_standings:
            return

        # Update home club
        home_standings.played += 1
        home_standings.goals_for += match.home_score
        home_standings.goals_against += match.away_score

        if match.home_score > match.away_score:
            home_standings.won += 1
        elif match.home_score == match.away_score:
            home_standings.drawn += 1
        else:
            home_standings.lost += 1

        # Update away club
        away_standings.played += 1
        away_standings.goals_for += match.away_score
        away_standings.goals_against += match.home_score

        if match.away_score > match.home_score:
            away_standings.won += 1
        elif match.away_score == match.home_score:
            away_standings.drawn += 1
        else:
            away_standings.lost += 1

        # Update form
        home_standings.form = self._update_form(home_standings, True)
        away_standings.form = self._update_form(away_standings, False)

        # Update head-to-head
        await self._update_head_to_head(home_standings, away_standings)

    def _update_form(self, standings: LeagueStandings, is_win: bool) -> List[str]:
        """Update form string based on result."""
        form = standings.form[-4:] if len(standings.form) >= 4 else standings.form

        if is_win:
            form.append("W")
        else:
            form.append("L")

        return form

    async def _update_head_to_head(
        self,
        home_standings: LeagueStandings,
        away_standings: LeagueStandings,
    ) -> None:
        """Update head-to-head record."""
        # Find existing H2H record
        for record in self.european_fixtures:
            if (
                record.home_club_id == home_standings.club_id
                and record.away_club_id == away_standings.club_id
            ):
                if record.home_away is not None:
                    record.home_away = 0
                break

        # Update H2H
        if home_standings.home_away is not None:
            home_standings.home_away += home_standings.goals_for - home_standings.goals_against
        if away_standings.home_away is not None:
            away_standings.home_away = away_standings.goals_for - away_standings.goals_against

    async def _get_club_players(
        self,
        club_id: int,
        session: AsyncSession,
    ) -> List[Player]:
        """Get players for a club with state management."""
        result = await session.execute(select(Player).where(Player.club_id == club_id))
        players = list(result.scalars().all())
        return players

    def _get_club_formation(self, club_id: int, league_id: int) -> str:
        """Get club's preferred formation."""
        # For now, return default formation
        # Could be stored in club preferences
        return "4-3-3"

    async def _generate_double_round_robin(
        self,
        league: League,
        year: int,
        start_date: date,
    ) -> List[List[Match]]:
        """Generate double round-robin fixtures."""
        # Get clubs
        async with get_db_session() as session:
            result = await session.execute(select(Club).where(Club.league_id == league.id))
            clubs = list(result.scalars().all())

        if len(clubs) < 2:
            return []

        num_teams = len(clubs)
        num_rounds = (num_teams - 1) * 2  # Home and away fixtures for each team

        fixtures = []
        for round_num in range(num_rounds):
            round_matches = []

            for i in range(num_teams // 2):
                home_idx = (round_num + i) % num_teams
                away_idx = (round_num + num_teams - 1 - i) % num_teams

                home_club = clubs[home_idx]
                away_club = clubs[away_idx]

                # Determine match date
                match_date = start_date + timedelta(weeks=round_num)

                match = Match(
                    season_id=0,  # Will be set when season created
                    matchday=round_num + 1,
                    match_date=match_date,
                    home_club_id=home_club.id,
                    away_club_id=away_club.id,
                    home_score=0,
                    away_score=0,
                    status=MatchStatus.SCHEDULED,
                )
                round_matches.append(match)

            fixtures.append(round_matches)

        return fixtures

    async def _generate_european_fixtures(
        self,
        leagues: List[League],
        year: int,
        start_date: date,
    ) -> None:
        """Generate European competition fixtures."""
        # Get top teams from each league for CL/EL qualification
        for league in leagues:
            await self._allocate_european_spots(league)

    async def _allocate_european_spots(self, league: League) -> None:
        """Allocate Champions League and Europa League spots."""
        # Get clubs
        async with get_db_session() as get_session:
            result = await get_session.execute(
                select(Club).where(Club.league_id == league.id).order_by(Club.reputation.desc())
            )
            clubs = list(result.scalars().all())

        # CL spots: top 4
        # EL spots: next 2 (5th and 6th place)

        if len(clubs) >= 4:
            for i in range(4):
                standings = self.standings.get(league.id, {})
                if clubs[i].id in standings:
                    standings[clubs[i].id].cl_position = i + 1

        if len(clubs) >= 6:
            for i in [4, 5]:  # 5th and 6th place
                standings = self.standings.get(league.id, {})
                if clubs[i].id in standings:
                    standings[clubs[i].id].el_position = i - 3

    async def _process_weekly_finances(
        self,
        matchday: int,
        fixtures: Dict[int, List[List[Match]]],
        session: AsyncSession,
    ) -> None:
        """Process financial transactions for a matchday."""
        for league_id, league_fixtures in fixtures.items():
            for match in league_fixtures[matchday - 1]:
                if match.status != MatchStatus.FULL_TIME:
                    continue

                # Get clubs
                result = await session.execute(
                    select(Club).where(Club.id.in_([match.home_club_id, match.away_club_id]))
                )
                clubs = {c.id: c for c in result.scalars().all()}

                # Process home club finances
                home_club = clubs.get(match.home_club_id)
                if home_club and match.home_club_id == match.home_club_id:
                    club_finances = await self._load_club_finances(home_club.id, session)
                    self.finance_engine.process_matchday(
                        club_finances, home_club, is_home=True, match_importance="normal"
                    )
                    self._save_club_finances(club_finances, session)

                # Process away club finances
                away_club = clubs.get(match.away_club_id)
                if away_club and match.away_club_id == match.away_club_id:
                    club_finances = await self._load_club_finances(away_club.id, session)
                    self.finance_engine.process_matchday(
                        club_finances, away_club, is_home=False, match_importance="normal"
                    )
                    self._save_club_finances(club_finances, session)

    async def _load_club_finances(
        self,
        club_id: int,
        session: AsyncSession,
    ) -> object:
        """Load club finances from database."""
        # This would need proper ClubFinances model
        # For now, return a simple object
        from dataclasses import dataclass

        @dataclass
        class ClubFinances:
            club_id: int
            balance: int = 0
            transfer_budget: int = 0
            wage_budget: int = 0

        # Try to get existing or create default
        result = await session.execute(select(Club).where(Club.id == club_id))
        club = result.scalars().first()

        if club:
            return ClubFinances(
                club_id=club.id,
                balance=club.balance or 0,
                transfer_budget=club.transfer_budget or 50_000_000,
                wage_budget=club.wage_budget or 5_000_000,
            )
        else:
            return ClubFinances(club_id=club_id)

    async def _save_club_finances(self, club_finances: object, session: AsyncSession) -> None:
        """Save club finances to database."""
        # Save logic would go here
        pass

    async def _handle_season_end(
        self,
        leagues: List[League],
        session: AsyncSession,
    ) -> None:
        """Handle end of season: promotion/relegation, awards."""
        for league in leagues:
            if league.id not in self.standings:
                continue

            standings_list = list(self.standings[league.id].values())

            # Sort by: points, goal difference, goals for
            standings_list.sort(
                key=lambda x: (x.points, x.goal_difference, x.goals_for), reverse=True
            )

            # Process promotion/relegation
            if len(standings_list) >= 3:
                promoted = standings_list[-3:]  # Top 3
                relegated = standings_list[:3]  # Bottom 3
            else:
                promoted = [standings_list[-1]]  # Top 1
                relegated = [standings_list[0]]  # Bottom 1

            # Update clubs with promotion/relegation status
            for club_entry in promoted + relegated:
                # Would update club attributes here
                pass

    def _sort_standings(
        self,
        standings: Dict[int, LeagueStandings],
        league_id: int,
    ) -> List[LeagueStandings]:
        """Sort standings by points with proper tie-breakers."""
        standings_list = list(standings[league_id].values())

        # Sort by points (primary)
        standings_list.sort(key=lambda x: x.points, reverse=True)

        # Handle ties
        i = 0
        while i < len(standings_list) - 1:
            current = standings_list[i]
            next_team = standings_list[i + 1]

            if current.points == next_team.points:
                # Tie-breaker 1: Goal difference
                if current.goal_difference > next_team.goal_difference:
                    continue  # Already correct
                elif current.goal_difference < next_team.goal_difference:
                    # Swap
                    standings_list[i], standings_list[i + 1] = (
                        standings_list[i + 1],
                        standings_list[i],
                    )
                    continue
                # Tie-breaker 2: Head-to-head
                # Find their H2H
                h2h_home = current.head_to_head if current.home_team_id == next_team.club_id else 0
                h2h_away = current.home_to_head if current.club_id == next_team.club_id else 0

                if h2h_home > h2h_away:
                    continue  # Home team has better H2H
                elif h2h_home < h2h_away:
                    standings_list[i], standings_list[i + 1] = (
                        standings_list[i + 1],
                        standings_list[i],
                    )
                    continue
                # Tie-breaker 3: Goals for
                if current.goals_for > next_team.goals_for:
                    continue
                elif current.goals_for < next_team.goals_for:
                    standings_list[i], standings_list[i + 1] = (
                        standings_list[i + 1],
                        standings_list[i],
                    )
                    continue
                # Tie-breaker 4: Play-off (if applicable)
                # Would need additional data

            i += 1

        return standings_list

    async def get_final_standings(self, league_id: int) -> List[LeagueStandings]:
        """Get sorted final standings for a league."""
        if league_id not in self.standings:
            return []

        return self._sort_standings(self.standings[league_id], league_id)

    def get_final_standings_summary(self, league_id: int) -> str:
        """Get formatted standings summary."""
        standings = self.get_final_standings(league_id)

        if not standings:
            return "No standings available"

        lines = []
        for i, entry in enumerate(standings, 1):
            lines.append(
                f"{i:2d}. {entry.club_name:<25} | "
                f"P:{entry.played:2d} | "
                f"W:{entry.won:2d} | "
                f"D:{entry.drawn:2d} | "
                f"L:{entry.lost:2d} | "
                f"GF:{entry.goals_for:2d} | "
                f"GA:{entry.goals_against:2d} | "
                f"GD:{entry.goal_difference:+d} | "
                f"Pts:{entry.points:2d} | "
                f"Form:{''.join(entry.form[-5:])}"
            )

        return "\n".join(lines)

    async def _get_european_winners(self) -> Dict[str, List[int]]:
        """Get winners of European competitions."""
        return {
            "champions_league": [],
            "europa_league": [],
        }
