"""Cup competition engine for FM Manager.

Handles all cup competition functionality:
- Domestic cups (FA Cup, League Cup) - single elimination
- European competitions (Champions League, Europa League) - group stage + knockout
- Draw generation
- Match scheduling
- Prize money distribution
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional, List, Dict, Tuple, Set
from enum import Enum, auto

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import (
    Club,
    Match,
    MatchStatus,
    Season,
    Player,
    CupCompetition,
    CupEdition,
    CupRound,
    CupParticipant,
    CupMatch,
    CupType,
    CupFormat,
    CupRoundType,
    CupStatus,
)
from fm_manager.engine.match_engine_markov import MarkovMatchEngine, MatchState
from fm_manager.engine.team_state import TeamStateManager


class DrawType(Enum):
    """Types of draws."""

    RANDOM = auto()  # Completely random
    SEEDED = auto()  # Based on club reputation/league position
    GEOGRAPHIC = auto()  # Try to minimize travel
    TIERED = auto()  # Different tiers enter at different rounds


@dataclass
class DrawResult:
    """Result of a cup draw."""

    round_id: int
    pairings: List[Tuple[int, int]] = field(default_factory=list)  # (home_club_id, away_club_id)
    byes: List[int] = field(default_factory=list)  # Clubs that get a bye

    def get_match_count(self) -> int:
        """Get total number of matches in this round."""
        return len(self.pairings)

    def get_participating_clubs(self) -> Set[int]:
        """Get all club IDs participating in this round."""
        clubs = set(self.byes)
        for home, away in self.pairings:
            clubs.add(home)
            clubs.add(away)
        return clubs


@dataclass
class GroupStanding:
    """Standing in a group stage."""

    club_id: int
    club_name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def add_result(self, goals_for: int, goals_against: int) -> None:
        """Add a match result."""
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against

        if goals_for > goals_against:
            self.won += 1
            self.points += 3
        elif goals_for == goals_against:
            self.drawn += 1
            self.points += 1
        else:
            self.lost += 1


@dataclass
class TwoLegResult:
    """Result of a two-legged tie."""

    first_leg: CupMatch
    second_leg: CupMatch

    @property
    def aggregate_home(self) -> int:
        """Aggregate score for team that played first leg at home."""
        return self.first_leg.match.home_score + self.second_leg.match.away_score

    @property
    def aggregate_away(self) -> int:
        """Aggregate score for team that played first leg away."""
        return self.first_leg.match.away_score + self.second_leg.match.home_score

    @property
    def home_away_goals(self) -> int:
        """Away goals for team that played first leg at home."""
        return self.first_leg.match.away_score

    @property
    def away_away_goals(self) -> int:
        """Away goals for team that played first leg away."""
        return self.second_leg.match.away_score

    def get_winner(self) -> Optional[int]:
        """Get winner club ID based on aggregate score and away goals."""
        if self.aggregate_home > self.aggregate_away:
            return self.first_leg.match.home_club_id
        elif self.aggregate_away > self.aggregate_home:
            return self.first_leg.match.away_club_id
        else:
            # Away goals rule
            if self.home_away_goals > self.away_away_goals:
                return self.first_leg.match.home_club_id
            elif self.away_away_goals > self.home_away_goals:
                return self.first_leg.match.away_club_id
            else:
                # Would go to extra time/penalties - for now return None
                return None


class CupDrawGenerator:
    """Generate draws for cup competitions."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def random_draw(
        self,
        clubs: List[Club],
        allow_byes: bool = True,
    ) -> List[Tuple[Club, Club]]:
        """Generate a completely random draw.

        Args:
            clubs: List of clubs to draw
            allow_byes: Whether to allow byes if odd number of clubs

        Returns:
            List of (home, away) pairings
        """
        shuffled = clubs.copy()
        self.rng.shuffle(shuffled)

        pairings = []
        i = 0

        while i < len(shuffled) - 1:
            home = shuffled[i]
            away = shuffled[i + 1]
            pairings.append((home, away))
            i += 2

        # Handle bye if odd number and allowed
        if i < len(shuffled) and allow_byes:
            # Last club gets a bye
            pass

        return pairings

    def seeded_draw(
        self,
        clubs: List[Club],
        num_pots: int = 2,
    ) -> List[Tuple[Club, Club]]:
        """Generate a seeded draw where teams from different pots play each other.

        Args:
            clubs: List of clubs (should be pre-sorted by seeding)
            num_pots: Number of pots (usually 2 for knockout draws)

        Returns:
            List of (home, away) pairings
        """
        clubs_per_pot = len(clubs) // num_pots
        pots = []

        for i in range(num_pots):
            start = i * clubs_per_pot
            end = start + clubs_per_pot
            pot = clubs[start:end]
            self.rng.shuffle(pot)
            pots.append(pot)

        pairings = []
        # Match highest from pot 0 with random from pot 1, etc.
        for i in range(clubs_per_pot):
            if len(pots) >= 2:
                home = pots[0][i]
                away = pots[1][i]
                pairings.append((home, away))

        return pairings

    def tiered_draw(
        self,
        clubs_by_tier: Dict[int, List[Club]],
        tier_entry_rounds: Dict[int, int],
        current_round: int,
    ) -> List[Tuple[Club, Club]]:
        """Generate a draw for tiered entry (e.g., FA Cup).

        Args:
            clubs_by_tier: Dict mapping tier to list of clubs
            tier_entry_rounds: Dict mapping tier to round they enter
            current_round: Current round number

        Returns:
            List of (home, away) pairings
        """
        eligible_clubs = []

        for tier, entry_round in tier_entry_rounds.items():
            if entry_round <= current_round and tier in clubs_by_tier:
                eligible_clubs.extend(clubs_by_tier[tier])

        return self.random_draw(eligible_clubs)

    def group_stage_draw(
        self,
        clubs: List[Club],
        num_groups: int = 8,
        clubs_per_group: int = 4,
    ) -> Dict[str, List[Club]]:
        """Generate a group stage draw (Champions League style).

        Args:
            clubs: List of 32 clubs (pre-sorted into 4 pots of 8)
            num_groups: Number of groups
            clubs_per_group: Clubs per group

        Returns:
            Dict mapping group letter to list of clubs
        """
        groups = {chr(65 + i): [] for i in range(num_groups)}  # A, B, C...

        # Clubs should be in 4 pots of 8
        pots = [clubs[i * 8 : (i + 1) * 8] for i in range(4)]

        # Shuffle each pot
        for pot in pots:
            self.rng.shuffle(pot)

        # Draw one from each pot into each group
        for group_idx in range(num_groups):
            group_letter = chr(65 + group_idx)
            for pot_idx in range(4):
                if group_idx < len(pots[pot_idx]):
                    groups[group_letter].append(pots[pot_idx][group_idx])

        return groups


