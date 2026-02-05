"""Demo of the new tool-calling architecture.

This shows how the new architecture handles queries flexibly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fm_manager.ai.tools.tool_implementations import (
    set_current_club,
    get_squad_tool,
    search_players_tool,
)
from fm_manager.ai.tools.tool_registry import get_tool_registry
from fm_manager.data.cleaned_data_loader import load_for_match_engine


def demo_tool_calling():
    """Demonstrate the tool calling architecture."""
    print("=" * 80)
    print("Tool Calling Architecture Demo")
    print("=" * 80)

    # Load data
    clubs, players = load_for_match_engine()

    # Find a club with players
    for club in clubs.values():
        if len(getattr(club, "players", [])) > 10:
            print(f"\nClub: {club.name}")
            print(f"Players: {len(club.players)}")
            break

    set_current_club(club)

    # Demo 1: Get squad sorted by value
    print("\n" + "-" * 80)
    print("Query: '球队阵容从最高身价到最低身价列出来'")
    print("-" * 80)
    print("Tool call: get_squad(sort_by='value', limit=10)")
    print()

    result = get_squad_tool(sort_by="value", limit=10)
    print(f"Total squad value: £{result['total_value']:,}")
    print(f"\nTop 10 players by value:")
    for i, p in enumerate(result["players"], 1):
        print(f"{i:2d}. {p['name']:<25} {p['position']:<6} £{p['market_value']:>10,}")

    # Demo 2: Search for specific players
    print("\n" + "-" * 80)
    print("Query: 'Find English GK age 18-22 with PA > 85'")
    print("-" * 80)
    print(
        "Tool call: search_players(nationality='England', position='GK', min_age=18, max_age=22, min_potential=85)"
    )
    print()

    result = search_players_tool(
        nationality="England",
        position="GK",
        min_age=18,
        max_age=22,
        min_potential=85,
        sort_by="potential",
        limit=5,
    )

    print(f"Found {result['total_found']} players:")
    for p in result["players"]:
        print(f"  • {p['name']} ({p['position']}, {p['age']}yo, PA: {p['potential_ability']})")

    # Demo 3: Flexible analysis
    print("\n" + "-" * 80)
    print("Query: 'Who are the best young prospects in my team?'")
    print("-" * 80)
    print("Tool call: get_squad(sort_by='potential', limit=5) + filter age < 21")
    print()

    result = get_squad_tool(sort_by="potential", limit=10)
    young_players = [p for p in result["players"] if p["age"] < 21][:5]

    print("Top 5 young prospects (under 21):")
    for i, p in enumerate(young_players, 1):
        print(
            f"{i}. {p['name']:<25} Age: {p['age']:>2} | PA: {p['potential_ability']:>5.1f} | Value: £{p['market_value']:>10,}"
        )

    print("\n" + "=" * 80)
    print("Key Benefits of Tool Calling Architecture:")
    print("=" * 80)
    print("""
1. FLEXIBILITY: LLM decides which tools to call and how to combine them
   - No need to pre-define every query pattern
   - Can handle complex, multi-step queries

2. EXTENSIBILITY: Easy to add new tools
   - Just register a new tool function
   - LLM automatically learns to use it

3. NATURAL RESPONSES: LLM generates human-like replies
   - Not constrained by fixed templates
   - Can provide analysis and insights

4. MULTI-LANGUAGE: Works in any language
   - LLM understands context in user's language
   - Generates responses in the same language

Example flow:
  User: "球队阵容从最高身价到最低身价列出来"
  LLM:  Call get_squad(sort_by='value') 
  LLM:  Generate natural response with the data
  
  User: "Find me a cheap backup goalkeeper"
  LLM:  Call search_players(position='GK', max_price=1000000, sort_by='value')
  LLM:  Suggest best options based on ability/price ratio
""")


if __name__ == "__main__":
    demo_tool_calling()
