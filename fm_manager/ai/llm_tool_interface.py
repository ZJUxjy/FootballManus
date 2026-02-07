"""LLM Tool Calling Interface for FM Manager.

Replaces the old intent-based system with a flexible tool-calling architecture.
"""

import json
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from fm_manager.engine.llm_client import LLMClient, LLMProvider
from fm_manager.ai.tools.tool_registry import get_tool_registry
from fm_manager.ai.tools.tool_implementations import set_current_club, set_current_calendar
from fm_manager.data.cleaned_data_loader import ClubDataFull


@dataclass
class ToolCallResult:
    """Result of a tool call."""

    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    iteration: int = 1


@dataclass
class SearchAdjustment:
    original_params: Dict[str, Any]
    adjusted_params: Dict[str, Any]
    reason: str
    iteration: int


@dataclass
class LLMResponse:
    """Response from LLM with optional tool calls."""

    content: str
    tool_calls: List[ToolCallResult]
    raw_response: str


class LLMToolInterface:
    """Interface for LLM to call tools and generate responses."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize the LLM tool interface."""
        if llm_client is None:
            llm_client = LLMClient(provider=LLMProvider.MOCK)
        self.llm = llm_client
        self.tool_registry = get_tool_registry()
        self.current_club: Optional[ClubDataFull] = None

    def set_club(self, club: Optional[ClubDataFull]):
        """Set the current club context."""
        self.current_club = club
        set_current_club(club)

    def set_calendar(self, calendar):
        """Set the current calendar context."""
        set_current_calendar(calendar)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions."""
        tools_desc = self.tool_registry.to_prompt_description()

        club_info = ""
        if self.current_club:
            club_info = f"""
Current Club: {self.current_club.name}
League: {self.current_club.league}
Reputation: {self.current_club.reputation}
"""

        return f"""You are an AI assistant for FM Manager (Football Manager game).

Your role is to help the user manage their football team by providing information and analysis.

{tools_desc}

{club_info}

When responding to user queries:
1. Analyze what information the user needs
2. Call the appropriate tool(s) to get the data
3. Provide a helpful, natural response based on the tool results

You can call tools by including a JSON block in your response like this:
```tool
{{"tool": "tool_name", "parameters": {{"param1": "value1", "param2": "value2"}}}}
```

You can call multiple tools if needed. The system will execute them and provide you with the results.

Guidelines:
- Always respond in the same language as the user's query
- Be concise but informative
- If the user asks for a list, provide a formatted list
- If the user asks for a specific player, provide detailed info
- If the user asks for analysis, provide insights based on the data
- If you need more information, ask clarifying questions

Examples:

User: "Who is the most valuable player in my team?"
Your response should:
1. Call get_squad with sort_by="value" and limit=1
2. Respond with the player's details

