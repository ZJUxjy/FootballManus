"""Sponsorship model definition."""

from dataclasses import dataclass
from datetime import date
from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING, Dict, Any

from sqlalchemy import ForeignKey, Integer, String, Float, Date, Enum, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.club import Club


class SponsorLevel(PyEnum):
    """Sponsor level based on investment size and global reach."""
    GLOBAL = 5      # 100M-200M EUR/year - Top global brands (top clubs)
    PREMIUM = 4     # 50M-100M EUR/year - Major global brands (elite clubs)
    MAJOR = 3       # 20M-50M EUR/year - National/international brands (top league)
    REGIONAL = 2    # 5M-20M EUR/year - Regional brands (lower leagues)
    LOCAL = 1       # 1M-5M EUR/year - Local businesses (low-level clubs)


class SponsorType(PyEnum):
    """Type of sponsorship deal."""
    MAIN_SPONSOR = "main_sponsor"           # Shirt front sponsor
    KIT_SPONSOR = "kit_sponsor"             # Kit manufacturer
    STADIUM_NAMING = "stadium_naming"       # Stadium naming rights
    SLEEVE_SPONSOR = "sleeve_sponsor"       # Sleeve sponsor (secondary)
    TRAINING_KIT = "training_kit"           # Training kit sponsor
    OFFICIAL_PARTNER = "official_partner"   # Various official partnerships


class ContractStatus(PyEnum):
    """Status of a sponsorship contract."""
    ACTIVE = "active"
    EXPIRED = "expired"
    NEGOTIATING = "negotiating"
    TERMINATED = "terminated"
    PENDING = "pending"


class Sponsor(Base):
    """Sponsor entity representing a commercial partner."""
    
    __tablename__ = "sponsors"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="")
    
    # Sponsor characteristics
    level: Mapped[SponsorLevel] = mapped_column(
        Enum(SponsorLevel), default=SponsorLevel.LOCAL
    )
    sponsor_type: Mapped[SponsorType] = mapped_column(
        Enum(SponsorType), default=SponsorType.OFFICIAL_PARTNER
    )
    
    # Financial details
    base_annual_payment: Mapped[int] = mapped_column(Integer, default=0)
    performance_bonus_rate: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # Bonus as percentage of base payment
    max_annual_bonus: Mapped[int] = mapped_column(Integer, default=0)
    
    # Contract dates
    contract_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Contract status
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.PENDING
    )
    
    # Relationship with club
    club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id"), nullable=True
    )
    club: Mapped["Club"] = relationship("Club")
    
    # Sponsor reputation (0-100) - affects which clubs they approach
    reputation: Mapped[int] = mapped_column(Integer, default=50)
    
    # Requirements and preferences
    min_club_reputation: Mapped[int] = mapped_column(Integer, default=1000)
    preferred_leagues: Mapped[str] = mapped_column(
        Text, default=""
    )  # Comma-separated league names
    
    # Negotiation history
    negotiation_count: Mapped[int] = mapped_column(Integer, default=0)
    last_negotiation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Performance tracking for bonuses
    matches_sponsored: Mapped[int] = mapped_column(Integer, default=0)
    goals_scored_in_sponsored_matches: Mapped[int] = mapped_column(Integer, default=0)
    wins_in_sponsored_matches: Mapped[int] = mapped_column(Integer, default=0)
    
    # Auto-renewal
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=False)
    
    @property
    def is_active(self) -> bool:
        """Check if sponsor contract is currently active."""
        if self.status != ContractStatus.ACTIVE:
            return False
        if not self.contract_start or not self.contract_end:
            return False
        today = date.today()
        return self.contract_start <= today <= self.contract_end
    
    @property
    def contract_remaining_days(self) -> int:
        """Get remaining days in current contract."""
        if not self.contract_end:
            return 0
        today = date.today()
        if today > self.contract_end:
            return 0
        return (self.contract_end - today).days
    
    @property
    def weekly_payment(self) -> int:
        """Calculate weekly payment amount."""
        return self.base_annual_payment // 52
    
    @property
    def can_renew(self) -> bool:
        """Check if contract can be renewed (within 6 months of expiry)."""
        if not self.contract_end:
            return False
        if self.status not in [ContractStatus.ACTIVE, ContractStatus.EXPIRED]:
            return False
        days_remaining = self.contract_remaining_days
        return days_remaining <= 180 or days_remaining == 0
    
    def calculate_performance_bonus(
        self, 
        matches_played: int = 0,
        wins: int = 0,
        goals_scored: int = 0
    ) -> int:
        """Calculate performance bonus based on metrics.
        
        Args:
            matches_played: Number of matches in period
            wins: Number of wins in period
            goals_scored: Number of goals scored in period
            
        Returns:
            Bonus amount in EUR
        """
        if not self.performance_bonus_rate or not self.base_annual_payment:
            return 0
        
        # Calculate performance score (simplified)
        win_rate = wins / matches_played if matches_played > 0 else 0
        
        # Performance multiplier based on win rate
        # 0.7+ win rate = 100% bonus
        # 0.5-0.7 = 75% bonus
        # 0.3-0.5 = 50% bonus
        # Below 0.3 = 25% bonus
        if win_rate >= 0.7:
            performance_multiplier = 1.0
        elif win_rate >= 0.5:
            performance_multiplier = 0.75
        elif win_rate >= 0.3:
            performance_multiplier = 0.5
        else:
            performance_multiplier = 0.25
        
        bonus = int(self.base_annual_payment * self.performance_bonus_rate * performance_multiplier)
        return min(bonus, self.max_annual_bonus)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sponsor to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "country": self.country,
            "level": self.level.name if self.level else None,
            "sponsor_type": self.sponsor_type.value if self.sponsor_type else None,
            "base_annual_payment": self.base_annual_payment,
            "weekly_payment": self.weekly_payment,
            "performance_bonus_rate": self.performance_bonus_rate,
            "max_annual_bonus": self.max_annual_bonus,
            "contract_start": self.contract_start.isoformat() if self.contract_start else None,
            "contract_end": self.contract_end.isoformat() if self.contract_end else None,
            "status": self.status.value if self.status else None,
            "is_active": self.is_active,
            "contract_remaining_days": self.contract_remaining_days,
            "club_id": self.club_id,
            "reputation": self.reputation,
            "can_renew": self.can_renew,
        }
    
    def __repr__(self) -> str:
        return f"<Sponsor(id={self.id}, name='{self.name}', level={self.level.name}, club_id={self.club_id})>"


