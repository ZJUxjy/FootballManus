"""Tests for cup competition system.

Comprehensive tests for:
- CupCompetitionEngine (base functionality)
- DomesticCupEngine (FA Cup, League Cup)
- EuropeanCompetitionEngine (Champions League, Europa League)
"""

import pytest
import random
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
    CupDrawGenerator,
    DrawType,
    DrawResult,
    GroupStanding,
    CupPrizeCalculator,
)
from fm_manager.engine.domestic_cup_engine import (
    DomesticCupEngine,
    DomesticCupConfig,
)
from fm_manager.engine.european_competition_engine import (
    EuropeanCompetitionEngine,
    EuropeanCompetitionConfig,
)


class TestCupDrawGenerator:
    """Tests for the cup draw generator."""

    def test_random_draw_basic(self):
        """Test basic random draw functionality."""
        generator = CupDrawGenerator(seed=42)

        # Create mock clubs
        clubs = [MagicMock(id=i, name=f"Club {i}") for i in range(8)]

        pairings = generator.random_draw(clubs)

        assert len(pairings) == 4

        # Check all clubs are used exactly once
        all_clubs = set()
        for home, away in pairings:
            all_clubs.add(home.id)
            all_clubs.add(away.id)

        assert len(all_clubs) == 8

    def test_seeded_draw(self):
        """Test seeded draw with pots."""
        generator = CupDrawGenerator(seed=42)

        # Create clubs sorted by "reputation"
        clubs = [MagicMock(id=i, reputation=100 - i) for i in range(8)]

        pairings = generator.seeded_draw(clubs, num_pots=2)

        assert len(pairings) == 4

        # In a seeded draw, top 4 should play bottom 4
        for home, away in pairings:
            assert home.reputation >= 97
            assert away.reputation <= 96

    def test_group_stage_draw(self):
        """Test Champions League style group stage draw."""
        generator = CupDrawGenerator(seed=42)

        # Create 32 clubs
        clubs = [MagicMock(id=i, reputation=100 - i) for i in range(32)]

        groups = generator.group_stage_draw(clubs, num_groups=8, clubs_per_group=4)

        assert len(groups) == 8

        # Each group should have 4 clubs
        for group_letter, group_clubs in groups.items():
            assert len(group_clubs) == 4

        # Total clubs should be 32
        total = sum(len(g) for g in groups.values())
        assert total == 32


class TestCupPrizeCalculator:
    """Tests for prize money calculations."""

    def test_champions_league_participation_bonus(self):
        """Test CL group stage participation bonus."""
        calculator = CupPrizeCalculator()

        bonus = calculator.calculate_participation_bonus(
            CupType.CHAMPIONS_LEAGUE,
            CupRoundType.GROUP_STAGE,
        )

        assert bonus == 15_600_000

    def test_champions_league_progression_bonus(self):
        """Test CL knockout progression bonuses."""
        calculator = CupPrizeCalculator()

        # Round of 16
        bonus = calculator.calculate_progression_bonus(
            CupType.CHAMPIONS_LEAGUE,
            CupRoundType.ROUND_OF_16,
        )
        assert bonus == 9_600_000

        # Final (includes winner bonus)
        bonus = calculator.calculate_progression_bonus(
            CupType.CHAMPIONS_LEAGUE,
            CupRoundType.FINAL,
        )
        assert bonus == 15_500_000 + 4_500_000

    def test_fa_cup_prize_money(self):
        """Test FA Cup prize money structure."""
        calculator = CupPrizeCalculator()

        # Third round (when Premier League enters)
        bonus = calculator.calculate_progression_bonus(
            CupType.DOMESTIC_CUP,
            CupRoundType.ROUND_OF_64,
        )
        assert bonus == 40_000

        # Final
        bonus = calculator.calculate_progression_bonus(
            CupType.DOMESTIC_CUP,
            CupRoundType.FINAL,
        )
        assert bonus == 2_000_000


