"""Enhanced Transfer Engine with multi-round negotiations and transfer history.

Improvements over base transfer_engine:
- Multi-round negotiation system
- Transfer history tracking
- Agent system for players
- Better AI decision making for clubs
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fm_manager.core.models import Club, Player, Transfer, TransferStatus, TransferWindow
from fm_manager.engine.transfer_engine import (
    TransferOffer, ContractOffer, TransferWindowType, OfferType,
    TransferEngine, PlayerValuationCalculator, ContractNegotiator
)


class NegotiationRound(Enum):
    """Negotiation round stages."""
    INITIAL = "initial"           # First offer
    COUNTER = "counter"            # Selling club counter-offer
    FINAL = "final"                # Last offer before deadline


class NegotiationStatus(Enum):
    """Status of an ongoing negotiation."""
    ONGOING = "ongoing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


@dataclass
class TransferNegotiation:
    """Track an ongoing transfer negotiation."""
    negotiation_id: str
    player_id: int
    buying_club_id: int
    selling_club_id: int

    # Negotiation state
    status: NegotiationStatus = NegotiationStatus.ONGOING
    current_round: NegotiationRound = NegotiationRound.INITIAL
    rounds_completed: int = 0
    max_rounds: int = 3

    # Offers history
    offers: List[Dict] = field(default_factory=list)

    # Timeline
    started_at: date = field(default_factory=date.today)
    last_updated: date = field(default_factory=date.today)
    expires_at: Optional[date] = None

    def is_expired(self) -> bool:
        """Check if negotiation has expired."""
        if self.expires_at:
            return date.today() >= self.expires_at
        return False

    def add_offer(self, offer_type: str, fee: int, from_club_id: int, to_club_id: int) -> None:
        """Add an offer to the negotiation history."""
        self.offers.append({
            "round": self.current_round.value,
            "type": offer_type,
            "fee": fee,
            "from_club": from_club_id,
            "to_club": to_club_id,
            "timestamp": date.today(),
        })
        self.last_updated = date.today()

    def advance_round(self) -> None:
        """Advance to next negotiation round."""
        if self.current_round == NegotiationRound.INITIAL:
            self.current_round = NegotiationRound.COUNTER
        elif self.current_round == NegotiationRound.COUNTER:
            self.current_round = NegotiationRound.FINAL
        self.rounds_completed += 1
        self.last_updated = date.today()


@dataclass
class TransferHistory:
    """Track completed transfers."""
    transfers: List[Dict] = field(default_factory=list)

    def add_transfer(self, transfer: Transfer) -> None:
        """Add a completed transfer to history."""
        self.transfers.append({
            "player_id": transfer.player_id,
            "from_club_id": transfer.from_club_id,
            "to_club_id": transfer.to_club_id,
            "fee": transfer.fee,
            "offer_type": transfer.offer_type.value,
            "completed_at": transfer.responded_at or date.today(),
        })


@dataclass
class PlayerAgent:
    """Represents a player's agent handling their contract."""

    # Agent personality
    aggressiveness: float = 0.5  # 0 = passive, 1 = very aggressive
    loyalty_to_player: float = 0.7  # How much they prioritize player
    greed: float = 0.5  # How much they want higher fees

    # Agent preferences
    prefers_bonuses: bool = True
    prefers_clauses: bool = True
    accepts_loans: bool = True

    def __post_init__(self):
        """Initialize random agent traits if not set."""
        if self.aggressiveness == 0.5:
            self.aggressiveness = random.uniform(0.3, 0.8)
        if self.loyalty_to_player == 0.7:
            self.loyalty_to_player = random.uniform(0.5, 0.9)
        if self.greed == 0.5:
            self.greed = random.uniform(0.3, 0.8)


@dataclass
class AgentContractPreference:
    """Agent's contract negotiation preferences."""

    # Financial priorities
    prioritize_wage: float = 0.6
    prioritize_signing_bonus: float = 0.4
    prioritize_contract_length: float = 0.3
    prioritize_clauses: float = 0.2

    # Contract terms preferences
    preferred_length_years: int = 3
    minimum_release_clause: int = 0  # As percentage of player value
    prefer_buy_option: bool = False
    prefer_loan_obligation: bool = False


