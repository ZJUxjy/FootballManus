"""Cup competition models for FM Manager.

Defines data models for cup competitions including domestic cups (FA Cup, League Cup)
and European competitions (Champions League, Europa League).
"""

from datetime import date
from enum import Enum as PyEnum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Integer, String, Date, ForeignKey, Text, Enum, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.club import Club
    from fm_manager.core.models.match import Match
    from fm_manager.core.models.league import Season


class CupType(PyEnum):
    """Types of cup competitions."""

    DOMESTIC_CUP = "domestic_cup"  # e.g., FA Cup, Copa del Rey
    DOMESTIC_LEAGUE_CUP = "domestic_league_cup"  # e.g., League Cup, DFB-Pokal
    SUPER_CUP = "super_cup"  # e.g., Community Shield
    CHAMPIONS_LEAGUE = "champions_league"  # UEFA Champions League
    EUROPA_LEAGUE = "europa_league"  # UEFA Europa League
    CONFERENCE_LEAGUE = "conference_league"  # UEFA Conference League


class CupFormat(PyEnum):
    """Cup competition formats."""

    KNOCKOUT = "knockout"  # Single elimination
    KNOCKOUT_TWO_LEG = "knockout_two_leg"  # Two-legged ties
    GROUP_THEN_KNOCKOUT = "group_then_knockout"  # Group stage + knockout
    GROUP_STAGE_ONLY = "group_stage_only"  # Only group stage


class CupRoundType(PyEnum):
    """Types of rounds in a cup competition."""

    PRELIMINARY = "preliminary"
    FIRST_QUALIFYING = "first_qualifying"
    SECOND_QUALIFYING = "second_qualifying"
    THIRD_QUALIFYING = "third_qualifying"
    PLAYOFF = "playoff"
    ROUND_OF_64 = "round_of_64"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    FINAL = "final"
    GROUP_STAGE = "group_stage"


class CupStatus(PyEnum):
    """Status of a cup competition edition."""

    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CupCompetition(Base):
    """Cup competition definition (e.g., 'FA Cup', 'Champions League').

    This is a static definition of a competition type, not a specific season.
    """

    __tablename__ = "cup_competitions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)

    # Type and format
    cup_type: Mapped[CupType] = mapped_column(Enum(CupType), nullable=False)
    format: Mapped[CupFormat] = mapped_column(Enum(CupFormat), nullable=False)

    # Country/Region (empty for international competitions)
    country: Mapped[str] = mapped_column(String(100), default="")

    # Organizer
    organizer: Mapped[str] = mapped_column(String(100), default="")

    # Entry criteria
    min_league_tier: Mapped[int] = mapped_column(Integer, default=1)  # Min league level to enter
    max_league_tier: Mapped[int] = mapped_column(
        Integer, default=4
    )  # Max league level (for FA Cup)

    # Number of participants
    typical_participants: Mapped[int] = mapped_column(Integer, default=32)

    # Prize money (in currency units)
    total_prize_pool: Mapped[int] = mapped_column(Integer, default=0)

    # TV rights
    tv_rights_value: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    editions: Mapped[List["CupEdition"]] = relationship(
        back_populates="competition",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<CupCompetition(id={self.id}, name='{self.name}', type='{self.cup_type.value}')>"


class CupEdition(Base):
    """A specific edition/season of a cup competition.

    e.g., '2024-25 FA Cup', '2024-25 Champions League'
    """

    __tablename__ = "cup_editions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    competition_id: Mapped[int] = mapped_column(ForeignKey("cup_competitions.id"))
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))

    # Edition info
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[CupStatus] = mapped_column(
        Enum(CupStatus),
        default=CupStatus.UPCOMING,
    )

    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Winner
    winner_club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=True,
    )

    # Relationships
    competition: Mapped["CupCompetition"] = relationship(back_populates="editions")
    season: Mapped["Season"] = relationship(back_populates="cup_editions")
    winner: Mapped[Optional["Club"]] = relationship("Club")
    rounds: Mapped[List["CupRound"]] = relationship(
        back_populates="edition",
        lazy="dynamic",
        order_by="CupRound.round_order",
    )
    participants: Mapped[List["CupParticipant"]] = relationship(
        back_populates="edition",
        lazy="dynamic",
    )

    @property
    def name(self) -> str:
        """Get edition name (e.g., '2024-25 FA Cup')."""
        return f"{self.start_year}-{str(self.end_year)[-2:]} {self.competition.name}"

    def __repr__(self) -> str:
        return f"<CupEdition(id={self.id}, name='{self.name}', status='{self.status.value}')>"


