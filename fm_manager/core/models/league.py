"""League and Season model definitions."""

from datetime import date
from enum import Enum as PyEnum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Integer, String, Date, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.club import Club
    from fm_manager.core.models.match import Match
    from fm_manager.core.models.cup_competition import CupEdition


class LeagueFormat(PyEnum):
    """League format types."""

    DOUBLE_ROUND_ROBIN = "double_round_robin"  # Play every team twice
    SINGLE_ROUND_ROBIN = "single_round_robin"  # Play every team once
    SPLIT = "split"  # Split into groups after certain round
    PLAYOFF = "playoff"  # Playoff system


class League(Base):
    """League entity representing a football competition."""

    __tablename__ = "leagues"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Level (1 = top division, 2 = second division, etc.)
    tier: Mapped[int] = mapped_column(Integer, default=1)

    # Format
    format: Mapped[LeagueFormat] = mapped_column(
        Enum(LeagueFormat),
        default=LeagueFormat.DOUBLE_ROUND_ROBIN,
    )
    teams_count: Mapped[int] = mapped_column(Integer, default=20)

    # Promotion/Relegation
    promotion_count: Mapped[int] = mapped_column(Integer, default=3)
    relegation_count: Mapped[int] = mapped_column(Integer, default=3)
    has_promotion_playoff: Mapped[bool] = mapped_column(Boolean, default=False)
    has_relegation_playoff: Mapped[bool] = mapped_column(Boolean, default=False)

    # Schedule
    season_start_month: Mapped[int] = mapped_column(Integer, default=8)  # August
    season_end_month: Mapped[int] = mapped_column(Integer, default=5)  # May
    has_winter_break: Mapped[bool] = mapped_column(Boolean, default=False)
    winter_break_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    winter_break_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Match rules
    matches_on_weekdays: Mapped[bool] = mapped_column(Boolean, default=True)
    typical_match_days: Mapped[str] = mapped_column(
        String(50),
        default="Saturday,Sunday",
    )  # Comma-separated days

    # European qualification spots
    champions_league_spots: Mapped[int] = mapped_column(Integer, default=4)
    europa_league_spots: Mapped[int] = mapped_column(Integer, default=2)
    conference_league_spots: Mapped[int] = mapped_column(Integer, default=1)

    # Prize money (in currency units)
    prize_money_first: Mapped[int] = mapped_column(Integer, default=100_000_000)
    prize_money_last: Mapped[int] = mapped_column(Integer, default=10_000_000)

    # TV rights
    tv_rights_base: Mapped[int] = mapped_column(Integer, default=50_000_000)

    # Relationships
    clubs: Mapped[List["Club"]] = relationship(
        back_populates="league",
        lazy="dynamic",
    )
    seasons: Mapped[List["Season"]] = relationship(
        back_populates="league",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<League(id={self.id}, name='{self.name}', country='{self.country}')>"


class Season(Base):
    """Season entity representing a specific season of a league."""

    __tablename__ = "seasons"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"))

    # Season info
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="upcoming")
    # upcoming, active, finished

    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Current state
    current_matchday: Mapped[int] = mapped_column(Integer, default=0)
    total_matchdays: Mapped[int] = mapped_column(Integer, default=38)

    # Relationships
    league: Mapped["League"] = relationship(back_populates="seasons")
    matches: Mapped[List["Match"]] = relationship(
        back_populates="season",
        lazy="dynamic",
    )
    cup_editions: Mapped[List["CupEdition"]] = relationship(
        "CupEdition",
        back_populates="season",
        lazy="dynamic",
    )

    @property
    def name(self) -> str:
        """Get season name (e.g., '2024-25')."""
        return f"{self.start_year}-{str(self.end_year)[-2:]}"

    def __repr__(self) -> str:
        return f"<Season(id={self.id}, league='{self.league.name}', year='{self.name}')>"
