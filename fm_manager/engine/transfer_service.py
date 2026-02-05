"""Transfer service for in-memory transfer operations."""

from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta

from fm_manager.data.cleaned_data_loader import ClubDataFull, PlayerDataFull
from fm_manager.engine.transfer_market_types import (
    TransferOffer,
    PlayerListing,
    OfferType,
    ListingReason,
)


class TransferService:
    """In-memory transfer operations service."""

    def __init__(self, all_clubs: Dict[int, ClubDataFull], all_players: Dict[int, PlayerDataFull]):
        self.all_clubs = all_clubs
        self.all_players = all_players
        self.transfers: List[TransferOffer] = []
        self.listings: List[PlayerListing] = []
        self._next_offer_id = 1

    def create_offer(
        self,
        player_id: int,
        from_club_id: int,
        to_club_id: int,
        fee: int,
        offer_type: OfferType = OfferType.BUY,
        proposed_wage: Optional[int] = None,
        proposed_contract_years: int = 3,
    ) -> Optional[TransferOffer]:
        """Create a new transfer offer."""
        offer_id = f"offer_{self._next_offer_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._next_offer_id += 1

        offer = TransferOffer(
            offer_id=offer_id,
            player_id=player_id,
            from_club_id=from_club_id,
            to_club_id=to_club_id,
            offer_type=offer_type,
            fee=fee,
            proposed_wage=proposed_wage,
            proposed_contract_years=proposed_contract_years,
            expires_at=datetime.now() + timedelta(days=7),
        )

        self.transfers.append(offer)
        return offer

    def get_offer_by_id(self, offer_id: str) -> Optional[TransferOffer]:
        """Get offer by ID."""
        for offer in self.transfers:
            if offer.offer_id == offer_id:
                return offer
        return None

    def get_offers_by_player(self, player_id: int) -> List[TransferOffer]:
        """Get all offers for a specific player."""
        return [o for o in self.transfers if o.player_id == player_id and o.is_active()]

    def get_offers_by_buying_club(self, club_id: int) -> List[TransferOffer]:
        """Get all offers from a buying club."""
        return [o for o in self.transfers if o.from_club_id == club_id]

    def get_offers_by_selling_club(self, club_id: int) -> List[TransferOffer]:
        """Get all offers to a selling club."""
        return [o for o in self.transfers if o.to_club_id == club_id]

    def update_offer_status(self, offer_id: str, status: str) -> bool:
        """Update status of an existing offer."""
        offer = self.get_offer_by_id(offer_id)
        if offer:
            offer.status = status
            offer.responded_at = datetime.now()
            return True
        return False

    def add_counter_offer(self, offer_id: str, counter_fee: int) -> Optional[TransferOffer]:
        """Add a counter-offer to existing negotiation."""
        offer = self.get_offer_by_id(offer_id)
        if offer:
            offer.counter_fee = counter_fee
            offer.status = "negotiating"
            offer.negotiation_round += 1
            offer.responded_at = datetime.now()
            return offer
        return None

    def create_listing(
        self, player_id: int, club_id: int, asking_price: int, reason: ListingReason
    ) -> Optional[PlayerListing]:
        """Create a player listing for transfer."""
        for listing in self.listings:
            if listing.player_id == player_id:
                return None

        listing = PlayerListing(
            player_id=player_id, club_id=club_id, asking_price=asking_price, reason=reason
        )
        self.listings.append(listing)
        return listing

    def get_listings(
        self, club_id: Optional[int] = None, filters: Optional[Dict] = None
    ) -> List[PlayerListing]:
        """Get player listings with optional filters."""
        result = self.listings

        if club_id:
            result = [l for l in result if l.club_id == club_id]

        if filters:
            if "position" in filters:
                result = [
                    l
                    for l in result
                    if self._get_player_position(l.player_id) == filters["position"]
                ]
            if "max_price" in filters:
                result = [l for l in result if l.asking_price <= filters["max_price"]]

        return result

    def remove_listing(self, player_id: int) -> bool:
        """Remove a player listing."""
        for i, listing in enumerate(self.listings):
            if listing.player_id == player_id:
                self.listings.pop(i)
                return True
        return False

    def move_player_to_club(self, player_id: int, from_club_id: int, to_club_id: int) -> bool:
        """Move a player from one club to another."""
        player = self.all_players.get(player_id)
        from_club = self.all_clubs.get(from_club_id)
        to_club = self.all_clubs.get(to_club_id)

        if not player or not from_club or not to_club:
            return False

        player.club_id = to_club_id
        player.club_name = to_club.name

        if hasattr(from_club, "players") and player in from_club.players:
            from_club.players.remove(player)

        if hasattr(to_club, "players"):
            to_club.players.append(player)

        return True

    def validate_finances(self, club_id: int, fee: int) -> Tuple[bool, str, int]:
        """Validate if a club can afford a transfer."""
        club = self.all_clubs.get(club_id)
        if not club:
            return False, "Club not found", 0

        budget = getattr(club, "transfer_budget", 0)
        if budget < fee:
            return False, f"Insufficient funds. Budget: £{budget:,}, Fee: £{fee:,}", budget

        return True, "OK", budget - fee

    def _get_player_position(self, player_id: int) -> str:
        """Get player position."""
        player = self.all_players.get(player_id)
        if player:
            return getattr(player, "position", "Unknown")
        return "Unknown"
