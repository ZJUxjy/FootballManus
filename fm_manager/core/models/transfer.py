"""Transfer model definition."""

from datetime import datetime, date
from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, Date, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fm_manager.core.database import Base

if TYPE_CHECKING:
    from fm_manager.core.models.club import Club
    from fm_manager.core.models.player import Player


class TransferStatus(PyEnum):
    """Transfer offer status."""
    PENDING = "pending"  # Offer made, awaiting response
    NEGOTIATING = "negotiating"  # Counter offer made
    ACCEPTED = "accepted"  # Club accepted, now player negotiation
    REJECTED = "rejected"  # Offer rejected
    COMPLETED = "completed"  # Transfer done
    CANCELLED = "cancelled"  # Cancelled by either party
    EXPIRED = "expired"  # Offer timed out


class Transfer(Base):
    """Transfer entity representing a transfer offer/deal."""
    
    __tablename__ = "transfers"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Foreign keys
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    from_club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    to_club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    
    # Offer details
    offered_fee: Mapped[int] = mapped_column(Integer, nullable=False)  # Transfer fee
    is_loan: Mapped[bool] = mapped_column(Boolean, default=False)
    loan_duration_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    loan_wage_split: Mapped[int] = mapped_column(Integer, default=100)  # % paid by loaning club
    
    # Negotiation
    offered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Counter offer
    counter_fee: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus),
        default=TransferStatus.PENDING,
    )
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Contract terms (for accepted offers)
    proposed_wage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    proposed_contract_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    signing_on_fee: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    release_clause: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Player acceptance
    player_accepted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    player_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Completion
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_fee: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Final fee
    
    # Add-ons
    add_ons_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    add_ons_max_value: Mapped[int] = mapped_column(Integer, default=0)
    
    # AI/Manager notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    player: Mapped["Player"] = relationship(foreign_keys=[player_id])
    from_club: Mapped["Club"] = relationship(foreign_keys=[from_club_id])
    to_club: Mapped["Club"] = relationship(foreign_keys=[to_club_id])
    
    @property
    def is_active(self) -> bool:
        """Check if transfer is still active."""
        return self.status in {
            TransferStatus.PENDING,
            TransferStatus.NEGOTIATING,
            TransferStatus.ACCEPTED,
        }
    
    @property
    def total_potential_cost(self) -> int:
        """Calculate maximum potential cost including add-ons."""
        fee = self.actual_fee or self.offered_fee
        return fee + self.add_ons_max_value
    
    def __repr__(self) -> str:
        return (
            f"<Transfer(id={self.id}, "
            f"player={self.player_id}, "
            f"fee={self.offered_fee}, "
            f"status={self.status.value})>"
        )


class TransferWindow(Base):
    """Transfer window periods."""
    
    __tablename__ = "transfer_windows"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Season
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    
    # Window type
    name: Mapped[str] = mapped_column(String(50))  # "Summer", "Winter"
    
    # Dates
    open_date: Mapped[date] = mapped_column(Date)
    close_date: Mapped[date] = mapped_column(Date)
    
    # Status
    is_open: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<TransferWindow(name='{self.name}', open={self.is_open})>"
