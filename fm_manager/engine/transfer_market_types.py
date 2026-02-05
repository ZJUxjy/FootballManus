"""Transfer market data structures and types.

This module defines all data structures used by the transfer market system.
All classes are designed to work with in-memory data from cleaned_data_loader.
"""

from typing import Optional, List, Dict, Tuple, Callable, Any
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum as PyEnum


class OfferType(PyEnum):
    """Types of transfer offers."""

    BUY = "buy"
    LOAN = "loan"


class ListingReason(PyEnum):
    """Reasons for listing a player."""

    SURPLUS = "surplus"
    DEADWOOD = "deadwood"
    FINANCIAL = "financial"
    SQUAD_BALANCE = "squad_balance"


class NegotiationRound(PyEnum):
    """Negotiation round stages."""

    INITIAL = "initial"
    COUNTER = "counter"
    FINAL = "final"


class NegotiationStatus(PyEnum):
    """Status of an ongoing negotiation."""

    ONGOING = "ongoing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


@dataclass
class PlayerListing:
    """A player listed for transfer by their club."""

    player_id: int
    club_id: int
    asking_price: int
    reason: ListingReason
    listed_at: date = field(default_factory=date.today)
    deadline: Optional[date] = None
    is_negotiable: bool = True


@dataclass
class TransferOffer:
    """A transfer offer from one club to another."""

    offer_id: str
    player_id: int
    from_club_id: int
    to_club_id: int
    offer_type: OfferType = OfferType.BUY
    fee: int = 0
    proposed_wage: Optional[int] = None
    proposed_contract_years: int = 3
    signing_on_fee: int = 0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    counter_fee: Optional[int] = None
    notes: str = ""
    negotiation_round: int = 1
    max_rounds: int = 3

    def is_active(self) -> bool:
        return self.status in ["pending", "negotiating", "countered"]


@dataclass
class TransferNegotiation:
    """Track an ongoing transfer negotiation."""

    negotiation_id: str
    player_id: int
    buying_club_id: int
    selling_club_id: int
    status: NegotiationStatus = NegotiationStatus.ONGOING
    current_round: NegotiationRound = NegotiationRound.INITIAL
    rounds_completed: int = 0
    max_rounds: int = 3
    offers: List[Dict] = field(default_factory=list)
    started_at: date = field(default_factory=date.today)
    last_updated: date = field(default_factory=date.today)
    expires_at: Optional[date] = None
    final_fee: Optional[int] = None

    def is_expired(self) -> bool:
        if self.expires_at:
            return date.today() >= self.expires_at
        return False

    def add_offer(self, offer_type: str, fee: int, from_club_id: int) -> None:
        self.offers.append(
            {
                "round": self.current_round.value,
                "type": offer_type,
                "fee": fee,
                "from_club": from_club_id,
                "timestamp": date.today(),
            }
        )
        self.last_updated = date.today()

    def advance_round(self) -> None:
        if self.current_round == NegotiationRound.INITIAL:
            self.current_round = NegotiationRound.COUNTER
        elif self.current_round == NegotiationRound.COUNTER:
            self.current_round = NegotiationRound.FINAL
        self.rounds_completed += 1
        self.last_updated = date.today()


@dataclass
class TransferResponse:
    """Response from AI club to transfer offer."""

    action: str
    new_fee: Optional[int] = None
    reason: str = ""
    counter_message: str = ""


@dataclass
class TransferAction:
    """An AI transfer action to be executed."""

    action_type: str
    club_id: int
    player_id: Optional[int] = None
    fee: Optional[int] = None
    reasoning: str = ""


@dataclass
class TransferUpdate:
    """Update to be broadcast to game."""

    update_type: str
    negotiation_id: str
    from_club_id: int
    to_club_id: int
    player_id: int
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OfferResult:
    """Result of making a transfer offer."""

    success: bool
    status: str
    message: str
    transfer_id: Optional[str] = None
    negotiation_started: bool = False
    rejection_reason: Optional[str] = None
    window_open: bool = True
    budget_remaining: int = 0


@dataclass
class SquadNeeds:
    """AI analysis of squad needs."""

    priority_positions: List[str] = field(default_factory=list)
    position_count: Dict[str, int] = field(default_factory=dict)
    budget_available: int = 0
    sell_targets: List[int] = field(default_factory=list)
    buy_targets: List[int] = field(default_factory=list)


@dataclass
class PlayerTarget:
    """An AI-identified transfer target."""

    player_id: int
    fit_score: float = 0.0
    estimated_value: int = 0
    max_offer: int = 0
    reasoning: str = ""


@dataclass
class CompletedTransfer:
    """Record of a completed transfer."""

    transfer_id: str
    player_id: int
    player_name: str
    from_club_id: int
    from_club_name: str
    to_club_id: int
    to_club_name: str
    fee: int
    completed_at: date = field(default_factory=date.today)
    offer_type: str = "buy"