class CupRound(Base):
    """A round within a cup edition.

    e.g., 'Third Round', 'Quarter Finals', 'Group Stage Matchday 1'
    """

    __tablename__ = "cup_rounds"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    edition_id: Mapped[int] = mapped_column(ForeignKey("cup_editions.id"))

    # Round info
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "Third Round"
    round_type: Mapped[CupRoundType] = mapped_column(Enum(CupRoundType), nullable=False)
    round_order: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, ...

    # For group stage
    is_group_stage: Mapped[bool] = mapped_column(Boolean, default=False)
    group_stage_matchday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Round settings
    is_two_legged: Mapped[bool] = mapped_column(Boolean, default=False)
    has_replay: Mapped[bool] = mapped_column(Boolean, default=False)  # For domestic cups

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Dates
    scheduled_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    edition: Mapped["CupEdition"] = relationship(back_populates="rounds")
    matches: Mapped[List["CupMatch"]] = relationship(
        back_populates="cup_round",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<CupRound(id={self.id}, name='{self.name}', order={self.round_order})>"


class CupParticipant(Base):
    """A club participating in a cup edition."""

    __tablename__ = "cup_participants"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    edition_id: Mapped[int] = mapped_column(ForeignKey("cup_editions.id"))
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))

    # Entry info
    entry_round_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cup_rounds.id"),
        nullable=True,
    )

    # How they qualified
    qualification_method: Mapped[str] = mapped_column(
        String(50),
        default="league_position",  # league_position, cup_winner, previous_winner, etc.
    )

    # Progress
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    eliminated_in_round_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cup_rounds.id"),
        nullable=True,
    )
    final_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Group stage (for CL/EL)
    group_name: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)  # A, B, C...
    group_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    group_points: Mapped[int] = mapped_column(Integer, default=0)
    group_goals_for: Mapped[int] = mapped_column(Integer, default=0)
    group_goals_against: Mapped[int] = mapped_column(Integer, default=0)

    # Prize money earned
    prize_money_earned: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    edition: Mapped["CupEdition"] = relationship(back_populates="participants")
    club: Mapped["Club"] = relationship("Club")
    entry_round: Mapped[Optional["CupRound"]] = relationship(
        "CupRound",
        foreign_keys=[entry_round_id],
    )
    eliminated_in_round: Mapped[Optional["CupRound"]] = relationship(
        "CupRound",
        foreign_keys=[eliminated_in_round_id],
    )

    @property
    def group_goal_difference(self) -> int:
        """Calculate group stage goal difference."""
        return self.group_goals_for - self.group_goals_against

    def __repr__(self) -> str:
        return f"<CupParticipant(club='{self.club.name}', edition='{self.edition.name}')>"


class CupMatch(Base):
    """A match in a cup competition.

    Links to the base Match model and adds cup-specific fields.
    """

    __tablename__ = "cup_matches"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    round_id: Mapped[int] = mapped_column(ForeignKey("cup_rounds.id"))
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))

    # For two-legged ties
    is_first_leg: Mapped[bool] = mapped_column(Boolean, default=True)
    aggregate_home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aggregate_away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Away goals (for tie-breaking)
    home_away_goals: Mapped[int] = mapped_column(Integer, default=0)
    away_away_goals: Mapped[int] = mapped_column(Integer, default=0)

    # Replay info (for domestic cups)
    is_replay: Mapped[bool] = mapped_column(Boolean, default=False)
    original_match_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cup_matches.id"),
        nullable=True,
    )

    # Winner
    winner_club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id"),
        nullable=True,
    )

    # Extra time / penalties
    went_to_extra_time: Mapped[bool] = mapped_column(Boolean, default=False)
    home_penalty_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_penalty_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    cup_round: Mapped["CupRound"] = relationship(back_populates="matches")
    match: Mapped["Match"] = relationship("Match")
    winner: Mapped[Optional["Club"]] = relationship("Club")
    original_match: Mapped[Optional["CupMatch"]] = relationship(
        "CupMatch",
        remote_side=[id],
    )

    @property
    def aggregate_score(self) -> Optional[str]:
        """Get aggregate score string for two-legged ties."""
        if self.aggregate_home_score is not None and self.aggregate_away_score is not None:
            return f"{self.aggregate_home_score}-{self.aggregate_away_score}"
        return None

    @property
    def away_goals_string(self) -> str:
        """Get away goals for display."""
        if self.is_first_leg:
            return f"Away: {self.away_away_goals}"
        else:
            return f"Away: {self.home_away_goals}"

    def __repr__(self) -> str:
        return f"<CupMatch(round='{self.cup_round.name}', match_id={self.match_id})>"


class CupPrizeMoney(Base):
    """Prize money structure for a cup competition."""

    __tablename__ = "cup_prize_money"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key
    competition_id: Mapped[int] = mapped_column(ForeignKey("cup_competitions.id"))

    # Round/Stage
    round_type: Mapped[CupRoundType] = mapped_column(Enum(CupRoundType), nullable=False)

    # Prize amounts
    participation_bonus: Mapped[int] = mapped_column(Integer, default=0)  # For entering round
    win_bonus: Mapped[int] = mapped_column(Integer, default=0)  # For winning match
    progression_bonus: Mapped[int] = mapped_column(Integer, default=0)  # For advancing

    # Group stage specific
    group_win_bonus: Mapped[int] = mapped_column(Integer, default=0)
    group_draw_bonus: Mapped[int] = mapped_column(Integer, default=0)

    # Final position
    final_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<CupPrizeMoney(round='{self.round_type.value}', progression={self.progression_bonus})>"
