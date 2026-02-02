"""Player model definition."""

from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Integer, String, Float, Date, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base


class Position(PyEnum):
    """Player positions on the field."""
    GK = "GK"  # Goalkeeper
    CB = "CB"  # Center Back
    LB = "LB"  # Left Back
    RB = "RB"  # Right Back
    LWB = "LWB"  # Left Wing Back
    RWB = "RWB"  # Right Wing Back
    CDM = "CDM"  # Central Defensive Midfielder
    CM = "CM"  # Central Midfielder
    LM = "LM"  # Left Midfielder
    RM = "RM"  # Right Midfielder
    CAM = "CAM"  # Central Attacking Midfielder
    LW = "LW"  # Left Winger
    RW = "RW"  # Right Winger
    CF = "CF"  # Center Forward
    ST = "ST"  # Striker


class WorkRate(PyEnum):
    """Player work rate."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Foot(PyEnum):
    """Preferred foot."""
    LEFT = "Left"
    RIGHT = "Right"
    BOTH = "Both"


class Player(Base):
    """Player entity representing a football player."""
    
    __tablename__ = "players"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Basic info
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str] = mapped_column(String(100), default="Unknown")
    
    # Position
    position: Mapped[Position] = mapped_column(Enum(Position), nullable=False)
    secondary_position: Mapped[Position | None] = mapped_column(
        Enum(Position), nullable=True
    )
    
    # Physical attributes
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)  # cm
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)  # kg
    preferred_foot: Mapped[Foot] = mapped_column(Enum(Foot), default=Foot.RIGHT)
    
    # Technical attributes (0-100 scale)
    pace: Mapped[int] = mapped_column(Integer, default=50)
    acceleration: Mapped[int] = mapped_column(Integer, default=50)
    stamina: Mapped[int] = mapped_column(Integer, default=50)
    strength: Mapped[int] = mapped_column(Integer, default=50)
    
    # Technical
    shooting: Mapped[int] = mapped_column(Integer, default=50)
    passing: Mapped[int] = mapped_column(Integer, default=50)
    dribbling: Mapped[int] = mapped_column(Integer, default=50)
    crossing: Mapped[int] = mapped_column(Integer, default=50)
    first_touch: Mapped[int] = mapped_column(Integer, default=50)
    
    # Mental/Defensive
    tackling: Mapped[int] = mapped_column(Integer, default=50)
    marking: Mapped[int] = mapped_column(Integer, default=50)
    positioning: Mapped[int] = mapped_column(Integer, default=50)
    vision: Mapped[int] = mapped_column(Integer, default=50)
    decisions: Mapped[int] = mapped_column(Integer, default=50)
    
    # Goalkeeping (for GKs)
    reflexes: Mapped[int] = mapped_column(Integer, default=50)
    handling: Mapped[int] = mapped_column(Integer, default=50)
    kicking: Mapped[int] = mapped_column(Integer, default=50)
    one_on_one: Mapped[int] = mapped_column(Integer, default=50)
    
    # Mental attributes
    work_rate: Mapped[WorkRate] = mapped_column(Enum(WorkRate), default=WorkRate.MEDIUM)
    determination: Mapped[int] = mapped_column(Integer, default=50)
    leadership: Mapped[int] = mapped_column(Integer, default=50)
    teamwork: Mapped[int] = mapped_column(Integer, default=50)
    aggression: Mapped[int] = mapped_column(Integer, default=50)
    
    # Overall ratings
    current_ability: Mapped[int] = mapped_column(Integer, default=50)
    potential_ability: Mapped[int] = mapped_column(Integer, default=50)
    
    # Contract info
    club_id: Mapped[int | None] = mapped_column(
        ForeignKey("clubs.id"), nullable=True
    )
    contract_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary: Mapped[int] = mapped_column(Integer, default=0)  # Weekly wage
    market_value: Mapped[int] = mapped_column(Integer, default=0)
    release_clause: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Status
    fitness: Mapped[int] = mapped_column(Integer, default=100)  # 0-100
    morale: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    form: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    
    # Statistics (current season)
    appearances: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    
    # Career stats
    career_goals: Mapped[int] = mapped_column(Integer, default=0)
    career_appearances: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    club: Mapped["Club"] = relationship(back_populates="players")
    
    @property
    def full_name(self) -> str:
        """Get player's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int | None:
        """Calculate player age from birth date."""
        if self.birth_date is None:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def outfield_attributes(self) -> dict[str, int]:
        """Get outfield player attributes."""
        return {
            "pace": self.pace,
            "acceleration": self.acceleration,
            "stamina": self.stamina,
            "strength": self.strength,
            "shooting": self.shooting,
            "passing": self.passing,
            "dribbling": self.dribbling,
            "crossing": self.crossing,
            "first_touch": self.first_touch,
            "tackling": self.tackling,
            "marking": self.marking,
            "positioning": self.positioning,
            "vision": self.vision,
            "decisions": self.decisions,
        }
    
    @property
    def goalkeeper_attributes(self) -> dict[str, int]:
        """Get goalkeeper attributes."""
        return {
            "reflexes": self.reflexes,
            "handling": self.handling,
            "kicking": self.kicking,
            "one_on_one": self.one_on_one,
            "positioning": self.positioning,
            "vision": self.vision,
        }
    
    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name='{self.full_name}', pos={self.position.value})>"
