"""Tool registry and definitions for FM Manager AI.

Provides a flexible tool-calling architecture where LLM can decide
which tools to use and how to combine them.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
from enum import Enum
import json


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called by LLM."""

    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM consumption."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description,
                        **({"enum": p.enum} if p.enum else {}),
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required],
            },
        }


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self.tools.values())

    def to_prompt_description(self) -> str:
        """Generate tool description for LLM prompt."""
        lines = ["Available tools:"]
        for tool in self.tools.values():
            lines.append(f"\n{tool.name}:")
            lines.append(f"  Description: {tool.description}")
            lines.append(f"  Parameters:")
            for param in tool.parameters:
                req = " (required)" if param.required else ""
                default = f" (default: {param.default})" if param.default is not None else ""
                lines.append(
                    f"    - {param.name} ({param.type}){req}{default}: {param.description}"
                )
        return "\n".join(lines)

    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters."""
        tool = self.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Fill in default values for missing optional parameters
        for param in tool.parameters:
            if param.name not in parameters and param.default is not None:
                parameters[param.name] = param.default

        return tool.handler(**parameters)


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(
    name: str,
    description: str,
    parameters: List[ToolParameter],
    handler: Callable,
):
    """Decorator to register a tool."""
    registry = get_tool_registry()
    tool = ToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
        handler=handler,
    )
    registry.register(tool)
    return handler