@dataclass
class SponsorshipDeal:
    """Data class representing a sponsorship deal proposal or active deal."""
    
    sponsor_id: int
    sponsor_name: str
    sponsor_level: SponsorLevel
    sponsor_type: SponsorType
    club_id: int
    club_name: str
    
    # Financial terms
    annual_payment: int
    contract_length_years: int
    performance_bonus_rate: float = 0.0
    max_annual_bonus: int = 0
    
    # Negotiation
    initial_offer: int = 0
    current_offer: int = 0
    sponsor_min_acceptable: int = 0
    
    # Status
    status: ContractStatus = ContractStatus.NEGOTIATING
    negotiation_round: int = 0
    
    # Dates
    proposed_start: Optional[date] = None
    proposed_end: Optional[date] = None
    
    # Deal specifics
    exclusivity: bool = False  # Whether sponsor has exclusive rights
    activation_requirements: list = None  # Marketing obligations
    
    # Calculated fields
    @property
    def total_contract_value(self) -> int:
        """Calculate total value of the contract."""
        total_base = self.annual_payment * self.contract_length_years
        max_bonuses = self.max_annual_bonus * self.contract_length_years
        return total_base + max_bonuses
    
    @property
    def weekly_value(self) -> int:
        """Calculate weekly payment."""
        return self.annual_payment // 52
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert deal to dictionary."""
        return {
            "sponsor_id": self.sponsor_id,
            "sponsor_name": self.sponsor_name,
            "sponsor_level": self.sponsor_level.name if self.sponsor_level else None,
            "sponsor_type": self.sponsor_type.value if self.sponsor_type else None,
            "club_id": self.club_id,
            "club_name": self.club_name,
            "annual_payment": self.annual_payment,
            "contract_length_years": self.contract_length_years,
            "total_contract_value": self.total_contract_value,
            "weekly_value": self.weekly_value,
            "performance_bonus_rate": self.performance_bonus_rate,
            "max_annual_bonus": self.max_annual_bonus,
            "status": self.status.value if self.status else None,
            "negotiation_round": self.negotiation_round,
            "proposed_start": self.proposed_start.isoformat() if self.proposed_start else None,
            "proposed_end": self.proposed_end.isoformat() if self.proposed_end else None,
            "exclusivity": self.exclusivity,
        }


# Sponsor payment ranges by level (annual in EUR)
SPONSOR_PAYMENT_RANGES = {
    SponsorLevel.GLOBAL: (100_000_000, 200_000_000),
    SponsorLevel.PREMIUM: (50_000_000, 100_000_000),
    SponsorLevel.MAJOR: (20_000_000, 50_000_000),
    SponsorLevel.REGIONAL: (5_000_000, 20_000_000),
    SponsorLevel.LOCAL: (1_000_000, 5_000_000),
}

# Minimum club reputation required for each sponsor level
SPONSOR_LEVEL_REPUTATION_REQUIREMENTS = {
    SponsorLevel.GLOBAL: 8000,
    SponsorLevel.PREMIUM: 6000,
    SponsorLevel.MAJOR: 4000,
    SponsorLevel.REGIONAL: 2000,
    SponsorLevel.LOCAL: 500,
}

# Sponsor type payment multipliers (relative to base)
SPONSOR_TYPE_MULTIPLIERS = {
    SponsorType.MAIN_SPONSOR: 1.0,
    SponsorType.KIT_SPONSOR: 0.8,
    SponsorType.STADIUM_NAMING: 1.5,
    SponsorType.SLEEVE_SPONSOR: 0.2,
    SponsorType.TRAINING_KIT: 0.3,
    SponsorType.OFFICIAL_PARTNER: 0.1,
}
