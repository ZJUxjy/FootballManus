"""Domestic cup competitions (FA Cup, League Cup) for FM Manager.

Implements single-elimination knockout tournaments with tiered entry.
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import (
    Club,
    League,
    Match,
    MatchStatus,
    Season,
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
from fm_manager.engine.cup_competition_engine import (
    CupCompetitionEngine,
    DrawType,
    DrawResult,
)


class DomesticCupConfig:
    """Configuration for domestic cup competitions."""

    # FA Cup configuration
    FA_CUP = {
        "name": "FA Cup",
        "short_name": "FAC",
        "country": "England",
        "tier_entry_rounds": {
            1: 4,  # Premier League enters at Round 3
            2: 3,  # Championship enters at Round 2
            3: 2,  # League One enters at Round 1
            4: 1,  # League Two enters at First Qualifying
            5: 1,  # National League enters at First Qualifying
        },
        "has_replays": True,
        "semifinal_neutral_venue": True,
        "final_neutral_venue": True,
    }

    # League Cup configuration
    LEAGUE_CUP = {
        "name": "Carabao Cup",
        "short_name": "LC",
        "country": "England",
        "tier_entry_rounds": {
            1: 1,  # Premier League (top teams enter later)
            2: 1,  # Championship
        },
        "has_replays": False,
        "semifinal_two_legs": True,
        "final_neutral_venue": True,
        "premier_league_exempt": 7,  # Top 7 PL teams enter at Round 3
    }

    # Copa del Rey configuration
    COPA_DEL_REY = {
        "name": "Copa del Rey",
        "short_name": "CdR",
        "country": "Spain",
        "tier_entry_rounds": {
            1: 3,  # La Liga enters at Round of 32
            2: 2,  # Segunda Division enters earlier
        },
        "has_replays": False,
        "single_match_all_rounds": True,
        "lower_division_home": True,  # Lower division team always hosts
    }


class DomesticCupEngine:
    """Engine for managing domestic cup competitions.

    Supports FA Cup style (tiered entry, replays) and League Cup style
    (single elimination, two-legged semis).
    """

    def __init__(self, session: AsyncSession, engine_version: str = "v2"):
        self.session = session
        self.base_engine = CupCompetitionEngine(session, engine_version)
        self.config = DomesticCupConfig()

    async def create_fa_cup(self, season_id: int, start_year: int) -> CupEdition:
        """Create an FA Cup edition.

        Args:
            season_id: Season ID
            start_year: Starting year

        Returns:
            Created CupEdition
        """
        config = self.config.FA_CUP

        # Create competition if not exists
        result = await self.session.execute(
            select(CupCompetition).where(
                and_(
                    CupCompetition.name == config["name"],
                    CupCompetition.country == config["country"],
                )
            )
        )
        competition = result.scalar_one_or_none()

        if not competition:
            competition = await self.base_engine.create_domestic_cup(
                name=config["name"],
                short_name=config["short_name"],
                country=config["country"],
                tier_entry_rounds=config["tier_entry_rounds"],
            )

        # Create edition
        edition = await self.base_engine.create_edition(
            competition_id=competition.id,
            season_id=season_id,
            start_year=start_year,
            start_date=date(start_year, 11, 1),  # Starts in November
        )

        return edition

    async def create_league_cup(self, season_id: int, start_year: int) -> CupEdition:
        """Create a League Cup (Carabao Cup) edition.

        Args:
            season_id: Season ID
            start_year: Starting year

        Returns:
            Created CupEdition
        """
        config = self.config.LEAGUE_CUP

        # Create competition if not exists
        result = await self.session.execute(
            select(CupCompetition).where(
                and_(
                    CupCompetition.name == config["name"],
                    CupCompetition.country == config["country"],
                )
            )
        )
        competition = result.scalar_one_or_none()

        if not competition:
            competition = CupCompetition(
                name=config["name"],
                short_name=config["short_name"],
                cup_type=CupType.DOMESTIC_LEAGUE_CUP,
                format=CupFormat.KNOCKOUT,
                country=config["country"],
                min_league_tier=1,
                max_league_tier=2,
            )
            self.session.add(competition)
            await self.session.commit()

        # Create edition
        edition = await self.base_engine.create_edition(
            competition_id=competition.id,
            season_id=season_id,
            start_year=start_year,
            start_date=date(start_year, 8, 1),  # Starts in August
        )

        # Update rounds for League Cup format (two-legged semis)
        rounds = await self.session.execute(
            select(CupRound).where(CupRound.edition_id == edition.id).order_by(CupRound.round_order)
        )
        rounds_list = list(rounds.scalars().all())

        # Make semi-finals two-legged
        for cup_round in rounds_list:
            if cup_round.round_type == CupRoundType.SEMI_FINAL:
                cup_round.is_two_legged = True

        await self.session.commit()

        return edition

    async def populate_fa_cup_participants(
        self,
        edition_id: int,
        include_premier_league: bool = True,
        include_championship: bool = True,
        include_lower_leagues: bool = True,
    ) -> Dict[int, List[CupParticipant]]:
        """Populate FA Cup with participants from different tiers.

        Args:
            edition_id: Cup edition ID
            include_premier_league: Include Premier League teams
            include_championship: Include Championship teams
            include_lower_leagues: Include League One and below

        Returns:
            Dict mapping tier to list of participants
        """
        edition = await self.session.get(CupEdition, edition_id)
        competition = await self.session.get(CupCompetition, edition.competition_id)

        participants_by_tier = {}

        # Get rounds for entry point lookup
        rounds_result = await self.session.execute(
            select(CupRound).where(CupRound.edition_id == edition_id).order_by(CupRound.round_order)
        )
        rounds_list = list(rounds_result.scalars().all())

        # Map round types to round IDs
        round_map = {r.round_type: r.id for r in rounds_list}

        # Get clubs by tier
        for tier, entry_round_num in competition.tier_entry_rounds.items():
            if tier == 1 and not include_premier_league:
                continue
            if tier == 2 and not include_championship:
                continue
            if tier >= 3 and not include_lower_leagues:
                continue

            # Get clubs in this tier
            clubs_result = await self.session.execute(
                select(Club)
                .join(League)
                .where(
                    and_(
                        League.tier == tier,
                        League.country == competition.country,
                    )
                )
            )
            clubs = list(clubs_result.scalars().all())

            if not clubs:
                continue

            # Find entry round
            entry_round_id = None
            if entry_round_num <= len(rounds_list):
                entry_round_id = rounds_list[entry_round_num - 1].id

            # Create participants
            participants = await self.base_engine.add_participants(
                edition_id=edition_id,
                clubs=clubs,
                entry_round_id=entry_round_id,
            )

            participants_by_tier[tier] = participants

        return participants_by_tier

    async def populate_league_cup_participants(
        self,
        edition_id: int,
    ) -> Tuple[List[CupParticipant], List[CupParticipant]]:
        """Populate League Cup with Premier League and Championship teams.

        Args:
            edition_id: Cup edition ID

        Returns:
            Tuple of (round_1_participants, round_2_participants)
        """
        edition = await self.session.get(CupEdition, edition_id)
        competition = await self.session.get(CupCompetition, edition.competition_id)

        # Get all Premier League and Championship clubs
        clubs_result = await self.session.execute(
            select(Club)
            .join(League)
            .where(
                and_(
                    League.tier.in_([1, 2]),
                    League.country == competition.country,
                )
            )
        )
        all_clubs = list(clubs_result.scalars().all())

        # Split by tier
        premier_league = [c for c in all_clubs if c.league.tier == 1]
        championship = [c for c in all_clubs if c.league.tier == 2]

        # Sort Premier League by reputation (approximate league position)
        premier_league.sort(key=lambda c: c.reputation, reverse=True)

        # Top 7 enter at Round 3
        top_7 = premier_league[:7]
        rest_pl = premier_league[7:]

        # Get rounds
        rounds_result = await self.session.execute(
            select(CupRound).where(CupRound.edition_id == edition_id).order_by(CupRound.round_order)
        )
        rounds_list = list(rounds_result.scalars().all())

        round_1_id = rounds_list[0].id if rounds_list else None
        round_2_id = rounds_list[1].id if len(rounds_list) > 1 else None
        round_3_id = rounds_list[2].id if len(rounds_list) > 2 else None

        # Round 1: Championship teams
        round_1_participants = await self.base_engine.add_participants(
            edition_id=edition_id,
            clubs=championship,
            entry_round_id=round_1_id,
        )

        # Round 2: Lower Premier League teams enter
        round_2_participants = await self.base_engine.add_participants(
            edition_id=edition_id,
            clubs=rest_pl,
            entry_round_id=round_2_id,
        )

        # Round 3: Top 7 enter
        await self.base_engine.add_participants(
            edition_id=edition_id,
            clubs=top_7,
            entry_round_id=round_3_id,
        )

        return round_1_participants, round_2_participants

    async def conduct_fa_cup_draw(
        self,
        round_id: int,
        prefer_lower_division_home: bool = True,
    ) -> DrawResult:
        """Conduct an FA Cup draw with optional home advantage for lower divisions.

        Args:
            round_id: Cup round ID
            prefer_lower_division_home: If True, lower division teams host when possible

        Returns:
            DrawResult with pairings
        """
        cup_round = await self.session.get(CupRound, round_id)

        # Get active participants
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

        # Shuffle for random draw
        clubs = [p.club for p in participants]
        random.shuffle(clubs)

        pairings = []
        i = 0

        while i < len(clubs) - 1:
            club1 = clubs[i]
            club2 = clubs[i + 1]

            # Determine home team
            if prefer_lower_division_home:
                # Lower division team hosts
                tier1 = club1.league.tier if club1.league else 1
                tier2 = club2.league.tier if club2.league else 1

                if tier2 > tier1:
                    home, away = club2, club1
                else:
                    home, away = club1, club2
            else:
                home, away = club1, club2

            pairings.append((home.id, away.id))
            i += 2

        return DrawResult(
            round_id=round_id,
            pairings=pairings,
            byes=[],
        )

    async def simulate_fa_cup_round(
        self,
        round_id: int,
        match_date: date,
        allow_replays: bool = True,
    ) -> Dict[str, List]:
        """Simulate an FA Cup round with optional replays for draws.

        Args:
            round_id: Cup round ID
            match_date: Date for matches
            allow_replays: Whether to schedule replays for draws

        Returns:
            Dict with "completed", "replays", "advancing" keys
        """
        cup_round = await self.session.get(CupRound, round_id)

        # Conduct draw
        draw_result = await self.conduct_fa_cup_draw(round_id)

        # Schedule matches
        cup_matches = await self.base_engine.schedule_matches(
            round_id=round_id,
            draw_result=draw_result,
            match_date=match_date,
        )

        # Simulate matches
        completed = []
        replays = []

        for cup_match in cup_matches:
            match_state = await self.base_engine.simulate_match(cup_match)

            if cup_match.winner_club_id:
                completed.append(cup_match)
            else:
                # Draw - schedule replay if allowed
                if allow_replays:
                    replays.append(cup_match)
                else:
                    # Random winner
                    match = cup_match.match
                    winner = random.choice([match.home_club_id, match.away_club_id])
                    cup_match.winner_club_id = winner
                    completed.append(cup_match)

        # Process results
        advancing = await self.base_engine.process_round_results(round_id)

        return {
            "completed": completed,
            "replays": replays,
            "advancing": advancing,
        }

    async def schedule_replay(
        self,
        original_cup_match: CupMatch,
        replay_date: date,
        swap_venue: bool = True,
    ) -> CupMatch:
        """Schedule a replay match.

        Args:
            original_cup_match: Original drawn match
            replay_date: Date for replay
            swap_venue: If True, swap home/away from original

        Returns:
            Created replay CupMatch
        """
        original_match = original_cup_match.match
        cup_round = await self.session.get(CupRound, original_cup_match.round_id)
        edition = await self.session.get(CupEdition, cup_round.edition_id)

        # Determine teams and venue
        if swap_venue:
            home_id = original_match.away_club_id
            away_id = original_match.home_club_id
        else:
            home_id = original_match.home_club_id
            away_id = original_match.away_club_id

        # Create replay match
        replay_match = Match(
            season_id=edition.season_id,
            matchday=cup_round.round_order,
            match_date=replay_date,
            home_club_id=home_id,
            away_club_id=away_id,
            home_score=0,
            away_score=0,
            status=MatchStatus.SCHEDULED,
        )
        self.session.add(replay_match)
        await self.session.flush()

        # Create CupMatch
        replay_cup_match = CupMatch(
            round_id=cup_round.id,
            match_id=replay_match.id,
            is_first_leg=True,
            is_replay=True,
            original_match_id=original_cup_match.id,
        )
        self.session.add(replay_cup_match)
        await self.session.commit()

        return replay_cup_match

    async def get_fa_cup_prize_money(self, round_type: CupRoundType) -> int:
        """Get FA Cup prize money for reaching a round.

        Args:
            round_type: The round reached

        Returns:
            Prize money amount
        """
        prizes = {
            CupRoundType.FIRST_QUALIFYING: 2_000,
            CupRoundType.SECOND_QUALIFYING: 3_000,
            CupRoundType.THIRD_QUALIFYING: 5_000,
            CupRoundType.PLAYOFF: 7_500,
            CupRoundType.ROUND_OF_64: 40_000,
            CupRoundType.ROUND_OF_32: 60_000,
            CupRoundType.ROUND_OF_16: 90_000,
            CupRoundType.QUARTER_FINAL: 450_000,
            CupRoundType.SEMI_FINAL: 1_000_000,
            CupRoundType.FINAL: 2_000_000,  # Runner-up
        }
        return prizes.get(round_type, 0)

    async def distribute_fa_cup_prizes(
        self,
        edition_id: int,
    ) -> Dict[int, int]:
        """Distribute FA Cup prize money to all participants.

        Args:
            edition_id: Cup edition ID

        Returns:
            Dict mapping club_id to prize money earned
        """
        edition = await self.session.get(CupEdition, edition_id)

        # Get all participants
        result = await self.session.execute(
            select(CupParticipant).where(CupParticipant.edition_id == edition_id)
        )
        participants = list(result.scalars().all())

        prizes_earned = {}

        for participant in participants:
            # Determine furthest round reached
            if participant.final_position == 1:
                # Winner gets final prize + winner bonus
                prize = await self.get_fa_cup_prize_money(CupRoundType.FINAL) + 1_000_000
            elif participant.eliminated_in_round_id:
                eliminated_round = await self.session.get(
                    CupRound, participant.eliminated_in_round_id
                )
                prize = await self.get_fa_cup_prize_money(eliminated_round.round_type)
            else:
                prize = 0

            if prize > 0:
                await self.base_engine.distribute_prize_money(
                    edition_id=edition_id,
                    club_id=participant.club_id,
                    amount=prize,
                )
                prizes_earned[participant.club_id] = prize

        return prizes_earned

    async def run_complete_fa_cup(
        self,
        season_id: int,
        start_year: int,
        match_dates: Optional[List[date]] = None,
    ) -> CupEdition:
        """Run a complete FA Cup tournament.

        Args:
            season_id: Season ID
            start_year: Starting year
            match_dates: Optional list of dates for each round

        Returns:
            Completed CupEdition
        """
        # Create edition
        edition = await self.create_fa_cup(season_id, start_year)

        # Populate participants
        await self.populate_fa_cup_participants(edition.id)

        # Default match dates (spaced 3-4 weeks apart)
        if match_dates is None:
            base_date = date(start_year, 11, 1)
            match_dates = [
                base_date + timedelta(weeks=i * 3)
                for i in range(14)  # Up to 14 rounds
            ]

        # Get rounds
        rounds_result = await self.session.execute(
            select(CupRound).where(CupRound.edition_id == edition.id).order_by(CupRound.round_order)
        )
        rounds_list = list(rounds_result.scalars().all())

        # Simulate each round
        for i, cup_round in enumerate(rounds_list):
            if cup_round.round_type == CupRoundType.FINAL:
                # Final at Wembley (neutral venue)
                pass

            match_date = match_dates[i] if i < len(match_dates) else match_dates[-1]

            result = await self.simulate_fa_cup_round(
                round_id=cup_round.id,
                match_date=match_date,
                allow_replays=(
                    cup_round.round_type
                    not in [
                        CupRoundType.SEMI_FINAL,
                        CupRoundType.FINAL,
                    ]
                ),
            )

            # Mark round as completed
            cup_round.is_completed = True

            # If final, set winner
            if cup_round.round_type == CupRoundType.FINAL and result["completed"]:
                final_match = result["completed"][0]
                edition.winner_club_id = final_match.winner_club_id

        # Distribute prizes
        await self.distribute_fa_cup_prizes(edition.id)

        # Mark edition as completed
        edition.status = CupStatus.COMPLETED
        await self.session.commit()

        return edition