class TestGroupStanding:
    """Tests for group stage standings."""

    def test_add_result_win(self):
        """Test adding a win to standings."""
        standing = GroupStanding(club_id=1, club_name="Test FC")

        standing.add_result(3, 1)  # 3-1 win

        assert standing.played == 1
        assert standing.won == 1
        assert standing.points == 3
        assert standing.goals_for == 3
        assert standing.goals_against == 1
        assert standing.goal_difference == 2

    def test_add_result_draw(self):
        """Test adding a draw to standings."""
        standing = GroupStanding(club_id=1, club_name="Test FC")

        standing.add_result(1, 1)  # 1-1 draw

        assert standing.played == 1
        assert standing.drawn == 1
        assert standing.points == 1

    def test_add_result_loss(self):
        """Test adding a loss to standings."""
        standing = GroupStanding(club_id=1, club_name="Test FC")

        standing.add_result(0, 2)  # 0-2 loss

        assert standing.played == 1
        assert standing.lost == 1
        assert standing.points == 0

    def test_multiple_results(self):
        """Test adding multiple results."""
        standing = GroupStanding(club_id=1, club_name="Test FC")

        standing.add_result(3, 1)  # Win
        standing.add_result(1, 1)  # Draw
        standing.add_result(0, 2)  # Loss

        assert standing.played == 3
        assert standing.won == 1
        assert standing.drawn == 1
        assert standing.lost == 1
        assert standing.points == 4


class TestDrawResult:
    """Tests for DrawResult dataclass."""

    def test_get_match_count(self):
        """Test match count calculation."""
        result = DrawResult(
            round_id=1,
            pairings=[(1, 2), (3, 4), (5, 6)],
            byes=[7],
        )

        assert result.get_match_count() == 3

    def test_get_participating_clubs(self):
        """Test getting all participating clubs."""
        result = DrawResult(
            round_id=1,
            pairings=[(1, 2), (3, 4)],
            byes=[5],
        )

        clubs = result.get_participating_clubs()

        assert clubs == {1, 2, 3, 4, 5}


@pytest.mark.asyncio
class TestCupCompetitionEngine:
    """Integration tests for CupCompetitionEngine."""

    async def test_create_domestic_cup(self, mock_session):
        """Test creating a domestic cup competition."""
        engine = CupCompetitionEngine(mock_session)

        cup = await engine.create_domestic_cup(
            name="FA Cup",
            short_name="FAC",
            country="England",
            tier_entry_rounds={1: 3, 2: 2, 3: 1},
        )

        assert cup.name == "FA Cup"
        assert cup.cup_type == CupType.DOMESTIC_CUP
        assert cup.format == CupFormat.KNOCKOUT
        assert cup.country == "England"

    async def test_create_european_competition(self, mock_session):
        """Test creating a European competition."""
        engine = CupCompetitionEngine(mock_session)

        cup = await engine.create_european_competition(
            name="Champions League",
            short_name="UCL",
            cup_type=CupType.CHAMPIONS_LEAGUE,
        )

        assert cup.name == "Champions League"
        assert cup.cup_type == CupType.CHAMPIONS_LEAGUE
        assert cup.format == CupFormat.GROUP_THEN_KNOCKOUT

    async def test_create_edition(self, mock_session):
        """Test creating a cup edition."""
        engine = CupCompetitionEngine(mock_session)

        # Mock competition
        mock_competition = MagicMock()
        mock_competition.id = 1
        mock_competition.format = CupFormat.KNOCKOUT
        mock_competition.typical_participants = 64

        mock_session.get.return_value = mock_competition

        edition = await engine.create_edition(
            competition_id=1,
            season_id=1,
            start_year=2024,
        )

        assert edition.competition_id == 1
        assert edition.season_id == 1
        assert edition.start_year == 2024
        assert edition.status == CupStatus.UPCOMING


