"""Natural Language Intent Parser for FM Manager.

Uses LLM with Function Calling to convert natural language commands into
structured game actions.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal
from enum import Enum

from pydantic import BaseModel, Field

from fm_manager.engine.llm_client import LLMClient, LLMProvider


class GameIntentType(str, Enum):
    """Types of game intents that can be parsed."""

    SEARCH_PLAYERS = "search_players"
    VIEW_SQUAD = "view_squad"
    VIEW_PLAYER_DETAILS = "view_player_details"
    SET_TACTICS = "set_tactics"
    MAKE_TRANSFER = "make_transfer"
    VIEW_FIXTURES = "view_fixtures"
    ADVANCE_MATCH = "advance_match"
    SAVE_GAME = "save_game"
    HELP = "help"
    UNKNOWN = "unknown"


class PlayerSearchIntent(BaseModel):
    """Intent to search for players."""

    intent_type: Literal["search_players"] = "search_players"
    nationality: Optional[str] = Field(
        None, description="Player nationality, e.g., 'England', 'Brazil'"
    )
    age_description: Optional[str] = Field(
        None, description="Age constraint, e.g., 'under 23', 'over 30', '25 years old'"
    )
    position: Optional[str] = Field(
        None, description="Position, e.g., 'midfielder', 'striker', 'CM'"
    )
    ability_level: Optional[str] = Field(
        None, description="Ability level, e.g., 'high', '80+', 'good'"
    )
    potential_level: Optional[str] = Field(
        None, description="Potential level, e.g., 'high', 'great potential', '85+'"
    )
    max_price: Optional[str] = Field(
        None, description="Maximum price, e.g., '50M', '50 million', '100k'"
    )
    sort_by: Optional[str] = Field(
        "potential", description="Sort by: 'potential', 'ability', 'value', 'age'"
    )
    limit: int = Field(10, description="Number of results to return")


class ViewSquadIntent(BaseModel):
    """Intent to view current squad."""

    intent_type: Literal["view_squad"] = "view_squad"
    sort_by: Optional[str] = Field(
        "ability", description="Sort by: 'ability', 'potential', 'value', 'position'"
    )
    filter_position: Optional[str] = Field(None, description="Filter by position")
    limit: Optional[int] = Field(None, description="Limit number of players returned (e.g., top 5)")
    aggregation: Optional[str] = Field(None, description="Aggregation type: 'max', 'min', 'top'")
    sort_field: Optional[str] = Field(
        None, description="Field to sort by: 'value', 'ability', 'potential', 'age', 'wage'"
    )


class ViewPlayerDetailsIntent(BaseModel):
    """Intent to view specific player details."""

    intent_type: Literal["view_player_details"] = "view_player_details"
    player_name: str = Field(..., description="Player name to search for")


class SetTacticsIntent(BaseModel):
    """Intent to set team tactics."""

    intent_type: Literal["set_tactics"] = "set_tactics"
    formation: Optional[str] = Field(None, description="Formation, e.g., '4-3-3', '4-4-2'")
    style: Optional[str] = Field(
        None, description="Playing style, e.g., 'possession', 'counter-attack', 'high-press'"
    )
    mentality: Optional[str] = Field(
        None, description="Mentality: 'attacking', 'balanced', 'defensive'"
    )


class MakeTransferIntent(BaseModel):
    """Intent to make a transfer offer."""

    intent_type: Literal["make_transfer"] = "make_transfer"
    player_name: str = Field(..., description="Player name to transfer")
    offer_amount: Optional[str] = Field(None, description="Offer amount, e.g., '50M', '30 million'")
    transfer_type: Optional[str] = Field("buy", description="Type: 'buy', 'loan', 'sell'")


class ViewFixturesIntent(BaseModel):
    """Intent to view fixtures."""

    intent_type: Literal["view_fixtures"] = "view_fixtures"
    view_type: Optional[str] = Field("upcoming", description="'upcoming', 'results', 'all'")


class AdvanceMatchIntent(BaseModel):
    """Intent to advance to next match."""

    intent_type: Literal["advance_match"] = "advance_match"
    confirm: bool = Field(True, description="Confirm advancement")


class SaveGameIntent(BaseModel):
    """Intent to save game."""

    intent_type: Literal["save_game"] = "save_game"
    save_name: Optional[str] = Field(None, description="Custom save name")


class HelpIntent(BaseModel):
    """Intent to get help."""

    intent_type: Literal["help"] = "help"
    topic: Optional[str] = Field(None, description="Specific help topic")


class UnknownIntent(BaseModel):
    """Intent that couldn't be parsed."""

    intent_type: Literal["unknown"] = "unknown"
    raw_input: str = Field(..., description="Original user input")
    suggested_action: Optional[str] = Field(None, description="Suggested alternative action")