class EnhancedTransferEngine:
    """Enhanced transfer engine with advanced features."""

    def __init__(self):
        # Use base engine for core functionality
        self.base_engine = TransferEngine()

        # Track ongoing negotiations
        self.negotiations: Dict[str, TransferNegotiation] = {}

        # Transfer history
        self.history = TransferHistory()

        # Agent registry (player_id -> agent)
        self.agents: Dict[int, PlayerAgent] = {}

    def get_or_create_agent(self, player_id: int) -> PlayerAgent:
        """Get or create an agent for a player."""
        if player_id not in self.agents:
            self.agents[player_id] = PlayerAgent()
        return self.agents[player_id]

    def create_negotiation(
        self,
        player: Player,
        buying_club: Club,
        selling_club: Club,
        initial_offer: TransferOffer,
    ) -> TransferNegotiation:
        """Start a new transfer negotiation."""
        negotiation_id = f"neg_{player.id}_{buying_club.id}_{selling_club.id}_{date.today().strftime('%Y%m%d')}"

        # Calculate expiry (7 days from start)
        expires_at = date.today() + timedelta(days=7)

        negotiation = TransferNegotiation(
            negotiation_id=negotiation_id,
            player_id=player.id,
            buying_club_id=buying_club.id,
            selling_club_id=selling_club.id,
            current_round=NegotiationRound.INITIAL,
            max_rounds=3,
            started_at=date.today(),
            expires_at=expires_at,
        )

        # Add initial offer
        negotiation.add_offer(
            offer_type="initial",
            fee=initial_offer.fee,
            from_club_id=initial_offer.from_club_id,
            to_club_id=initial_offer.to_club_id,
        )

        self.negotiations[negotiation_id] = negotiation
        return negotiation

    def process_negotiation_turn(
        self,
        negotiation_id: str,
        session: AsyncSession,
        buying_club: Club,
        selling_club: Club,
        player: Player,
    ) -> Tuple[bool, Optional[str]]:
        """Process one turn of a negotiation.

        Returns:
            (completed, message) - True if negotiation is done
        """
        negotiation = self.negotiations.get(negotiation_id)
        if not negotiation:
            return False, "Negotiation not found"

        # Check if expired
        if negotiation.is_expired():
            negotiation.status = NegotiationStatus.EXPIRED
            return True, "Negotiation expired"

        # Get agent
        agent = self.get_or_create_agent(player.id)

        # Get current offer
        current_offer = negotiation.offers[-1] if negotiation.offers else None
        if not current_offer:
            return False, "No current offer"

        # Get player valuation
        player_value = self.base_engine.valuation_calculator.calculate_value(player)

        # Determine next action based on negotiation round
        if negotiation.current_round == NegotiationRound.INITIAL:
            # Initial offer - check if selling club accepts
            evaluation = self.base_engine.evaluate_transfer_offer(
                current_offer, player, selling_club, buying_club
            )

            if evaluation["decision"] == "accept":
                negotiation.status = NegotiationStatus.ACCEPTED
                negotiation.add_offer("accepted", current_offer.fee,
                                  current_offer.from_club_id, current_offer.to_club_id)
                self.history.add_transfer(self._create_transfer_record(
                    player, current_offer, NegotiationStatus.ACCEPTED
                ))
                return True, "Offer accepted"
            elif evaluation["decision"] == "counter":
                # Create counter offer
                counter_fee = evaluation.get("counter_fee", int(player_value * 1.2))
                counter_offer = self.base_engine.create_transfer_offer(
                    player, buying_club, selling_club, counter_fee, current_offer.offer_type
                )
                negotiation.add_offer("counter", counter_offer.fee,
                                  buying_club.id, selling_club.id)
                negotiation.advance_round()
                return False, f"Counter-offered: €{counter_fee:,}"
            else:
                negotiation.status = NegotiationStatus.REJECTED
                return True, "Offer rejected"

        elif negotiation.current_round == NegotiationRound.COUNTER:
            # Counter offer - check if buying club accepts
            # Simulate decision based on club needs and agent

            # Calculate attractiveness of current offer
            offer_ratio = current_offer.fee / player_value

            # Agent wants higher fees, but doesn't want to kill deal
            # Agent and club factors
            agent_factor = agent.greed
            club_need_factor = self._calculate_club_urgency(buying_club, player)

            # Decision probability
            acceptance_prob = offer_ratio * agent_factor * club_need_factor

            if random.random() < acceptance_prob:
                # Accept counter
                negotiation.status = NegotiationStatus.ACCEPTED
                negotiation.add_offer("accepted_counter", current_offer.fee,
                                  current_offer.from_club_id, current_offer.to_club_id)
                self.history.add_transfer(self._create_transfer_record(
                    player, current_offer, NegotiationStatus.ACCEPTED
                ))
                return True, "Counter offer accepted"
            else:
                # Make new counter offer (or withdraw)
                new_fee = int(current_offer.fee * 1.05)  # 5% increase

                # Limit to max rounds
                if negotiation.rounds_completed >= negotiation.max_rounds:
                    negotiation.status = NegotiationStatus.EXPIRED
                    return True, "Negotiation reached max rounds"

                # Create counter
                counter_offer = self.base_engine.create_transfer_offer(
                    player, selling_club, buying_club, new_fee, current_offer.offer_type
                )
                negotiation.add_offer("counter", new_fee.fee,
                                  selling_club.id, buying_club.id)
                negotiation.advance_round()
                return False, f"Counter-offered: €{new_fee:,}"

        else:  # FINAL round
            # Accept or reject final offer
            if random.random() < 0.6:  # 60% chance of final acceptance
                negotiation.status = NegotiationStatus.ACCEPTED
                negotiation.add_offer("final", current_offer.fee,
                                  current_offer.from_club_id, current_offer.to_club_id)
                self.history.add_transfer(self._create_transfer_record(
                    player, current_offer, NegotiationStatus.ACCEPTED
                ))
                return True, "Final offer accepted"
            else:
                negotiation.status = NegotiationStatus.REJECTED
                return True, "Final offer rejected"

    def _calculate_club_urgency(self, club: Club, player: Player) -> float:
        """Calculate how urgently a club needs a player."""
        # Factors:
        # 1. Club needs at position
        # 2. Player is a key target
        # 3. Club has budget

        # Position need (simplified)
        position = player.position.value if player.position else "MID"
        position_needs = {
            "GK": 0.5,
            "CB": 1.0,
            "LB": 0.8,
            "RB": 0.8,
            "CDM": 0.9,
            "CM": 1.0,
            "CAM": 1.0,
            "LW": 0.8,
            "RW": 0.8,
            "ST": 1.0,
            "CF": 1.0,
        }

        urgency = position_needs.get(position, 0.5)

        # Boost for star players
        if player.current_ability > 80:
            urgency *= 1.2

        # Club budget (better budget = more urgency)
        if club.balance > 10_000_000:
            urgency *= 1.1

        return max(0.3, min(1.5, urgency))

    def _create_transfer_record(
        self,
        player: Player,
        offer: TransferOffer,
        status: NegotiationStatus,
    ) -> Transfer:
        """Create a completed Transfer record."""
        return Transfer(
            player_id=player.id,
            from_club_id=offer.from_club_id,
            to_club_id=offer.to_club_id,
            offer_type=offer.offer_type,
            fee=offer.fee,
            status=TransferStatus.COMPLETED if status == NegotiationStatus.ACCEPTED else TransferStatus.CANCELLED,
            offered_at=offer.offered_at,
            responded_at=date.today(),
        )

    def get_active_negotiations(self) -> List[TransferNegotiation]:
        """Get all active negotiations."""
        return [
            neg for neg in self.negotiations.values()
            if neg.status == NegotiationStatus.ONGOING
        ]

    def get_transfer_history(self, limit: int = 20) -> List[Dict]:
        """Get recent transfer history."""
        return self.history.transfers[-limit:] if self.history.transfers else []

    def get_player_transfer_history(
        self, player_id: int, limit: int = 10
    ) -> List[Dict]:
        """Get transfer history for a specific player."""
        return [
            t for t in self.history.transfers
            if t["player_id"] == player_id
        ][-limit:]

    def cleanup_expired_negotiations(self) -> List[str]:
        """Remove expired negotiations."""
        expired = []
        for neg_id, neg in self.negotiations.items():
            if neg.is_expired():
                expired.append(neg_id)
                neg.status = NegotiationStatus.EXPIRED

        # Remove expired
        for neg_id in expired:
            del self.negotiations[neg_id]

        return expired
