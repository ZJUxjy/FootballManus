"""Match model definition."""

from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import (
    Integer, String, Date, DateTime, ForeignKey, Text, Enum, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base


class MatchStatus(PyEnum):
    """Match status."""
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALF_TIME = "half_time"
    FULL_TIME = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class MatchEventType(PyEnum):
    """Types of match events."""
    GOAL = "goal"
    OWN_GOAL = "own_goal"
    PENALTY_GOAL = "penalty_goal"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    SUBSTITUTION = "substitution"
    INJURY = "injury"


class Match(Base):
    """Match entity representing a football match."""
    
    __tablename__ = "matches"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign keys
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    home_club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    away_club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    
    # Match info
    matchday: Mapped[int] = mapped_column(Integer, nullable=False)
    match_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    kickoff_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Venue
    venue: Mapped[str] = mapped_column(String(100), default="")
    attendance: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus),
        default=MatchStatus.SCHEDULED,
    )
    current_minute: Mapped[int] = mapped_column(Integer, default=0)
    
    # Score
    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)
    home_halftime_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_halftime_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Statistics (JSON string for flexibility)
    home_possession: Mapped[int] = mapped_column(Integer, default=50)  # Percentage
    home_shots: Mapped[int] = mapped_column(Integer, default=0)
    home_shots_on_target: Mapped[int] = mapped_column(Integer, default=0)
    home_corners: Mapped[int] = mapped_column(Integer, default=0)
    home_fouls: Mapped[int] = mapped_column(Integer, default=0)
    home_yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    home_red_cards: Mapped[int] = mapped_column(Integer, default=0)
    
    away_shots: Mapped[int] = mapped_column(Integer, default=0)
    away_shots_on_target: Mapped[int] = mapped_column(Integer, default=0)
    away_corners: Mapped[int] = mapped_column(Integer, default=0)
    away_fouls: Mapped[int] = mapped_column(Integer, default=0)
    away_yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    away_red_cards: Mapped[int] = mapped_column(Integer, default=0)
    
    # Events stored as JSON string
    events: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Lineups stored as JSON string
    home_lineup: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_lineup: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Tactics
    home_formation: Mapped[str] = mapped_column(String(10), default="4-3-3")
    away_formation: Mapped[str] = mapped_column(String(10), default="4-3-3")
    home_tactics: Mapped[str | None] = mapped_column(Text, nullable=True)
    away_tactics: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    season: Mapped["Season"] = relationship(back_populates="matches")
    home_club: Mapped["Club"] = relationship(
        foreign_keys=[home_club_id],
        back_populates="home_matches",
    )
    away_club: Mapped["Club"] = relationship(
        foreign_keys=[away_club_id],
        back_populates="away_matches",
    )
    
    @property
    def winner_id(self) -> int | None:
        """Get the winner's club ID, or None for a draw."""
        if self.status != MatchStatus.FULL_TIME:
            return None
        if self.home_score > self.away_score:
            return self.home_club_id
        elif self.away_score > self.home_score:
            return self.away_club_id
        return None
    
    @property
    def is_draw(self) -> bool:
        """Check if match ended in a draw."""
        return (
            self.status == MatchStatus.FULL_TIME
            and self.home_score == self.away_score
        )
    
    @property
    def score_string(self) -> str:
        """Get score as string (e.g., '2-1')."""
        return f"{self.home_score}-{self.away_score}"
    
    def __repr__(self) -> str:
        return (
            f"<Match(id={self.id}, "
            f"{self.home_club.short_name if hasattr(self, 'home_club') else '?'} "
            f"{self.home_score}-{self.away_score} "
            f"{self.away_club.short_name if hasattr(self, 'away_club') else '?'}, "
            f"status={self.status.value})>"
        )