# Union type for all possible intents
GameIntent = (
    PlayerSearchIntent
    | ViewSquadIntent
    | ViewPlayerDetailsIntent
    | SetTacticsIntent
    | MakeTransferIntent
    | ViewFixturesIntent
    | AdvanceMatchIntent
    | SaveGameIntent
    | HelpIntent
    | UnknownIntent
)


@dataclass
class ParsedIntent:
    """Parsed intent with metadata."""

    intent: GameIntent
    confidence: float = 1.0
    raw_input: str = ""
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        intent_dict = (
            self.intent.model_dump() if hasattr(self.intent, "model_dump") else vars(self.intent)
        )
        return {
            "intent_type": intent_dict.get("intent_type", "unknown"),
            "confidence": self.confidence,
            "raw_input": self.raw_input,
            "parameters": {
                k: v for k, v in intent_dict.items() if k != "intent_type" and v is not None
            },
        }


class NaturalLanguageIntentParser:
    """Parser for converting natural language to game intents."""

    # System prompt for intent parsing
    SYSTEM_PROMPT = """You are an AI assistant for a football management game (FM Manager).
Your job is to understand natural language commands from the user and convert them into structured game actions.

Available actions:
1. search_players - Search for players with specific criteria
2. view_squad - View the current team squad
3. view_player_details - View details of a specific player
4. set_tactics - Set team formation and playing style
5. make_transfer - Make a transfer offer for a player
6. view_fixtures - View upcoming matches or results
7. advance_match - Advance to the next match
8. save_game - Save the current game
9. help - Get help or instructions

Parse the user's input and extract all relevant parameters. Be intelligent about understanding:
- Position descriptions ("midfielder" should map to position parameter)
- Age constraints ("under 23" should set age_description)
- Ability levels ("high potential" should set potential_level)
- Price constraints ("under 50 million" should set max_price)

If the input doesn't match any known action, use the "unknown" intent type.
"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the parser.

        Args:
            llm_client: LLM client to use. If None, creates a mock client.
        """
        if llm_client is None:
            llm_client = LLMClient(provider=LLMProvider.MOCK)
        self.llm = llm_client

        # Track conversation context for follow-up queries
        self.conversation_history: List[Dict[str, Any]] = []
        self.last_intent: Optional[ParsedIntent] = None

    def parse(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> ParsedIntent:
        """
        Parse natural language input into a structured intent.

        Args:
            user_input: Natural language command from user
            context: Optional context (e.g., current club, game state)

        Returns:
            ParsedIntent with structured command

        Example:
            >>> parser.parse("Find English midfielders under 23 with high potential")
            ParsedIntent(intent=PlayerSearchIntent(
                intent_type="search_players",
                nationality="England",
                position="midfielder",
                age_description="under 23",
                potential_level="high"
            ))
        """
        import time

        start_time = time.time()

        # Check for follow-up queries
        if self._is_follow_up_query(user_input):
            intent = self._handle_follow_up(user_input)
        else:
            # Use LLM to parse the intent
            intent = self._parse_with_llm(user_input, context)

        processing_time = (time.time() - start_time) * 1000

        parsed = ParsedIntent(
            intent=intent,
            confidence=0.9 if intent.intent_type != "unknown" else 0.5,
            raw_input=user_input,
            processing_time_ms=processing_time,
        )

        # Store for potential follow-ups
        self.last_intent = parsed
        self.conversation_history.append(
            {
                "user": user_input,
                "intent": parsed.to_dict(),
            }
        )

        return parsed

    def _parse_with_llm(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> GameIntent:
        """
        Use LLM to parse the intent.

        For now, uses rule-based parsing as fallback since we don't have
        OpenAI function calling fully integrated.
        """
        # Try to use LLM if available
        if self.llm.provider != LLMProvider.MOCK:
            try:
                return self._parse_with_llm_function_calling(user_input, context)
            except Exception as e:
                print(f"LLM parsing failed: {e}, falling back to rule-based")

        # Fallback to rule-based parsing
        return self._rule_based_parse(user_input)

    def _parse_with_llm_function_calling(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> GameIntent:
        """Use LLM with structured prompting to parse intent."""

        # Build the system prompt
        system_prompt = """You are an AI assistant for a football management game (FM Manager).
Your job is to understand natural language commands and convert them into structured JSON.

Available intent types:
1. search_players - Search for players with specific criteria
2. view_squad - View the current team squad  
3. view_player_details - View details of a specific player
4. set_tactics - Set team formation and playing style
5. make_transfer - Make a transfer offer for a player
6. view_fixtures - View upcoming matches or results
7. advance_match - Advance to the next match
8. save_game - Save the current game
9. help - Get help or instructions
10. unknown - Command not understood

Respond with a JSON object containing:
- intent_type: The type of intent (from the list above)
- Parameters specific to that intent type

For search_players, extract:
- nationality: Player nationality (e.g., "England", "Brazil", "英格兰", "巴西")
- age_description: Age constraint (e.g., "under 23", "25岁以下")
- position: Position (e.g., "midfielder", "striker", "中场", "前锋")
- ability_level: Ability level (e.g., "high", "80+")
- potential_level: Potential level (e.g., "high", "great potential", "潜力高")
- max_price: Maximum price (e.g., "50M", "5000万")

Examples:
Input: "Find English midfielders under 23 with high potential"
Output: {"intent_type": "search_players", "nationality": "England", "position": "midfielder", "age_description": "under 23", "potential_level": "high"}

Input: "查看我的阵容"
Output: {"intent_type": "view_squad"}

Input: "保存游戏"
Output: {"intent_type": "save_game"}

Only respond with the JSON object, no other text."""

        # Build user prompt with context
        user_prompt = f"Input: {user_input}"
        if context:
            user_prompt += f"\nContext: Current club is {context.get('club', 'unknown')}"

        try:
            # Call LLM
            response = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.1,  # Low temperature for consistent parsing
            )

            # Parse JSON response
            content = response.content.strip()
            # Extract JSON if wrapped in markdown
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed = json.loads(content)

            # Convert parsed JSON to Intent object
            intent_type = parsed.get("intent_type", "unknown")

            if intent_type == "search_players":
                return PlayerSearchIntent(
                    intent_type="search_players",
                    nationality=parsed.get("nationality"),
                    age_description=parsed.get("age_description"),
                    position=parsed.get("position"),
                    ability_level=parsed.get("ability_level"),
                    potential_level=parsed.get("potential_level"),
                    max_price=parsed.get("max_price"),
                    sort_by=parsed.get("sort_by", "potential"),
                    limit=parsed.get("limit", 10),
                )
            elif intent_type == "view_squad":
                return ViewSquadIntent(
                    intent_type="view_squad",
                    sort_by=parsed.get("sort_by"),
                    filter_position=parsed.get("filter_position"),
                    limit=parsed.get("limit"),
                    aggregation=parsed.get("aggregation"),
                    sort_field=parsed.get("sort_field"),
                )
            elif intent_type == "view_player_details":
                return ViewPlayerDetailsIntent(
                    intent_type="view_player_details",
                    player_name=parsed.get("player_name", ""),
                )
            elif intent_type == "set_tactics":
                return SetTacticsIntent(
                    intent_type="set_tactics",
                    formation=parsed.get("formation"),
                    style=parsed.get("style"),
                    mentality=parsed.get("mentality"),
                )
            elif intent_type == "make_transfer":
                return MakeTransferIntent(
                    intent_type="make_transfer",
                    player_name=parsed.get("player_name", ""),
                    offer_amount=parsed.get("offer_amount"),
                    transfer_type=parsed.get("transfer_type", "buy"),
                )
            elif intent_type == "view_fixtures":
                return ViewFixturesIntent(
                    intent_type="view_fixtures",
                    view_type=parsed.get("view_type", "upcoming"),
                )
            elif intent_type == "advance_match":
                return AdvanceMatchIntent(
                    intent_type="advance_match",
                    confirm=parsed.get("confirm", True),
                )
            elif intent_type == "save_game":
                return SaveGameIntent(
                    intent_type="save_game",
                    save_name=parsed.get("save_name"),
                )
            elif intent_type == "help":
                return HelpIntent(
                    intent_type="help",
                    topic=parsed.get("topic"),
                )
            else:
                return UnknownIntent(
                    intent_type="unknown",
                    raw_input=user_input,
                    suggested_action=parsed.get("suggested_action"),
                )

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            return self._rule_based_parse(user_input)
        except Exception as e:
            print(f"LLM parsing error: {e}")
            return self._rule_based_parse(user_input)

    def _rule_based_parse(self, user_input: str) -> GameIntent:
        """
        Parse intent using rule-based matching.

        This is a robust fallback when LLM is not available.
        """
        user_lower = user_input.lower().strip()

        # Search players patterns
        search_patterns = [
            "find",
            "search",
            "look for",
            "show me",
            "get me",
            "find me",
            "search for",
            "i want",
            "i need",
            "找",
            "搜索",
            "查找",
            "给我找",
            "帮我找",
        ]

        # View squad patterns - check first for squad-related queries
        squad_patterns = [
            "squad",
            "team",
            "my players",
            "roster",
            "lineup",
            "阵容",
            "球队",
            "我的球员",
            "队员",
            "球员",
            "身价最高",
            "能力最强",
            "潜力最高",
            "最贵的",
            "最便宜的",
            "年龄最大",
            "年龄最小",
        ]
        if any(pattern in user_lower for pattern in squad_patterns):
            return self._parse_squad_intent(user_input)

        if any(pattern in user_lower for pattern in search_patterns):
            return self._parse_search_intent(user_input)

        # View player details patterns
        detail_patterns = [
            "details",
            "info",
            "information",
            "stats",
            "about",
            "详情",
            "信息",
            "资料",
            "数据",
        ]
        if any(pattern in user_lower for pattern in detail_patterns):
            # Try to extract player name
            player_name = self._extract_player_name(user_input)
            if player_name:
                return ViewPlayerDetailsIntent(
                    intent_type="view_player_details", player_name=player_name
                )

        # Tactics patterns
        tactic_patterns = [
            "tactics",
            "formation",
            "strategy",
            "play style",
            "战术",
            "阵型",
            "策略",
            "打法",
        ]
        if any(pattern in user_lower for pattern in tactic_patterns):
            return self._parse_tactics_intent(user_input)

        # Transfer patterns
        transfer_patterns = [
            "transfer",
            "buy",
            "sell",
            "loan",
            "sign",
            "offer",
            "转会",
            "购买",
            "出售",
            "租借",
            "签约",
            "报价",
        ]
        if any(pattern in user_lower for pattern in transfer_patterns):
            return self._parse_transfer_intent(user_input)

        # Fixtures patterns
        fixture_patterns = [
            "fixtures",
            "matches",
            "schedule",
            "games",
            "calendar",
            "比赛",
            "赛程",
            "日程",
            "赛事",
        ]
        if any(pattern in user_lower for pattern in fixture_patterns):
            return ViewFixturesIntent(intent_type="view_fixtures")

        # Advance patterns
        advance_patterns = [
            "advance",
            "next match",
            "continue",
            "proceed",
            "simulate",
            "推进",
            "下一场",
            "继续",
            "模拟",
        ]
        if any(pattern in user_lower for pattern in advance_patterns):
            return AdvanceMatchIntent(intent_type="advance_match")

        # Save patterns
        save_patterns = [
            "save",
            "save game",
            "保存",
            "存档",
        ]
        if any(pattern in user_lower for pattern in save_patterns):
            return SaveGameIntent(intent_type="save_game")

        # Help patterns
        help_patterns = ["help", "how to", "what can", "commands", "?"]
        if any(pattern in user_lower for pattern in help_patterns):
            return HelpIntent(intent_type="help")

        # Unknown intent
        return UnknownIntent(
            intent_type="unknown",
            raw_input=user_input,
            suggested_action="Try 'help' to see available commands",
        )

    def _parse_search_intent(self, user_input: str) -> PlayerSearchIntent:
        """Parse a player search intent."""
        user_lower = user_input.lower()

        # Initialize with defaults
        intent = PlayerSearchIntent(intent_type="search_players")

        # Extract nationality (common countries with Chinese support)
        nationality_mappings = {
            # English
            "england": "England",
            "english": "England",
            "british": "England",
            "brazil": "Brazil",
            "brazilian": "Brazil",
            "argentina": "Argentina",
            "argentinian": "Argentina",
            "spain": "Spain",
            "spanish": "Spain",
            "france": "France",
            "french": "France",
            "germany": "Germany",
            "german": "Germany",
            "italy": "Italy",
            "italian": "Italy",
            "portugal": "Portugal",
            "portuguese": "Portugal",
            "netherlands": "Netherlands",
            "dutch": "Netherlands",
            "belgium": "Belgium",
            "belgian": "Belgium",
            "croatia": "Croatia",
            "croatian": "Croatia",
            # Chinese
            "英格兰": "England",
            "英国": "England",
            "巴西": "Brazil",
            "阿根廷": "Argentina",
            "西班牙": "Spain",
            "法国": "France",
            "德国": "Germany",
            "意大利": "Italy",
            "葡萄牙": "Portugal",
            "荷兰": "Netherlands",
            "比利时": "Belgium",
            "克罗地亚": "Croatia",
        }
        for nat_key, nat_value in nationality_mappings.items():
            if nat_key in user_lower:
                intent.nationality = nat_value
                break

        age_patterns = [
            (
                r"between\s+(\d+)\s+(?:to|and)\s+(\d+)",
                lambda m: f"between {m.group(1)} to {m.group(2)}",
            ),
            (r"(\d+)\s*[-~]\s*(\d+)", lambda m: f"between {m.group(1)} to {m.group(2)}"),
            (r"(\d+)\s*到\s*(\d+)", lambda m: f"between {m.group(1)} to {m.group(2)}"),
            (r"under (\d+)", lambda m: f"under {m.group(1)}"),
            (r"below (\d+)", lambda m: f"under {m.group(1)}"),
            (r"younger than (\d+)", lambda m: f"under {m.group(1)}"),
            (r"over (\d+)", lambda m: f"over {m.group(1)}"),
            (r"above (\d+)", lambda m: f"over {m.group(1)}"),
            (r"older than (\d+)", lambda m: f"over {m.group(1)}"),
            (r"(\d+) years? old", lambda m: m.group(1)),
            (r"age (\d+)", lambda m: m.group(1)),
            (r"(\d+)岁", lambda m: m.group(1)),
            (r"(\d+)岁以下", lambda m: f"under {m.group(1)}"),
            (r"(\d+)岁以上", lambda m: f"over {m.group(1)}"),
            (r"小于(\d+)岁", lambda m: f"under {m.group(1)}"),
            (r"大于(\d+)岁", lambda m: f"over {m.group(1)}"),
        ]
        import re

        for pattern, extractor in age_patterns:
            match = re.search(pattern, user_lower)
            if match:
                intent.age_description = extractor(match)
                break

        # Extract position (English and Chinese)
        position_mappings = {
            # English
            "goalkeeper": "goalkeeper",
            "gk": "goalkeeper",
            "keeper": "goalkeeper",
            "defender": "defender",
            "center back": "center back",
            "centre back": "center back",
            "cb": "center back",
            "left back": "left back",
            "lb": "left back",
            "right back": "right back",
            "rb": "right back",
            "midfielder": "midfielder",
            "central midfielder": "central midfielder",
            "cm": "central midfielder",
            "defensive midfielder": "defensive midfielder",
            "dm": "defensive midfielder",
            "cdm": "defensive midfielder",
            "attacking midfielder": "attacking midfielder",
            "cam": "attacking midfielder",
            "winger": "winger",
            "left winger": "left winger",
            "lw": "left winger",
            "right winger": "right winger",
            "rw": "right winger",
            "striker": "striker",
            "forward": "striker",
            "st": "striker",
            "cf": "striker",
            "centre forward": "striker",
            # Chinese
            "门将": "goalkeeper",
            "守门员": "goalkeeper",
            "后卫": "defender",
            "中后卫": "center back",
            "中卫": "center back",
            "左后卫": "left back",
            "右后卫": "right back",
            "中场": "midfielder",
            "中前卫": "central midfielder",
            "后腰": "defensive midfielder",
            "前腰": "attacking midfielder",
            "进攻中场": "attacking midfielder",
            "边锋": "winger",
            "左边锋": "left winger",
            "右边锋": "right winger",
            "前锋": "striker",
            "中锋": "striker",
        }
        for pos_key, pos_value in position_mappings.items():
            if pos_key in user_lower:
                intent.position = pos_value
                break

        # Extract ability level
        ability_patterns = [
            (r"ability (\d+)", lambda m: m.group(1)),
            (r"ca (\d+)", lambda m: m.group(1)),
            (r"current ability (\d+)", lambda m: m.group(1)),
        ]
        for pattern, extractor in ability_patterns:
            match = re.search(pattern, user_lower)
            if match:
                intent.ability_level = extractor(match)
                break

        if not intent.ability_level:
            if any(
                word in user_lower for word in ["high ability", "good ability", "star", "quality"]
            ):
                intent.ability_level = "high"
            elif any(word in user_lower for word in ["decent", "average", "solid"]):
                intent.ability_level = "decent"

        # Extract potential level
        potential_patterns = [
            (r"potential (\d+)", lambda m: m.group(1)),
            (r"pa (\d+)", lambda m: m.group(1)),
            (r"potential (?:above|upper than|greater than|>) (\d+)", lambda m: m.group(1)),
            (r"pa (?:above|upper than|greater than|>) (\d+)", lambda m: m.group(1)),
            (r"潜力\s*(\d+)", lambda m: m.group(1)),
            (r"潜力(?:大于|高于|超过|above)\s*(\d+)", lambda m: m.group(1)),
        ]
        for pattern, extractor in potential_patterns:
            match = re.search(pattern, user_lower)
            if match:
                intent.potential_level = extractor(match)
                break

        if not intent.potential_level:
            if any(
                word in user_lower
                for word in [
                    "high potential",
                    "great potential",
                    "excellent potential",
                    "top potential",
                ]
            ):
                intent.potential_level = "high"
            elif any(word in user_lower for word in ["good potential", "decent potential"]):
                intent.potential_level = "good"

        # Extract price constraints
        price_patterns = [
            (r"under (\d+(?:\.\d+)?)\s*m", lambda m: f"{m.group(1)}M"),
            (r"under (\d+(?:\.\d+)?)\s*million", lambda m: f"{m.group(1)}M"),
            (r"less than (\d+(?:\.\d+)?)\s*m", lambda m: f"{m.group(1)}M"),
            (r"max (\d+(?:\.\d+)?)\s*m", lambda m: f"{m.group(1)}M"),
            (r"budget (\d+(?:\.\d+)?)\s*m", lambda m: f"{m.group(1)}M"),
        ]
        for pattern, extractor in price_patterns:
            match = re.search(pattern, user_lower)
            if match:
                intent.max_price = extractor(match)
                break

        return intent

    def _parse_tactics_intent(self, user_input: str) -> SetTacticsIntent:
        """Parse a tactics setting intent."""
        user_lower = user_input.lower()

        intent = SetTacticsIntent(intent_type="set_tactics")

        # Extract formation
        formation_patterns = [
            r"4-3-3",
            r"4-4-2",
            r"4-2-3-1",
            r"3-5-2",
            r"5-3-2",
            r"4-1-4-1",
            r"3-4-3",
            r"4-5-1",
        ]
        import re

        for pattern in formation_patterns:
            if re.search(pattern, user_lower):
                intent.formation = pattern
                break

        # Extract style
        styles = {
            "possession": ["possession", "tiki-taka", "tikka taka", "keep ball"],
            "counter-attack": ["counter", "counter-attack", "counter attack", "direct"],
            "high-press": ["high press", "pressing", "gegenpressing", "press"],
            "low-block": ["low block", "defensive", "park the bus"],
        }
        for style, keywords in styles.items():
            if any(kw in user_lower for kw in keywords):
                intent.style = style
                break

        # Extract mentality
        if any(word in user_lower for word in ["attacking", "attack", "offensive", "aggressive"]):
            intent.mentality = "attacking"
        elif any(word in user_lower for word in ["defensive", "defend", "defense", "cautious"]):
            intent.mentality = "defensive"
        elif any(word in user_lower for word in ["balanced", "normal", "standard"]):
            intent.mentality = "balanced"

        return intent

    def _parse_transfer_intent(self, user_input: str) -> MakeTransferIntent:
        """Parse a transfer intent."""
        user_lower = user_input.lower()

        # Extract player name (simplified - between "buy" and price or end)
        player_name = self._extract_player_name(user_input)

        intent = MakeTransferIntent(
            intent_type="make_transfer", player_name=player_name or "unknown"
        )

        # Extract offer amount
        price_patterns = [
            r"(\d+(?:\.\d+)?)\s*m",
            r"(\d+(?:\.\d+)?)\s*million",
            r"(\d+)k",
        ]
        import re

        for pattern in price_patterns:
            match = re.search(pattern, user_lower)
            if match:
                amount = match.group(1)
                if "k" in match.group(0).lower():
                    intent.offer_amount = f"{amount}k"
                else:
                    intent.offer_amount = f"{amount}M"
                break

        # Determine transfer type
        if any(word in user_lower for word in ["sell", "selling", "offload"]):
            intent.transfer_type = "sell"
        elif any(word in user_lower for word in ["loan", "borrow", "temporary"]):
            intent.transfer_type = "loan"
        else:
            intent.transfer_type = "buy"

        return intent

    def _parse_squad_intent(self, user_input: str) -> ViewSquadIntent:
        """Parse squad view intent with aggregation support."""
        import re

        user_lower = user_input.lower()

        # Initialize with defaults
        intent = ViewSquadIntent(intent_type="view_squad")

        # Extract limit (e.g., "top 5", "前3名", "前5个")
        limit_patterns = [
            (r"top\s*(\d+)", lambda m: int(m.group(1))),
            (r"前\s*(\d+)\s*个", lambda m: int(m.group(1))),
            (r"前\s*(\d+)\s*名", lambda m: int(m.group(1))),
        ]
        for pattern, extractor in limit_patterns:
            match = re.search(pattern, user_lower)
            if match:
                intent.limit = extractor(match)
                intent.aggregation = "top"
                break

        # Check for single result queries (highest/lowest/best)
        single_result_patterns = [
            (r"最高|最高.*是", "max"),
            (r"最低|最低.*是", "min"),
            (r"最贵|最贵.*是", "max"),
            (r"最便宜|最便宜.*是", "min"),
            (r"最强|最强.*是", "max"),
            (r"最好|最好.*是", "max"),
            (r"highest|most valuable", "max"),
            (r"lowest|cheapest", "min"),
            (r"best", "max"),
        ]
        for pattern, agg_type in single_result_patterns:
            if re.search(pattern, user_lower):
                intent.aggregation = agg_type
                if intent.limit is None:
                    intent.limit = 1
                break

        # Extract sort field
        field_patterns = [
            (r"身价|价值|value|valuable", "value"),
            (r"能力|实力|ability", "ability"),
            (r"潜力|potential", "potential"),
            (r"年龄|age", "age"),
            (r"工资|周薪|wage|salary", "wage"),
        ]
        for pattern, field in field_patterns:
            if re.search(pattern, user_lower):
                intent.sort_field = field
                break

        # If sort_field is set but not sort_by, use sort_field for sort_by
        if intent.sort_field:
            intent.sort_by = intent.sort_field

        return intent

    def _extract_player_name(self, user_input: str) -> Optional[str]:
        """Extract player name from input (simplified)."""
        # This is a simplified version - in production, use NER or fuzzy matching
        # Look for capitalized words that might be a name
        import re

        # Pattern: "details of Player Name" or "about Player Name"
        patterns = [
            r"(?:details?|info|about|stats?)\s+(?:of|for)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"(?:buy|sell|transfer)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(1)

        return None

    def _is_follow_up_query(self, user_input: str) -> bool:
        """Check if this is a follow-up to the previous query."""
        if not self.last_intent:
            return False

        follow_up_patterns = [
            "more",
            "another",
            "also",
            "and",
            "additionally",
            "younger",
            "older",
            "cheaper",
            "better",
            "worse",
            "instead",
            "rather",
            "how about",
            "what about",
            "还有",
            "另外",
            "再",
            "更",
            "怎么样",
        ]

        user_lower = user_input.lower()
        return any(pattern in user_lower for pattern in follow_up_patterns)

    def _handle_follow_up(self, user_input: str) -> GameIntent:
        """Handle a follow-up query by modifying the last intent."""
        if not self.last_intent:
            return UnknownIntent(intent_type="unknown", raw_input=user_input)

        last_intent = self.last_intent.intent
        user_lower = user_input.lower()

        # Only handle follow-ups for search intents
        if last_intent.intent_type != "search_players":
            return self._rule_based_parse(user_input)

        # Modify the search criteria based on follow-up
        import copy

        new_intent = copy.copy(last_intent)

        # Adjust age
        if any(word in user_lower for word in ["younger", "young"]):
            if new_intent.age_description:
                # Reduce age limit
                import re

                match = re.search(r"(\d+)", new_intent.age_description)
                if match:
                    current_age = int(match.group(1))
                    new_intent.age_description = f"under {current_age - 2}"
        elif any(word in user_lower for word in ["older", "old"]):
            if new_intent.age_description:
                import re

                match = re.search(r"(\d+)", new_intent.age_description)
                if match:
                    current_age = int(match.group(1))
                    new_intent.age_description = f"under {current_age + 2}"

        # Adjust price
        if any(word in user_lower for word in ["cheaper", "less", "lower"]):
            if new_intent.max_price:
                import re

                match = re.search(r"(\d+(?:\.\d+)?)", new_intent.max_price)
                if match:
                    current_price = float(match.group(1))
                    new_price = current_price * 0.8  # 20% cheaper
                    new_intent.max_price = f"{new_price:.1f}M"

        return new_intent

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.last_intent = None


# Global instance
_parser: Optional[NaturalLanguageIntentParser] = None


def get_intent_parser(
    llm_client: Optional[LLMClient] = None, force_new: bool = False
) -> NaturalLanguageIntentParser:
    """Get or create the global intent parser.

    Args:
        llm_client: LLM client to use. If None and force_new is True, creates parser without LLM.
        force_new: If True, create a new parser even if one exists (useful when switching LLM providers)
    """
    global _parser
    if _parser is None or force_new:
        _parser = NaturalLanguageIntentParser(llm_client)
    return _parser


def parse_intent(user_input: str, context: Optional[Dict[str, Any]] = None) -> ParsedIntent:
    """
    Convenience function to parse intent.

    Example:
        >>> result = parse_intent("Find English midfielders under 23 with high potential")
        >>> print(result.intent.intent_type)
        'search_players'
    """
    parser = get_intent_parser()
    return parser.parse(user_input, context)
