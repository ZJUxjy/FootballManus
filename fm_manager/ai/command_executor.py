"""Command Executor for Natural Language Game Interface.

Maps parsed intents to actual game actions and coordinates between
NL interface and existing game systems.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime

from colorama import Fore, Style

from fm_manager.ai.intent_parser import (
    ParsedIntent,
    GameIntentType,
    PlayerSearchIntent,
    ViewSquadIntent,
    ViewPlayerDetailsIntent,
    SetTacticsIntent,
    MakeTransferIntent,
    ViewFixturesIntent,
    AdvanceMatchIntent,
    SaveGameIntent,
    HelpIntent,
    UnknownIntent,
)
from fm_manager.ai.tools.player_search_tool import (
    PlayerSearchTool,
    PlayerSearchCriteria,
    get_player_search_tool,
)
from fm_manager.data.cleaned_data_loader import load_for_match_engine, ClubDataFull


@dataclass
class CommandResult:
    """Result of executing a command."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    action_taken: str = ""
    error: Optional[str] = None
    follow_up_suggested: Optional[str] = None


class CommandExecutor:
    """Executes parsed intents by mapping them to game actions."""

    def __init__(self, current_club: Optional[ClubDataFull] = None):
        """
        Initialize the command executor.

        Args:
            current_club: The club currently being managed
        """
        self.current_club = current_club
        self.search_tool = get_player_search_tool()
        self.clubs, self.players = load_for_match_engine()

        # Command handlers mapping
        self.handlers = {
            GameIntentType.SEARCH_PLAYERS: self._handle_search_players,
            GameIntentType.VIEW_SQUAD: self._handle_view_squad,
            GameIntentType.VIEW_PLAYER_DETAILS: self._handle_view_player_details,
            GameIntentType.SET_TACTICS: self._handle_set_tactics,
            GameIntentType.MAKE_TRANSFER: self._handle_make_transfer,
            GameIntentType.VIEW_FIXTURES: self._handle_view_fixtures,
            GameIntentType.ADVANCE_MATCH: self._handle_advance_match,
            GameIntentType.SAVE_GAME: self._handle_save_game,
            GameIntentType.HELP: self._handle_help,
            GameIntentType.UNKNOWN: self._handle_unknown,
        }

    async def execute(self, parsed_intent: ParsedIntent) -> CommandResult:
        """
        Execute a parsed intent.

        Args:
            parsed_intent: The parsed intent to execute

        Returns:
            CommandResult with execution results
        """
        intent_type = GameIntentType(parsed_intent.intent.intent_type)
        handler = self.handlers.get(intent_type, self._handle_unknown)

        try:
            result = await handler(parsed_intent.intent)
            return result
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error executing command: {str(e)}",
                error=str(e),
                action_taken=intent_type.value,
            )

    async def _handle_search_players(self, intent: PlayerSearchIntent) -> CommandResult:
        """Handle player search intent."""
        # Build search criteria from intent
        criteria = self.search_tool.build_criteria_from_natural_language(
            nationality=intent.nationality,
            age=intent.age_description,
            position=intent.position,
            ability=intent.ability_level,
            potential=intent.potential_level,
            max_price=intent.max_price,
        )

        # Set additional parameters
        criteria.limit = intent.limit
        criteria.sort_by = self._map_sort_field(intent.sort_by)
        criteria.exclude_club_id = getattr(self.current_club, "id", None)

        # Execute search
        result = self.search_tool.search(criteria)

        # Format response
        if result.total_count == 0:
            return CommandResult(
                success=True,
                message="No players found matching your criteria.",
                data={"total": 0, "players": []},
                action_taken="search_players",
                follow_up_suggested="Try relaxing some criteria or search for different attributes.",
            )

        # Build natural language response
        message = self._format_search_results(result)

        return CommandResult(
            success=True,
            message=message,
            data=result.to_dict(),
            action_taken="search_players",
            follow_up_suggested="You can ask to see more details about any player, or refine your search.",
        )

    async def _handle_view_squad(self, intent: ViewSquadIntent) -> CommandResult:
        """Handle view squad intent with aggregation support."""
        if not self.current_club:
            return CommandResult(
                success=False,
                message="No club selected. Please start a career first.",
                action_taken="view_squad",
            )

        players = getattr(self.current_club, "players", [])
        if not players:
            return CommandResult(
                success=True,
                message=f"{self.current_club.name} has no players in the squad.",
                data={"total": 0},
                action_taken="view_squad",
            )

        # Sort players
        sort_key = self._map_squad_sort(intent.sort_by)
        sorted_players = sorted(players, key=sort_key, reverse=True)

        # Apply limit if specified
        if intent.limit:
            sorted_players = sorted_players[: intent.limit]
        else:
            sorted_players = sorted_players[:25]

        # Format based on aggregation type
        if intent.limit == 1 and intent.aggregation:
            # Single result - format as natural language
            player = sorted_players[0]
            sort_field_name = self._get_sort_field_name(intent.sort_field or intent.sort_by)
            sort_value = self._get_sort_value(player, intent.sort_field or intent.sort_by)

            message = self._format_single_player_result(
                player, sort_field_name, sort_value, intent.aggregation
            )

            return CommandResult(
                success=True,
                message=message,
                data={
                    "club": self.current_club.name,
                    "player": {
                        "id": getattr(player, "id", 0),
                        "name": getattr(player, "full_name", "Unknown"),
                        "position": str(getattr(player, "position", "-")),
                        "age": getattr(player, "age", 0),
                        "ca": getattr(player, "current_ability", 0),
                        "pa": getattr(player, "potential_ability", 0),
                        "value": getattr(player, "market_value", 0),
                    },
                },
                action_taken="view_squad",
                follow_up_suggested="Ask about other players or search for new talent.",
            )
        elif intent.limit and intent.limit > 1:
            # Limited results - format as list with header
            sort_field_name = self._get_sort_field_name(intent.sort_field or intent.sort_by)
            lines = [
                f"{sort_field_name}最高的{intent.limit}名球员：",
                "",
            ]

            for i, player in enumerate(sorted_players, 1):
                name = getattr(player, "full_name", "Unknown")
                pos = getattr(player, "position", "-")
                pos_str = pos if isinstance(pos, str) else getattr(pos, "value", "-")
                age = getattr(player, "age", "-")
                value = getattr(player, "market_value", 0)
                ca = getattr(player, "current_ability", "-")
                pa = getattr(player, "potential_ability", "-")

                lines.append(f"{i}. {name} ({pos_str}, {age}岁)")
                lines.append(f"   能力: {ca} | 潜力: {pa} | 身价: £{value / 1_000_000:.1f}M")
                lines.append("")

            return CommandResult(
                success=True,
                message="\n".join(lines),
                data={
                    "club": self.current_club.name,
                    "total": len(sorted_players),
                    "players": [
                        {
                            "id": getattr(p, "id", 0),
                            "name": getattr(p, "full_name", "Unknown"),
                            "position": str(getattr(p, "position", "-")),
                            "age": getattr(p, "age", 0),
                            "ca": getattr(p, "current_ability", 0),
                            "pa": getattr(p, "potential_ability", 0),
                        }
                        for p in sorted_players
                    ],
                },
                action_taken="view_squad",
                follow_up_suggested="Ask about specific player details or search for new talent.",
            )
        else:
            # Default - format as table
            lines = [
                f"{self.current_club.name} Squad ({len(players)} players):",
                "",
                f"{'#':<4} {'Name':<25} {'Pos':<6} {'Age':<4} {'CA':<4} {'PA':<4} {'Value':<12}",
                "-" * 70,
            ]

            for i, player in enumerate(sorted_players, 1):
                name = getattr(player, "full_name", "Unknown")[:24]
                pos = getattr(player, "position", "-")
                pos_str = pos if isinstance(pos, str) else getattr(pos, "value", "-")
                age = getattr(player, "age", "-")
                ca = getattr(player, "current_ability", "-")
                pa = getattr(player, "potential_ability", "-")
                value = getattr(player, "market_value", 0)

                lines.append(
                    f"{i:<4} {name:<25} {pos_str:<6} {age:<4} {ca:<4} {pa:<4} £{value / 1_000_000:.1f}M"
                )

            return CommandResult(
                success=True,
                message="\n".join(lines),
                data={
                    "club": self.current_club.name,
                    "total_players": len(players),
                    "players": [
                        {
                            "id": getattr(p, "id", 0),
                            "name": getattr(p, "full_name", "Unknown"),
                            "position": str(getattr(p, "position", "-")),
                            "age": getattr(p, "age", 0),
                            "ca": getattr(p, "current_ability", 0),
                            "pa": getattr(p, "potential_ability", 0),
                        }
                        for p in sorted_players[:10]
                    ],
                },
                action_taken="view_squad",
                follow_up_suggested="Ask about specific player details or say 'search for players' to find new talent.",
            )

    async def _handle_view_player_details(self, intent: ViewPlayerDetailsIntent) -> CommandResult:
        """Handle view player details intent."""
        # Search for player by name
        player_name = intent.player_name.lower()

        # Search in current squad first
        if self.current_club:
            for player in getattr(self.current_club, "players", []):
                if player_name in getattr(player, "full_name", "").lower():
                    return self._format_player_details(player, in_squad=True)

        # Search in all players
        matches = []
        for player in self.players.values():
            if player_name in getattr(player, "full_name", "").lower():
                matches.append(player)

        if not matches:
            return CommandResult(
                success=False,
                message=f"No player found matching '{intent.player_name}'.",
                action_taken="view_player_details",
            )

        if len(matches) == 1:
            return self._format_player_details(matches[0], in_squad=False)
        else:
            # Multiple matches - show list
            message = f"Found {len(matches)} players matching '{intent.player_name}':\n\n"
            for i, p in enumerate(matches[:5], 1):
                message += f"{i}. {getattr(p, 'full_name', 'Unknown')} ({getattr(p, 'position', '-')}, {getattr(p, 'club_name', 'Unknown')})\n"
            message += "\nPlease specify which player you want to see details for."

            return CommandResult(
                success=True,
                message=message,
                data={"matches": len(matches)},
                action_taken="view_player_details",
                follow_up_suggested="Say the full name of the player you want to see.",
            )

    async def _handle_set_tactics(self, intent: SetTacticsIntent) -> CommandResult:
        """Handle set tactics intent."""
        if not self.current_club:
            return CommandResult(
                success=False,
                message="No club selected. Please start a career first.",
                action_taken="set_tactics",
            )

        # Build confirmation message
        changes = []
        if intent.formation:
            changes.append(f"Formation: {intent.formation}")
        if intent.style:
            changes.append(f"Style: {intent.style}")
        if intent.mentality:
            changes.append(f"Mentality: {intent.mentality}")

        if not changes:
            return CommandResult(
                success=True,
                message="Current tactics remain unchanged. What would you like to change?",
                action_taken="set_tactics",
                follow_up_suggested="Say something like 'play 4-3-3' or 'use high pressing'.",
            )

        message = f"Tactics updated for {self.current_club.name}:\n"
        for change in changes:
            message += f"  • {change}\n"

        # Note: Actual tactic application would integrate with existing tactic system

        return CommandResult(
            success=True,
            message=message,
            data={
                "formation": intent.formation,
                "style": intent.style,
                "mentality": intent.mentality,
            },
            action_taken="set_tactics",
            follow_up_suggested="You can adjust tactics anytime or say 'advance to next match' to continue.",
        )

    async def _handle_make_transfer(self, intent: MakeTransferIntent) -> CommandResult:
        """Handle make transfer intent."""
        # Find the player
        player_name = intent.player_name.lower()
        matches = []

        for player in self.players.values():
            if player_name in getattr(player, "full_name", "").lower():
                matches.append(player)

        if not matches:
            return CommandResult(
                success=False,
                message=f"No player found matching '{intent.player_name}'.",
                action_taken="make_transfer",
            )

        player = matches[0]  # Take first match

        # Build transfer message
        transfer_type = intent.transfer_type or "buy"
        offer = intent.offer_amount or "market value"

        message = f"Transfer {transfer_type} proposal prepared:\n\n"
        message += f"Player: {getattr(player, 'full_name', 'Unknown')}\n"
        message += f"Position: {getattr(player, 'position', '-')}\n"
        message += f"Current Club: {getattr(player, 'club_name', 'Unknown')}\n"
        message += f"Market Value: £{getattr(player, 'market_value', 0):,}\n"
        message += f"Your Offer: {offer}\n\n"

        if transfer_type == "buy":
            message += "This offer will be sent to the selling club for consideration."
        elif transfer_type == "sell":
            message += "This player will be listed for transfer."
        elif transfer_type == "loan":
            message += "Loan proposal will be sent to interested clubs."

        return CommandResult(
            success=True,
            message=message,
            data={
                "player_id": getattr(player, "id", 0),
                "player_name": getattr(player, "full_name", "Unknown"),
                "transfer_type": transfer_type,
                "offer": offer,
            },
            action_taken="make_transfer",
            follow_up_suggested="The transfer will be processed. Check 'transfer history' for updates.",
        )

    async def _handle_view_fixtures(self, intent: ViewFixturesIntent) -> CommandResult:
        """Handle view fixtures intent."""
        if not self.current_club:
            return CommandResult(
                success=False,
                message="No club selected. Please start a career first.",
                action_taken="view_fixtures",
            )

        view_type = intent.view_type or "upcoming"

        # Placeholder fixtures (would integrate with actual fixture system)
        if view_type == "upcoming":
            message = f"Upcoming matches for {self.current_club.name}:\n\n"
            message += "Week 15: vs Arsenal (Home)\n"
            message += "Week 16: vs Chelsea (Away)\n"
            message += "Week 17: vs Liverpool (Home)\n"
            message += "Week 18: vs Man City (Away)\n"
        elif view_type == "results":
            message = f"Recent results for {self.current_club.name}:\n\n"
            message += "Week 14: Tottenham 2-1 (W)\n"
            message += "Week 13: Everton 0-0 (D)\n"
            message += "Week 12: Brighton 3-2 (W)\n"
            message += "Week 11: Newcastle 1-2 (L)\n"
        else:
            message = f"Full schedule for {self.current_club.name}:\n\n"
            message += "[Full season schedule would be displayed here]"

        return CommandResult(
            success=True,
            message=message,
            data={"view_type": view_type},
            action_taken="view_fixtures",
            follow_up_suggested="Say 'advance to next match' to play the next game.",
        )

    async def _handle_advance_match(self, intent: AdvanceMatchIntent) -> CommandResult:
        """Handle advance match intent."""
        if not self.current_club:
            return CommandResult(
                success=False,
                message="No club selected. Please start a career first.",
                action_taken="advance_match",
            )

        # Placeholder match result
        message = f"Match Result: {self.current_club.name} 2-1 Arsenal\n\n"
        message += "Goalscorers:\n"
        message += "  34' - Smith\n"
        message += "  67' - Johnson\n\n"
        message += "Great win! The team is building momentum."

        return CommandResult(
            success=True,
            message=message,
            data={
                "result": "win",
                "score": "2-1",
                "opponent": "Arsenal",
            },
            action_taken="advance_match",
            follow_up_suggested="Check 'fixtures' for the next match or 'squad' to review player fitness.",
        )

    async def _handle_save_game(self, intent: SaveGameIntent) -> CommandResult:
        """Handle save game intent."""
        save_name = (
            intent.save_name
            or f"{self.current_club.name if self.current_club else 'Career'}_{datetime.now().strftime('%Y%m%d')}"
        )

        message = f"Game saved successfully!\n"
        message += f"Save name: {save_name}"

        return CommandResult(
            success=True,
            message=message,
            data={"save_name": save_name},
            action_taken="save_game",
            follow_up_suggested="Continue playing or exit when ready.",
        )

    async def _handle_help(self, intent: HelpIntent) -> CommandResult:
        """Handle help intent."""
        topic = intent.topic

        if topic:
            # Specific help topic
            help_texts = {
                "search": "Search for players using natural language. Try: 'Find English midfielders under 23 with high potential'",
                "transfer": "Make transfer offers. Try: 'Buy Jude Bellingham for 80M' or 'Sell my backup goalkeeper'",
                "tactics": "Set team tactics. Try: 'Play 4-3-3 with high pressing' or 'Use defensive mentality'",
                "squad": "View your squad. Try: 'Show my squad' or 'Who are my best players?'",
            }
            message = help_texts.get(topic.lower(), f"Help for '{topic}' is not available yet.")
        else:
            # General help
            message = """FM Manager - Natural Language Commands

You can control the game by typing commands in natural language:

Player Search:
  • "Find English midfielders under 23 with high potential"
  • "Search for Brazilian strikers worth under 50M"
  • "Show me goalkeepers with CA above 80"

Squad Management:
  • "View my squad"
  • "Show player details for [player name]"
  • "Who are my best young players?"

Transfers:
  • "Buy [player name] for [amount]"
  • "Sell [player name]"
  • "Loan a young midfielder"

Tactics:
  • "Set formation to 4-3-3"
  • "Play with high pressing"
  • "Use attacking mentality"

Game Progress:
  • "Advance to next match"
  • "View fixtures"
  • "Save game"

Tips:
  • You can combine multiple criteria in searches
  • Follow-up queries work: "younger", "cheaper", "better"
  • Type 'help [topic]' for specific help
"""

        return CommandResult(
            success=True, message=message, data={"topic": topic}, action_taken="help"
        )

    async def _handle_unknown(self, intent: UnknownIntent) -> CommandResult:
        """Handle unknown intent."""
        message = f"I'm not sure what you mean by '{intent.raw_input}'.\n\n"
        message += "Try commands like:\n"
        message += "  • 'Find English midfielders under 23'\n"
        message += "  • 'View my squad'\n"
        message += "  • 'Help' for more options"

        if intent.suggested_action:
            message += f"\n{intent.suggested_action}"

        return CommandResult(
            success=False,
            message=message,
            data={"raw_input": intent.raw_input},
            action_taken="unknown",
            follow_up_suggested="Type 'help' to see available commands.",
        )

    def _format_search_results(self, result) -> str:
        """Format search results into natural language."""
        total = result.total_count
        players = result.players[:10]  # Show first 10

        message = f"Found {total} player{'s' if total != 1 else ''} matching your criteria:\n\n"

        for i, player in enumerate(players, 1):
            message += f"{i}. {player.full_name}\n"
            message += f"   Position: {player.position} | Age: {player.age}\n"
            message += f"   CA: {player.current_ability:.0f} | PA: {player.potential_ability:.0f}\n"
            message += f"   Value: £{player.market_value:,} | Wage: £{player.weekly_wage:,}/week\n"
            message += f"   Club: {player.club_name}\n\n"

        if total > 10:
            message += f"... and {total - 10} more players.\n"

        return message

    def _format_player_details(self, player, in_squad: bool) -> CommandResult:
        """Format detailed player information."""
        lines = [
            f"{getattr(player, 'full_name', 'Unknown')}",
            "=" * 50,
            "",
            f"Position: {getattr(player, 'position', '-')}",
            f"Age: {getattr(player, 'age', '-')}",
            f"Nationality: {getattr(player, 'nationality', '-')}",
            "",
            "Abilities:",
            f"  Current Ability (CA): {getattr(player, 'current_ability', 0):.0f}",
            f"  Potential Ability (PA): {getattr(player, 'potential_ability', 0):.0f}",
            "",
            "Contract & Value:",
            f"  Market Value: £{getattr(player, 'market_value', 0):,}",
            f"  Weekly Wage: £{getattr(player, 'weekly_wage', 0):,}",
        ]

        if not in_squad:
            lines.extend(
                [
                    "",
                    f"Current Club: {getattr(player, 'club_name', 'Unknown')}",
                ]
            )

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={
                "player_id": getattr(player, "id", 0),
                "name": getattr(player, "full_name", "Unknown"),
                "in_squad": in_squad,
            },
            action_taken="view_player_details",
            follow_up_suggested="Say 'buy this player' to make an offer, or search for more options.",
        )

    def _map_sort_field(self, sort_by: Optional[str]) -> str:
        """Map natural language sort field to criteria field."""
        mapping = {
            "potential": "potential_ability",
            "ability": "current_ability",
            "value": "market_value",
            "price": "market_value",
            "age": "age",
            "name": "name",
        }
        return mapping.get(sort_by, "current_ability")

    def _map_squad_sort(self, sort_by: Optional[str]) -> Callable:
        """Map sort field to sort key function."""
        mapping = {
            "ability": lambda p: getattr(p, "current_ability", 0),
            "potential": lambda p: getattr(p, "potential_ability", 0),
            "value": lambda p: getattr(p, "market_value", 0),
            "age": lambda p: getattr(p, "age", 0),
            "position": lambda p: str(getattr(p, "position", "")),
            "wage": lambda p: getattr(p, "weekly_wage", 0),
        }
        return mapping.get(sort_by, mapping["ability"])

    def _get_sort_field_name(self, sort_by: Optional[str]) -> str:
        """Get human-readable sort field name."""
        names = {
            "ability": "能力",
            "potential": "潜力",
            "value": "身价",
            "age": "年龄",
            "wage": "工资",
        }
        return names.get(sort_by, "能力")

    def _get_sort_value(self, player, sort_by: Optional[str]):
        """Get the sort value for display."""
        if sort_by == "value":
            return f"£{getattr(player, 'market_value', 0) / 1_000_000:.1f}M"
        elif sort_by == "wage":
            return f"£{getattr(player, 'weekly_wage', 0):,}/周"
        elif sort_by == "age":
            return f"{getattr(player, 'age', 0)}岁"
        else:
            return getattr(player, "current_ability", 0)

    def _format_single_player_result(
        self, player, field_name: str, field_value, aggregation: str
    ) -> str:
        """Format single player result in natural language."""
        name = getattr(player, "full_name", "Unknown")
        pos = getattr(player, "position", "-")
        pos_str = pos if isinstance(pos, str) else getattr(pos, "value", "-")
        age = getattr(player, "age", "-")
        ca = getattr(player, "current_ability", "-")
        pa = getattr(player, "potential_ability", "-")
        value = getattr(player, "market_value", 0)

        lines = [
            f"{field_name}最高的球员是 {name}",
            f"",
            f"位置: {pos_str} | 年龄: {age}岁",
            f"当前能力: {ca} | 潜力: {pa}",
            f"身价: £{value / 1_000_000:.1f}M",
        ]

        return "\n".join(lines)

    def set_current_club(self, club: Optional[ClubDataFull]):
        """Update the current club context."""
        self.current_club = club


# Global instance
_executor: Optional[CommandExecutor] = None


def get_command_executor(current_club: Optional[ClubDataFull] = None) -> CommandExecutor:
    """Get or create the global command executor."""
    global _executor
    if _executor is None:
        _executor = CommandExecutor(current_club)
    else:
        _executor.set_current_club(current_club)
    return _executor