class CupPrizeCalculator:
    """Calculate and distribute cup prize money."""

    # Champions League prize money (simplified, in euros)
    CL_PRIZES = {
        "group_stage_participation": 15_600_000,
        "group_stage_win": 2_800_000,
        "group_stage_draw": 930_000,
        "round_of_16": 9_600_000,
        "quarter_final": 10_600_000,
        "semi_final": 12_500_000,
        "final": 15_500_000,
        "winner": 4_500_000,
    }

    # Europa League prize money
    EL_PRIZES = {
        "group_stage_participation": 3_600_000,
        "group_stage_win": 630_000,
        "group_stage_draw": 210_000,
        "round_of_16": 1_200_000,
        "quarter_final": 1_800_000,
        "semi_final": 2_800_000,
        "final": 4_600_000,
        "winner": 4_000_000,
    }

    # FA Cup prize money (in pounds)
    FA_CUP_PRIZES = {
        CupRoundType.FIRST_QUALIFYING: 2_000,
        CupRoundType.SECOND_QUALIFYING: 3_000,
        CupRoundType.THIRD_QUALIFYING: 5_000,
        CupRoundType.PLAYOFF: 7_500,
        CupRoundType.ROUND_OF_64: 40_000,
        CupRoundType.ROUND_OF_32: 60_000,
        CupRoundType.ROUND_OF_16: 90_000,
        CupRoundType.QUARTER_FINAL: 450_000,
        CupRoundType.SEMI_FINAL: 1_000_000,
        CupRoundType.FINAL: 2_000_000,
    }

    def calculate_participation_bonus(
        self,
        competition_type: CupType,
        round_type: CupRoundType,
    ) -> int:
        """Calculate participation bonus for entering a round."""
        if competition_type == CupType.CHAMPIONS_LEAGUE:
            if round_type == CupRoundType.GROUP_STAGE:
                return self.CL_PRIZES["group_stage_participation"]
            return 0
        elif competition_type == CupType.EUROPA_LEAGUE:
            if round_type == CupRoundType.GROUP_STAGE:
                return self.EL_PRIZES["group_stage_participation"]
            return 0
        elif competition_type == CupType.DOMESTIC_CUP:
            return self.FA_CUP_PRIZES.get(round_type, 0)

        return 0

    def calculate_progression_bonus(
        self,
        competition_type: CupType,
        round_type: CupRoundType,
    ) -> int:
        """Calculate bonus for advancing to next round."""
        if competition_type == CupType.CHAMPIONS_LEAGUE:
            if round_type == CupRoundType.ROUND_OF_16:
                return self.CL_PRIZES["round_of_16"]
            elif round_type == CupRoundType.QUARTER_FINAL:
                return self.CL_PRIZES["quarter_final"]
            elif round_type == CupRoundType.SEMI_FINAL:
                return self.CL_PRIZES["semi_final"]
            elif round_type == CupRoundType.FINAL:
                return self.CL_PRIZES["final"] + self.CL_PRIZES["winner"]
        elif competition_type == CupType.EUROPA_LEAGUE:
            if round_type == CupRoundType.ROUND_OF_16:
                return self.EL_PRIZES["round_of_16"]
            elif round_type == CupRoundType.QUARTER_FINAL:
                return self.EL_PRIZES["quarter_final"]
            elif round_type == CupRoundType.SEMI_FINAL:
                return self.EL_PRIZES["semi_final"]
            elif round_type == CupRoundType.FINAL:
                return self.EL_PRIZES["final"] + self.EL_PRIZES["winner"]
        elif competition_type == CupType.DOMESTIC_CUP:
            return self.FA_CUP_PRIZES.get(round_type, 0)

        return 0

    def calculate_match_bonus(
        self,
        competition_type: CupType,
        is_group_stage: bool,
        is_win: bool,
    ) -> int:
        """Calculate bonus for winning/drawing a match."""
        if not is_group_stage:
            return 0

        if competition_type == CupType.CHAMPIONS_LEAGUE:
            return (
                self.CL_PRIZES["group_stage_win"] if is_win else self.CL_PRIZES["group_stage_draw"]
            )
        elif competition_type == CupType.EUROPA_LEAGUE:
            return (
                self.EL_PRIZES["group_stage_win"] if is_win else self.EL_PRIZES["group_stage_draw"]
            )

        return 0


