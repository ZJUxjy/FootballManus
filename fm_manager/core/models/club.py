"""Club model definition."""

from datetime import date
from enum import Enum as PyEnum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, Date, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.league import League
    from fm_manager.core.models.player import Player
    from fm_manager.core.models.match import Match


class ClubReputation(PyEnum):
    """Club reputation levels."""
    WORLD_CLASS = 5  # Real Madrid, Man City, etc.
    ELITE = 4  # Top clubs in big leagues
    ESTABLISHED = 3  # Regular top division clubs
    RESPECTABLE = 2  # Mid-table/lower division
    UNKNOWN = 1  # Small/new clubs


class Club(Base):
    """Club entity representing a football club."""
    
    __tablename__ = "clubs"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Location
    city: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    
    # Stadium
    stadium_name: Mapped[str] = mapped_column(String(100), default="")
    stadium_capacity: Mapped[int] = mapped_column(Integer, default=0)
    
    # Reputation (0-10000)
    reputation: Mapped[int] = mapped_column(Integer, default=1000)
    reputation_level: Mapped[ClubReputation] = mapped_column(
        Enum(ClubReputation), default=ClubReputation.RESPECTABLE
    )
    
    # Colors
    primary_color: Mapped[str] = mapped_column(String(7), default="#FF0000")
    secondary_color: Mapped[str] = mapped_column(String(7), default="#FFFFFF")
    
    # League
    league_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leagues.id"), nullable=True
    )
    
    # Finances
    balance: Mapped[int] = mapped_column(Integer, default=0)  # Club bank balance
    transfer_budget: Mapped[int] = mapped_column(Integer, default=0)
    wage_budget: Mapped[int] = mapped_column(Integer, default=0)
    weekly_wage_bill: Mapped[int] = mapped_column(Integer, default=0)
    
    # Income multipliers
    ticket_price: Mapped[int] = mapped_column(Integer, default=50)
    average_attendance: Mapped[int] = mapped_column(Integer, default=0)
    commercial_income: Mapped[int] = mapped_column(Integer, default=0)
    
    # Youth setup
    youth_facility_level: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    youth_academy_country: Mapped[str] = mapped_column(String(100), default="")
    
    # Training
    training_facility_level: Mapped[int] = mapped_column(Integer, default=50)
    
    # Ownership
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_ai_controlled: Mapped[bool] = mapped_column(default=True)

    # AI Configuration (JSON string)
    llm_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Season objectives
    season_objective: Mapped[str] = mapped_column(String(50), default="mid_table")
    # win_title, champions_league, europa_league, top_half, avoid_relegation
    
    # Relationships
    league: Mapped["League"] = relationship(back_populates="clubs")
    players: Mapped[List["Player"]] = relationship(
        back_populates="club",
        lazy="dynamic",
    )
    home_matches: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.home_club_id",
        back_populates="home_club",
        lazy="dynamic",
    )
    away_matches: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.away_club_id",
        back_populates="away_club",
        lazy="dynamic",
    )
    
    # Stats
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    matches_won: Mapped[int] = mapped_column(Integer, default=0)
    matches_drawn: Mapped[int] = mapped_column(Integer, default=0)
    matches_lost: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    league_position: Mapped[int] = mapped_column(Integer, default=0)
    
    @property
    def goal_difference(self) -> int:
        """Calculate goal difference."""
        return self.goals_for - self.goals_against
    
    @property
    def available_wage_budget(self) -> int:
        """Calculate remaining wage budget."""
        return self.wage_budget - self.weekly_wage_bill
    
    @property
    def squad_size(self) -> int:
        """Get number of players in squad."""
        # This requires the session to be active
        return len(self.players) if self.players else 0
    
    def calculate_matchday_income(self, attendance_percent: float = 0.9) -> int:
        """Calculate income from a home match."""
        attendance = int(self.stadium_capacity * attendance_percent)
        return attendance * self.ticket_price
    
    def __repr__(self) -> str:
        return f"<Club(id={self.id}, name='{self.name}', rep={self.reputation})>"
