"""Staff model definition."""

from dataclasses import dataclass
from datetime import date
from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Float, Date, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.club import Club


class StaffRole(PyEnum):
    """Staff roles in a football club."""
    HEAD_COACH = "head_coach"
    ASSISTANT_MANAGER = "assistant_manager"
    GOALKEEPER_COACH = "goalkeeper_coach"
    FITNESS_COACH = "fitness_coach"
    CHIEF_SCOUT = "chief_scout"
    HEAD_PHYSIO = "head_physio"


@dataclass
class StaffEffect:
    """Effect of staff on various aspects of club operations.
    
    Values are multipliers (1.0 = baseline, 1.1 = +10%, etc.)
    """
    # Player development
    player_development: float = 1.0
    match_preparation: float = 1.0
    
    # Training
    goalkeeper_training: float = 1.0
    fitness_training: float = 1.0
    
    # Medical/Injury
    injury_prevention: float = 1.0
    injury_recovery: float = 1.0
    
    # Scouting
    scouting_quality: float = 1.0
    scouting_range: float = 1.0
    
    # Morale
    team_morale: float = 1.0
    
    def combine(self, other: "StaffEffect") -> "StaffEffect":
        """Combine effects by multiplying values."""
        return StaffEffect(
            player_development=self.player_development * other.player_development,
            match_preparation=self.match_preparation * other.match_preparation,
            goalkeeper_training=self.goalkeeper_training * other.goalkeeper_training,
            fitness_training=self.fitness_training * other.fitness_training,
            injury_prevention=self.injury_prevention * other.injury_prevention,
            injury_recovery=self.injury_recovery * other.injury_recovery,
            scouting_quality=self.scouting_quality * other.scouting_quality,
            scouting_range=self.scouting_range * other.scouting_range,
            team_morale=self.team_morale * other.team_morale,
        )


class Staff(Base):
    """Staff entity representing non-player personnel in a football club."""
    
    __tablename__ = "staff"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Basic info
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    nationality: Mapped[str] = mapped_column(String(100), default="Unknown")
    
    # Role
    role: Mapped[StaffRole] = mapped_column(Enum(StaffRole), nullable=False)
    
    # Ability (0-100 scale)
    ability: Mapped[int] = mapped_column(Integer, default=50)
    
    # Reputation (0-10000 scale)
    reputation: Mapped[int] = mapped_column(Integer, default=1000)
    
    # Contract info
    club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id"), nullable=True
    )
    contract_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    salary: Mapped[int] = mapped_column(Integer, default=1000)  # Weekly wage
    
    # Contract clauses
    has_release_clause: Mapped[bool] = mapped_column(default=False)
    release_clause_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    is_hired: Mapped[bool] = mapped_column(default=False)
    
    # Relationships
    club: Mapped["Club"] = relationship(back_populates="staff")
    
    @property
    def full_name(self) -> str:
        """Get staff's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> Optional[int]:
        """Calculate staff age from birth date."""
        if self.birth_date is None:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def ability_rating(self) -> str:
        """Get ability as a rating string."""
        if self.ability >= 90:
            return "World Class"
        elif self.ability >= 80:
            return "Excellent"
        elif self.ability >= 70:
            return "Good"
        elif self.ability >= 60:
            return "Average"
        elif self.ability >= 50:
            return "Below Average"
        else:
            return "Poor"
    
    @property
    def contract_years_remaining(self) -> float:
        """Calculate remaining contract years."""
        if self.contract_until is None:
            return 0.0
        days_remaining = (self.contract_until - date.today()).days
        return max(0.0, days_remaining / 365.25)
    
    def calculate_effect(self) -> StaffEffect:
        """Calculate the effect of this staff member based on their ability."""
        # Base multiplier calculation
        # Ability 50 = 1.0 (baseline)
        # Ability 100 = 1.5 (max bonus)
        base_multiplier = 1.0 + (self.ability - 50) / 100
        
        # Role-specific effect calculation
        if self.role == StaffRole.HEAD_COACH:
            return StaffEffect(
                player_development=base_multiplier,
                match_preparation=base_multiplier,
                team_morale=base_multiplier * 0.8 + 0.2,
            )
        elif self.role == StaffRole.ASSISTANT_MANAGER:
            return StaffEffect(
                match_preparation=base_multiplier * 0.9 + 0.1,
                team_morale=base_multiplier * 0.8 + 0.2,
            )
        elif self.role == StaffRole.GOALKEEPER_COACH:
            return StaffEffect(
                goalkeeper_training=base_multiplier * 1.1 + 0.1,
            )
        elif self.role == StaffRole.FITNESS_COACH:
            return StaffEffect(
                fitness_training=base_multiplier,
                injury_prevention=base_multiplier * 0.8 + 0.2,
            )
        elif self.role == StaffRole.CHIEF_SCOUT:
            return StaffEffect(
                scouting_quality=base_multiplier,
                scouting_range=base_multiplier * 0.7 + 0.3,
            )
        elif self.role == StaffRole.HEAD_PHYSIO:
            return StaffEffect(
                injury_recovery=base_multiplier,
                injury_prevention=base_multiplier * 0.7 + 0.3,
            )
        else:
            return StaffEffect()
    
    def __repr__(self) -> str:
        return f"<Staff(id={self.id}, name='{self.full_name}', role={self.role.value})>"