class CupCompetitionEngine:
    """Main engine for managing cup competitions."""

    def __init__(self, session: AsyncSession, engine_version: str = "v2"):
        self.session = session
        self.draw_generator = CupDrawGenerator()
        self.prize_calculator = CupPrizeCalculator()
        self.state_manager = TeamStateManager()

        if engine_version == "v2":
            self.match_simulator = MarkovMatchEngine()
        else:
            self.match_simulator = MarkovMatchEngine()

    async def create_domestic_cup(
        self,
        name: str,
        short_name: str,
        country: str,
        tier_entry_rounds: Dict[int, int],
        total_rounds: int = 6,
    ) -> CupCompetition:
        """Create a domestic cup competition (e.g., FA Cup).

        Args:
            name: Full name of the cup
            short_name: Short abbreviation
            country: Country code
            tier_entry_rounds: Dict mapping league tier to round they enter
            total_rounds: Total number of rounds

        Returns:
            Created CupCompetition
        """
        cup = CupCompetition(
            name=name,
            short_name=short_name,
            cup_type=CupType.DOMESTIC_CUP,
            format=CupFormat.KNOCKOUT,
            country=country,
            min_league_tier=min(tier_entry_rounds.keys()),
            max_league_tier=max(tier_entry_rounds.keys()),
        )
        self.session.add(cup)
        await self.session.commit()

        return cup

    async def create_european_competition(
        self,
        name: str,
        short_name: str,
        cup_type: CupType,
    ) -> CupCompetition:
        """Create a European competition (Champions League or Europa League).

        Args:
            name: Full name
            short_name: Short abbreviation
            cup_type: CHAMPIONS_LEAGUE or EUROPA_LEAGUE

        Returns:
            Created CupCompetition
        """
        cup = CupCompetition(
            name=name,
            short_name=short_name,
            cup_type=cup_type,
            format=CupFormat.GROUP_THEN_KNOCKOUT,
            country="",  # International
            typical_participants=32 if cup_type == CupType.CHAMPIONS_LEAGUE else 32,
        )
        self.session.add(cup)
        await self.session.commit()

        return cup

    async def create_edition(
        self,
        competition_id: int,
        season_id: int,
        start_year: int,
        start_date: Optional[date] = None,
    ) -> CupEdition:
        """Create a new edition of a cup competition.

        Args:
            competition_id: Cup competition ID
            season_id: Season ID
            start_year: Starting year
            start_date: Start date

        Returns:
            Created CupEdition
        """
        competition = await self.session.get(CupCompetition, competition_id)
        if not competition:
            raise ValueError(f"Competition {competition_id} not found")

        edition = CupEdition(
            competition_id=competition_id,
            season_id=season_id,
            start_year=start_year,
            end_year=start_year + 1,
            start_date=start_date,
            status=CupStatus.UPCOMING,
        )
        self.session.add(edition)
        await self.session.commit()

        # Create rounds based on format
        if competition.format == CupFormat.KNOCKOUT:
            await self._create_knockout_rounds(edition, competition)
        elif competition.format == CupFormat.GROUP_THEN_KNOCKOUT:
            await self._create_group_then_knockout_rounds(edition, competition)

        return edition

    async def _create_knockout_rounds(
        self,
        edition: CupEdition,
        competition: CupCompetition,
    ) -> None:
        """Create rounds for a knockout competition."""
        round_types = [
            CupRoundType.FIRST_QUALIFYING,
            CupRoundType.SECOND_QUALIFYING,
            CupRoundType.THIRD_QUALIFYING,
            CupRoundType.PLAYOFF,
            CupRoundType.ROUND_OF_64,
            CupRoundType.ROUND_OF_32,
            CupRoundType.ROUND_OF_16,
            CupRoundType.QUARTER_FINAL,
            CupRoundType.SEMI_FINAL,
            CupRoundType.FINAL,
        ]

        # Filter based on competition size
        if competition.typical_participants <= 32:
            round_types = round_types[-6:]  # Last 6 rounds
        elif competition.typical_participants <= 64:
            round_types = round_types[-7:]  # Last 7 rounds

        for i, round_type in enumerate(round_types):
            cup_round = CupRound(
                edition_id=edition.id,
                name=self._get_round_name(round_type),
                round_type=round_type,
                round_order=i + 1,
                is_two_legged=False,
                has_replay=False,
            )
            self.session.add(cup_round)

        await self.session.commit()

    async def _create_group_then_knockout_rounds(
        self,
        edition: CupEdition,
        competition: CupCompetition,
    ) -> None:
        """Create rounds for group stage + knockout competition."""
        # Group stage matchdays
        for matchday in range(1, 7):
            cup_round = CupRound(
                edition_id=edition.id,
                name=f"Group Stage - Matchday {matchday}",
                round_type=CupRoundType.GROUP_STAGE,
                round_order=matchday,
                is_group_stage=True,
                group_stage_matchday=matchday,
            )
            self.session.add(cup_round)

        # Knockout rounds
        knockout_rounds = [
            (CupRoundType.ROUND_OF_16, "Round of 16"),
            (CupRoundType.QUARTER_FINAL, "Quarter Finals"),
            (CupRoundType.SEMI_FINAL, "Semi Finals"),
            (CupRoundType.FINAL, "Final"),
        ]

        for i, (round_type, name) in enumerate(knockout_rounds):
            cup_round = CupRound(
                edition_id=edition.id,
                name=name,
                round_type=round_type,
                round_order=6 + i + 1,
                is_two_legged=(round_type != CupRoundType.FINAL),
            )
            self.session.add(cup_round)

        await self.session.commit()

    def _get_round_name(self, round_type: CupRoundType) -> str:
        """Get display name for a round type."""
        names = {
            CupRoundType.FIRST_QUALIFYING: "First Qualifying Round",
            CupRoundType.SECOND_QUALIFYING: "Second Qualifying Round",
            CupRoundType.THIRD_QUALIFYING: "Third Qualifying Round",
            CupRoundType.PLAYOFF: "Playoff Round",
            CupRoundType.ROUND_OF_64: "Round of 64",
            CupRoundType.ROUND_OF_32: "Round of 32",
            CupRoundType.ROUND_OF_16: "Round of 16",
            CupRoundType.QUARTER_FINAL: "Quarter Finals",
            CupRoundType.SEMI_FINAL: "Semi Finals",
            CupRoundType.FINAL: "Final",
        }
        return names.get(round_type, round_type.value)

    async def add_participants(
        self,
        edition_id: int,
        clubs: List[Club],
        entry_round_id: Optional[int] = None,
    ) -> List[CupParticipant]:
        """Add clubs as participants to a cup edition.

        Args:
            edition_id: Cup edition ID
            clubs: List of clubs to add
            entry_round_id: Round they enter (None for all from start)

        Returns:
            List of created CupParticipants
        """
        participants = []

        for club in clubs:
            participant = CupParticipant(
                edition_id=edition_id,
                club_id=club.id,
                entry_round_id=entry_round_id,
                is_active=True,
            )
            self.session.add(participant)
            participants.append(participant)

        await self.session.commit()
        return participants

    async def conduct_draw(
        self,
        round_id: int,
        draw_type: DrawType = DrawType.RANDOM,
        seed: Optional[int] = None,
    ) -> DrawResult:
        """Conduct a draw for a cup round.

        Args:
            round_id: Cup round ID
            draw_type: Type of draw to conduct
            seed: Random seed for reproducibility

        Returns:
            DrawResult with pairings
        """
        cup_round = await self.session.get(CupRound, round_id)
        if not cup_round:
            raise ValueError(f"Round {round_id} not found")

        # Get active participants for this round
        result = await self.session.execute(
            select(CupParticipant).where(
                and_(
                    CupParticipant.edition_id == cup_round.edition_id,
                    CupParticipant.is_active == True,
                )
            )
        )
        participants = list(result.scalars().all())

        if len(participants) < 2:
            return DrawResult(round_id=round_id, pairings=[], byes=[])

        # Get club objects
        clubs = [p.club for p in participants]

        # Generate draw based on type
        if seed is not None:
            self.draw_generator = CupDrawGenerator(seed)

        if draw_type == DrawType.RANDOM:
            pairings = self.draw_generator.random_draw(clubs)
        elif draw_type == DrawType.SEEDED:
            # Sort by reputation for seeding
            clubs_sorted = sorted(clubs, key=lambda c: c.reputation, reverse=True)
            pairings = self.draw_generator.seeded_draw(clubs_sorted)
        else:
            pairings = self.draw_generator.random_draw(clubs)

        # Convert to IDs
        pairing_ids = [(home.id, away.id) for home, away in pairings]

        return DrawResult(
            round_id=round_id,
            pairings=pairing_ids,
            byes=[],
        )

    async def schedule_matches(
        self,
        round_id: int,
        draw_result: DrawResult,
        match_date: date,
    ) -> List[CupMatch]:
        """Schedule matches for a round based on draw result.

        Args:
            round_id: Cup round ID
            draw_result: Draw result with pairings
            match_date: Date for the matches

        Returns:
            List of created CupMatches
        """
        cup_round = await self.session.get(CupRound, round_id)
        edition = await self.session.get(CupEdition, cup_round.edition_id)

        cup_matches = []

        for home_id, away_id in draw_result.pairings:
            # Create base Match
            match = Match(
                season_id=edition.season_id,
                matchday=cup_round.round_order,
                match_date=match_date,
                home_club_id=home_id,
                away_club_id=away_id,
                home_score=0,
                away_score=0,
                status=MatchStatus.SCHEDULED,
            )
            self.session.add(match)
            await self.session.flush()  # Get match ID

            # Create CupMatch
            cup_match = CupMatch(
                round_id=round_id,
                match_id=match.id,
                is_first_leg=True,
            )
            self.session.add(cup_match)
            cup_matches.append(cup_match)

        await self.session.commit()
        return cup_matches

    async def simulate_match(
        self,
        cup_match: CupMatch,
        home_lineup: Optional[List[Player]] = None,
        away_lineup: Optional[List[Player]] = None,
    ) -> MatchState:
        """Simulate a cup match.

        Args:
            cup_match: CupMatch to simulate
            home_lineup: Optional home lineup
            away_lineup: Optional away lineup

        Returns:
            MatchState with result
        """
        match = cup_match.match

        # Get lineups if not provided
        if home_lineup is None:
            home_lineup = await self._get_lineup(match.home_club_id)
        if away_lineup is None:
            away_lineup = await self._get_lineup(match.away_club_id)

        # Simulate
        match_state = self.match_simulator.simulate(
            home_lineup=home_lineup[:11],
            away_lineup=away_lineup[:11],
        )

        # Update match
        match.home_score = match_state.home_score
        match.away_score = match_state.away_score
        match.status = MatchStatus.FULL_TIME

        # Update CupMatch
        if match.home_score > match.away_score:
            cup_match.winner_club_id = match.home_club_id
        elif match.away_score > match.home_score:
            cup_match.winner_club_id = match.away_club_id

        await self.session.commit()

        return match_state

    async def _get_lineup(self, club_id: int) -> List[Player]:
        """Get starting lineup for a club."""
        result = await self.session.execute(
            select(Player)
            .where(Player.club_id == club_id)
            .order_by(Player.current_ability.desc())
            .limit(11)
        )
        return list(result.scalars().all())

    async def process_round_results(
        self,
        round_id: int,
    ) -> List[int]:
        """Process results of a round and determine advancing teams.

        Args:
            round_id: Cup round ID

        Returns:
            List of club IDs that advance
        """
        cup_round = await self.session.get(CupRound, round_id)

        # Get all matches in this round
        result = await self.session.execute(select(CupMatch).where(CupMatch.round_id == round_id))
        cup_matches = list(result.scalars().all())

        advancing = []
        eliminated = []

        for cup_match in cup_matches:
            match = cup_match.match

            if match.status != MatchStatus.FULL_TIME:
                continue

            # Determine winner
            if cup_match.winner_club_id:
                advancing.append(cup_match.winner_club_id)

                # Determine loser
                if cup_match.winner_club_id == match.home_club_id:
                    eliminated.append(match.away_club_id)
                else:
                    eliminated.append(match.home_club_id)
            else:
                # Draw - would need replay or extra time
                # For now, random winner
                winner = random.choice([match.home_club_id, match.away_club_id])
                cup_match.winner_club_id = winner
                advancing.append(winner)
                eliminated.append(
                    match.away_club_id if winner == match.home_club_id else match.home_club_id
                )

        # Update participant status
        for club_id in eliminated:
            result = await self.session.execute(
                select(CupParticipant).where(
                    and_(
                        CupParticipant.edition_id == cup_round.edition_id,
                        CupParticipant.club_id == club_id,
                    )
                )
            )
            participant = result.scalar_one_or_none()
            if participant:
                participant.is_active = False
                participant.eliminated_in_round_id = round_id

        await self.session.commit()

        return advancing

    async def conduct_group_stage_draw(
        self,
        edition_id: int,
        clubs: List[Club],
    ) -> Dict[str, List[int]]:
        """Conduct group stage draw for European competitions.

        Args:
            edition_id: Cup edition ID
            clubs: List of 32 clubs (should be pre-sorted into 4 pots)

        Returns:
            Dict mapping group letter to list of club IDs
        """
        # Sort clubs into 4 pots of 8 by reputation
        clubs_sorted = sorted(clubs, key=lambda c: c.reputation, reverse=True)

        # Generate draw
        groups = self.draw_generator.group_stage_draw(clubs_sorted)

        # Create/update participants with group assignments
        for group_letter, group_clubs in groups.items():
            for position, club in enumerate(group_clubs):
                result = await self.session.execute(
                    select(CupParticipant).where(
                        and_(
                            CupParticipant.edition_id == edition_id,
                            CupParticipant.club_id == club.id,
                        )
                    )
                )
                participant = result.scalar_one_or_none()
                if participant:
                    participant.group_name = group_letter
                    participant.group_position = position + 1

        await self.session.commit()

        # Return group assignments
        return {letter: [c.id for c in clubs] for letter, clubs in groups.items()}

    async def get_group_standings(
        self,
        edition_id: int,
        group_name: str,
    ) -> List[GroupStanding]:
        """Get standings for a group.

        Args:
            edition_id: Cup edition ID
            group_name: Group letter (A, B, C...)

        Returns:
            List of GroupStanding sorted by position
        """
        # Get participants in this group
        result = await self.session.execute(
            select(CupParticipant).where(
                and_(
                    CupParticipant.edition_id == edition_id,
                    CupParticipant.group_name == group_name,
                )
            )
        )
        participants = list(result.scalars().all())

        standings = []
        for p in participants:
            standing = GroupStanding(
                club_id=p.club_id,
                club_name=p.club.name,
                played=p.group_points // 3 + (p.group_points % 3),  # Approximate
                won=p.group_points // 3,
                drawn=p.group_points % 3,
                lost=0,  # Would need to calculate
                goals_for=p.group_goals_for,
                goals_against=p.group_goals_against,
                points=p.group_points,
            )
            standings.append(standing)

        # Sort by points, then goal difference
        standings.sort(key=lambda s: (s.points, s.goal_difference), reverse=True)

        return standings

    async def distribute_prize_money(
        self,
        edition_id: int,
        club_id: int,
        amount: int,
    ) -> None:
        """Distribute prize money to a club.

        Args:
            edition_id: Cup edition ID
            club_id: Club ID
            amount: Prize money amount
        """
        result = await self.session.execute(
            select(CupParticipant).where(
                and_(
                    CupParticipant.edition_id == edition_id,
                    CupParticipant.club_id == club_id,
                )
            )
        )
        participant = result.scalar_one_or_none()

        if participant:
            participant.prize_money_earned += amount

            # Update club balance
            club = await self.session.get(Club, club_id)
            if club:
                club.balance += amount

            await self.session.commit()
