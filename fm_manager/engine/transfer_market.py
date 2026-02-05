"""Simplified but functional transfer market system."""

from typing import Optional, List, Dict, Tuple, Any
from datetime import date, datetime, timedelta
import random

from fm_manager.data.cleaned_data_loader import ClubDataFull, PlayerDataFull
from fm_manager.engine.transfer_market_types import (
    TransferOffer,
    PlayerListing,
    OfferType,
    ListingReason,
    OfferResult,
    TransferResponse,
    TransferAction,
    CompletedTransfer,
)
from fm_manager.engine.transfer_service import TransferService


class TransferMarket:
    """Core transfer market orchestrator."""

    def __init__(
        self,
        all_clubs: Dict[int, ClubDataFull],
        all_players: Dict[int, PlayerDataFull],
        current_date: date,
        transfer_window_open: bool = True,
    ):
        self.all_clubs = all_clubs
        self.all_players = all_players
        self.current_date = current_date
        self.transfer_window_open = transfer_window_open
        self.service = TransferService(all_clubs, all_players)
        self.completed_transfers: List[CompletedTransfer] = []
        self.update_callbacks: List = []

    def list_player_for_transfer(
        self,
        player_id: int,
        asking_price: Optional[int] = None,
        reason: Optional[ListingReason] = None,
    ) -> Tuple[bool, str]:
        """List a player for transfer."""
        player = self.all_players.get(player_id)
        if not player:
            return False, "Player not found"

        club_id = getattr(player, "club_id", None)
        if not club_id:
            return False, "Player has no club"

        if asking_price is None:
            asking_price = getattr(player, "market_value", 1000000)

        if reason is None:
            reason = ListingReason.SURPLUS

        listing = self.service.create_listing(player_id, club_id, asking_price, reason)
        if listing:
            return True, f"Listed {player.full_name} for £{asking_price:,}"
        return False, "Player already listed"

    def submit_transfer_offer(
        self, player_id: int, from_club_id: int, to_club_id: int, fee: int
    ) -> OfferResult:
        """Submit a transfer offer."""
        if not self.transfer_window_open:
            return OfferResult(
                success=False,
                status="rejected",
                message="Transfer window is closed",
                window_open=False,
            )

        can_offer, reason, remaining = self.service.validate_finances(from_club_id, fee)
        if not can_offer:
            return OfferResult(
                success=False, status="rejected", message=reason, budget_remaining=remaining
            )

        player = self.all_players.get(player_id)
        if not player:
            return OfferResult(success=False, status="rejected", message="Player not found")

        offer = self.service.create_offer(
            player_id=player_id, from_club_id=from_club_id, to_club_id=to_club_id, fee=fee
        )

        if offer:
            return OfferResult(
                success=True,
                status="pending",
                message=f"Offer of £{fee:,} submitted for {player.full_name}",
                transfer_id=offer.offer_id,
                negotiation_started=True,
                budget_remaining=remaining,
            )

        return OfferResult(success=False, status="rejected", message="Failed to create offer")

    def respond_to_offer(self, offer_id: str, response: TransferResponse) -> Tuple[bool, str]:
        """Respond to a transfer offer."""
        offer = self.service.get_offer_by_id(offer_id)
        if not offer:
            return False, "Offer not found"

        if response.action == "accept":
            self.service.update_offer_status(offer_id, "accepted")
            return self._complete_transfer(offer_id)
        elif response.action == "reject":
            self.service.update_offer_status(offer_id, "rejected")
            return True, "Offer rejected"
        elif response.action == "counter":
            self.service.add_counter_offer(offer_id, response.new_fee or offer.fee)
            return True, f"Counter-offer of £{response.new_fee:,} submitted"

        return False, "Invalid action"

    def _complete_transfer(self, offer_id: str) -> Tuple[bool, str]:
        """Complete a transfer."""
        offer = self.service.get_offer_by_id(offer_id)
        if not offer:
            return False, "Offer not found"

        player = self.all_players.get(offer.player_id)
        from_club = self.all_clubs.get(offer.from_club_id)
        to_club = self.all_clubs.get(offer.to_club_id)

        if not all([player, from_club, to_club]):
            return False, "Invalid transfer data"

        success = self.service.move_player_to_club(
            offer.player_id, offer.from_club_id, offer.to_club_id
        )

        if success:
            from_budget = getattr(from_club, "transfer_budget", 0)
            to_budget = getattr(to_club, "transfer_budget", 0)
            setattr(from_club, "transfer_budget", from_budget - offer.fee)
            setattr(to_club, "transfer_budget", to_budget + offer.fee)

            completed = CompletedTransfer(
                transfer_id=offer_id,
                player_id=offer.player_id,
                player_name=player.full_name,
                from_club_id=offer.from_club_id,
                from_club_name=from_club.name,
                to_club_id=offer.to_club_id,
                to_club_name=to_club.name,
                fee=offer.fee,
            )
            self.completed_transfers.append(completed)

            self.service.remove_listing(offer.player_id)

            return (
                True,
                f"Transfer complete! {player.full_name} moved to {to_club.name} for £{offer.fee:,}",
            )

        return False, "Failed to complete transfer"

    def get_available_listings(self, limit: int = 50) -> List[PlayerListing]:
        """Get available player listings."""
        return self.service.get_listings()[:limit]

    def get_incoming_offers(self, club_id: int) -> List[TransferOffer]:
        """Get incoming offers for a club."""
        return self.service.get_offers_by_selling_club(club_id)

    def get_outgoing_offers(self, club_id: int) -> List[TransferOffer]:
        """Get outgoing offers from a club."""
        return self.service.get_offers_by_buying_club(club_id)

    def process_ai_turn(self, ai_club_id: int) -> List[TransferAction]:
        """Process AI club transfer decisions."""
        actions = []
        club = self.all_clubs.get(ai_club_id)
        if not club:
            return actions

        players = getattr(club, "players", [])
        if not players:
            return actions

        for player in players:
            if getattr(player, "current_ability", 0) < 70:
                if random.random() < 0.3:
                    success, _ = self.list_player_for_transfer(
                        player.id, reason=ListingReason.SURPLUS
                    )
                    if success:
                        actions.append(
                            TransferAction(
                                action_type="list_player",
                                club_id=ai_club_id,
                                player_id=player.id,
                                reasoning="Surplus to requirements",
                            )
                        )

        listings = self.get_available_listings(20)
        budget = getattr(club, "transfer_budget", 0)

        for listing in listings:
            if listing.club_id == ai_club_id:
                continue

            player = self.all_players.get(listing.player_id)
            if not player:
                continue

            if budget >= listing.asking_price and random.random() < 0.1:
                result = self.submit_transfer_offer(
                    player_id=listing.player_id,
                    from_club_id=ai_club_id,
                    to_club_id=listing.club_id,
                    fee=listing.asking_price,
                )
                if result.success:
                    actions.append(
                        TransferAction(
                            action_type="make_offer",
                            club_id=ai_club_id,
                            player_id=listing.player_id,
                            fee=listing.asking_price,
                            reasoning="Good value target",
                        )
                    )
                    budget -= listing.asking_price

        return actions

    def advance_week(self) -> List[str]:
        """Advance transfer market by one week."""
        updates = []

        # Process AI clubs
        for club_id in self.all_clubs:
            if random.random() < 0.5:
                actions = self.process_ai_turn(club_id)
                for action in actions:
                    updates.append(f"{action.action_type}: Club {action.club_id}")

        current_time = datetime.now()
        for offer in self.service.transfers:
            if offer.is_active() and offer.expires_at and current_time > offer.expires_at:
                offer.status = "expired"
                updates.append(f"Offer {offer.offer_id} expired")

        return updates