User: "Find me young English goalkeepers with high potential"
Your response should:
1. Call search_players with nationality="England", position="GK", max_age=23, min_potential=80
2. Present the results in a helpful format
"""

    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response."""
        tool_calls = []

        # Look for ```tool blocks
        import re

        pattern = r"```tool\s*\n(.*?)\n```"
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue

        return tool_calls

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCallResult]:
        """Execute tool calls and return results."""
        results = []

        for call in tool_calls:
            tool_name = call.get("tool")
            if not tool_name:
                continue
            parameters = call.get("parameters", {})

            try:
                result = self.tool_registry.execute(tool_name, parameters)
                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        parameters=parameters,
                        result=result,
                        success=True,
                    )
                )
            except Exception as e:
                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        parameters=parameters,
                        result=None,
                        success=False,
                        error=str(e),
                    )
                )

        return results

    def _build_follow_up_prompt(
        self, original_query: str, tool_results: List[ToolCallResult]
    ) -> str:
        """Build a follow-up prompt with tool results."""
        lines = [
            f"Original user query: {original_query}",
            "",
            "Tool execution results:",
        ]

        for result in tool_results:
            lines.append(f"\nTool: {result.tool_name}")
            lines.append(f"Parameters: {json.dumps(result.parameters, ensure_ascii=False)}")
            if result.success:
                lines.append(f"Result: {json.dumps(result.result, ensure_ascii=False, indent=2)}")
            else:
                lines.append(f"Error: {result.error}")

        lines.append("\nBased on these results, provide a helpful response to the user.")
        lines.append("Respond in the same language as the original query.")

        return "\n".join(lines)

    def _is_empty_search_result(self, result: Any) -> bool:
        """Check if search result is empty and needs adjustment."""
        if isinstance(result, dict):
            # Check for empty player list or zero results
            if "players" in result and len(result["players"]) == 0:
                return True
            if "total" in result and result["total"] == 0:
                return True
            if "total_players" in result and result["total_players"] == 0:
                return True
        elif isinstance(result, list) and len(result) == 0:
            return True
        return False

    def _adjust_search_params(
        self, params: Dict[str, Any], iteration: int
    ) -> Tuple[Dict[str, Any], str]:
        """Adjust search parameters for next iteration."""
        adjusted = params.copy()
        adjustments = []

        # Gradually relax constraints
        if "min_potential" in adjusted and iteration == 1:
            old_val = adjusted["min_potential"]
            adjusted["min_potential"] = max(70, old_val - 10)
            adjustments.append(f"降低潜力要求从 {old_val} 到 {adjusted['min_potential']}")

        elif "min_potential" in adjusted and iteration == 2:
            old_val = adjusted["min_potential"]
            adjusted["min_potential"] = max(60, old_val - 10)
            adjustments.append(f"进一步降低潜力要求从 {old_val} 到 {adjusted['min_potential']}")

        elif "max_age" in adjusted and iteration <= 2:
            old_val = adjusted["max_age"]
            adjusted["max_age"] = old_val + 2
            adjustments.append(f"放宽年龄限制从 {old_val} 到 {adjusted['max_age']}")

        elif "max_price" in adjusted and iteration <= 2:
            old_val = adjusted["max_price"]
            adjusted["max_price"] = int(old_val * 1.2)
            adjustments.append(f"提高预算上限从 £{old_val:,} 到 £{adjusted['max_price']:,}")

        if not adjustments:
            adjustments.append("放宽所有搜索条件")
            # Remove restrictive filters
            for key in ["min_potential", "min_ability"]:
                if key in adjusted:
                    del adjusted[key]

        return adjusted, "; ".join(adjustments)

    def _build_iterative_search_prompt(
        self,
        user_query: str,
        all_results: List[ToolCallResult],
        adjustments: List[SearchAdjustment],
    ) -> str:
        """Build prompt for iterative search with all attempts."""
        lines = [
            f"Original user query: {user_query}",
            "",
            "Search history:",
        ]

        for i, (result, adj) in enumerate(zip(all_results, adjustments)):
            lines.append(f"\nAttempt {i + 1}:")
            lines.append(f"  Parameters: {json.dumps(adj.original_params, ensure_ascii=False)}")
            lines.append(f"  Adjustment: {adj.reason}")
            lines.append(
                f"  Results: {len(result.result.get('players', [])) if isinstance(result.result, dict) else 'N/A'} players found"
            )

        lines.append("\n" + "=" * 50)
        lines.append("\nFinal results to present to user:")
        if all_results:
            final_result = all_results[-1].result
            if isinstance(final_result, dict) and "players" in final_result:
                lines.append(f"Found {len(final_result['players'])} players")
            else:
                lines.append(json.dumps(final_result, ensure_ascii=False, indent=2)[:500])

        lines.append("\nProvide a helpful response summarizing the search results.")
        lines.append("If multiple attempts were made, briefly mention the adjustments.")
        lines.append("Respond in the same language as the original query.")

        return "\n".join(lines)

    async def process_query(self, user_query: str, max_iterations: int = 3) -> str:
        """
        Process a user query using tool calling with multi-step search support.

        Args:
            user_query: The user's natural language query
            max_iterations: Maximum number of search attempts (default: 3)

        Returns:
            A helpful response based on tool execution
        """
        system_prompt = self._build_system_prompt()

        # First LLM call - decide which tools to call
        response1 = self.llm.generate(
            prompt=user_query,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        content1 = response1.content

        # Extract tool calls
        tool_calls = self._extract_tool_calls(content1)

        if not tool_calls:
            # No tool calls, return the LLM response directly
            return content1

        # Execute tool calls
        tool_results = self._execute_tool_calls(tool_calls)

        # Check if any search results are empty and need iterative adjustment
        all_results = list(tool_results)
        adjustments = []
        iteration = 1

        for result in tool_results:
            if result.tool_name == "search_players" and self._is_empty_search_result(result.result):
                # Iteratively adjust search params until we find results or hit max iterations
                current_params = result.parameters.copy()

                while iteration < max_iterations and self._is_empty_search_result(result.result):
                    # Adjust parameters
                    adjusted_params, reason = self._adjust_search_params(current_params, iteration)

                    adjustments.append(
                        SearchAdjustment(
                            original_params=current_params.copy(),
                            adjusted_params=adjusted_params.copy(),
                            reason=reason,
                            iteration=iteration,
                        )
                    )

                    # Execute new search
                    try:
                        new_result = self.tool_registry.execute("search_players", adjusted_params)
                        all_results.append(
                            ToolCallResult(
                                tool_name="search_players",
                                parameters=adjusted_params,
                                result=new_result,
                                success=True,
                                iteration=iteration + 1,
                            )
                        )
                        result = all_results[-1]
                        current_params = adjusted_params
                        iteration += 1
                    except Exception as e:
                        break

        # Build final prompt with all search history
        if adjustments:
            final_prompt = self._build_iterative_search_prompt(user_query, all_results, adjustments)
        else:
            final_prompt = self._build_follow_up_prompt(user_query, all_results)

        final_system_prompt = (
            system_prompt
            + """

IMPORTANT: Based on the tool results provided above, generate a natural language response to the user.
DO NOT output any tool call blocks (```tool). 
DO NOT make additional tool calls.
Simply provide a helpful, conversational response summarizing the results."""
        )

        response2 = self.llm.generate(
            prompt=final_prompt,
            system_prompt=final_system_prompt,
            max_tokens=1500,
            temperature=0.5,
        )

        content2 = response2.content
        if "```tool" in content2:
            additional_calls = self._extract_tool_calls(content2)
            if additional_calls:
                additional_results = self._execute_tool_calls(additional_calls)
                all_results.extend(additional_results)
                final_prompt = self._build_follow_up_prompt(user_query, all_results)
                response2 = self.llm.generate(
                    prompt=final_prompt,
                    system_prompt=final_system_prompt,
                    max_tokens=1500,
                    temperature=0.5,
                )
                content2 = response2.content

        return content2

    def process_query_sync(self, user_query: str) -> str:
        """Synchronous version of process_query."""
        import asyncio

        return asyncio.run(self.process_query(user_query))


# Global instance
_interface: Optional[LLMToolInterface] = None


def get_llm_tool_interface(llm_client: Optional[LLMClient] = None) -> LLMToolInterface:
    """Get or create the global LLM tool interface."""
    global _interface
    if _interface is None:
        _interface = LLMToolInterface(llm_client)
    return _interface