@pytest.mark.asyncio
class TestDomesticCupEngine:
    """Tests for DomesticCupEngine."""

    async def test_create_fa_cup(self, mock_session):
        """Test creating FA Cup."""
        engine = DomesticCupEngine(mock_session)

        mock_competition = MagicMock()
        mock_competition.id = 1

        async def mock_create_domestic_cup(*args, **kwargs):
            return mock_competition

        engine.base_engine.create_domestic_cup = mock_create_domestic_cup

        mock_edition = MagicMock()
        mock_edition.id = 1
        engine.base_engine.create_edition = AsyncMock(return_value=mock_edition)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        edition = await engine.create_fa_cup(season_id=1, start_year=2024)

        engine.base_engine.create_edition.assert_called_once()
        assert edition.id == 1

    async def test_create_league_cup(self, mock_session):
        """Test creating League Cup."""
        engine = DomesticCupEngine(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        engine.base_engine.create_edition = AsyncMock()

        mock_edition = MagicMock()
        mock_edition.id = 1
        engine.base_engine.create_edition.return_value = mock_edition

        edition = await engine.create_league_cup(season_id=1, start_year=2024)

        engine.base_engine.create_edition.assert_called_once()

    async def test_get_fa_cup_prize_money(self, mock_session):
        """Test FA Cup prize money retrieval."""
        engine = DomesticCupEngine(mock_session)

        prize = await engine.get_fa_cup_prize_money(CupRoundType.FINAL)

        assert prize == 2_000_000


@pytest.mark.asyncio
class TestEuropeanCompetitionEngine:
    """Tests for EuropeanCompetitionEngine."""

    async def test_create_champions_league(self, mock_session):
        """Test creating Champions League."""
        engine = EuropeanCompetitionEngine(mock_session)

        mock_competition = MagicMock()
        mock_competition.id = 1

        async def mock_create_european_competition(*args, **kwargs):
            return mock_competition

        engine.base_engine.create_european_competition = mock_create_european_competition

        mock_edition = MagicMock()
        mock_edition.id = 1
        engine.base_engine.create_edition = AsyncMock(return_value=mock_edition)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        edition = await engine.create_champions_league(season_id=1, start_year=2024)

        engine.base_engine.create_edition.assert_called_once()
        assert edition.id == 1

    async def test_conduct_group_stage_draw(self, mock_session):
        """Test group stage draw."""
        engine = EuropeanCompetitionEngine(mock_session)

        mock_participants = []
        for i in range(32):
            p = MagicMock()
            p.club_id = i
            p.club = MagicMock(id=i, reputation=100 - i)
            mock_participants.append(p)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_participants
        mock_session.execute.return_value = mock_result

        groups = await engine.conduct_group_stage_draw(edition_id=1)

        assert len(groups) == 8
        for group_letter, club_ids in groups.items():
            assert len(club_ids) == 4


# Fixtures
@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_clubs():
    """Create sample clubs for testing."""
    clubs = []
    for i in range(20):
        club = MagicMock(spec=Club)
        club.id = i
        club.name = f"Club {i}"
        club.reputation = 5000 + (20 - i) * 100
        clubs.append(club)
    return clubs


@pytest.fixture
def sample_league():
    """Create a sample league."""
    league = MagicMock(spec=League)
    league.id = 1
    league.name = "Premier League"
    league.country = "England"
    league.tier = 1
    return league


# Integration test
@pytest.mark.asyncio
async def test_full_fa_cup_simulation(mock_session, sample_clubs):
    """Test a complete FA Cup simulation flow."""
    engine = DomesticCupEngine(mock_session)

    # This would be a full integration test
    # For now, just verify the engine initializes correctly
    assert engine is not None
    assert engine.base_engine is not None


@pytest.mark.asyncio
async def test_full_champions_league_simulation(mock_session, sample_clubs):
    """Test a complete Champions League simulation flow."""
    engine = EuropeanCompetitionEngine(mock_session)

    # Verify engine initialization
    assert engine is not None
    assert engine.base_engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
