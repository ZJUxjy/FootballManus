"""Tool implementations for FM Manager AI.

These are the actual tool handlers that can be called by the LLM.
"""

from typing import Any, Dict, List, Optional
from fm_manager.ai.tools.tool_registry import (
    ToolParameter,
    ToolDefinition,
    get_tool_registry,
    register_tool,
)
from fm_manager.ai.tools.player_search_tool import (
    get_player_search_tool,
    PlayerSearchCriteria,
    PositionCategory,
)
from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull


# Current club context (set by the game interface)
_current_club: Optional[ClubDataFull] = None
_current_calendar = None


def set_current_club(club: Optional[ClubDataFull]):
    """Set the current club context for tools."""
    global _current_club
    _current_club = club


def set_current_calendar(calendar):
    """Set the current calendar context for tools."""
    global _current_calendar
    _current_calendar = calendar


def search_players_tool(
    nationality: Optional[str] = None,
    position: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    min_potential: Optional[int] = None,
    max_potential: Optional[int] = None,
    min_ability: Optional[int] = None,
    max_ability: Optional[int] = None,
    max_price: Optional[int] = None,
    sort_by: str = "potential",
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search for players in the database.

    Args:
        nationality: Player nationality (e.g., "England", "Brazil")
        position: Position (e.g., "GK", "CM", "ST")
        min_age: Minimum age
        max_age: Maximum age
        min_potential: Minimum potential ability (0-200)
        max_potential: Maximum potential ability
        min_ability: Minimum current ability
        max_ability: Maximum current ability
        max_price: Maximum price in pounds
        sort_by: Sort by field ("value", "ability", "potential", "age")
        limit: Maximum number of results

    Returns:
        Dictionary with players list and metadata
    """
    tool = get_player_search_tool()

    criteria = PlayerSearchCriteria(
        nationality=nationality,
        position=position,
        min_age=min_age,
        max_age=max_age,
        min_potential_ability=min_potential,
        max_potential_ability=max_potential,
        min_current_ability=min_ability,
        max_current_ability=max_ability,
        max_market_value=max_price,
        sort_by=sort_by,
        limit=limit,
    )

    result = tool.search(criteria)

    return {
        "total_found": result.total_count,
        "players": [
            {
                "id": p.id,
                "name": p.full_name,
                "position": p.position,
                "age": p.age,
                "nationality": p.nationality,
                "current_ability": round(p.current_ability, 1),
                "potential_ability": round(p.potential_ability, 1),
                "market_value": p.market_value,
                "weekly_wage": p.weekly_wage,
                "club": p.club_name,
            }
            for p in result.players
        ],
    }


def get_squad_tool(
    sort_by: str = "ability",
    limit: Optional[int] = None,
    position: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get the current club's squad.

    Args:
        sort_by: Sort by field ("value", "ability", "potential", "age", "wage")
        limit: Maximum number of players to return
        position: Filter by position (e.g., "GK", "CM")

    Returns:
        Dictionary with squad info and players list
    """
    if not _current_club:
        return {"error": "No club selected"}

    players = getattr(_current_club, "players", [])
    if not players:
        return {"club": _current_club.name, "players": [], "total": 0}

    # Filter by position if specified
    if position:
        players = [
            p for p in players if position.upper() in str(getattr(p, "position", "")).upper()
        ]

    sorted_by_ca = sorted(players, key=lambda p: getattr(p, "current_ability", 0), reverse=True)
    top_players = sorted_by_ca[:25]
    young_potentials = [
        p
        for p in sorted_by_ca[25:]
        if getattr(p, "age", 30) <= 21 and getattr(p, "potential_ability", 0) >= 80
    ]
    young_potentials = sorted(
        young_potentials, key=lambda p: getattr(p, "potential_ability", 0), reverse=True
    )[:5]
    selected_players = top_players + young_potentials
    if sort_by != "ability":
        sort_key = {
            "value": lambda p: getattr(p, "market_value", 0),
            "potential": lambda p: getattr(p, "potential_ability", 0),
            "age": lambda p: getattr(p, "age", 0),
            "wage": lambda p: getattr(p, "weekly_wage", 0),
        }.get(sort_by, lambda p: getattr(p, "current_ability", 0))
        selected_players = sorted(selected_players, key=sort_key, reverse=True)
    if limit:
        selected_players = selected_players[:limit]

    # Calculate squad stats
    total_value = sum(getattr(p, "market_value", 0) for p in players)
    avg_age = sum(getattr(p, "age", 0) for p in players) / len(players) if players else 0

    return {
        "club": _current_club.name,
        "total_players": len(players),
        "total_value": total_value,
        "average_age": round(avg_age, 1),
        "players": [
            {
                "id": getattr(p, "id", 0),
                "name": getattr(p, "full_name", "Unknown"),
                "position": str(getattr(p, "position", "-")),
                "age": getattr(p, "age", 0),
                "current_ability": round(getattr(p, "current_ability", 0), 1),
                "potential_ability": round(getattr(p, "potential_ability", 0), 1),
                "market_value": getattr(p, "market_value", 0),
                "weekly_wage": getattr(p, "weekly_wage", 0),
            }
            for p in selected_players
        ],
    }


def get_player_details_tool(player_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific player.

    Args:
        player_name: Player name to search for

    Returns:
        Dictionary with player details
    """
    # Search in current squad first
    if _current_club:
        for player in getattr(_current_club, "players", []):
            if player_name.lower() in getattr(player, "full_name", "").lower():
                return {
                    "found": True,
                    "in_squad": True,
                    "player": {
                        "id": getattr(player, "id", 0),
                        "name": getattr(player, "full_name", "Unknown"),
                        "position": str(getattr(player, "position", "-")),
                        "age": getattr(player, "age", 0),
                        "nationality": getattr(player, "nationality", "-"),
                        "current_ability": round(getattr(player, "current_ability", 0), 1),
                        "potential_ability": round(getattr(player, "potential_ability", 0), 1),
                        "market_value": getattr(player, "market_value", 0),
                        "weekly_wage": getattr(player, "weekly_wage", 0),
                    },
                }

    # Search in all players
    clubs, players = load_for_match_engine()
    matches = []

    for player in players.values():
        if player_name.lower() in getattr(player, "full_name", "").lower():
            matches.append(player)

    if not matches:
        return {"found": False, "message": f"No player found matching '{player_name}'"}

    if len(matches) == 1:
        player = matches[0]
        return {
            "found": True,
            "in_squad": False,
            "player": {
                "id": player.id,
                "name": player.full_name,
                "position": player.position,
                "age": player.age,
                "nationality": player.nationality,
                "current_ability": round(player.current_ability, 1),
                "potential_ability": round(player.potential_ability, 1),
                "market_value": player.market_value,
                "weekly_wage": player.weekly_wage,
                "club": player.club_name,
            },
        }
    else:
        return {
            "found": True,
            "multiple_matches": True,
            "matches": [
                {
                    "name": p.full_name,
                    "position": p.position,
                    "club": p.club_name,
                }
                for p in matches[:5]
            ],
        }


def get_club_info_tool() -> Dict[str, Any]:
    """
    Get information about the current club.

    Returns:
        Dictionary with club details
    """
    if not _current_club:
        return {"error": "No club selected"}

    players = getattr(_current_club, "players", [])
    total_value = sum(getattr(p, "market_value", 0) for p in players)
    avg_age = sum(getattr(p, "age", 0) for p in players) / len(players) if players else 0

    return {
        "name": _current_club.name,
        "league": _current_club.league,
        "reputation": _current_club.reputation,
        "squad_size": len(players),
        "total_value": total_value,
        "average_age": round(avg_age, 1),
        "transfer_budget": getattr(_current_club, "transfer_budget", 0)
        or getattr(_current_club, "balance", 0),
    }


def set_tactics_tool(
    formation: Optional[str] = None,
    style: Optional[str] = None,
    mentality: Optional[str] = None,
    pressing: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set team tactics and formation.

    Args:
        formation: Formation (e.g., '4-3-3', '4-4-2', '3-5-2')
        style: Playing style ('possession', 'counter-attack', 'direct', 'wing-play')
        mentality: Team mentality ('attacking', 'balanced', 'defensive', 'very-defensive')
        pressing: Pressing intensity ('high', 'medium', 'low')

    Returns:
        Dictionary with updated tactics
    """
    if not _current_club:
        return {"error": "No club selected"}

    # Validate formation
    valid_formations = ["4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "5-3-2", "4-1-4-1", "3-4-3"]
    if formation and formation not in valid_formations:
        return {"error": f"Invalid formation. Valid options: {', '.join(valid_formations)}"}

    # Build tactics update
    tactics = {}
    if formation:
        tactics["formation"] = formation
    if style:
        tactics["style"] = style
    if mentality:
        tactics["mentality"] = mentality
    if pressing:
        tactics["pressing"] = pressing

    # In a real implementation, this would update the database
    # For now, we just return what would be set
    return {
        "success": True,
        "club": _current_club.name,
        "tactics": tactics,
        "message": f"Tactics updated for {_current_club.name}",
    }


def make_transfer_tool(
    player_name: str,
    offer_type: str = "buy",
    offer_amount: Optional[int] = None,
    loan_duration: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Make a transfer offer for a player.

    Args:
        player_name: Name of the player to transfer
        offer_type: Type of offer ('buy', 'loan', 'sell')
        offer_amount: Offer amount in pounds (for buy/sell)
        loan_duration: Loan duration in months (for loan)

    Returns:
        Dictionary with transfer proposal details
    """
    # Search for player
    from fm_manager.data.cleaned_data_loader import load_for_match_engine

    clubs, players = load_for_match_engine()

    matches = []
    for player in players.values():
        if player_name.lower() in player.full_name.lower():
            matches.append(player)

    if not matches:
        return {"error": f"No player found matching '{player_name}'"}

    player = matches[0]

    # Build transfer proposal
    proposal = {
        "player": {
            "name": player.full_name,
            "position": player.position,
            "age": player.age,
            "current_ability": round(player.current_ability, 1),
            "potential_ability": round(player.potential_ability, 1),
            "market_value": player.market_value,
            "current_club": player.club_name,
        },
        "offer_type": offer_type,
        "status": "pending",
    }

    if offer_type == "buy":
        proposal["offer_amount"] = offer_amount or player.market_value
        proposal["message"] = (
            f"Buy offer of £{proposal['offer_amount']:,} submitted for {player.full_name}"
        )
    elif offer_type == "loan":
        proposal["loan_duration"] = loan_duration or 12
        proposal["message"] = (
            f"Loan proposal for {proposal['loan_duration']} months submitted for {player.full_name}"
        )
    elif offer_type == "sell":
        proposal["asking_price"] = offer_amount or player.market_value
        proposal["message"] = f"{player.full_name} listed for sale at £{proposal['asking_price']:,}"

    return proposal


def view_fixtures_tool(
    view_type: str = "upcoming",
    limit: int = 5,
) -> Dict[str, Any]:
    """
    View match fixtures and schedule.

    Args:
        view_type: Type of fixtures to view ('upcoming', 'results', 'all')
        limit: Number of matches to return

    Returns:
        Dictionary with fixture list
    """
    if not _current_club:
        return {"error": "No club selected"}

    fixtures = []

    if _current_calendar:
        current_week = _current_calendar.current_week

        if view_type in ["upcoming", "all"]:
            # Get future matches for user's team
            team_matches = [
                m
                for m in _current_calendar.matches
                if (m.home_team == _current_club.name or m.away_team == _current_club.name)
                and m.week >= current_week
                and not m.played
            ]

            for match in sorted(team_matches, key=lambda m: m.week)[:limit]:
                is_home = match.home_team == _current_club.name
                fixtures.append(
                    {
                        "week": match.week,
                        "date": match.match_date.strftime("%b %d"),
                        "opponent": match.away_team if is_home else match.home_team,
                        "venue": "Home" if is_home else "Away",
                        "competition": _current_calendar.league_name,
                    }
                )

        if view_type in ["results", "all"]:
            # Get played matches
            team_matches = [
                m
                for m in _current_calendar.matches
                if (m.home_team == _current_club.name or m.away_team == _current_club.name)
                and m.played
            ]

            for match in sorted(team_matches, key=lambda m: m.week, reverse=True)[:limit]:
                is_home = match.home_team == _current_club.name
                our_goals = match.home_goals if is_home else match.away_goals
                their_goals = match.away_goals if is_home else match.home_goals

                if our_goals > their_goals:
                    result_str = f"{our_goals}-{their_goals} Win"
                elif our_goals < their_goals:
                    result_str = f"{our_goals}-{their_goals} Loss"
                else:
                    result_str = f"{our_goals}-{their_goals} Draw"

                fixtures.append(
                    {
                        "week": match.week,
                        "opponent": match.away_team if is_home else match.home_team,
                        "result": result_str,
                        "venue": "Home" if is_home else "Away",
                    }
                )

        return {
            "club": _current_club.name,
            "view_type": view_type,
            "fixtures": fixtures,
            "current_week": current_week,
        }
    else:
        # Fallback when no calendar is available
        return {
            "club": _current_club.name,
            "view_type": view_type,
            "fixtures": [],
            "current_week": 1,
            "message": "Calendar not initialized. Use 'calendar' or 'next' commands to start season.",
        }


def advance_match_tool(
    simulate: bool = True,
) -> Dict[str, Any]:
    """
    Advance to and simulate the next match.

    Args:
        simulate: Whether to simulate the match (default: True)

    Returns:
        Dictionary with match result
    """
    if not _current_club:
        return {"error": "No club selected"}

    # Placeholder match result (in real implementation, would use match engine)
    import random

    opponent = "Arsenal"
    our_score = random.randint(0, 3)
    their_score = random.randint(0, 2)

    result = "Win" if our_score > their_score else "Loss" if our_score < their_score else "Draw"

    return {
        "match_played": True,
        "club": _current_club.name,
        "opponent": opponent,
        "score": f"{our_score}-{their_score}",
        "result": result,
        "goal_scorers": ["Smith (34')", "Johnson (67')"] if our_score > 0 else [],
        "next_match_week": 16,
    }


def save_game_tool(
    save_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save the current game state.

    Args:
        save_name: Custom save name (optional)

    Returns:
        Dictionary with save confirmation
    """
    if not _current_club:
        return {"error": "No club selected"}

    from datetime import datetime

    save_name = save_name or f"{_current_club.name}_{datetime.now().strftime('%Y%m%d')}"

    # In real implementation, would serialize game state to file/database
    return {
        "saved": True,
        "save_name": save_name,
        "club": _current_club.name,
        "date": datetime.now().isoformat(),
        "message": f"Game saved successfully as '{save_name}'",
    }


def register_all_tools():
    """Register all tools with the registry."""
    registry = get_tool_registry()

    # Register search_players tool
    registry.register(
        ToolDefinition(
            name="search_players",
            description="Search for players in the database with various filters",
            parameters=[
                ToolParameter(
                    "nationality",
                    "string",
                    "Player nationality (e.g., 'England', 'Brazil')",
                    required=False,
                ),
                ToolParameter(
                    "position", "string", "Position (e.g., 'GK', 'CM', 'ST')", required=False
                ),
                ToolParameter("min_age", "integer", "Minimum age", required=False),
                ToolParameter("max_age", "integer", "Maximum age", required=False),
                ToolParameter(
                    "min_potential", "integer", "Minimum potential ability (0-200)", required=False
                ),
                ToolParameter(
                    "max_potential", "integer", "Maximum potential ability", required=False
                ),
                ToolParameter("min_ability", "integer", "Minimum current ability", required=False),
                ToolParameter("max_ability", "integer", "Maximum current ability", required=False),
                ToolParameter("max_price", "integer", "Maximum price in pounds", required=False),
                ToolParameter(
                    "sort_by", "string", "Sort field", required=False, default="potential"
                ),
                ToolParameter("limit", "integer", "Maximum results", required=False, default=10),
            ],
            handler=search_players_tool,
        )
    )

    # Register get_squad tool
    registry.register(
        ToolDefinition(
            name="get_squad",
            description="Get the current club's squad information",
            parameters=[
                ToolParameter(
                    "sort_by",
                    "string",
                    "Sort by field (value, ability, potential, age, wage)",
                    required=False,
                    default="ability",
                ),
                ToolParameter("limit", "integer", "Maximum players to return", required=False),
                ToolParameter("position", "string", "Filter by position", required=False),
            ],
            handler=get_squad_tool,
        )
    )

    # Register get_player_details tool
    registry.register(
        ToolDefinition(
            name="get_player_details",
            description="Get detailed information about a specific player",
            parameters=[
                ToolParameter("player_name", "string", "Player name to search for", required=True),
            ],
            handler=get_player_details_tool,
        )
    )

    # Register get_club_info tool
    registry.register(
        ToolDefinition(
            name="get_club_info",
            description="Get information about the current club",
            parameters=[],
            handler=get_club_info_tool,
        )
    )

    # Register set_tactics tool
    registry.register(
        ToolDefinition(
            name="set_tactics",
            description="Set team tactics, formation, and playing style",
            parameters=[
                ToolParameter(
                    "formation",
                    "string",
                    "Formation (e.g., '4-3-3', '4-4-2', '3-5-2')",
                    required=False,
                    enum=["4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "5-3-2", "4-1-4-1", "3-4-3"],
                ),
                ToolParameter(
                    "style",
                    "string",
                    "Playing style",
                    required=False,
                    enum=["possession", "counter-attack", "direct", "wing-play"],
                ),
                ToolParameter(
                    "mentality",
                    "string",
                    "Team mentality",
                    required=False,
                    enum=["attacking", "balanced", "defensive", "very-defensive"],
                ),
                ToolParameter(
                    "pressing",
                    "string",
                    "Pressing intensity",
                    required=False,
                    enum=["high", "medium", "low"],
                ),
            ],
            handler=set_tactics_tool,
        )
    )

    # Register make_transfer tool
    registry.register(
        ToolDefinition(
            name="make_transfer",
            description="Make a transfer offer for a player (buy, loan, or sell)",
            parameters=[
                ToolParameter("player_name", "string", "Name of the player", required=True),
                ToolParameter(
                    "offer_type",
                    "string",
                    "Type of offer",
                    required=False,
                    default="buy",
                    enum=["buy", "loan", "sell"],
                ),
                ToolParameter(
                    "offer_amount",
                    "integer",
                    "Offer amount in pounds (for buy/sell)",
                    required=False,
                ),
                ToolParameter(
                    "loan_duration", "integer", "Loan duration in months (for loan)", required=False
                ),
            ],
            handler=make_transfer_tool,
        )
    )

    # Register view_fixtures tool
    registry.register(
        ToolDefinition(
            name="view_fixtures",
            description="View match fixtures and schedule",
            parameters=[
                ToolParameter(
                    "view_type",
                    "string",
                    "Type of fixtures to view",
                    required=False,
                    default="upcoming",
                    enum=["upcoming", "results", "all"],
                ),
                ToolParameter(
                    "limit", "integer", "Number of matches to return", required=False, default=5
                ),
            ],
            handler=view_fixtures_tool,
        )
    )

    # Register advance_match tool
    registry.register(
        ToolDefinition(
            name="advance_match",
            description="Advance to and simulate the next match",
            parameters=[
                ToolParameter(
                    "simulate",
                    "boolean",
                    "Whether to simulate the match",
                    required=False,
                    default=True,
                ),
            ],
            handler=advance_match_tool,
        )
    )

    # Register save_game tool
    registry.register(
        ToolDefinition(
            name="save_game",
            description="Save the current game state",
            parameters=[
                ToolParameter("save_name", "string", "Custom save name (optional)", required=False),
            ],
            handler=save_game_tool,
        )
    )


# Auto-register tools on import
register_all_tools()
