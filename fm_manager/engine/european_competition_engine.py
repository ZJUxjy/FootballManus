"""European competitions (Champions League, Europa League) for FM Manager.

Implements group stage + knockout format with two-legged ties.
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Set

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import (
    Club,
    League,
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
from fm_manager.engine.cup_competition_engine import (
    CupCompetitionEngine,
    DrawType,
    DrawResult,
    GroupStanding,
)


class EuropeanCompetitionConfig:
    """Configuration for European competitions."""

    # Champions League
    CHAMPIONS_LEAGUE = {
        "name": "UEFA Champions League",
        "short_name": "UCL",
        "cup_type": CupType.CHAMPIONS_LEAGUE,
        "num_groups": 8,
        "clubs_per_group": 4,
        "group_stage_matchdays": 6,
        "qualifying_spots": {
            "england": 4,
            "spain": 4,
            "germany": 4,
            "italy": 4,
            "france": 3,
            "portugal": 2,
            "netherlands": 2,
        },
    }

    # Europa League
    EUROPA_LEAGUE = {
        "name": "UEFA Europa League",
        "short_name": "UEL",
        "cup_type": CupType.EUROPA_LEAGUE,
        "num_groups": 8,
        "clubs_per_group": 4,
        "group_stage_matchdays": 6,
    }


class EuropeanCompetitionEngine:
    """Engine for managing European competitions (Champions League, Europa League).

    Implements group stage + knockout format with two-legged ties.
    """

    def __init__(self, session: AsyncSession, engine_version: str = "v2"):
        self.session = session
        self.base_engine = CupCompetitionEngine(session, engine_version)
        self.config = EuropeanCompetitionConfig()

    async def create_champions_league(
        self,
        season_id: int,
        start_year: int,
    ) -> CupEdition:
        """Create a Champions League edition.

        Args:
            season_id: Season ID
            start_year: Starting year

        Returns:
            Created CupEdition
        """
        config = self.config.CHAMPIONS_LEAGUE

        # Create competition if not exists
        result = await self.session.execute(
            select(CupCompetition).where(CupCompetition.cup_type == CupType.CHAMPIONS_LEAGUE)
        )
        competition = result.scalar_one_or_none()

        if not competition:
            competition = await self.base_engine.create_european_competition(
                name=config["name"],
                short_name=config["short_name"],
                cup_type=CupType.CHAMPIONS_LEAGUE,
            )

        # Create edition
        edition = await self.base_engine.create_edition(
            competition_id=competition.id,
            season_id=season_id,
            start_year=start_year,
            start_date=date(start_year, 9, 1),  # Starts in September
        )

        return edition

    async def create_europa_league(
        self,
        season_id: int,
        start_year: int,
    ) -> CupEdition:
        """Create a Europa League edition.

        Args:
            season_id: Season ID
            start_year: Starting year

        Returns:
            Created CupEdition
        """
        config = self.config.EUROPA_LEAGUE

        # Create competition if not exists
        result = await self.session.execute(
            select(CupCompetition).where(CupCompetition.cup_type == CupType.EUROPA_LEAGUE)
        )
        competition = result.scalar_one_or_none()

        if not competition:
            competition = await self.base_engine.create_european_competition(
                name=config["name"],
                short_name=config["short_name"],
                cup_type=CupType.EUROPA_LEAGUE,
            )

        # Create edition
        edition = await self.base_engine.create_edition(
            competition_id=competition.id,
            season_id=season_id,
            start_year=start_year,
            start_date=date(start_year, 9, 1),
        )

        return edition

    async def qualify_clubs_by_league_position(
        self,
        edition_id: int,
        league_standings: Dict[int, List[int]],  # league_id -> ordered list of club_ids
    ) -> List[CupParticipant]:
        """Qualify clubs based on their league position.

        Args:
            edition_id: Cup edition ID
            league_standings: Dict mapping league_id to ordered list of club IDs
                            (index 0 = 1st place, index 1 = 2nd place, etc.)

        Returns:
            List of qualified participants
        """
        edition = await self.session.get(CupEdition, edition_id)
        competition = await self.session.get(CupCompetition, edition.competition_id)

        participants = []

        # Get qualifying spots configuration
        if competition.cup_type == CupType.CHAMPIONS_LEAGUE:
            spots_config = self.config.CHAMPIONS_LEAGUE["qualifying_spots"]
        else:
            spots_config = {}

        for league_id, standings in league_standings.items():
            league = await self.session.get(League, league_id)
            if not league:
                continue

            # Get number of spots for this country
            country_key = league.country.lower()
            num_spots = spots_config.get(country_key, 1)

            # Qualify top N clubs
            for position in range(min(num_spots, len(standings))):
                club_id = standings[position]
                club = await self.session.get(Club, club_id)

                if club:
                    participant = CupParticipant(
                        edition_id=edition_id,
                        club_id=club_id,
                        qualification_method=f"league_position_{position + 1}",
                        is_active=True,
                    )
                    self.session.add(participant)
                    participants.append(participant)

        await self.session.commit()
        return participants

    async def conduct_group_stage_draw(
        self,
        edition_id: int,
    ) -> Dict[str, List[int]]:
        """Conduct the Champions League group stage draw.

        Clubs are divided into 4 pots based on UEFA coefficients/reputation,
        then drawn into 8 groups of 4.

        Args:
            edition_id: Cup edition ID

        Returns:
            Dict mapping group letter to list of club IDs
        """
        # Get participants
        result = await self.session.execute(
            select(CupParticipant).where(
                and_(
                    CupParticipant.edition_id == edition_id,
                    CupParticipant.is_active == True,
                )
            )
        )
        participants = list(result.scalars().all())

        if len(participants) != 32:
            raise ValueError(f"Expected 32 participants, got {len(participants)}")

        # Sort clubs into 4 pots by reputation
        clubs = [p.club for p in participants]
        clubs.sort(key=lambda c: c.reputation, reverse=True)

        # Create 4 pots of 8
        pots = [clubs[i * 8 : (i + 1) * 8] for i in range(4)]

        # Shuffle each pot
        for pot in pots:
            random.shuffle(pot)

        # Draw into 8 groups
        groups = {chr(65 + i): [] for i in range(8)}  # A, B, C, D, E, F, G, H

        for pot_idx, pot in enumerate(pots):
            for group_idx, club in enumerate(pot):
                group_letter = chr(65 + group_idx)
                groups[group_letter].append(club)

        # Update participants with group assignments
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

        # Return group assignments as IDs
        return {letter: [c.id for c in clubs] for letter, clubs in groups.items()}

    async def simulate_group_stage_matchday(
        self,
        edition_id: int,
        matchday: int,
        match_date: date,
    ) -> List[CupMatch]:
        """Simulate a group stage matchday.

        Args:
            edition_id: Cup edition ID
            matchday: Matchday number (1-6)
            match_date: Date for matches

        Returns:
            List of CupMatches
        """
        edition = await self.session.get(CupEdition, edition_id)

        # Get the group stage round for this matchday
        result = await self.session.execute(
            select(CupRound).where(
                and_(
                    CupRound.edition_id == edition_id,
                    CupRound.round_type == CupRoundType.GROUP_STAGE,
                    CupRound.group_stage_matchday == matchday,
                )
            )
        )
        cup_round = result.scalar_one_or_none()

        if not cup_round:
            raise ValueError(f"Group stage matchday {matchday} not found")

        # Get all groups
        result = await self.session.execute(
            select(CupParticipant).where(
                and_(
                    CupParticipant.edition_id == edition_id,
                    CupParticipant.group_name != None,
                )
            )
        )
        participants = list(result.scalars().all())

        # Group by group_name
        groups: Dict[str, List[CupParticipant]] = {}
        for p in participants:
            if p.group_name not in groups:
                groups[p.group_name] = []
            groups[p.group_name].append(p)

        cup_matches = []

        # Standard group stage schedule (6 matchdays)
        # Matchday 1: 1v2, 3v4
        # Matchday 2: 2v4, 1v3
        # Matchday 3: 4v1, 2v3
        # Matchday 4: 2v1, 4v3
        # Matchday 5: 4v2, 3v1
        # Matchday 6: 1v4, 3v2

        schedules = {
            1: [(0, 1), (2, 3)],
            2: [(1, 3), (0, 2)],
            3: [(3, 0), (1, 2)],
            4: [(1, 0), (3, 2)],
            5: [(3, 1), (2, 0)],
            6: [(0, 3), (2, 1)],
        }

        schedule = schedules.get(matchday, [])

        for group_name, group_participants in groups.items():
            if len(group_participants) != 4:
                continue

            # Sort by position
            group_participants.sort(key=lambda p: p.group_position or 0)

            for home_idx, away_idx in schedule:
                home_club_id = group_participants[home_idx].club_id
                away_club_id = group_participants[away_idx].club_id

                # Create match
                match = Match(
                    season_id=edition.season_id,
                    matchday=matchday,
                    match_date=match_date,
                    home_club_id=home_club_id,
                    away_club_id=away_club_id,
                    home_score=0,
                    away_score=0,
                    status=MatchStatus.SCHEDULED,
                )
                self.session.add(match)
                await self.session.flush()

                # Create CupMatch
                cup_match = CupMatch(
                    round_id=cup_round.id,
                    match_id=match.id,
                    is_first_leg=True,
                )
                self.session.add(cup_match)
                cup_matches.append(cup_match)

        await self.session.commit()

        # Simulate all matches
        for cup_match in cup_matches:
            await self.base_engine.simulate_match(cup_match)

        return cup_matches

    async def update_group_standings(
        self,
        edition_id: int,
    ) -> Dict[str, List[GroupStanding]]:
        """Update and return group standings after matches.

        Args:
            edition_id: Cup edition ID

        Returns:
            Dict mapping group letter to sorted list of GroupStanding
        """
        # Get all group stage matches
        result = await self.session.execute(
            select(CupMatch)
            .join(CupRound)
            .where(
                and_(
                    CupRound.edition_id == edition_id,
                    CupRound.round_type == CupRoundType.GROUP_STAGE,
                )
            )
        )
        cup_matches = list(result.scalars().all())

        # Calculate standings per group
        standings: Dict[str, Dict[int, GroupStanding]] = {}

        for cup_match in cup_matches:
            match = cup_match.match
            if match.status != MatchStatus.FULL_TIME:
                continue

            # Get group for home team
            result = await self.session.execute(
                select(CupParticipant).where(
                    and_(
                        CupParticipant.edition_id == edition_id,
                        CupParticipant.club_id == match.home_club_id,
                    )
                )
            )
            home_participant = result.scalar_one_or_none()

            if not home_participant or not home_participant.group_name:
                continue

            group_name = home_participant.group_name

            if group_name not in standings:
                standings[group_name] = {}

            # Initialize standings if needed
            if match.home_club_id not in standings[group_name]:
                standings[group_name][match.home_club_id] = GroupStanding(
                    club_id=match.home_club_id,
                    club_name=match.home_club.name if hasattr(match, "home_club") else "",
                )
            if match.away_club_id not in standings[group_name]:
                standings[group_name][match.away_club_id] = GroupStanding(
                    club_id=match.away_club_id,
                    club_name=match.away_club.name if hasattr(match, "away_club") else "",
                )

            # Update standings
            standings[group_name][match.home_club_id].add_result(match.home_score, match.away_score)
            standings[group_name][match.away_club_id].add_result(match.away_score, match.home_score)

        # Sort and return
        result = {}
        for group_name, group_standings in standings.items():
            sorted_standings = sorted(
                group_standings.values(),
                key=lambda s: (s.points, s.goal_difference, s.goals_for),
                reverse=True,
            )
            result[group_name] = sorted_standings

        return result

    async def get_group_winners_and_runners_up(
        self,
        edition_id: int,
    ) -> Tuple[List[int], List[int]]:
        """Get group winners and runners-up for knockout stage.

        Args:
            edition_id: Cup edition ID

        Returns:
            Tuple of (winners, runners_up) as lists of club IDs
        """
        standings = await self.update_group_standings(edition_id)

        winners = []
        runners_up = []

        for group_name in sorted(standings.keys()):
            group = standings[group_name]
            if len(group) >= 1:
                winners.append(group[0].club_id)
            if len(group) >= 2:
                runners_up.append(group[1].club_id)

        return winners, runners_up

    async def conduct_round_of_16_draw(
        self,
        edition_id: int,
    ) -> DrawResult:
        """Conduct Round of 16 draw (group winners vs runners-up).

        Winners are seeded, runners-up are unseeded.
        Group winners cannot play against:
        - Teams from their own group
        - Teams from their own country

        Args:
            edition_id: Cup edition ID

        Returns:
            DrawResult with pairings
        """
        winners, runners_up = await self.get_group_winners_and_runners_up(edition_id)

        if len(winners) != 8 or len(runners_up) != 8:
            raise ValueError(f"Expected 8 winners and 8 runners-up")

        # Get club objects
        winner_clubs = [await self.session.get(Club, cid) for cid in winners]
        runner_up_clubs = [await self.session.get(Club, cid) for cid in runners_up]

        # Get group and country info
        winner_info = []
        for club in winner_clubs:
            result = await self.session.execute(
                select(CupParticipant).where(
                    and_(
                        CupParticipant.edition_id == edition_id,
                        CupParticipant.club_id == club.id,
                    )
                )
            )
            p = result.scalar_one_or_none()
            winner_info.append(
                {
                    "club": club,
                    "group": p.group_name if p else "",
                    "country": club.country if hasattr(club, "country") else "",
                }
            )

        runner_up_info = []
        for club in runner_up_clubs:
            result = await self.session.execute(
                select(CupParticipant).where(
                    and_(
                        CupParticipant.edition_id == edition_id,
                        CupParticipant.club_id == club.id,
                    )
                )
            )
            p = result.scalar_one_or_none()
            runner_up_info.append(
                {
                    "club": club,
                    "group": p.group_name if p else "",
                    "country": club.country if hasattr(club, "country") else "",
                }
            )

        # Conduct draw
        pairings = []
        available_runners = runner_up_info.copy()

        for winner in winner_info:
            valid_opponents = [
                r
                for r in available_runners
                if r["group"] != winner["group"] and r["country"] != winner["country"]
            ]

            if not valid_opponents:
                # Fallback: just avoid same group
                valid_opponents = [r for r in available_runners if r["group"] != winner["group"]]

            if not valid_opponents:
                # Last resort: any available
                valid_opponents = available_runners

            # Random selection
            opponent = random.choice(valid_opponents)
            available_runners.remove(opponent)

            # Winner plays at home in second leg
            pairings.append((winner["club"].id, opponent["club"].id))

        # Get round ID
        result = await self.session.execute(
            select(CupRound).where(
                and_(
                    CupRound.edition_id == edition_id,
                    CupRound.round_type == CupRoundType.ROUND_OF_16,
                )
            )
        )
        cup_round = result.scalar_one()

        return DrawResult(
            round_id=cup_round.id,
            pairings=pairings,
            byes=[],
        )

    async def schedule_two_legged_tie(
        self,
        round_id: int,
        home_club_id: int,
        away_club_id: int,
        first_leg_date: date,
        second_leg_date: date,
    ) -> Tuple[CupMatch, CupMatch]:
        """Schedule a two-legged knockout tie.

        Args:
            round_id: Cup round ID
            home_club_id: ID of team playing first leg at home
            away_club_id: ID of team playing first leg away
            first_leg_date: Date for first leg
            second_leg_date: Date for second leg

        Returns:
            Tuple of (first_leg, second_leg) CupMatches
        """
        cup_round = await self.session.get(CupRound, round_id)
        edition = await self.session.get(CupEdition, cup_round.edition_id)

        # First leg
        match1 = Match(
            season_id=edition.season_id,
            matchday=cup_round.round_order,
            match_date=first_leg_date,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_score=0,
            away_score=0,
            status=MatchStatus.SCHEDULED,
        )
        self.session.add(match1)
        await self.session.flush()

        cup_match1 = CupMatch(
            round_id=round_id,
            match_id=match1.id,
            is_first_leg=True,
        )
        self.session.add(cup_match1)

        # Second leg
        match2 = Match(
            season_id=edition.season_id,
            matchday=cup_round.round_order,
            match_date=second_leg_date,
            home_club_id=away_club_id,
            away_club_id=home_club_id,
            home_score=0,
            away_score=0,
            status=MatchStatus.SCHEDULED,
        )
        self.session.add(match2)
        await self.session.flush()

        cup_match2 = CupMatch(
            round_id=round_id,
            match_id=match2.id,
            is_first_leg=False,
        )
        self.session.add(cup_match2)

        await self.session.commit()

        return cup_match1, cup_match2

    async def simulate_two_legged_tie(
        self,
        first_leg: CupMatch,
        second_leg: CupMatch,
    ) -> int:
        """Simulate a two-legged tie and determine winner.

        Args:
            first_leg: First leg CupMatch
            second_leg: Second leg CupMatch

        Returns:
            Winner club ID
        """
        # Simulate both legs
        await self.base_engine.simulate_match(first_leg)
        await self.base_engine.simulate_match(second_leg)

        # Calculate aggregate
        match1 = first_leg.match
        match2 = second_leg.match

        # Team that played first leg at home
        first_leg_home = match1.home_club_id
        first_leg_away = match1.away_club_id

        aggregate_home = match1.home_score + match2.away_score
        aggregate_away = match1.away_score + match2.home_score

        # Store aggregate scores
        first_leg.aggregate_home_score = aggregate_home
        first_leg.aggregate_away_score = aggregate_away
        second_leg.aggregate_home_score = aggregate_away  # Swapped for second leg perspective
        second_leg.aggregate_away_score = aggregate_home

        # Away goals
        home_away_goals = match1.away_score  # Goals scored away by first leg home team
        away_away_goals = match2.away_score  # Goals scored away by first leg away team

        first_leg.home_away_goals = home_away_goals
        first_leg.away_away_goals = away_away_goals
        second_leg.home_away_goals = away_away_goals
        second_leg.away_away_goals = home_away_goals

        # Determine winner
        winner_id = None

        if aggregate_home > aggregate_away:
            winner_id = first_leg_home
        elif aggregate_away > aggregate_home:
            winner_id = first_leg_away
        else:
            # Away goals rule (historical - now uses extra time/penalties)
            if home_away_goals > away_away_goals:
                winner_id = first_leg_home
            elif away_away_goals > home_away_goals:
                winner_id = first_leg_away
            else:
                # Would go to penalties - random for now
                winner_id = random.choice([first_leg_home, first_leg_away])
                first_leg.went_to_extra_time = True
                second_leg.went_to_extra_time = True

        # Update winners
        first_leg.winner_club_id = winner_id
        second_leg.winner_club_id = winner_id

        await self.session.commit()

        return winner_id

    async def distribute_champions_league_prizes(
        self,
        edition_id: int,
    ) -> Dict[int, int]:
        """Distribute Champions League prize money.

        Args:
            edition_id: Cup edition ID

        Returns:
            Dict mapping club_id to prize money earned
        """
        calculator = self.base_engine.prize_calculator

        # Get all participants
        result = await self.session.execute(
            select(CupParticipant).where(CupParticipant.edition_id == edition_id)
        )
        participants = list(result.scalars().all())

        prizes_earned = {}

        for participant in participants:
            total_prize = 0

            # Group stage participation
            if participant.group_points > 0 or participant.group_name:
                total_prize += calculator.calculate_participation_bonus(
                    CupType.CHAMPIONS_LEAGUE,
                    CupRoundType.GROUP_STAGE,
                )

            # Group stage performance (approximate)
            wins = participant.group_points // 3
            draws = participant.group_points % 3
            total_prize += wins * calculator.CL_PRIZES["group_stage_win"]
            total_prize += draws * calculator.CL_PRIZES["group_stage_draw"]

            # Knockout progression
            if participant.final_position:
                if participant.final_position <= 16:
                    total_prize += calculator.CL_PRIZES["round_of_16"]
                if participant.final_position <= 8:
                    total_prize += calculator.CL_PRIZES["quarter_final"]
                if participant.final_position <= 4:
                    total_prize += calculator.CL_PRIZES["semi_final"]
                if participant.final_position <= 2:
                    total_prize += calculator.CL_PRIZES["final"]
                if participant.final_position == 1:
                    total_prize += calculator.CL_PRIZES["winner"]

            if total_prize > 0:
                await self.base_engine.distribute_prize_money(
                    edition_id=edition_id,
                    club_id=participant.club_id,
                    amount=total_prize,
                )
                prizes_earned[participant.club_id] = total_prize

        return prizes_earned

    async def run_complete_champions_league(
        self,
        season_id: int,
        start_year: int,
        qualified_clubs: List[int],
        group_stage_dates: Optional[List[date]] = None,
        knockout_dates: Optional[List[Tuple[date, date]]] = None,
    ) -> CupEdition:
        """Run a complete Champions League tournament.

        Args:
            season_id: Season ID
            start_year: Starting year
            qualified_clubs: List of 32 qualified club IDs
            group_stage_dates: List of 6 dates for group stage matchdays
            knockout_dates: List of (first_leg, second_leg) dates for knockouts

        Returns:
            Completed CupEdition
        """
        # Create edition
        edition = await self.create_champions_league(season_id, start_year)

        # Add participants
        clubs = [await self.session.get(Club, cid) for cid in qualified_clubs]
        await self.base_engine.add_participants(edition.id, clubs)

        # Default dates
        if group_stage_dates is None:
            base = date(start_year, 9, 15)
            group_stage_dates = [base + timedelta(weeks=i * 2) for i in range(6)]

        if knockout_dates is None:
            base = date(start_year + 1, 2, 15)
            knockout_dates = [
                (base + timedelta(weeks=i * 3), base + timedelta(weeks=i * 3 + 1)) for i in range(4)
            ]

        # Group stage draw
        await self.conduct_group_stage_draw(edition.id)

        # Simulate group stage
        for matchday in range(1, 7):
            await self.simulate_group_stage_matchday(
                edition.id,
                matchday,
                group_stage_dates[matchday - 1],
            )

        # Update standings
        await self.update_group_standings(edition.id)

        # Get qualifiers for knockout
        winners, runners_up = await self.get_group_winners_and_runners_up(edition.id)

        # Round of 16 draw and matches
        ro16_draw = await self.conduct_round_of_16_draw(edition.id)
        ro16_date = knockout_dates[0]

        advancing = []
        for home_id, away_id in ro16_draw.pairings:
            first_leg, second_leg = await self.schedule_two_legged_tie(
                ro16_draw.round_id,
                home_id,
                away_id,
                ro16_date[0],
                ro16_date[1],
            )
            winner = await self.simulate_two_legged_tie(first_leg, second_leg)
            advancing.append(winner)

        # Quarter-finals
        result = await self.session.execute(
            select(CupRound).where(
                and_(
                    CupRound.edition_id == edition.id,
                    CupRound.round_type == CupRoundType.QUARTER_FINAL,
                )
            )
        )
        qf_round = result.scalar_one()
        qf_date = knockout_dates[1]

        # Random draw for QF
        random.shuffle(advancing)
        qf_winners = []
        for i in range(0, len(advancing), 2):
            first_leg, second_leg = await self.schedule_two_legged_tie(
                qf_round.id,
                advancing[i],
                advancing[i + 1],
                qf_date[0],
                qf_date[1],
            )
            winner = await self.simulate_two_legged_tie(first_leg, second_leg)
            qf_winners.append(winner)

        # Semi-finals
        result = await self.session.execute(
            select(CupRound).where(
                and_(
                    CupRound.edition_id == edition.id,
                    CupRound.round_type == CupRoundType.SEMI_FINAL,
                )
            )
        )
        sf_round = result.scalar_one()
        sf_date = knockout_dates[2]

        sf_winners = []
        for i in range(0, len(qf_winners), 2):
            first_leg, second_leg = await self.schedule_two_legged_tie(
                sf_round.id,
                qf_winners[i],
                qf_winners[i + 1],
                sf_date[0],
                sf_date[1],
            )
            winner = await self.simulate_two_legged_tie(first_leg, second_leg)
            sf_winners.append(winner)

        # Final (single match)
        result = await self.session.execute(
            select(CupRound).where(
                and_(
                    CupRound.edition_id == edition.id,
                    CupRound.round_type == CupRoundType.FINAL,
                )
            )
        )
        final_round = result.scalar_one()
        final_date = knockout_dates[3][0]

        final_match = Match(
            season_id=edition.season_id,
            matchday=final_round.round_order,
            match_date=final_date,
            home_club_id=sf_winners[0],
            away_club_id=sf_winners[1],
            home_score=0,
            away_score=0,
            status=MatchStatus.SCHEDULED,
        )
        self.session.add(final_match)
        await self.session.flush()

        final_cup_match = CupMatch(
            round_id=final_round.id,
            match_id=final_match.id,
            is_first_leg=True,
        )
        self.session.add(final_cup_match)
        await self.session.commit()

        # Simulate final
        await self.base_engine.simulate_match(final_cup_match)

        # Set winner
        edition.winner_club_id = final_cup_match.winner_club_id

        # Distribute prizes
        await self.distribute_champions_league_prizes(edition.id)

        # Mark as completed
        edition.status = CupStatus.COMPLETED
        await self.session.commit()

        return edition
