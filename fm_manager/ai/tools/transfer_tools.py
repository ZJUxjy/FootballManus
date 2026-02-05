"""Transfer tools for LLM integration."""

from typing import Dict, Any, Optional

from fm_manager.data.cleaned_data_loader import load_for_match_engine
from fm_manager.engine.transfer_market import TransferMarket
from fm_manager.engine.transfer_market_types import TransferResponse, ListingReason


_transfer_market: Optional[TransferMarket] = None
_current_club_id: Optional[int] = None


def set_transfer_market(market: TransferMarket) -> None:
    """Set the global transfer market instance."""
    global _transfer_market
    _transfer_market = market


def set_current_club_id(club_id: int) -> None:
    """Set the current club ID for transfer operations."""
    global _current_club_id
    _current_club_id = club_id


def make_transfer_offer_tool(
    player_name: str, offer_amount: int, offer_type: str = "buy"
) -> Dict[str, Any]:
    """Submit a transfer offer."""
    if not _transfer_market:
        return {"error": "Transfer market not initialized"}

    if not _current_club_id:
        return {"error": "No club selected"}

    # Find player
    clubs, players = load_for_match_engine()
    target_player = None
    for player in players.values():
        if player_name.lower() in player.full_name.lower():
            target_player = player
            break

    if not target_player:
        return {"error": f"Player '{player_name}' not found"}

    # Get player's current club
    to_club_id = getattr(target_player, "club_id", None)
    if not to_club_id:
        return {"error": "Player has no club"}

    if to_club_id == _current_club_id:
        return {"error": "Cannot buy from your own club"}

    # Submit offer
    result = _transfer_market.submit_transfer_offer(
        player_id=target_player.id,
        from_club_id=_current_club_id,
        to_club_id=to_club_id,
        fee=offer_amount,
    )

    return {
        "success": result.success,
        "status": result.status,
        "message": result.message,
        "transfer_id": result.transfer_id,
        "budget_remaining": result.budget_remaining,
        "window_open": result.window_open,
    }


def list_player_for_transfer_tool(
    player_name: str, asking_price: Optional[int] = None
) -> Dict[str, Any]:
    """List a player for transfer."""
    if not _transfer_market:
        return {"error": "Transfer market not initialized"}

    if not _current_club_id:
        return {"error": "No club selected"}

    # Find player in current club
    clubs, players = load_for_match_engine()
    target_player = None
    for player in players.values():
        if player_name.lower() in player.full_name.lower():
            if getattr(player, "club_id", None) == _current_club_id:
                target_player = player
                break

    if not target_player:
        return {"error": f"Player '{player_name}' not found in your squad"}

    success, message = _transfer_market.list_player_for_transfer(
        player_id=target_player.id, asking_price=asking_price
    )

    return {
        "success": success,
        "message": message,
        "player_id": target_player.id if success else None,
        "asking_price": asking_price or getattr(target_player, "market_value", 0),
    }


def view_transfer_list_tool(
    position: Optional[str] = None, max_price: Optional[int] = None, limit: int = 20
) -> Dict[str, Any]:
    """View available players on transfer list."""
    if not _transfer_market:
        return {"error": "Transfer market not initialized"}

    listings = _transfer_market.get_available_listings(limit=limit)

    # Filter by position
    if position:
        listings = [
            l
            for l in listings
            if position.upper()
            in str(getattr(_transfer_market.all_players.get(l.player_id), "position", "")).upper()
        ]

    # Filter by max price
    if max_price:
        listings = [l for l in listings if l.asking_price <= max_price]

    players_data = []
    for listing in listings:
        player = _transfer_market.all_players.get(listing.player_id)
        if player:
            players_data.append(
                {
                    "id": player.id,
                    "name": player.full_name,
                    "position": getattr(player, "position", "Unknown"),
                    "age": getattr(player, "age", 0),
                    "club": getattr(player, "club_name", "Unknown"),
                    "asking_price": listing.asking_price,
                    "market_value": getattr(player, "market_value", 0),
                    "current_ability": round(getattr(player, "current_ability", 0), 1),
                    "potential_ability": round(getattr(player, "potential_ability", 0), 1),
                }
            )

    return {"total_available": len(players_data), "players": players_data}


def view_my_offers_tool() -> Dict[str, Any]:
    """View incoming and outgoing offers."""
    if not _transfer_market:
        return {"error": "Transfer market not initialized"}

    if not _current_club_id:
        return {"error": "No club selected"}

    incoming = _transfer_market.get_incoming_offers(_current_club_id)
    outgoing = _transfer_market.get_outgoing_offers(_current_club_id)

    def format_offer(offer, is_incoming: bool):
        player = _transfer_market.all_players.get(offer.player_id)
        other_club = _transfer_market.all_clubs.get(
            offer.from_club_id if is_incoming else offer.to_club_id
        )
        return {
            "offer_id": offer.offer_id,
            "player_name": player.full_name if player else "Unknown",
            "other_club": other_club.name if other_club else "Unknown",
            "fee": offer.fee,
            "status": offer.status,
            "round": offer.negotiation_round,
        }

    return {
        "incoming_offers": [format_offer(o, True) for o in incoming],
        "outgoing_offers": [format_offer(o, False) for o in outgoing],
        "total_incoming": len(incoming),
        "total_outgoing": len(outgoing),
    }


def respond_to_offer_tool(
    offer_id: str, action: str, counter_amount: Optional[int] = None
) -> Dict[str, Any]:
    """Respond to a transfer offer."""
    if not _transfer_market:
        return {"error": "Transfer market not initialized"}

    if action not in ["accept", "reject", "counter"]:
        return {"error": "Invalid action. Use 'accept', 'reject', or 'counter'"}

    response = TransferResponse(
        action=action, new_fee=counter_amount if action == "counter" else None
    )

    success, message = _transfer_market.respond_to_offer(offer_id, response)

    return {"success": success, "message": message, "action": action}


def withdraw_offer_tool(offer_id: str) -> Dict[str, Any]:
    """Withdraw a transfer offer."""
    if not _transfer_market:
        return {"error": "Transfer market not initialized"}

    offer = _transfer_market.service.get_offer_by_id(offer_id)
    if not offer:
        return {"error": "Offer not found"}

    if offer.from_club_id != _current_club_id:
        return {"error": "Cannot withdraw offer from another club"}

    success = _transfer_market.service.update_offer_status(offer_id, "withdrawn")

    return {
        "success": success,
        "message": "Offer withdrawn" if success else "Failed to withdraw offer",
        "refund_amount": offer.fee if success else 0,
    }
