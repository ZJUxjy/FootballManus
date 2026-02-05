"""LLM Tool Calling Interface for FM Manager.

Replaces the old intent-based system with a flexible tool-calling architecture.
"""

import json
from typing import Optional, Dict, Any, List
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

    async def process_query(self, user_query: str) -> str:
        """
        Process a user query using tool calling.

        Args:
            user_query: The user's natural language query

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

        # Build follow-up prompt with results
        follow_up_prompt = self._build_follow_up_prompt(user_query, tool_results)

        # Second LLM call - generate final response based on tool results
        response2 = self.llm.generate(
            prompt=follow_up_prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.5,
        )

        return response2.content

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
